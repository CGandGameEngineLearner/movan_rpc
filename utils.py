from typing import Dict


def verify_msg(msg:Dict)->bool:
    proto = msg.get('type')
    if proto != 'call' and proto != 'return':
        return False

    timestamp = msg.get('timestamp')
    if isinstance(timestamp,float):
        return False
    
    uuid = msg.get('uuid')
    if isinstance(uuid,str):
        return False

    return True