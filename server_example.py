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



server.run()

