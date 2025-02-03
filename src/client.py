import asyncio
from kcp.client import KCPClientSync
import msgpack
import time
from typing import Dict, Any, Callable

class RPCClient:
    def __init__(self, address:str, port:int):
        self.host:str = address
        self.port:int = port
        self.methods:Dict[str,Callable] = {}
        self.kcp_client:KCPClientSync = KCPClientSync(
            address = address,
            port = port,
            conv_id=1,
            no_delay=True,
            update_interval=10,
            resend_count=5,
            no_congestion_control=True,
            receive_window_size=1024,
            send_window_size=1024
            )
        
        self.kcp_client.on_data(self.on_data)
        self.kcp_client.on_start(self.on_start)
        self.return_buffer:Dict[float,Any] = {}

    def register_method(self, name:str, method:Callable):
        if self.methods.get(name):
            raise Exception(f"Method {name} already registered")
        self.methods[name] = method

    # Decorator to register method
    def method(self, func: Callable):
        self.register_method(func.__name__, func)
        return func

    def start(self):
        self.kcp_client.start()
    
    def on_start(self):
        print('Connection established')
        print(self.call('add', [1, 2]))
        

    
    def on_data(self, data:bytes):
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
                    self.call(msgpack.packb({'error': f"Method {method_name} not found"}))
                    return
                result = method(*args, **kwargs)
                msg = {'type':'return', 'timestamp' : timestamp,'result' : result}
                self.call(msgpack.packb(msg))
            except Exception as e:
                self.call(msgpack.packb({'error': str(e)}))
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

    
def print_result(x):
    print(f'Result: {x}')



async def main():
    client = RPCClient('127.0.0.1', 9999)
    client.start()
    

if __name__ == "__main__":
    asyncio.run(main())