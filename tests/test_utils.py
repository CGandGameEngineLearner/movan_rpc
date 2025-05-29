from movan_rpc import utils

def test_verify_msg():
    # 测试有效消息
    valid_msg = {
        "type": "call",
        "timestamp": "1620000000.0",
        "id": "12345",
    }
    assert utils.verify_msg(valid_msg)
    
    # 测试无效消息类型
    invalid_type_msg = {
        "type": "invalid_type",
        "timestamp": "1620000000.0",
        "id": "12345",
    }
    assert not utils.verify_msg(invalid_type_msg)
    
    # 测试无效时间戳
    invalid_timestamp_msg = {
        "type": "call",
        "timestamp": 1620000000.0,  # 数字而非字符串
        "id": "12345",
    }
    assert not utils.verify_msg(invalid_timestamp_msg)
    
    # 测试无效ID
    invalid_id_msg = {
        "type": "call",
        "timestamp": "1620000000.0",
        "id": 12345,  # 数字而非字符串
    }
    assert not utils.verify_msg(invalid_id_msg)