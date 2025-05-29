"""
加密工具模块 - 提供 Movan RPC 的加密通信功能

实现了一个混合加密策略：
1. 使用 RSA 非对称加密进行初始密钥交换
2. 使用 RSA 加密传输 AES 对称密钥
3. 后续通信使用 AES-GCM 对称加密
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature
import os
import base64
import json
from typing import Tuple, Dict, Any, Union, Optional


class CryptoManager:
    """
    加密管理器 - 处理 RSA 和 AES 加密操作
    """
    
    def __init__(self):
        # 初始化时不生成密钥，等待显式调用
        self.rsa_private_key = None
        self.rsa_public_key = None
        self.peer_public_key = None
        self.aes_key = None
        self.encryption_enabled = False
    
    def generate_rsa_keypair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        生成 RSA 公钥/私钥对
        
        参数:
            key_size: RSA 密钥大小（位）
            
        返回:
            (private_key_pem, public_key_pem) 的元组
        """
        # 生成私钥
        self.rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
        
        # 获取公钥
        self.rsa_public_key = self.rsa_private_key.public_key()
        
        # 序列化为 PEM 格式
        private_key_pem = self.rsa_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_key_pem = self.rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_key_pem, public_key_pem
    
    def get_public_key_pem(self) -> bytes:
        """获取当前公钥的 PEM 格式"""
        if not self.rsa_public_key:
            self.generate_rsa_keypair()
            
        return self.rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def set_peer_public_key(self, public_key_pem: bytes) -> None:
        """设置对方的公钥"""
        self.peer_public_key = serialization.load_pem_public_key(public_key_pem)
    
    def generate_aes_key(self, key_size: int = 32) -> bytes:
        """生成 AES 密钥（默认 256 位）"""
        self.aes_key = os.urandom(key_size)
        return self.aes_key
    
    def encrypt_with_rsa(self, data: bytes) -> bytes:
        """使用 RSA 公钥加密数据（用于密钥交换）"""
        if not self.peer_public_key:
            raise ValueError("未设置对方公钥，无法加密")
            
        ciphertext = self.peer_public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    
    def decrypt_with_rsa(self, ciphertext: bytes) -> bytes:
        """使用 RSA 私钥解密数据"""
        if not self.rsa_private_key:
            raise ValueError("未生成 RSA 密钥对，无法解密")
            
        plaintext = self.rsa_private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
    
    def encrypt_with_aes(self, data: bytes) -> Tuple[bytes, bytes]:
        """
        使用 AES-GCM 加密数据
        
        返回:
            (nonce, ciphertext) 元组
        """
        if not self.aes_key:
            raise ValueError("未设置 AES 密钥，无法加密")
            
        # 生成随机 nonce (每次加密必须不同)
        nonce = os.urandom(12)  # 12 bytes for AES-GCM
        
        # 加密
        aesgcm = AESGCM(self.aes_key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        return nonce, ciphertext
    
    def decrypt_with_aes(self, nonce: bytes, ciphertext: bytes) -> bytes:
        """使用 AES-GCM 解密数据"""
        if not self.aes_key:
            raise ValueError("未设置 AES 密钥，无法解密")
            
        aesgcm = AESGCM(self.aes_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext
    
    def encrypt_message(self, message: Dict) -> Dict:
        """
        加密 JSON 消息对象
        
        如果加密已启用，使用 AES 加密消息
        如果加密未启用，直接返回原消息
        """
        if not self.encryption_enabled or not self.aes_key:
            return message
            
        # 将消息转换为 JSON 字符串，再转为字节
        message_bytes = json.dumps(message).encode('utf-8')
        
        # 加密
        nonce, ciphertext = self.encrypt_with_aes(message_bytes)
        
        # 构造加密消息结构
        encrypted_message = {
            "type": "encrypted",
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "data": base64.b64encode(ciphertext).decode('utf-8')
        }
        
        return encrypted_message
    
    def decrypt_message(self, message: Dict) -> Dict:
        """
        解密消息
        
        如果是加密消息（类型为 "encrypted"），则解密
        否则，直接返回原消息
        """
        if not self.encryption_enabled or message.get("type") != "encrypted":
            return message
            
        if not self.aes_key:
            raise ValueError("未设置 AES 密钥，无法解密消息")
            
        # 解析加密消息
        nonce = base64.b64decode(message["nonce"])
        ciphertext = base64.b64decode(message["data"])
        
        # 解密
        plaintext = self.decrypt_with_aes(nonce, ciphertext)
        
        # 解析 JSON
        decrypted_message = json.loads(plaintext.decode('utf-8'))
        return decrypted_message
    
    def enable_encryption(self) -> None:
        """启用加密"""
        self.encryption_enabled = True
    
    def disable_encryption(self) -> None:
        """禁用加密"""
        self.encryption_enabled = False


# 加密消息类型
HANDSHAKE_INIT = "handshake_init"        # 初始握手请求
HANDSHAKE_RESPONSE = "handshake_response"  # 握手响应
KEY_EXCHANGE = "key_exchange"            # 密钥交换


def create_handshake_message(public_key_pem: bytes) -> Dict[str, Any]:
    """
    创建握手消息，包含公钥信息
    """
    return {
        "type": HANDSHAKE_INIT,
        "public_key": base64.b64encode(public_key_pem).decode('utf-8')
    }


def create_handshake_response(public_key_pem: bytes) -> Dict[str, Any]:
    """
    创建握手响应消息
    """
    return {
        "type": HANDSHAKE_RESPONSE,
        "public_key": base64.b64encode(public_key_pem).decode('utf-8')
    }


def create_key_exchange_message(encrypted_aes_key: bytes) -> Dict[str, Any]:
    """
    创建密钥交换消息，包含用 RSA 加密的 AES 密钥
    """
    return {
        "type": KEY_EXCHANGE,
        "key": base64.b64encode(encrypted_aes_key).decode('utf-8')
    }