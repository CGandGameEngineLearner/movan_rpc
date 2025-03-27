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

## 安装

只需复制`src`目录下的`server.py`和`client.py`文件到你的项目中即可使用。

```
python>=3.11  # 最低要求Python 3.11版本
```

## 使用方法

### 服务器端

```python
from server import RPCServer,AddressType
import asyncio
import time

# 创建服务器
server = RPCServer('127.0.0.1', 9999)



# 使用装饰器注册同步方法
@server.method
def server_add(a:int, b:int):
    return a + b

# 使用装饰器注册异步方法
@server.method
async def server_add_async(a:int, b:int):
    await asyncio.sleep(1)  
    return a + b


# 调用客户端方法（异步）
async def call_client_method(client_address):
    result = await server.call(client_address, 'client_subtract', [6, 2])
    print(f"调用客户端方法（异步） 客户端方法返回: {result}")

# 调用客户端方法 (同步)
def call_client_sync(client_address):
    result = server.call_sync(client_address, 'client_subtract', [465, 2])
    print(f"调用客户端方法 (同步) 客户端方法返回: {result}")

# 使用装饰器创建客户端方法的存根 然后调用
@server.client_method_stub
def client_subtract(client_address:AddressType, a:int, b:int):
    pass

@server.client_method_stub
async def client_hello(client_address:AddressType, data:str):
    pass

# 启动服务器
async def run_server():
    asyncio.create_task(server.start())
    await asyncio.sleep(8)
    for client_address in server.connections.keys():
        asyncio.create_task(call_client_method(client_address))
        call_client_sync(client_address)
        client_subtract(client_address, 10, 2)
        asyncio.create_task(client_hello(client_address,"Hello,I am Server!"))
    

asyncio.run(run_server())

```

### 客户端

```python
from client import RPCClient
import asyncio
client = RPCClient('127.0.0.1', 9999)

@client.method
def client_subtract(a, b):
    return a - b

@client.method
def client_hello(data:str):
    return data + "   Hello,I am Client!"

@client.server_method_stub
def server_add(a:int, b:int):
    pass

@client.server_method_stub
async def server_add_async(a:int, b:int):
    pass




async def run_client():
    asyncio.create_task(client.start())
    await asyncio.sleep(8)
    result = await client.call('server_add', [6, 2])
    print(result)
    result = client.call_sync('server_add', [6, 3])
    print(result)
    result = await server_add_async(6, 80)
    print(result)
    result = server_add(6, 80)
    print(result)


asyncio.run(run_client())
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
