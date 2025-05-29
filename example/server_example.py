from movan_rpc import RPCServer
import asyncio

# 创建服务器
server = RPCServer('127.0.0.1', 9999)


# 使用装饰器注册异步方法 (推荐使用) 
@server.method
async def server_add_async(a:int, b:int)->int:
    await asyncio.sleep(1)  
    return a + b


# 使用装饰器注册同步方法 服务器线程会阻塞在这里 直到计算得到结果才返回 (不推荐使用)
@server.method
def server_add(a:int, b:int)->int:
    return a + b


@server.method
def server_hello(hello:str):
    print(hello)


server.run()

