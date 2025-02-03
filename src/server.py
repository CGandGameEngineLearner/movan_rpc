from kcp.server import Connection
from kcp.server import KCPServerAsync
import msgpack
import asyncio
from typing import Dict, Callable

class RPCServer:
    def __init__(self, address:str, port:int):
        self.host = address
        self.port = port
        self.methods:Dict[str,Callable] = {}
        self.kcp_server:KCPServerAsync = KCPServerAsync(
            address = address,
            port = port,
            conv_id = 1,
            no_delay= True
            
        )
        self.kcp_server.set_performance_options(
            update_interval=10,
        )
        self.kcp_server.on_data(self.on_data)
    


    def register_method(self, name:str, method:Callable):
        if self.methods.get(name):
            raise Exception(f"Method {name} already registered")
        self.methods[name] = method

    # Decorator to register method
    def method(self, func: Callable):
        self.register_method(func.__name__, func)
        return func
    
    async def on_data(self, connection: Connection, data: bytes) -> None:
        print("server on data")
        try:
            data = msgpack.unpackb(data)
            timestamp = data.get('timestamp')
            method_name = data.get('method')
            args = data.get('args', [])
            kwargs = data.get('kwargs', {})
            method = self.methods.get(method_name)
            if not method:
                connection.enqueue(msgpack.packb({'error': f"Method {method_name} not found"}))
            result = method(*args, **kwargs)
            msg = {'timestamp' : timestamp,'result' : result}
            connection.enqueue(msgpack.packb(msg))
        except Exception as e:
            connection.enqueue(msgpack.packb({'error': str(e)}))
        
        

    def start(self):
       self.kcp_server.start()

async def print_data(connection: Connection, data: bytes):
    print("server on data")

def add(x, y):
    return x + y

if __name__ == "__main__":
    server = RPCServer('127.0.0.1', 9999)
    server.register_method('add', add)
    server.start()