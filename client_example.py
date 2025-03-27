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
        
        # 使用异常处理保护每一次调用
        try:
            result = await client.call('server_add', [6, 2])
            print(f"server_add结果: {result}")
        except Exception as e:
            print(f"调用server_add失败: {e}")
        
        # 短暂暂停
        await asyncio.sleep(0.5)
        
        try:
            # 使用异步调用替代同步调用
            result = await client.call('server_add', [6, 3])
            print(f"第二次server_add结果: {result}")
        except Exception as e:
            print(f"第二次调用server_add失败: {e}")
        
        await asyncio.sleep(0.5)
        
        try:
            result = await server_add_async(6, 80)
            print(f"server_add_async结果: {result}")
        except Exception as e:
            print(f"调用server_add_async失败: {e}")
        
        await asyncio.sleep(0.5)
        
        try:
            # 使用异步版本
            result = await server_add(6, 80)
            print(f"server_add存根结果: {result}")
        except Exception as e:
            print(f"调用server_add存根失败: {e}")
        
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

try:
    asyncio.run(run_client())
except KeyboardInterrupt:
    print("\n客户端已通过键盘中断停止")
except Exception as e:
    print(f"运行客户端时发生未捕获异常: {e}")