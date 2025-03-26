# Movan RPC

一个简单的RPC（远程过程调用）框架，使用Python标准库实现，无需第三方依赖。支持同步和异步方法调用，
以及服务器端到客户端的反向调用。

本项目原本只是Movan Server项目的RPC模块，现在剥离出来做成一个独立的库，方便其他项目使用。

## 特性

- 基于Python标准库`asyncio`和`json`模块
- 支持同步和异步方法定义与调用
- 支持双向RPC调用（客户端可以调用服务器方法，服务器也可以调用客户端方法）
- 简洁的装饰器API
- 完善的错误处理和超时机制
- 支持位置参数和关键字参数
- 线程安全设计

## 安装

只需复制`src`目录下的`server.py`和`client.py`文件到你的项目中即可使用。

```
python>=3.11  # 最低要求Python 3.11版本
```

## 使用方法

### 服务器端

```python
from server import RPCServer
import asyncio

# 创建服务器
server = RPCServer('127.0.0.1', 9999)

# 注册同步方法
@server.method
def add(a, b):
    return a + b

# 注册异步方法
@server.method
async def async_operation(data):
    await asyncio.sleep(1)  # 异步操作
    return f"处理完成: {data}"

# 调用客户端方法（异步）
async def call_client_method(client_address):
    result = await server.call(client_address, 'client_method', [1, 2])
    print(f"客户端方法返回: {result}")

# 调用客户端方法（同步，从其他线程）
def call_client_sync(client_address):
    result = server.call_sync(client_address, 'client_method', [1, 2])
    print(f"客户端方法返回: {result}")

# 启动服务器（阻塞调用）
server.run()
```

### 客户端

```python
import asyncio
from client import RPCClient

class MyClient(RPCClient):
    def __init__(self, host, port):
        super().__init__(host, port)
        
    # 使用装饰器注册方法，供服务器调用
    @RPCClient.method
    def client_method(self, a, b):
        return a + b
        
    # 异步方法也支持
    @RPCClient.method
    async def async_method(self, data):
        await asyncio.sleep(0.5)
        return f"已处理: {data}"
        
    async def run(self):
        # 连接到服务器
        if not await self.connect():
            return False
            
        # 启动读取循环
        read_task = asyncio.create_task(self._read_loop())
        
        try:
            # 异步调用服务器方法
            result = await self.call('add', [5, 3])
            print(f"5 + 3 = {result}")
            
            # 异步调用服务器的异步方法
            result = await self.call('async_operation', ["测试数据"])
            print(result)
            
            # 等待服务器调用本地方法
            await asyncio.sleep(60)
        finally:
            read_task.cancel()
            await self.close()

# 创建客户端实例
client = MyClient('127.0.0.1', 9999)

# 同步调用（阻塞）
def sync_example():
    # 创建客户端并进行同步调用
    client = MyClient('127.0.0.1', 9999)
    
    # 方法一：blocking_call 适合在没有事件循环的地方使用
    result = client.blocking_call('add', [10, 20])
    print(f"10 + 20 = {result}")
    
    # 方法二：启动客户端，然后可以在其他线程中使用call_sync
    client.start()  # 启动完整的客户端（阻塞）

# 异步运行完整客户端
asyncio.run(client.run())
```

## 三种调用方式对比

1. **异步调用 (`await client.call(...)`)** 
   - 在异步代码中使用
   - 需要异步上下文（async函数内）
   - 不会阻塞事件循环

2. **同步调用 (`client.call_sync(...)`)** 
   - 在客户端已启动状态下使用（已有事件循环）
   - 可以从任何线程调用
   - 会阻塞当前线程直到结果返回

3. **阻塞调用 (`client.blocking_call(...)`)** 
   - 适用于没有事件循环的情况
   - 会创建临时事件循环
   - 会阻塞当前线程

## 完整示例

详细示例代码请参考 `src/example.py` 文件，展示了：
- 服务器端同步和异步方法的定义
- 客户端同步和异步方法的定义
- 同步客户端和异步客户端的实现
- 服务器调用客户端方法
- 错误处理和超时处理
- 不同线程中的RPC调用

## 运行示例

```bash
python src/example.py
```

## 注意事项

- 所有可调用方法的参数和返回值必须能够被JSON序列化和反序列化
- 默认调用超时时间为5秒，可以在调用时自定义
- 服务器和客户端都支持同步和异步方法
- 通信使用TCP协议，所以需要网络连接 

## 装饰器使用说明

### 服务器端装饰器

1. **server_method_stub 装饰器**
   ```python
   from server import server_method_stub
   
   class MyServer(RPCServer):
       def __init__(self, host, port):
           super().__init__(host, port)
           
       @server_method_stub
       def decorated_method(self, a, b):
           return a + b
   ```

2. **直接注册方法**
   ```python
   class MyServer(RPCServer):
       def __init__(self, host, port):
           super().__init__(host, port)
           # 直接注册方法
           self.register_method("method_name", self.method_impl)
           
       def method_impl(self, a, b):
           return a + b
   ```

### 客户端装饰器

1. **client_method_stub 装饰器**
   ```python
   from client import client_method_stub
   
   class MyClient(RPCClient):
       def __init__(self, host, port):
           super().__init__(host, port)
           
       @client_method_stub
       def decorated_method(self, a, b):
           return a - b
   ```

2. **直接注册方法**
   ```python
   class MyClient(RPCClient):
       def __init__(self, host, port):
           super().__init__(host, port)
           # 直接注册方法
           self.register_method("method_name", self.method_impl)
           
       def method_impl(self, a, b):
           return a - b
   ```

### 装饰器使用注意事项

1. 装饰器方法支持同步和异步实现
2. 装饰器方法可以像普通方法一样被调用
3. 装饰器会自动处理方法的注册，无需手动注册

### 完整示例

```python
import asyncio
from server import RPCServer, server_method_stub
from client import RPCClient, client_method_stub

# 服务器端
class MyServer(RPCServer):
    def __init__(self, host, port):
        super().__init__(host, port)
        
    @server_method_stub
    def decorated_add(self, a, b):
        return a + b
        
    @server_method_stub
    async def decorated_async_process(self, data):
        await asyncio.sleep(0.5)
        return f"处理完成: {data}"

# 客户端
class MyClient(RPCClient):
    def __init__(self, host, port):
        super().__init__(host, port)
        
    @client_method_stub
    def decorated_subtract(self, a, b):
        return a - b
        
    @client_method_stub
    async def decorated_async_process(self, data):
        await asyncio.sleep(0.5)
        return f"处理完成: {data}"
``` 