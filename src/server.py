from kcp.server import Connection
from kcp.server import KCPServerAsync
import msgpack
import asyncio
import time
from typing import Dict, Any, Callable

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
        self.kcp_server.on_data(self.on_data)
        self.return_buffer:Dict[float,Any] = {}
    


    def register_method(self, name:str, method:Callable):
        if self.methods.get(name):
            raise Exception(f"Method {name} already registered")
        self.methods[name] = method

    # Decorator to register method
    def method(self, func: Callable):
        self.register_method(func.__name__, func)
        return func
    
    async def on_data(self, connection: Connection, data: bytes) -> None:
        try:
            msg = msgpack.unpackb(data)
            msg_type = msg.get('type')
            if msg_type is None:
                raise Exception('No type')
        except Exception as e:
            return
        
        if msg_type == 'call':
            try:
                timestamp = msg.get('timestamp')
                method_name = msg.get('method')
                args = msg.get('args', [])
                kwargs = msg.get('kwargs', {})
                method = self.methods.get(method_name)
                if not method:
                    connection.enqueue(msgpack.packb({'error': f"Method {method_name} not found"}))
                result = method(*args, **kwargs)
                msg = {'type':'return', 'timestamp' : timestamp,'result' : result}
                connection.enqueue(msgpack.packb(msg))
            except Exception as e:
                connection.enqueue(msgpack.packb({'error': str(e)}))
        elif msg_type == 'return':
            try:
                timestamp:float = msg.get('timestamp')
                if timestamp is None:
                    raise Exception('No timestamp')
                error = msg.get('error')
                if error:
                    self.return_buffer[timestamp] = error
                    return
                result = msg.get('result')
                if result is None:
                    raise Exception('No result')
                self.return_buffer[timestamp] = result
            except Exception as e:
                return
        else:
            return
            

    def call(self, method:str, params = [], kwargs = {}):
        timestamp:float = time.time()
        msg:bytes = msgpack.packb({
            'type': 'call',
            'timestamp': timestamp,
            'method': method,
            'args': params,
            'kwargs': kwargs
        })

        self.kcp_client.send(msg)

        while time.time() < timestamp + 5:
            if timestamp in self.return_buffer:
                result = self.return_buffer[timestamp]
                del self.return_buffer[timestamp]
                return result
        
        print('Timeout')
        return None
        

    async def call_async(self, method:str, params = [], kwargs = {}, callback:Callable = None):
        timestamp:float = time.time()
        msg:bytes = msgpack.packb({
            'type': 'call',
            'timestamp': timestamp,
            'method': method,
            'args': params,
            'kwargs': kwargs
        })

        self.kcp_client.send(msg)

        while time.time() < timestamp + 5:
            if timestamp in self.return_buffer:
                result = self.return_buffer[timestamp]
                del self.return_buffer[timestamp]
                if callback is not None:
                    callback(result)
                return result
        
        print('Timeout')
        
        if callback is not None:
            callback(None)
        return None
        
        

    def start(self):
       self.kcp_server.start()

async def print_data(connection: Connection, data: bytes):
    print("server on data")

def test_add(x, y):
    return x + y

if __name__ == "__main__":
    server = RPCServer('127.0.0.1', 9999)
    server.register_method('add', test_add)
    server.start()