import asyncio
import kcp
import msgpack

class RPCClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    async def call_method(self, method, params):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        request = msgpack.packb({'method': method, 'params': params}, use_bin_type=True)
        writer.write(request)
        await writer.drain()
        data = await reader.read(1024)
        response = msgpack.unpackb(data, raw=False)
        writer.close()
        return response['result']

async def main():
    client = RPCClient('127.0.0.1', 9999)
    result = await client.call_method('add', [1, 2])
    print(f'Result: {result}')

if __name__ == "__main__":
    asyncio.run(main())