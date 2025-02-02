from kcp.server import Connection
from kcp.server import KCPServerAsync
import msgpack
import asyncio
from typing import Dict, Callable

class RPCServer:
    def __init__(self, host:str, port:int):
        self.host = host
        self.port = port
        self.methods:Dict[str,Callable] = {}
        self.kcp_server:KCPServerAsync = KCPServerAsync(
            host = host,
            port = port,
            conv_id = 1,
            no_delay= True
        )
        self.kcp_server.on_data = self.on_data
    


    def register_method(self, name:str, method:Callable):
        if self.methods.get(name):
            raise Exception(f"Method {name} already registered")
        self.methods[name] = method

    # Decorator to register method
    def method(self, func: Callable):
        self.register_method(func.__name__, func)
        return func
    
    def on_data(self, data:bytes, conn:Connection):
        try:
            data = msgpack.unpackb(data)
            method_name = data.get('method')
            args = data.get('args', [])
            kwargs = data.get('kwargs', {})
            method = self.methods.get(method_name)
            if not method:
                conn.send(msgpack.packb({'error': f"Method {method_name} not found"}))
            result = method(*args, **kwargs)
            conn.send(msgpack.packb(result))
        except Exception as e:
            conn.send(msgpack.packb({'error': str(e)}))
        
        

    async def start(self):
        self.kcp_server.start()
        await self.handle_client()

def add(x, y):
    return x + y

if __name__ == "__main__":
    server = RPCServer('127.0.0.1', 9999)
    server.register_method('add', add)
    asyncio.run(server.start_server())