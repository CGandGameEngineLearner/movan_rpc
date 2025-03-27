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
    # 启动服务器（作为主任务而不是子任务）
    server_task = asyncio.create_task(server.start())
    
    # 等待一段时间让客户端连接
    await asyncio.sleep(8)
    
    try:
        # 获取连接的副本以避免迭代时修改
        client_connections = list(server.connections.keys())
        
        for client_address in client_connections:
            try:
                # 并发执行多个客户端调用
                tasks = [
                    asyncio.create_task(call_client_method(client_address)),
                    asyncio.create_task(asyncio.to_thread(call_client_sync, client_address)),
                    asyncio.create_task(client_subtract(client_address, 10, 2)),
                    asyncio.create_task(client_hello(client_address, "Hello,I am Server!"))
                ]
                
                # 等待所有任务完成，允许单个任务失败
                done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
                
                # 检查是否有任务出错
                for task in done:
                    if task.exception():
                        print(f"客户端调用出错: {task.exception()}")
            except Exception as e:
                print(f"处理客户端 {client_address} 时出错: {e}")
        
        # 保持服务器运行直到手动终止或Ctrl+C
        try:
            # 等待服务器任务完成（实际上会一直运行直到被终止）
            await server_task
        except asyncio.CancelledError:
            print("服务器任务被取消")
    except Exception as e:
        print(f"服务器运行时出错: {e}")
    finally:
        # 如果server_task仍在运行，确保它被正确关闭
        if not server_task.done():
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

try:

    
    # 运行服务器
    asyncio.run(run_server())
except KeyboardInterrupt:
    print("\n服务器已通过键盘中断停止")

