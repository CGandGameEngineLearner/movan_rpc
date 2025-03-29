"""
Movan RPC - 一个简单的 RPC（远程过程调用）框架

使用 Python 标准库实现，无需第三方依赖。
支持同步和异步方法调用。
"""

from .movan_rpc import RPCServer as RPCServer, RPCClient as RPCClient, AddressType as AddressType

__all__ = ['RPCServer', 'RPCClient', 'AddressType']
__version__ = '0.1.0'