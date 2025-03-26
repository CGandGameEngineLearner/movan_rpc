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

