from movan_rpc import RPCClient
import asyncio
client = RPCClient('127.0.0.1', 9999)



@client.server_method_stub
async def server_add(a:int, b:int)->int:
    pass

@client.server_method_stub
async def server_add_async(a:int, b:int)->int:
    pass


@client.server_method_stub
async def server_hello(hello:str):
    pass


async def run_client():
    # 启动客户端作为主任务
    client_task = asyncio.create_task(client.start())
    
    try:
        # 等待客户端启动并连接
        await asyncio.sleep(2)
        
        # 检查客户端是否成功连接
        if not client.connected:
            print("客户端未能成功连接，等待更长时间...")
            await asyncio.sleep(6)
            if not client.connected:
                print("客户端连接失败")
                return
        
        print("开始调用服务器方法...")
        
       
        
        # 短暂暂停
        await asyncio.sleep(0.5)
        
        try:
            # 使用异步调用替代同步调用
            result = await client.call('server_add', [6, 3])
            print(f"server_add结果: {result}")
        except Exception as e:
            print(f"server_add失败: {e}")
        
        await asyncio.sleep(0.5)
        
        try:
            result = await server_add_async(6, 80)
            print(f"server_add_async结果: {result}")
        except Exception as e:
            print(f"调用server_add_async失败: {e}")
            # 尝试直接调用，绕过stub

        try:
            result = await client.call('server_add_async', [6, 80], timeout=10.0)
            print(f"直接调用server_add_async结果: {result}")
        except Exception as e2:
            print(f"直接调用server_add_async失败: {e2}")

        try:
            result = await server_hello("hello")
            print(f"server_hello结果: {result}")
        except Exception as e2:
            print(f"server_hello失败: {e2}")
        
        await asyncio.sleep(0.5)
        
        
        # 让客户端保持运行一段时间
        print("所有调用完成，客户端保持运行中...")
        await asyncio.sleep(10)
        
    except Exception as e:
        print(f"运行客户端时出错: {e}")
    finally:
        # 确保客户端正确关闭
        if client.connected:
            await client.close()
        
        # 取消客户端任务
        if not client_task.done():
            client_task.cancel()
            try:
                await client_task
            except asyncio.CancelledError:
                pass
        
        print("客户端已完成执行")

asyncio.run(run_client())
