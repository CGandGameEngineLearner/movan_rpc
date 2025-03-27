from typing import Dict


def verify_msg(msg:Dict)->bool:
    proto = msg.get('type')
    # 新增ping和pong消息类型支持
    if proto not in ['call', 'return', 'ping', 'pong']:
        return False

    timestamp = msg.get('timestamp')
    if not isinstance(timestamp,str):
        return False
    
    id = msg.get('id')
    if not isinstance(id,str):
        return False

    return True