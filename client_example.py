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