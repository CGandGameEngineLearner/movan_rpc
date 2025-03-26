import asyncio
import json
import time

import inspect
from typing import Dict, Any, Callable, Optional, List, Union,Tuple
import uuid
import utils

class RPCClient:
    def __init__(self, address: str, port: int):
        self.host: str = address
        self.port: int = port
        self.methods: Dict[str, Callable] = {}
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self._return_buffer: Dict[(float,str), Dict[str, Any]] = {}
        self._running_task = None
        self._loop = None

        self._return_buffer_lock = asyncio.Lock()
        self._call_buffer:Dict[Tuple[float,str],Any] = {}
        self._call_buffer_lock = asyncio.Lock()


    def register_method(self, name: str, method: Callable):
        if self.methods.get(name):
            raise Exception(f"方法 {name} 已经注册")
        self.methods[name] = method



    def server_method_stub(self, func: Callable):
        def sync_wrapper(*args, **kwargs):
            # 非异步函数的处理
            result = self.call_sync(func.__name__, *args, **kwargs)
            return result
        
        async def async_wrapper(*args, **kwargs):
            # 异步函数的处理
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
    
    async def handle_call_buffer(self):
        async with self._call_buffer_lock:
            for (timestamp,id), result in self._call_buffer.items():
                response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'result': result}
                await self._send_message(response)
            self._call_buffer.clear()
            

    async def _compute_result(self,timestamp:float,id:str,result):
        result = await result
        async with self._call_buffer_lock:
            self._call_buffer[(timestamp,id)] = result

    async def connect(self):
        """连接到服务器"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.connected = True
            print(f"已连接到服务器 {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"连接服务器失败: {e}")
            return False

    async def _read_loop(self):
        """读取服务器消息的循环"""
        try:
            while self.connected:
                # 读取长度头部（4字节整数）
                length_bytes = await self.reader.readexactly(4)
                length = int.from_bytes(length_bytes, byteorder='big')
                
                # 读取实际数据
                data = await self.reader.readexactly(length)
                await self._handle_data(data)
                
        except asyncio.IncompleteReadError:
            # 连接关闭
            self.connected = False
            print("连接已关闭")
        except Exception as e:
            print(f"读取数据错误: {e}")
            self.connected = False

    async def _handle_data(self, data: bytes):
        try:
            msg = json.loads(data.decode('utf-8'))
            
            if not utils.verify_msg(msg):
                raise Exception('消息格式错误')
        except Exception as e:
            print(f"解析数据时出错:{e}")
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
                    await self._send_message(error_response)
                    return
                    
                # 处理同步和异步方法
                result = method(*args, **kwargs)

                # 异步方法异步执行完后才发送返回消息
                if asyncio.iscoroutine(result):
                    asyncio.create_task(self._compute_result(timestamp,id,result))
                    return
                    
                response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'result': result}
                await self._send_message(response)
            except Exception as e:
                error_response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'error': str(e)}
                await self._send_message(error_response)
        elif msg_type == 'return':
            try:
                timestamp: float = msg.get('timestamp')
                id:str = msg.get('id')
                if timestamp is None:
                    return
                error = msg.get('error')
                if error:
                    with self._return_buffer_lock:
                        self._return_buffer[(timestamp,id)] = {'error': error}
                    return
                result = msg.get('result')
                with self._return_buffer_lock:
                    self._return_buffer[(timestamp,id)] = {'result': result}
            except Exception as e:
                print(f"处理返回错误: {e}")
                return
        else:
            return

    async def _send_message(self, message: Dict):
        """发送消息到服务器"""
        if not self.connected or not self.writer:
            raise Exception("未连接到服务器")
            
        try:
            # 将消息转换为JSON并添加长度头部
            data = json.dumps(message).encode('utf-8')
            length = len(data)
            length_bytes = length.to_bytes(4, byteorder='big')
            
            # 发送数据
            self.writer.write(length_bytes + data)
            await self.writer.drain()
        except Exception as e:
            print(f"发送消息失败: {e}")
            self.connected = False
            raise e

    async def call(self, method: str, params: List = None, kwargs: Dict = None, timeout: float = 5.0) -> Any:
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
            
        timestamp: float = time.time()
        id = str(uuid.uuid4())
        msg = {
            'type': 'call',
            'timestamp': timestamp,
            'method': method,
            'args': params,
            'kwargs': kwargs,
            'id':id
        }
        
        self._send_message(msg)
        
        # 等待响应
        wait_step = 0.01  # 每次等待的时间（秒）
        steps = int(timeout / wait_step)
        
        for _ in range(steps):
            with self._return_buffer_lock:
                if (timestamp,id) in self._return_buffer.keys():
                    result_data = self._return_buffer[(timestamp,id)]
                    del self._return_buffer[(timestamp,id)]
                    
                    # 检查是否有错误
                    if 'error' in result_data:
                        raise Exception(f"远程调用错误: {result_data['error']}")
                    
                    # 返回结果
                    return result_data.get('result')
            
            await asyncio.sleep(wait_step)
        
        raise TimeoutError(f"调用方法 {method} 超时（{timeout}秒）")

    def call_sync(self, method: str, params: List = None, kwargs: Dict = None, timeout: float = 5.0) -> Any:
        """
        同步调用远程方法（在已存在的事件循环内使用）
        
        参数:
            method: 要调用的方法名
            params: 位置参数列表 
            kwargs: 关键字参数字典
            timeout: 超时时间（秒）
            
        返回:
            方法的返回值，如果出现错误则抛出异常
        """
        if self._loop is None:
            raise RuntimeError("客户端未启动，无法使用同步调用")

        # 在现有事件循环中执行异步调用
        future = asyncio.run_coroutine_threadsafe(
            self.call(method, params, kwargs, timeout),
            self._loop
        )
        return future.result()  # 这会阻塞直到结果返回
        
    def blocking_call(self, method: str, params: List = None, kwargs: Dict = None, timeout: float = 5.0) -> Any:
        """
        阻塞式调用远程方法（创建新的事件循环）
        
        当在没有事件循环的线程中使用时，此方法会创建一个临时事件循环
        
        参数同call_sync
        """
        # 创建新的事件循环来执行此调用
        return asyncio.run(self._blocking_call_helper(method, params, kwargs, timeout))
        
    async def _blocking_call_helper(self, method: str, params: List = None, kwargs: Dict = None, timeout: float = 5.0) -> Any:
        """帮助函数，用于阻塞调用"""
        # 如果未连接，先连接
        if not self.connected:
            if not await self.connect():
                raise ConnectionError("无法连接到服务器")
                
        # 执行调用
        return await self.call(method, params, kwargs, timeout)

    async def start_async(self):
        """异步启动客户端"""
        if not await self.connect():
            return False
            
        # 保存当前事件循环
        self._loop = asyncio.get_running_loop()
            
        # 启动读取循环
        self._running_task = asyncio.create_task(self._read_loop())
        
        # 触发启动回调
        await self.on_connect()
        return True
        
    async def on_connect(self):
        """连接成功后的回调（可以重写）"""
        print('连接已建立')
        # 示例: 调用远程方法
        try:
            result = await self.call('test_server_add', [1, 2])
            print(f"远程调用结果: {result}")
        except Exception as e:
            print(f"示例调用失败: {e}")

    def start(self):
        """同步启动客户端（阻塞）"""
        asyncio.run(self.run())
        
    async def run(self):
        """运行客户端主循环"""
        if await self.start_async():
            # 保持客户端运行
            try:
                while self.connected:
                    await asyncio.sleep(0.01)
            except KeyboardInterrupt:
                print("客户端正在关闭...")
            finally:
                await self.close()
                
    async def close(self):
        """关闭连接"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
        if self._running_task:
            self._running_task.cancel()

if __name__ == "__main__":
    client = RPCClient('127.0.0.1', 9999)
    
    @client.method
    def test_client_subtraction(a, b):
        return a - b
    
    # 启动客户端（阻塞调用）
    client.start()