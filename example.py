import asyncio
import time
from server import RPCServer
from client import RPCClient
import threading
import random

#==============================================================================
# 服务器端部分
#==============================================================================

class MyRPCServer(RPCServer):
    """自定义RPC服务器示例"""
    
    def __init__(self, address, port):
        super().__init__(address, port)
        # 存储客户端连接信息，用于演示服务器调用客户端
        self.client_addresses = []
        
        # 注册服务器方法
        self.register_server_methods()
        
    async def handle_connection(self, reader, writer):
        """重写连接处理方法，保存客户端地址"""
        addr = writer.get_extra_info('peername')
        if addr not in self.client_addresses:
            self.client_addresses.append(addr)
            print(f"新客户端连接: {addr}")
        await super().handle_connection(reader, writer)
        
    def register_server_methods(self):
        """注册服务器方法"""
        # 注册异步方法
        self.register_method("async_add", self.async_add)
        # 注册同步方法
        self.register_method("sync_multiply", self.sync_multiply)
        self.register_method("get_time", self.get_time)
        self.register_method("get_random_number", self.get_random_number)
        
        # 使用装饰器注册方法
        self.register_method("decorated_add", self.decorated_add)
        self.register_method("decorated_async_process", self.decorated_async_process)
    
    # 异步方法示例
    async def async_add(self, a, b):
        """异步方法示例 - 加法"""
        print(f"服务器异步执行: {a} + {b}")
        await asyncio.sleep(0.5)  # 模拟异步操作
        return a + b
    
    # 同步方法示例
    def sync_multiply(self, a, b):
        """同步方法示例 - 乘法"""
        print(f"服务器同步执行: {a} * {b}")
        return a * b
    
    def get_time(self):
        """返回当前时间"""
        return time.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_random_number(self, min_val=1, max_val=100):
        """返回随机数，演示默认参数"""
        return random.randint(min_val, max_val)
    
    # 使用装饰器的方法示例
    def decorated_add(self, a, b):
        """使用装饰器注册的同步方法"""
        print(f"服务器装饰器方法执行: {a} + {b}")
        return a + b
    
    async def decorated_async_process(self, data):
        """使用装饰器注册的异步方法"""
        print(f"服务器装饰器异步方法执行: {data}")
        await asyncio.sleep(0.3)
        return f"服务器已处理: {data}"
    
    # 使用 client_method_stub 装饰器的方法示例
    def call_client_decorated_method(self, client_addr, a, b):
        """使用装饰器调用客户端方法"""
        print(f"服务器调用客户端装饰器方法: {a} - {b}")
        return self.call_sync(client_addr, 'decorated_subtract', [a, b])
    
    async def call_client_decorated_async_method(self, client_addr, data):
        """使用装饰器异步调用客户端方法"""
        print(f"服务器调用客户端装饰器异步方法: {data}")
        return await self.call(client_addr, 'decorated_async_process', [data])
    
    # 调用客户端方法示例
    async def call_client_methods(self):
        """调用所有已连接客户端的方法"""
        print("\n===服务器调用客户端方法===")
        await asyncio.sleep(1)  # 等待客户端连接完成
        
        for client_addr in self.client_addresses:
            try:
                # 异步调用客户端方法
                print(f"调用客户端 {client_addr} 的减法方法")
                result = await self.call(client_addr, 'subtract', [10, 3])
                print(f"客户端减法结果: 10 - 3 = {result}")
                
                # 调用自定义方法（如果存在）
                try:
                    result = await self.call(client_addr, 'get_client_info')
                    print(f"客户端信息: {result}")
                except Exception as e:
                    print(f"调用get_client_info失败: {e}")
                
                # 使用装饰器调用客户端方法
                print(f"\n使用装饰器调用客户端 {client_addr} 的方法:")
                result = await self.call_client_decorated_async_method(client_addr, "测试数据")
                print(f"客户端装饰器异步方法结果: {result}")
                
                result = self.call_client_decorated_method(client_addr, 15, 6)
                print(f"客户端装饰器同步方法结果: 15 - 6 = {result}")
                
            except Exception as e:
                print(f"调用客户端方法失败: {e}")

def run_server():
    """运行服务器"""
    server = MyRPCServer('127.0.0.1', 9999)
    
    # 启动服务器并定期调用客户端方法
    async def run_and_call_clients():
        # 创建任务定期调用客户端方法
        call_task = asyncio.create_task(call_clients_periodically(server))
        # 启动服务器
        await server.start()
        
    async def call_clients_periodically(server):
        """定期调用所有客户端方法"""
        while True:
            if server.client_addresses:
                await server.call_client_methods()
            await asyncio.sleep(5)  # 每5秒调用一次
    
    # 启动服务器
    print("服务器开始运行...")
    asyncio.run(run_and_call_clients())

#==============================================================================
# 客户端部分
#==============================================================================

class MyRPCClient(RPCClient):
    """自定义RPC客户端示例"""
    
    def __init__(self, address, port, client_id="未命名客户端"):
        super().__init__(address, port)
        self.client_id = client_id
        
        # 注册客户端方法
        self.register_client_methods()
    
    def register_client_methods(self):
        """注册客户端方法"""
        self.register_method("subtract", self.subtract)
        self.register_method("async_process", self.async_process)
        self.register_method("get_client_info", self.get_client_info)
        
        # 使用装饰器注册方法
        self.register_method("decorated_subtract", self.decorated_subtract)
        self.register_method("decorated_async_process", self.decorated_async_process)
    
    # 同步方法示例
    def subtract(self, a, b):
        """减法示例 - 被服务器调用"""
        print(f"客户端[{self.client_id}]执行: {a} - {b}")
        return a - b
    
    # 异步方法示例
    async def async_process(self, data):
        """异步处理数据示例"""
        print(f"客户端[{self.client_id}]异步处理数据: {data}")
        await asyncio.sleep(0.3)  # 模拟异步操作
        return f"已处理: {data}"
    
    def get_client_info(self):
        """返回客户端信息"""
        return {
            "id": self.client_id,
            "time": time.strftime("%H:%M:%S"),
            "status": "在线"
        }
        
    # 使用装饰器的方法示例
    def decorated_subtract(self, a, b):
        """使用装饰器注册的同步方法"""
        print(f"客户端[{self.client_id}]装饰器方法执行: {a} - {b}")
        return a - b
    
    async def decorated_async_process(self, data):
        """使用装饰器注册的异步方法"""
        print(f"客户端[{self.client_id}]装饰器异步方法执行: {data}")
        await asyncio.sleep(0.3)
        return f"客户端已处理: {data}"
    
    # 使用 server_method_stub 装饰器的方法示例
    def call_server_decorated_method(self, a, b):
        """使用装饰器调用服务器方法"""
        print(f"客户端调用服务器装饰器方法: {a} + {b}")
        return self.call_sync('decorated_add', [a, b])
    
    async def call_server_decorated_async_method(self, data):
        """使用装饰器异步调用服务器方法"""
        print(f"客户端调用服务器装饰器异步方法: {data}")
        return await self.call('decorated_async_process', [data])
    
    async def run_demo(self):
        """运行演示"""
        print(f"\n===客户端[{self.client_id}]开始运行===")
        
        try:
            # 连接服务器
            if not await self.connect():
                print("连接服务器失败")
                return
            
            # 启动读取循环
            read_task = asyncio.create_task(self._read_loop())
            
            try:
                # 调用服务器同步方法
                print("\n调用服务器同步方法:")
                result = await self.call('sync_multiply', [4, 7])
                print(f"sync_multiply(4, 7) = {result}")
                
                # 调用服务器异步方法
                print("\n调用服务器异步方法:")
                result = await self.call('async_add', [5, 3])
                print(f"async_add(5, 3) = {result}")
                
                # 带关键字参数的调用
                print("\n带关键字参数的调用:")
                result = await self.call('get_random_number', [], {'min_val': 50, 'max_val': 100})
                print(f"随机数(50-100): {result}")
                
                # 获取服务器时间
                result = await self.call('get_time')
                print(f"服务器时间: {result}")
                
                # 使用装饰器调用服务器方法
                print("\n使用装饰器调用服务器方法:")
                result = await self.call('decorated_async_process', ["测试数据"])
                print(f"服务器装饰器异步方法结果: {result}")
                
                result = await self.call('decorated_add', [8, 9])
                print(f"服务器装饰器同步方法结果: 8 + 9 = {result}")
                
                # 演示错误处理
                try:
                    print("\n调用不存在的方法(演示错误处理):")
                    result = await self.call('non_existent_method')
                    print(f"结果(不应该显示): {result}")
                except Exception as e:
                    print(f"预期的错误: {e}")
                
                # 保持客户端运行，等待服务器调用
                print("\n客户端保持运行中，等待服务器调用...")
                await asyncio.sleep(60)  # 运行60秒后退出
                
            finally:
                # 关闭连接
                read_task.cancel()
                await self.close()
                
        except Exception as e:
            print(f"客户端运行错误: {e}")

# 运行同步客户端（阻塞）
def run_sync_client():
    """运行同步客户端示例"""
    print("\n===运行同步客户端===")
    client = MyRPCClient('127.0.0.1', 9999, "同步客户端")
    
    # 阻塞调用示例
    try:
        time.sleep(0.5)  # 等待服务器启动
        result = client.blocking_call('sync_multiply', [8, 9])
        print(f"同步调用结果: 8 * 9 = {result}")
        
        # 获取当前服务器时间
        result = client.blocking_call('get_time')
        print(f"服务器时间: {result}")
        
        # 保持客户端运行一段时间
        client.start()
    except Exception as e:
        print(f"同步客户端错误: {e}")

# 运行异步客户端
async def run_async_client():
    """运行异步客户端示例"""
    # 等待服务器启动
    await asyncio.sleep(1.5)
    
    client = MyRPCClient('127.0.0.1', 9999, "异步客户端")
    await client.run_demo()

#==============================================================================
# 主函数
#==============================================================================

if __name__ == "__main__":
    # 在后台线程中运行服务器
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 在另一个线程中运行同步客户端
    sync_client_thread = threading.Thread(target=run_sync_client)
    sync_client_thread.daemon = True
    sync_client_thread.start()
    
    # 在主线程中运行异步客户端
    asyncio.run(run_async_client()) 