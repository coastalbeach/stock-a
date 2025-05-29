#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置加载模块

提供统一的配置加载功能，支持从YAML文件加载配置信息
"""

import os
import sys
import yaml
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)


def load_config(config_name):
    """
    加载指定的配置文件
    
    Args:
        config_name (str): 配置文件名称，不包含扩展名
        
    Returns:
        dict: 配置信息字典
    """
    config_path = os.path.join(project_root, 'config', f'{config_name}.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return {}


def load_app_config():
    """
    加载应用程序配置
    
    Returns:
        dict: 应用程序配置信息
    """
    return load_config('app')


def load_connection_config():
    """
    加载数据库连接配置
    
    Returns:
        dict: 数据库连接配置信息
    """
    return load_config('connection')


def load_redis_config():
    """
    加载Redis配置
    
    Returns:
        dict: Redis配置信息
    """
    return load_config('redis')


def load_tables_config():
    """
    加载数据表配置
    
    Returns:
        dict: 数据表配置信息
    """
    return load_config('tables')