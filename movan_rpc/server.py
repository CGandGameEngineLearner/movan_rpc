import asyncio
import json
from typing import Dict, Any, Callable, Tuple
from . import utils


# 定义地址类型
AddressType = Tuple[str, int]

class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.address_tuple = writer.get_extra_info('peername')
        
        
    async def send(self, data: bytes) -> None:
        # print(data)
        self.writer.write(data)
        await self.writer.drain()
        
class RPCServer:
    def __init__(self, address: str, port: int):
        self.host = address
        self.port = port
        self.methods: Dict[str, Callable] = {}
        self.connections: Dict[AddressType, Connection] = {}
       
        self.server = None
        self._loop = None
        self._started = False
        
        self._call_buffer:Dict[Tuple[str,str,Connection],Any] = {}
        self._call_buffer_lock = asyncio.Lock()
        
        # 新增任务管理相关属性
        self._tasks = set()
        self._max_tasks = 1000  # 最大并发任务数
        self._task_semaphore = asyncio.Semaphore(self._max_tasks)
        
        self.register_method("init_connect",self._init_connect)

    def _init_connect(self):
        return True

    def register_method(self, name: str, method: Callable):
        if self.methods.get(name):
            raise Exception(f"方法 {name} 已经注册")
        self.methods[name] = method



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
                length_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=30.0)  # 添加超时
                length = int.from_bytes(length_bytes, byteorder='big')
                
                # 读取实际数据
                data = await asyncio.wait_for(reader.readexactly(length), timeout=30.0)  # 添加超时
                await self.on_data(connection, data)
                

                
        except asyncio.IncompleteReadError:
            # 连接关闭
            print(f"连接 {addr} 被客户端关闭")
        except ConnectionResetError as e:
            print(f"连接 {addr} 被重置: {e}")
        except Exception as e:
            print(f"处理连接 {addr} 异常: {e}")
        finally:
            try:
                writer.close()
                try:
                    # 使用超时避免无限等待
                    await asyncio.wait_for(writer.wait_closed(), timeout=5.0)
                except asyncio.TimeoutError:
                    print(f"等待连接 {addr} 关闭超时")
                except Exception as e:
                    print(f"关闭连接 {addr} 时出错: {e}")
            except Exception as e:
                print(f"关闭写入器时出错 {addr}: {e}")
                
            # 从连接列表中移除
            if addr in self.connections:
                del self.connections[addr]
            print(f"连接关闭：{addr}")

    async def handle_call_buffer(self):
        """处理调用缓冲区中的结果"""
        while self._started:
            try:
                async with self._call_buffer_lock:
                    if not self._call_buffer:
                        await asyncio.sleep(0.1)  # 增加sleep时间
                        continue
                        
                    # 批量处理结果
                    tasks = []
                    for (timestamp,id,connection), result in self._call_buffer.items():
                        response = {'type': 'return', 'timestamp': timestamp, 'id':id,'result': result}
                        tasks.append(self.send_response(connection, response))
                    
                    # 并行发送响应
                    await asyncio.gather(*tasks)
                    self._call_buffer.clear()
                    
            except Exception as e:
                print(f"处理调用缓冲区时出错: {e}")
                await asyncio.sleep(0.1)

    async def _create_task(self, coro):
        """创建受管理的任务"""
        async with self._task_semaphore:
            if len(self._tasks) >= self._max_tasks:
                raise Exception("达到最大并发任务数限制")
                
            task = asyncio.create_task(coro)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return task

    async def _compute_result(self, timestamp:float, id:str, connection:Connection, result):
        """计算异步结果并存储到缓冲区"""
        try:
            result = await asyncio.wait_for(result, timeout=30.0)
            async with self._call_buffer_lock:
                self._call_buffer[(timestamp, id, connection)] = result
        except asyncio.TimeoutError:
            async with self._call_buffer_lock:
                self._call_buffer[(timestamp, id, connection)] = {"error": "方法执行超时"}
        except Exception as e:
            async with self._call_buffer_lock:
                self._call_buffer[(timestamp, id, connection)] = {"error": str(e)}
    
    async def on_data(self, connection: Connection, data: bytes) -> None:
        """处理接收到的数据"""
        try:
            msg = json.loads(data.decode('utf-8'))
            # print(msg)
            if not utils.verify_msg(msg):
                raise Exception('消息格式错误')
                
            msg_type = msg.get('type')

            # print(msg)
            
            if msg_type == 'call':
                timestamp = msg.get('timestamp')
                id:str = msg.get('id')
                method_name = msg.get('method')
                args = msg.get('args', [])
                kwargs = msg.get('kwargs', {})
                method = self.methods.get(method_name)
                
                if not method:
                    error_response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'error': f"方法 {method_name} 未找到"}
                    await self.send_response(connection, error_response)
                    return
                    
                try:
                    # 处理同步和异步方法
                    result = method(*args, **kwargs)
                    
                    if asyncio.iscoroutine(result):                                                                                                                                                                                       
                        # 使用任务管理创建异步任务
                        await self._create_task(self._compute_result(timestamp, id, connection, result))
                    else:
                        response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'result': result}
                        await self.send_response(connection, response)
                        
                except Exception as e:
                    error_response = {'type': 'return', 'timestamp': timestamp, 'id': id, 'error': str(e)}
                    await self.send_response(connection, error_response)
            else:
                return
                
        except Exception as e:
            error_response = {'error': str(e)}
            await self.send_response(connection, error_response)
    
    async def send_response(self, connection: Connection, response: Dict):
        # 将响应转换为JSON并发送
        json_data = json.dumps(response).encode('utf-8')
        length = len(json_data)
        length_bytes = length.to_bytes(4, byteorder='big')
        
        # 发送长度头部和数据
        await connection.send(length_bytes + json_data)
    
    
    
    async def start(self):
        """启动服务器（异步）"""
        if self._started:
            return
        
        try:    
            self._loop = asyncio.get_running_loop()
            self._started = True
            
            self.server = await asyncio.start_server(
                self.handle_connection, 
                self.host, 
                self.port,
            )
            
            addr = self.server.sockets[0].getsockname()
            print(f'服务器启动在 {addr}')

            # 启动异步任务 返回客户端的调用结果
            buffer_task = asyncio.create_task(self.handle_call_buffer())
            self._tasks.add(buffer_task)
            buffer_task.add_done_callback(self._tasks.discard)
            
            async with self.server:
                await self.server.serve_forever()
        except Exception as e:
            self._started = False
            print(f"启动服务器时出错: {e}")
            raise
            
    async def shutdown(self):
        """优雅地关闭服务器"""
        print("正在关闭服务器...")
        if not self._started:
            return
            
        # 关闭服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        # 取消所有未完成的任务
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"取消任务时出错: {e}")
            
        # 关闭所有客户端连接
        close_tasks = []
        for addr, conn in list(self.connections.items()):
            try:
                conn.writer.close()
                close_tasks.append(conn.writer.wait_closed())
            except Exception as e:
                print(f"关闭连接 {addr} 时出错: {e}")
                
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
            
        self._started = False
        print("服务器已关闭")
    
    def run(self):
        """运行服务器（阻塞）"""
        asyncio.run(self.start())

