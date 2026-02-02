"""兼容的密码哈希实现"""
import sys
import os

# 添加项目根目录到Python路径
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_file_dir)
project_root = os.path.abspath(project_root)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入bcrypt/passlib，如果失败则使用备用方案
try:
    from passlib.context import CryptContext
    from passlib.exc import PasswordSizeError
    
    # 初始化bcrypt上下文
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            # 检查密码长度
            if len(plain_password.encode('utf-8')) > 72:
                # 截断到72字节以内再验证
                plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
            return pwd_context.verify(plain_password, hashed_password)
        except PasswordSizeError:
            # 如果是密码长度错误，截断后再试
            truncated_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
            return pwd_context.verify(truncated_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        try:
            # 检查密码长度
            if len(password.encode('utf-8')) > 72:
                # 截断到72字节以内
                password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            # 如果bcrypt失败，使用备用方案
            return _fallback_hash(password)
    
except ImportError:
    logger.warning("bcrypt/passlib not available, using fallback implementation")
    
    # 备用实现
    def _fallback_hash(password: str) -> str:
        """备用密码哈希实现"""
        # 使用SHA256加盐哈希（仅作备用，安全性较低）
        import secrets
        salt = secrets.token_hex(32)
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt.encode('ascii'), 
                                      100000)
        pwdhash = salt + pwdhash.hex()
        return pwdhash
    
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码（备用实现）"""
        try:
            # 从存储的哈希中提取盐
            salt = hashed_password[:64]  # 32字节的盐转换为hex是64字符
            stored_hash = hashed_password[64:]
            pwdhash = hashlib.pbkdf2_hmac('sha256',
                                          plain_password.encode('utf-8'),
                                          salt.encode('ascii'),
                                          100000)
            return pwdhash.hex() == stored_hash
        except:
            return False
    
    def get_password_hash(password: str) -> str:
        """生成密码哈希（备用实现）"""
        return _fallback_hash(password)


def test_password_functions():
    """测试密码函数"""
    print("测试密码函数...")
    
    # 测试正常长度密码
    try:
        normal_password = "normalpassword123"
        hashed = get_password_hash(normal_password)
        verified = verify_password(normal_password, hashed)
        print(f"正常密码测试: {'✓' if verified else '✗'}")
    except Exception as e:
        print(f"正常密码测试失败: {e}")
    
    # 测试超长密码
    try:
        long_password = "a" * 100  # 100个字符的密码
        hashed = get_password_hash(long_password)
        verified = verify_password(long_password, hashed)
        print(f"超长密码测试: {'✓' if verified else '✗'}")
    except Exception as e:
        print(f"超长密码测试失败: {e}")
    
    print("密码函数测试完成")


if __name__ == "__main__":
    test_password_functions()