import asyncio
import json
import time
import inspect
import uuid
from typing import Dict, Any, Callable, Tuple, Optional, List, Union
import utils


# 定义地址类型
AddressType = Tuple[str, int]

class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.address_tuple = writer.get_extra_info('peername')
        
        
    async def send(self, data: bytes) -> None:
        self.writer.write(data)
        await self.writer.drain()
        
class RPCServer:
    def __init__(self, address: str, port: int):
        self.host = address
        self.port = port
        self.methods: Dict[str, Callable] = {}
        self.connections: Dict[AddressType, Connection] = {}
        self.return_buffer: Dict[Tuple[str,str], Any] = {}
        self.server = None
        self._loop = None
        self._started = False
        self._return_buffer_lock = asyncio.Lock()
        self._call_buffer:Dict[Tuple[str,str,Connection],Any] = {}
        self._call_buffer_lock = asyncio.Lock()
        
        self.register_method("init_connect",self._init_connect)

    def _init_connect(self):
        return True

    def register_method(self, name: str, method: Callable):
        if self.methods.get(name):
            raise Exception(f"方法 {name} 已经注册")
        self.methods[name] = method

    def client_method_stub(self, func: Callable):
        def sync_wrapper(*args, **kwargs):
            # 非异步函数的处理
            if not isinstance(args[0], AddressType):
                raise Exception("第一个参数必须是AddressType类型的IP地址")
            result = self.call_sync(func.__name__, *args, **kwargs)
            return result
        
        async def async_wrapper(*args, **kwargs):
            # 异步函数的处理
            if not isinstance(args[0], AddressType):
                raise Exception("第一个参数必须是AddressType类型的IP地址")
            result = await self.call(func.__name__, *args, **kwargs)
            return result
        
        # 判断是否为异步函数
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    # 装饰器注册方法
    def method(self, func: Callable):
        self.register_method(func.__name__, func)
        return func
        
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        connection = Connection(reader, writer)
        addr = connection.address_tuple
        self.connections[addr] = connection
        print(f"连接建立：{addr}")
        
        try:
            while True:
                # 读取长度头部（4字节整数）
                length_bytes = await reader.readexactly(4)
                length = int.from_bytes(length_bytes, byteorder='big')
                
                # 读取实际数据
                data = await reader.readexactly(length)
                await self.on_data(connection, data)
                await self.handle_call_buffer()

                
                
        except asyncio.IncompleteReadError:
            # 连接关闭
            pass
        except Exception as e:
            print(f"处理连接异常: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            if addr in self.connections:
                del self.connections[addr]
            print(f"连接关闭：{addr}")

    async def handle_call_buffer(self):
        async with self._call_buffer_lock:
            for (timestamp,id,connection), result in self._call_buffer.items():
                response = {'type': 'return', 'timestamp': timestamp, 'id':id,'result': result}
                await self.send_response(connection, response)
            self._call_buffer.clear()
            

    async def _compute_result(self,timestamp:float,id:str,connection:Connection,result):
        result = await result
        async with self._call_buffer_lock:
            self._call_buffer[(timestamp,id,connection)] = result
    
    async def on_data(self, connection: Connection, data: bytes) -> None:
        try:
            msg = json.loads(data.decode('utf-8'))
            
            if not utils.verify_msg(msg):
                raise Exception('消息格式错误')
        except Exception as e:
            error_response = {'error': str(e)}
            await self.send_response(connection,error_response)
            return
        
        msg_type = msg.get('type')
        
        if msg_type == 'call':
            try:
                timestamp = msg.get('timestamp')
                id:str = msg.get('id')
                method_name = msg.get('method')
                args = msg.get('args', [])
                kwargs = msg.get('kwargs', {})
                method = self.methods.get(method_name)
                if not method:
                    error_response = {'type': 'return', 'timestamp': timestamp, 'id': id,'error': f"方法 {method_name} 未找到"}
                    await self.send_response(connection, error_response)
                    return
                    
                # 处理同步和异步方法
                result = method(*args, **kwargs)

                # 异步方法异步执行完后才发送返回消息
                if asyncio.iscoroutine(result):
                    msg['connection'] = connection 
                    asyncio.create_task(self._compute_result(timestamp,id,connection,result))
                    return
                    
                response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'result': result}
                await self.send_response(connection, response)
            except Exception as e:
                error_response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'error': str(e)}
                await self.send_response(connection, error_response)
        elif msg_type == 'return':
            try:
                timestamp: float = msg.get('timestamp')
                id:str = msg.get('id')
                if timestamp is None:
                    return
                error = msg.get('error')
                if error:
                    async with self._return_buffer_lock:
                        self.return_buffer[(timestamp,id)] = {'error': error}
                    return
                result = msg.get('result')
                async with self._return_buffer_lock:
                    self.return_buffer[(timestamp,id)] = {'result': result}
            except Exception as e:
                print(f"处理返回错误: {e}")
                return
        else:
            return
    
    async def send_response(self, connection: Connection, response: Dict):
        # 将响应转换为JSON并发送
        json_data = json.dumps(response).encode('utf-8')
        length = len(json_data)
        length_bytes = length.to_bytes(4, byteorder='big')
        
        # 发送长度头部和数据
        await connection.send(length_bytes + json_data)
    
    def call_sync(self, client_address: AddressType, method: str, params: List = None, kwargs: Dict = None, timeout: float = 5.0) -> Any:
        """
        同步调用客户端方法（在非asyncio上下文中使用）
        """
        if not self._started:
            raise RuntimeError("服务器尚未启动，无法调用")
            
        # 创建一个Future来存储结果
        future = asyncio.create_task(
            self.call(client_address, method, params, kwargs, timeout)
        )
        
        # 等待结果返回
        return future.result()
    
    async def call(self, client_address: AddressType, method: str, params: List = None, kwargs: Dict = None, timeout: float = 5.0) -> Any:
        """
        异步调用客户端方法
        
        参数:
            client_address: 客户端地址元组 (ip, port)
            method: 要调用的方法名
            params: 位置参数列表
            kwargs: 关键字参数字典
            timeout: 超时时间（秒）
            
        返回:
            方法的返回值，如果出现错误则抛出异常
        """
        if params is None:
            params = []
        if kwargs is None:
            kwargs = {}
            
        timestamp: str = str(time.time())
        id = str(uuid.uuid4())
        msg = {
            'type': 'call',
            'timestamp': timestamp,
            'method': method,
            'args': params,
            'kwargs': kwargs,
            'id':id
        }
        
        # 获取连接并发送数据
        connection = self.connections.get(client_address)
        if not connection:
            raise Exception(f"没有到 {client_address} 的连接")
            
        await self.send_response(connection, msg)
        
        # 等待响应
        wait_step = 0.1  # 每次等待的时间（秒）
        steps = int(timeout / wait_step)
        
        for _ in range(steps):
            async with self._return_buffer_lock:
                if (timestamp,id) in self.return_buffer.keys():
                    result_data = self.return_buffer[(timestamp,id)]
                    del self.return_buffer[(timestamp,id)]
                    
                    # 检查是否有错误
                    if 'error' in result_data:
                        raise Exception(f"远程调用错误: {result_data['error']}")
                    
                    # 返回结果
                    return result_data.get('result')
            
            await asyncio.sleep(wait_step)
        
        raise TimeoutError(f"调用方法 {method} 超时（{timeout}秒）")
    
    async def start(self):
        """启动服务器（异步）"""
        if self._started:
            return
            
        self._loop = asyncio.get_running_loop()
        self._started = True
        
        self.server = await asyncio.start_server(
            self.handle_connection, 
            self.host, 
            self.port
        )
        
        addr = self.server.sockets[0].getsockname()
        print(f'服务器启动在 {addr}')
        
        async with self.server:
            await self.server.serve_forever()
    
    def run(self):
        """运行服务器（阻塞）"""
        asyncio.run(self.start())

