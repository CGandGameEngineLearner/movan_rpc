import json
import time
import socket
import threading
import inspect
import queue
import select
from typing import Dict, Any, Callable, Optional, List, Union, Tuple
import uuid
from . import utils

CallId = Tuple[str,str]

class RPCClientThreading:
    def __init__(self, address: str, port: int):
        self.host: str = address
        self.port: int = port
        self.methods: Dict[str, Callable] = {}
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
        self._read_thread = None
        self._keep_running = False

        self._return_buffer: Dict[CallId, Dict[str, Any]] = {}
        self._callback_buffer: Dict[CallId, Callable] = {}
        self.return_buffer_lock = threading.Lock()
        self._socket_lock = threading.Lock()
        self._last_heartbeat_time = time.time()


    def register_method(self, name: str, method: Callable):
        if self.methods.get(name):
            raise Exception(f"方法 {name} 已经注册")
        self.methods[name] = method


    def server_method_stub(self, func: Callable):
        def wrapper(*args, **kwargs):
            # 同步函数的处理
            result = self.call(func.__name__, args, kwargs)
            return result
        
        return wrapper
    
    # 装饰器注册方法
    def method(self, func: Callable):
        self.register_method(func.__name__, func)
        return func
    

    def connect(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"已连接到服务器 {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"连接服务器失败: {e}")
            return False

    def _read_loop(self):
        """读取服务器消息的循环"""        

        try:
            while self._keep_running and self.connected:
                try:
                    timestamp = time.time()
                    if self._last_heartbeat_time + 1 < timestamp:
                        self._send_message({'type': 'heartbeat', 'timestamp': str(timestamp),"id":str(uuid.uuid4())})
                        self._last_heartbeat_time = timestamp
                    # 使用 select 函数检查是否有可读数据
                    ready = select.select([self.socket], [], [], 0.5)
                    if ready[0]:
                        # 读取长度头部（4字节整数）
                        length_bytes = self.socket.recv(4)
                        if not length_bytes:
                            # 连接关闭
                            self.connected = False
                            break
                            
                        length = int.from_bytes(length_bytes, byteorder='big')
                        
                        # 读取实际数据
                        data = b''
                        while len(data) < length:
                            chunk = self.socket.recv(min(4096, length - len(data)))
                            if not chunk:
                                # 连接关闭
                                self.connected = False
                                break
                            data += chunk
                            
                        if data:
                            self._handle_data(data)
                except socket.error as e:
                    print(f"连接错误: {e}")
                    self.connected = False
                    break
                except Exception as e:
                    print(f"读取数据错误: {e}")
                    if not self.connected:  # 避免重复报错
                        break
                    time.sleep(0.1)  # 短暂暂停避免CPU占用过高
            
        except Exception as e:
            print(f"读取循环发生未处理异常: {e}")
        finally:
            self.connected = False
            print("读取循环结束")
            
            if self._keep_running:
                # 尝试重连
                time.sleep(1)
                self.start_sync()

    def _handle_data(self, data: bytes):
        try:
            msg: dict = json.loads(data.decode('utf-8'))
            print(msg)
            
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
                timestamp: str = msg.get('timestamp')
                id: str = msg.get('id')
                error = msg.get('error')
                if error:
                    with self.return_buffer_lock:
                        self._return_buffer[(timestamp, id)] = {'error': error}
                    return
                result = msg.get('result')
                with self.return_buffer_lock:
                    self._return_buffer[(timestamp, id)] = {'result': result}
            except Exception as e:
                print(f"处理返回错误: {e}")
                return
        else:
            return

    def _send_message(self, message: Dict):
        """发送消息到服务器"""
        if not self.connected or not self.socket:
            raise Exception("未连接到服务器")
            
        try:
            # 将消息转换为JSON并添加长度头部
            data = json.dumps(message).encode('utf-8')
            length = len(data)
            length_bytes = length.to_bytes(4, byteorder='big')
            
            # 发送数据需要加锁以防止多线程同时写入
            with self._socket_lock:
                self.socket.sendall(length_bytes + data)
        except Exception as e:
            print(f"发送消息失败: {e}")
            self.connected = False
            raise e
        
    def unbind_call_back(self, call_id: CallId):
        """解除回调绑定"""
        if not call_id:
            return
        with self.return_buffer_lock:
            self._callback_buffer.pop(call_id, None)



    def call(self, method: str, call_back:Callable = None, params: List = None, kwargs: Dict = None) -> CallId:
        """
        同步调用客户端方法
        
        参数:
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
            'id': id
        }
        self._callback_buffer[(timestamp, id)] = call_back
        self._send_message(msg)
        return (timestamp,id)

    
    def on_tick(self):
        with self.return_buffer_lock:
            if len(self._return_buffer) > 0:
                for (timestamp, id) in self._return_buffer.keys():
                    result_data = self._return_buffer[(timestamp, id)]
                    print(result_data)
                    
                    # 检查是否有错误
                    if 'error' in result_data:
                        print(result_data['error'])
                    
                    # 返回结果
                    result = result_data.get('result')
                    call_back = self._callback_buffer.get((timestamp, id))
                    if call_back:
                        call_back(result)
                        # try:
                        #     call_back(result)
                        # except Exception as e:
                        #     print(f"call back error: {e}")
                        self._callback_buffer.pop((timestamp, id), None)
                self._return_buffer.clear()
                
        
        

    def start_sync(self):
        """同步启动客户端"""
        if not self.connect():
            return False
            
        # 启动读取线程
        self._keep_running = True
        self._read_thread = threading.Thread(target=self._read_loop)
        self._read_thread.daemon = True
        self._read_thread.start()
        
        # 触发启动回调
        self.on_connect()
        return True
        
    def on_connect(self):
        """连接成功后的回调（可以重写）"""
        print('连接已建立')
        # 示例: 调用远程方法
        try:
            result = self.call('init_connect')
            # print(f"远程调用结果: {result}")
        except Exception as e:
            print(f"示例调用失败: {e}")

    def run(self):
        """同步启动客户端（阻塞）"""
        self.start()
        

                
    def close(self):
        """关闭连接"""
        self.connected = False
        self._keep_running = False
        
        # 等待读取线程结束
        if self._read_thread and self._read_thread.is_alive():
            try:
                self._read_thread.join(timeout=1.0)
            except Exception as e:
                print(f"等待读取线程结束时出现错误: {e}")
                
        # 关闭socket
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"关闭socket时出现错误: {e}")