import asyncio
import json
import time
import inspect
from typing import Dict, Any, Callable, Optional, List
import uuid
from . import utils


class RPCClient:
    def __init__(self, address: str, port: int):
        self.host: str = address
        self.port: int = port
        self.methods: Dict[str, Callable] = {}
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        
        self._running_task = None
        self._loop = None

        self._return_buffer: Dict[(str,str), Dict[str, Any]] = {}
        self._return_buffer_lock = asyncio.Lock()



    def register_method(self, name: str, method: Callable):
        if self.methods.get(name):
            raise Exception(f"方法 {name} 已经注册")
        self.methods[name] = method



    def server_method_stub(self, func: Callable):
        async def wrapper(*args, **kwargs):
            # 异步函数的处理
            result = await self.call(func.__name__, args, kwargs)
            return result
        
        # 判断是否为异步函数
        if inspect.iscoroutinefunction(func):
            return wrapper
        else:
            raise SyntaxError("服务端方法的存根函数必须使用async def定义")
    
    # 装饰器注册方法
    def method(self, func: Callable):
        self.register_method(func.__name__, func)
        return func
    

            



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
                try:
                    # 读取长度头部（4字节整数）
                    length_bytes = await self.reader.readexactly(4)
                    length = int.from_bytes(length_bytes, byteorder='big')
                    
                    # 读取实际数据
                    data = await self.reader.readexactly(length)
                    await self._handle_data(data)
                except asyncio.IncompleteReadError:
                    # 连接关闭或被中断
                    print("服务器连接已断开")
                    self.connected = False
                    break
                except ConnectionResetError as e:
                    print(f"连接被重置: {e}")
                    self.connected = False
                    break
                except Exception as e:
                    print(f"读取数据错误: {e}")
                    if not self.connected:  # 避免重复报错
                        break
                    await asyncio.sleep(0.5)  # 短暂暂停避免CPU占用过高
            
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            print("读取循环任务已取消")
        except Exception as e:
            print(f"读取循环发生未处理异常: {e}")
        finally:
            self.connected = False
            print("读取循环结束")

    async def _handle_data(self, data: bytes):
        try:
            msg:dict = json.loads(data.decode('utf-8'))
            
            if not utils.verify_msg(msg):
                raise Exception('消息格式错误')
        except Exception as e:
            print(f"解析数据时出错:{e}")
            return
        
        msg_type = msg.get('type')

        # print("客户端消息")
        # print(msg)
        
        
        if msg_type == 'return':
            try:
                timestamp: float = msg.get('timestamp')
                id:str = msg.get('id')
                error = msg.get('error')
                if error:
                    async with self._return_buffer_lock:
                        self._return_buffer[(timestamp,id)] = {'error': error}
                    return
                result = msg.get('result')
                async with self._return_buffer_lock:
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
            # print("客户端发送数据")
            # print(data)
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
        
        await self._send_message(msg)
        
        # 等待响应
        wait_step = 0.1  # 每次等待的时间（秒）
        steps = int(timeout / wait_step)
        
        for _ in range(steps):
            async with self._return_buffer_lock:
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
            result = await self.call('init_connect')
            print(f"远程调用结果: {result}")
        except Exception as e:
            print(f"示例调用失败: {e}")

    def run(self):
        """同步启动客户端（阻塞）"""
        asyncio.run(self.start())
        
    async def start(self):
        """运行客户端主循环"""
        try:
            if await self.start_async():
                # 保持客户端运行
                try:
                    reconnect_attempts = 0
                    max_reconnect_attempts = 3
                    
                    while self.connected or reconnect_attempts < max_reconnect_attempts:
                        if not self.connected:
                            reconnect_attempts += 1
                            print(f"尝试重新连接 ({reconnect_attempts}/{max_reconnect_attempts})...")
                            if await self.start_async():
                                reconnect_attempts = 0  # 重置重连计数
                            else:
                                await asyncio.sleep(2)  # 重连间隔
                        else:
                            reconnect_attempts = 0  # 连接正常时重置重连计数
                            await asyncio.sleep(0.1)  # 减少CPU占用
                            
                except KeyboardInterrupt:
                    print("客户端正在关闭...")
        except Exception as e:
            print(f"客户端运行出错: {e}")
        finally:
            await self.close()
            print("客户端已关闭")
                
    async def close(self):
        """关闭连接"""
        self.connected = False
        

        # 取消读取循环任务
        if self._running_task:
            try:
                self._running_task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(self._running_task), 0.5)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass  # 预期的结果
            except Exception as e:
                print(f"取消读取任务时出现错误: {e}")
                
        # 关闭写入器
        if self.writer:
            try:
                self.writer.close()
                try:
                    # 添加超时以避免在连接已断开时无限等待
                    await asyncio.wait_for(self.writer.wait_closed(), 2.0)
                except asyncio.TimeoutError:
                    print("等待连接关闭超时")
                except ConnectionResetError:
                    print("连接已被远程端重置")
                except Exception as e:
                    print(f"关闭连接时出现错误: {e}")
            except Exception as e:
                print(f"关闭写入器时出现错误: {e}")

