# -*- coding: utf-8 -*-

"""
性能监控模块

提供性能监控装饰器，用于监控函数执行时间和资源使用情况
"""

import os
import sys
import time
import functools
import psutil
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入日志模块
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger('performance')


def performance_monitor(func):
    """装饰器：监控函数执行时间和资源使用情况
    
    Args:
        func (callable): 被装饰的函数
        
    Returns:
        callable: 包装后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 记录开始时间和资源使用
        start_time = time.time()
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = psutil.cpu_percent(interval=0.1)
        
        # 执行原函数
        result = func(*args, **kwargs)
        
        # 记录结束时间和资源使用
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = psutil.cpu_percent(interval=0.1)
        
        # 计算差异
        elapsed_time = end_time - start_time
        memory_diff = end_memory - start_memory
        
        # 记录性能数据
        logger.debug(f"性能监控 - {func.__name__}: 耗时={elapsed_time:.2f}秒, "
                    f"内存变化={memory_diff:.2f}MB, CPU使用={end_cpu}%")
        
        return result
    return wrapper