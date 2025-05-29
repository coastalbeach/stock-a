#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis数据库管理器

管理Redis连接和操作，适用于存储实时数据、热点数据和缓存，提供高速访问和发布/订阅功能
"""

import os
import sys
import yaml
import json
import redis
import pickle
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)  # db/redis_manager.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)


class RedisManager:
    """Redis数据库管理器类
    
    提供Redis数据库连接和操作功能，支持缓存、发布/订阅和分布式锁
    """
    
    def __init__(self):
        """初始化Redis连接"""
        self.conn = None
        self.config = self._load_config()
        self.connect()
    
    def _load_config(self):
        """加载Redis配置"""
        config_path = os.path.join(project_root, 'config', 'redis.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    
    def connect(self):
        """连接Redis数据库"""
        try:
            redis_config = self.config['redis']
            self.conn = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                password=redis_config['password'],
                socket_timeout=redis_config['socket_timeout'],
                socket_connect_timeout=redis_config['socket_connect_timeout'],
                retry_on_timeout=redis_config['retry_on_timeout'],
                max_connections=redis_config['max_connections']
            )
            # 测试连接
            self.conn.ping()
            print("Redis数据库连接成功")
            return True
        except Exception as e:
            print(f"Redis数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭Redis连接"""
        if self.conn:
            self.conn.close()
            print("Redis数据库连接已关闭")
    
    def is_connected(self):
        """检查Redis连接状态
        
        Returns:
            bool: 连接是否正常
        """
        try:
            if self.conn:
                self.conn.ping()
                return True
            return False
        except Exception as e:
            print(f"Redis连接检查失败: {e}")
            return False
    
    def set_value(self, key, value, expire=None):
        """设置键值对
        
        Args:
            key (str): 键名
            value (any): 值，非字符串类型会被序列化
            expire (int, optional): 过期时间（秒）
            
        Returns:
            bool: 设置是否成功
        """
        try:
            # 序列化非字符串类型
            if not isinstance(value, (str, bytes, int, float)):
                value = pickle.dumps(value)
            
            # 设置键值
            self.conn.set(key, value)
            
            # 设置过期时间
            if expire:
                self.conn.expire(key, expire)
            
            return True
        except Exception as e:
            print(f"设置键值对失败: {e}")
            return False
    
    def get_value(self, key, deserialize=True):
        """获取键值
        
        Args:
            key (str): 键名
            deserialize (bool, optional): 是否反序列化
            
        Returns:
            any: 键值，如果键不存在则返回None
        """
        try:
            value = self.conn.get(key)
            
            # 如果值不存在，返回None
            if value is None:
                return None
            
            # 尝试反序列化
            if deserialize:
                try:
                    return pickle.loads(value)
                except:
                    pass
            
            return value
        except Exception as e:
            print(f"获取键值失败: {e}")
            return None
    
    def delete_key(self, key):
        """删除键
        
        Args:
            key (str): 键名
            
        Returns:
            bool: 删除是否成功
        """
        try:
            return bool(self.conn.delete(key))
        except Exception as e:
            print(f"删除键失败: {e}")
            return False
    
    def key_exists(self, key):
        """检查键是否存在
        
        Args:
            key (str): 键名
            
        Returns:
            bool: 键是否存在
        """
        try:
            return bool(self.conn.exists(key))
        except Exception as e:
            print(f"检查键是否存在失败: {e}")
            return False
    
    def set_hash(self, key, field, value, expire=None):
        """设置哈希表字段
        
        Args:
            key (str): 键名
            field (str): 字段名
            value (any): 值，非字符串类型会被序列化
            expire (int, optional): 过期时间（秒）
            
        Returns:
            bool: 设置是否成功
        """
        try:
            # 序列化非字符串类型
            if not isinstance(value, (str, bytes, int, float)):
                value = pickle.dumps(value)
            
            # 设置哈希表字段
            self.conn.hset(key, field, value)
            
            # 设置过期时间
            if expire:
                self.conn.expire(key, expire)
            
            return True
        except Exception as e:
            print(f"设置哈希表字段失败: {e}")
            return False
    
    def get_hash(self, key, field, deserialize=True):
        """获取哈希表字段
        
        Args:
            key (str): 键名
            field (str): 字段名
            deserialize (bool, optional): 是否反序列化
            
        Returns:
            any: 字段值，如果字段不存在则返回None
        """
        try:
            value = self.conn.hget(key, field)
            
            # 如果值不存在，返回None
            if value is None:
                return None
            
            # 尝试反序列化
            if deserialize:
                try:
                    return pickle.loads(value)
                except:
                    pass
            
            return value
        except Exception as e:
            print(f"获取哈希表字段失败: {e}")
            return None
    
    def get_all_hash(self, key, deserialize=True):
        """获取哈希表所有字段
        
        Args:
            key (str): 键名
            deserialize (bool, optional): 是否反序列化
            
        Returns:
            dict: 哈希表字段字典，如果键不存在则返回空字典
        """
        try:
            hash_dict = self.conn.hgetall(key)
            
            # 如果哈希表不存在，返回空字典
            if not hash_dict:
                return {}
            
            # 尝试反序列化
            if deserialize:
                result = {}
                for field, value in hash_dict.items():
                    field = field.decode() if isinstance(field, bytes) else field
                    try:
                        result[field] = pickle.loads(value)
                    except:
                        result[field] = value
                return result
            
            return hash_dict
        except Exception as e:
            print(f"获取哈希表所有字段失败: {e}")
            return {}
    
    def acquire_lock(self, lock_name, expire=10):
        """获取分布式锁
        
        Args:
            lock_name (str): 锁名称
            expire (int, optional): 锁过期时间（秒）
            
        Returns:
            bool: 是否成功获取锁
        """
        try:
            # 使用setnx命令尝试获取锁
            lock_key = f"lock:{lock_name}"
            return bool(self.conn.set(lock_key, 1, ex=expire, nx=True))
        except Exception as e:
            print(f"获取分布式锁失败: {e}")
            return False
    
    def release_lock(self, lock_name):
        """释放分布式锁
        
        Args:
            lock_name (str): 锁名称
            
        Returns:
            bool: 是否成功释放锁
        """
        try:
            lock_key = f"lock:{lock_name}"
            return bool(self.conn.delete(lock_key))
        except Exception as e:
            print(f"释放分布式锁失败: {e}")
            return False