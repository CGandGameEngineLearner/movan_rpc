import asyncio
from kcp.client import KCPClientSync
import msgpack
import time
from typing import Dict, Any, Callable

class RPCClient:
    def __init__(self, address:str, port:int):
        self.host:str = address
        self.port:int = port
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
        self.message_buffer:Dict[float,Any] = {}

    def start(self):
        self.kcp_client.start()
    
    def on_start(self):
        print('Connection established')
        print(self.call('add', [1, 2]))
        

    
    def on_data(self, data:bytes):
        print('Data received')
        try:
            message = msgpack.unpackb(data)
            if message.get('error'):
                print(f'Error: {message["error"]}')
                return
            timestamp:float = message.get('timestamp')
            if timestamp is None:
                raise Exception('No timestamp')
            result = message.get('result')
            if result is None:
                raise Exception('No result')
            self.message_buffer[timestamp] = result
        except Exception as e:
            print(f'Error: {e}')

    def call(self, method:str, params = [], kwargs = {}):
        timestamp:float = time.time()
        self.kcp_client.send(msgpack.packb({
            'timestamp': timestamp,
            'method': method,
            'args': params,
            'kwargs': kwargs
        }))

        while time.time() < timestamp + 5:
            if timestamp in self.message_buffer:
                result = self.message_buffer[timestamp]
                del self.message_buffer[timestamp]
                return result
        
        print('Timeout')
        return None
        

    async def call_async(self, method:str, params = [], kwargs = {}, callback:Callable = None):
        timestamp:float = time.time()
        self.kcp_client.send(msgpack.packb({
            'timestamp': timestamp,
            'method': method,
            'args': params,
            'kwargs': kwargs
        }))

        while time.time() < timestamp + 5:
            if timestamp in self.message_buffer:
                result = self.message_buffer[timestamp]
                del self.message_buffer[timestamp]
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