# Movan RPC

一个轻量级的 RPC（远程过程调用）框架，使用 Python 标准库实现，无需第三方依赖。支持同步和异步方法调用，以及心跳检测机制。

本项目原本是 Movan Server 项目的 RPC 模块，现在剥离出来做成一个独立的库，方便其他项目使用。

## 特性

- 基于 Python 标准库 `asyncio`、`json` 和 `socket` 模块
- 支持同步和异步方法定义与调用
- 提供基于装饰器的简洁 API
- 异常处理和超时机制
- 支持位置参数和关键字参数传递
- 两种客户端实现：
  - 基于 `asyncio` 的异步客户端
  - 基于 `threading` 的同步客户端
- 自动重连功能
- 心跳检测机制，保持连接稳定

## 安装

### 方法一：从 PyPI 安装

```bash
pip install movan_rpc
```

### 方法二：从源码安装

```bash
git clone https://github.com/CGandGameEngineLearner/movan_rpc.git
cd movan_rpc
pip install -e .
```

## 使用方法

### 服务器端

```python
from movan_rpc import RPCServer
import asyncio

# 创建 RPC 服务器
server = RPCServer('127.0.0.1', 9999)

# 使用装饰器注册异步方法 (推荐)
@server.method
async def server_add_async(a: int, b: int) -> int:
    await asyncio.sleep(1)  # 模拟耗时操作
    return a + b

# 使用装饰器注册同步方法
@server.method
def server_add(a: int, b: int) -> int:
    return a + b

# 启动服务器 (阻塞)
server.run()
```

### 异步客户端

```python
from movan_rpc import RPCClient
import asyncio

client = RPCClient('127.0.0.1', 9999)

# 创建服务器方法的存根
@client.server_method_stub
async def server_add(a: int, b: int) -> int:
    pass

@client.server_method_stub
async def server_add_async(a: int, b: int) -> int:
    pass

async def main():
    # 启动客户端
    client_task = asyncio.create_task(client.start())
    
    # 等待客户端连接建立
    await asyncio.sleep(1)
    
    if client.connected:
        # 方法1：使用存根函数调用
        result1 = await server_add(10, 20)
        print(f"通过存根调用结果: {result1}")
        
        # 方法2：直接调用
        result2 = await client.call('server_add_async', [30, 40])
        print(f"直接调用结果: {result2}")
        
        # 关闭客户端
        await client.close()
    
    # 取消客户端任务
    client_task.cancel()

# 运行客户端
asyncio.run(main())
```

### 同步客户端 (基于线程)

```python
from movan_rpc import RPCClientThreading
import time

client = RPCClientThreading('127.0.0.1', 9999)

# 启动客户端
client.start_sync()

# 定义回调函数
def on_result(result):
    print(f"收到结果: {result}")

# 发起异步调用并设置回调
call_id = client.call('server_add', on_result, [50, 60])

# 主线程继续执行其他操作
for i in range(10):
    # 处理响应 (必须定期调用)
    client.on_tick()
    time.sleep(0.5)

# 关闭连接
client.close()
```

## 调用方式对比

1. **异步客户端 - 异步调用 (`await client.call(...)`)** 
   - 在异步代码中使用
   - 需要异步上下文（async 函数内）
   - 不会阻塞事件循环
   - 适用于高并发场景

2. **异步客户端 - 存根函数调用 (`await server_method(...)`)** 
   - 提供类似本地函数调用的语法
   - 有类型提示和自动补全支持
   - 内部调用 `client.call()`

3. **同步客户端 - 基于回调的调用 (`client.call(..., callback)`)** 
   - 适用于基于事件的编程模型
   - 不阻塞主线程
   - 主线程循环内需要定期调用 `on_tick()` 处理返回结果，这会在主线程内调用对应的回调函数

## 高级特性

- **异常处理**：远程调用时的异常会被捕获并传递给调用方
- **超时控制**：可设置 RPC 调用超时时间
- **心跳检测**：自动发送心跳包保持连接
- **自动重连**：连接断开后自动重连

## 项目结构

```
movan_rpc/
├── __init__.py
├── server.py
├── client.py
├── client_threading.py
└── utils.py
```



## 许可证

MIT 许可证

## 贡献

欢迎提交 Pull Request 或 Issue
