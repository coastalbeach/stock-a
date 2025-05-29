#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志管理模块

提供统一的日志记录功能，支持记录程序运行时间、运行是否完整、严重错误等信息
日志可以输出到文件和控制台，支持不同级别的日志记录
支持性能监控和运行状态跟踪
"""

import os
import sys
import time
import logging
import logging.handlers
import datetime
import threading
import traceback
import psutil
from pathlib import Path
import yaml

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)


class LoggerManager:
    """日志管理类
    
    提供统一的日志记录功能，支持记录程序运行时间、运行是否完整、严重错误等信息
    日志可以输出到文件和控制台，支持不同级别的日志记录
    支持性能监控和运行状态跟踪功能
    """
    
    # 单例模式，确保全局只有一个日志管理器实例
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_file=None):
        """初始化日志管理器
        
        Args:
            config_file (str, optional): 日志配置文件路径，默认为None，使用默认配置
        """
        # 避免重复初始化
        if self._initialized:
            return
            
        # 加载配置
        self.config = self._load_config(config_file)
        
        # 创建日志目录
        self.log_dir = os.path.join(project_root, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 初始化日志记录器字典
        self.loggers = {}
        
        # 性能监控相关
        self.performance_monitor = None
        self._start_performance_monitoring()
        
        # 运行状态跟踪
        self.run_status = {}
        
        # 标记为已初始化
        self._initialized = True
    
    def _load_config(self, config_file):
        """加载日志配置
        
        Args:
            config_file (str, optional): 配置文件路径
            
        Returns:
            dict: 日志配置字典
        """
        # 默认配置
        default_config = {
            'default_level': 'INFO',  # 默认日志级别
            'console_output': True,   # 是否输出到控制台
            'file_output': True,      # 是否输出到文件
            'max_bytes': 10485760,    # 单个日志文件最大字节数（10MB）
            'backup_count': 10,       # 备份文件数量
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
            'date_format': '%Y-%m-%d %H:%M:%S',  # 日期格式
            'modules': {  # 模块特定配置
                'stock_historical': {
                    'level': 'INFO',
                    'file': 'stock_historical.log'
                },
                'stock_financial': {
                    'level': 'INFO',
                    'file': 'stock_financial.log'
                },
                'index_quote': {
                    'level': 'INFO',
                    'file': 'index_quote.log'
                }
            }
        }
        
        # 如果提供了配置文件，则加载并合并配置
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    # 合并配置
                    if user_config:
                        # 合并顶层配置
                        for key, value in user_config.items():
                            if key != 'modules':
                                default_config[key] = value
                        
                        # 合并模块配置
                        if 'modules' in user_config:
                            for module, module_config in user_config['modules'].items():
                                if module in default_config['modules']:
                                    # 更新已有模块配置
                                    for k, v in module_config.items():
                                        default_config['modules'][module][k] = v
                                else:
                                    # 添加新模块配置
                                    default_config['modules'][module] = module_config
            except Exception as e:
                print(f"加载日志配置文件失败: {e}，使用默认配置")
        
        return default_config
    
    def get_logger(self, name):
        """获取指定名称的日志记录器
        
        Args:
            name (str): 日志记录器名称，通常为模块名
            
        Returns:
            logging.Logger: 日志记录器对象
        """
        # 如果已经创建过该日志记录器，则直接返回
        if name in self.loggers:
            return self.loggers[name]
        
        # 创建新的日志记录器
        logger = logging.getLogger(name)
        
        # 设置日志级别
        level_name = self.config['modules'].get(name, {}).get('level', self.config['default_level'])
        level = getattr(logging, level_name)
        logger.setLevel(level)
        
        # 防止日志重复输出
        if logger.handlers:
            return logger
        
        # 创建格式化器
        formatter = logging.Formatter(
            fmt=self.config['format'],
            datefmt=self.config['date_format']
        )
        
        # 添加控制台处理器
        if self.config['console_output']:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 添加文件处理器
        if self.config['file_output']:
            # 获取日志文件名
            log_file = self.config['modules'].get(name, {}).get('file', f"{name}.log")
            log_path = os.path.join(self.log_dir, log_file)
            
            # 创建按大小轮转的文件处理器
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_path,
                maxBytes=self.config['max_bytes'],
                backupCount=self.config['backup_count'],
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # 保存日志记录器
        self.loggers[name] = logger
        
        return logger
    
    def log_execution_time(self, logger_name, func_name, start_time, end_time=None, status="完成", details=None):
        """记录函数执行时间
        
        Args:
            logger_name (str): 日志记录器名称
            func_name (str): 函数名称
            start_time (float): 开始时间戳
            end_time (float, optional): 结束时间戳，默认为None，表示当前时间
            status (str, optional): 执行状态，默认为"完成"
            details (str, optional): 额外详情，默认为None
        """
        logger = self.get_logger(logger_name)
        
        # 如果未提供结束时间，则使用当前时间
        if end_time is None:
            end_time = time.time()
        
        # 计算执行时间
        execution_time = end_time - start_time
        
        # 格式化时间
        if execution_time < 1:  # 小于1秒
            time_str = f"{execution_time * 1000:.2f}毫秒"
        elif execution_time < 60:  # 小于1分钟
            time_str = f"{execution_time:.2f}秒"
        elif execution_time < 3600:  # 小于1小时
            minutes = int(execution_time // 60)
            seconds = execution_time % 60
            time_str = f"{minutes}分{seconds:.2f}秒"
        else:  # 大于等于1小时
            hours = int(execution_time // 3600)
            minutes = int((execution_time % 3600) // 60)
            seconds = execution_time % 60
            time_str = f"{hours}小时{minutes}分{seconds:.2f}秒"
        
        # 构建日志消息
        message = f"函数 {func_name} {status}，执行时间: {time_str}"
        if details:
            message += f"，详情: {details}"
        
        # 根据状态选择日志级别
        if status == "完成":
            logger.info(message)
        elif status == "部分完成":
            logger.warning(message)
        else:  # 失败或其他状态
            logger.error(message)
    
    def log_task_start(self, logger_name, task_name, details=None):
        """记录任务开始
        
        Args:
            logger_name (str): 日志记录器名称
            task_name (str): 任务名称
            details (str, optional): 额外详情，默认为None
            
        Returns:
            float: 开始时间戳
        """
        logger = self.get_logger(logger_name)
        
        # 获取当前时间戳
        start_time = time.time()
        
        # 构建日志消息
        message = f"任务 {task_name} 开始执行"
        if details:
            message += f"，详情: {details}"
        
        # 记录日志
        logger.info(message)
        
        return start_time
    
    def log_task_end(self, logger_name, task_name, start_time, status="完成", details=None):
        """记录任务结束
        
        Args:
            logger_name (str): 日志记录器名称
            task_name (str): 任务名称
            start_time (float): 开始时间戳
            status (str, optional): 执行状态，默认为"完成"
            details (str, optional): 额外详情，默认为None
            
        Returns:
            float: 结束时间戳
        """
        # 获取当前时间戳
        end_time = time.time()
        
        # 记录执行时间
        self.log_execution_time(logger_name, task_name, start_time, end_time, status, details)
        
        return end_time
    
    def log_error(self, logger_name, error_message, exception=None):
        """记录错误信息
        
        Args:
            logger_name (str): 日志记录器名称
            error_message (str): 错误消息
            exception (Exception, optional): 异常对象，默认为None
        """
        logger = self.get_logger(logger_name)
        
        # 构建日志消息
        message = error_message
        if exception:
            message += f": {str(exception)}"
        
        # 记录日志
        logger.error(message)
    
    def log_warning(self, logger_name, warning_message):
        """记录警告信息
        
        Args:
            logger_name (str): 日志记录器名称
            warning_message (str): 警告消息
        """
        logger = self.get_logger(logger_name)
        logger.warning(warning_message)
    
    def log_info(self, logger_name, info_message):
        """记录信息
        
        Args:
            logger_name (str): 日志记录器名称
            info_message (str): 信息消息
        """
        logger = self.get_logger(logger_name)
        logger.info(info_message)
    
    def log_debug(self, logger_name, debug_message):
        """记录调试信息
        
        Args:
            logger_name (str): 日志记录器名称
            debug_message (str): 调试消息
        """
        logger = self.get_logger(logger_name)
        logger.debug(debug_message)
    
    def _start_performance_monitoring(self):
        """启动性能监控
        
        根据配置启动性能监控线程，定期记录系统资源使用情况
        """
        # 检查是否启用性能监控
        if not self.config.get('performance_monitoring', {}).get('enabled', False):
            return
        
        # 创建性能监控专用日志记录器
        performance_logger = self.get_logger('performance')
        
        # 获取采样间隔
        sampling_interval = self.config.get('performance_monitoring', {}).get('sampling_interval', 60)
        
        # 定义监控函数
        def monitor_performance():
            process = psutil.Process(os.getpid())
            
            while True:
                try:
                    # 收集性能数据
                    stats = {}
                    
                    # 内存使用情况
                    if self.config.get('performance_monitoring', {}).get('memory_tracking', False):
                        memory_info = process.memory_info()
                        # 转换为更易读的格式
                        rss_mb = memory_info.rss / (1024 * 1024)  # 转换为MB
                        vms_mb = memory_info.vms / (1024 * 1024)  # 转换为MB
                        stats['memory'] = {
                            'rss': f"{rss_mb:.2f}MB",  # 物理内存使用
                            'vms': f"{vms_mb:.2f}MB",  # 虚拟内存使用
                            'percent': f"{process.memory_percent():.2f}%"  # 内存使用百分比
                        }
                        
                        # 获取系统内存信息
                        system_memory = psutil.virtual_memory()
                        stats['system_memory'] = {
                            'total': f"{system_memory.total / (1024 * 1024 * 1024):.2f}GB",
                            'available': f"{system_memory.available / (1024 * 1024 * 1024):.2f}GB",
                            'percent': f"{system_memory.percent:.2f}%"
                        }
                    
                    # CPU使用情况
                    if self.config.get('performance_monitoring', {}).get('cpu_tracking', False):
                        # 获取进程CPU使用率
                        process_cpu_percent = process.cpu_percent(interval=0.5)
                        # 获取系统CPU使用率
                        system_cpu_percent = psutil.cpu_percent(interval=0.5)
                        
                        stats['cpu'] = {
                            'process_percent': f"{process_cpu_percent:.2f}%",  # 进程CPU使用百分比
                            'system_percent': f"{system_cpu_percent:.2f}%",  # 系统CPU使用百分比
                            'threads': len(process.threads()),  # 线程数
                            'cores': psutil.cpu_count(logical=True)  # CPU核心数
                        }
                        
                        # 获取CPU频率信息（如果可用）
                        try:
                            cpu_freq = psutil.cpu_freq()
                            if cpu_freq:
                                stats['cpu']['frequency'] = f"{cpu_freq.current:.2f}MHz"
                        except Exception:
                            pass
                    
                    # 记录磁盘使用情况
                    try:
                        disk_usage = psutil.disk_usage(os.path.abspath(os.sep))
                        stats['disk'] = {
                            'total': f"{disk_usage.total / (1024 * 1024 * 1024):.2f}GB",
                            'used': f"{disk_usage.used / (1024 * 1024 * 1024):.2f}GB",
                            'free': f"{disk_usage.free / (1024 * 1024 * 1024):.2f}GB",
                            'percent': f"{disk_usage.percent:.2f}%"
                        }
                    except Exception:
                        pass
                    
                    # 记录性能数据
                    if stats:
                        performance_logger.info(f"性能监控: {stats}")
                    
                    # 等待下一次采样
                    time.sleep(sampling_interval)
                except Exception as e:
                    performance_logger.error(f"性能监控异常: {str(e)}")
                    # 记录详细的异常信息
                    performance_logger.error(f"异常详情: {traceback.format_exc()}")
                    time.sleep(sampling_interval)  # 发生异常时也等待一段时间
        
        # 创建并启动监控线程
        self.performance_monitor = threading.Thread(
            target=monitor_performance,
            daemon=True,  # 设为守护线程，主程序退出时自动结束
            name="PerformanceMonitor"
        )
        self.performance_monitor.start()
        
        # 记录监控启动信息
        performance_logger.info(f"性能监控已启动，采样间隔: {sampling_interval}秒")
        
        # 记录系统基本信息
        system_info = {
            'platform': sys.platform,
            'python_version': sys.version,
            'cpu_cores': psutil.cpu_count(logical=True),
            'memory_total': f"{psutil.virtual_memory().total / (1024 * 1024 * 1024):.2f}GB"
        }
        performance_logger.info(f"系统信息: {system_info}")
    
    def log_program_start(self, logger_name, program_name, version=None, args=None):
        """记录程序启动
        
        Args:
            logger_name (str): 日志记录器名称
            program_name (str): 程序名称
            version (str, optional): 程序版本，默认为None
            args (dict, optional): 启动参数，默认为None
            
        Returns:
            str: 运行ID，用于标识本次运行
        """
        # 检查是否启用运行状态跟踪
        if not self.config.get('run_status_tracking', {}).get('enabled', False):
            return None
            
        # 检查是否记录生命周期事件
        if not self.config.get('run_status_tracking', {}).get('lifecycle_events', False):
            return None
        
        logger = self.get_logger(logger_name)
        
        # 生成运行ID
        run_id = f"{program_name}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 记录启动信息
        message = f"程序启动: {program_name}"
        if version:
            message += f", 版本: {version}"
        if args:
            message += f", 参数: {args}"
        
        logger.info(message)
        
        # 保存运行状态
        self.run_status[run_id] = {
            'program': program_name,
            'start_time': time.time(),
            'status': 'running',
            'checkpoints': []
        }
        
        return run_id
    
    def log_program_end(self, logger_name, run_id, status="正常结束", details=None):
        """记录程序结束
        
        Args:
            logger_name (str): 日志记录器名称
            run_id (str): 运行ID，由log_program_start返回
            status (str, optional): 结束状态，默认为"正常结束"
            details (str, optional): 额外详情，默认为None
            
        Returns:
            dict: 包含程序运行完整信息的字典
        """
        # 检查是否启用运行状态跟踪
        if not self.config.get('run_status_tracking', {}).get('enabled', False):
            return None
            
        # 检查是否记录生命周期事件
        if not self.config.get('run_status_tracking', {}).get('lifecycle_events', False):
            return None
        
        # 检查运行ID是否存在
        if run_id not in self.run_status:
            return None
        
        logger = self.get_logger(logger_name)
        run_status_logger = self.get_logger('run_status')
        
        # 获取运行信息
        run_info = self.run_status[run_id]
        start_time = run_info['start_time']
        end_time = time.time()
        duration = end_time - start_time
        
        # 格式化运行时间
        if duration < 60:  # 小于1分钟
            time_str = f"{duration:.2f}秒"
        elif duration < 3600:  # 小于1小时
            minutes = int(duration // 60)
            seconds = duration % 60
            time_str = f"{minutes}分{seconds:.2f}秒"
        else:  # 大于等于1小时
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = duration % 60
            time_str = f"{hours}小时{minutes}分{seconds:.2f}秒"
        
        # 记录结束信息
        message = f"程序结束: {run_info['program']}, 状态: {status}, 运行时间: {time_str}"
        if details:
            message += f", 详情: {details}"
        
        # 根据状态选择日志级别
        if status == "正常结束":
            logger.info(message)
            run_status_logger.info(message)
        elif status == "部分完成":
            logger.warning(message)
            run_status_logger.warning(message)
        else:  # 异常结束或其他状态
            logger.error(message)
            run_status_logger.error(message)
        
        # 更新运行状态
        self.run_status[run_id].update({
            'end_time': end_time,
            'duration': duration,
            'duration_str': time_str,
            'status': status,
            'details': details
        })
        
        # 检查是否有未完成的检查点
        if self.config.get('run_status_tracking', {}).get('checkpoint_events', False):
            checkpoints = self.run_status[run_id].get('checkpoints', [])
            incomplete_checkpoints = [cp for cp in checkpoints if not cp.get('completed', False)]
            
            if incomplete_checkpoints:
                incomplete_msg = f"程序 {run_info['program']} 有 {len(incomplete_checkpoints)} 个检查点未完成"
                logger.warning(incomplete_msg)
                run_status_logger.warning(incomplete_msg)
                
                # 记录未完成的检查点
                for cp in incomplete_checkpoints:
                    cp_msg = f"未完成检查点: {cp.get('name')}, 开始于: {datetime.datetime.fromtimestamp(cp.get('start_time')).strftime('%Y-%m-%d %H:%M:%S')}"
                    logger.warning(cp_msg)
                    run_status_logger.warning(cp_msg)
        
        # 记录完整运行信息到运行状态日志
        run_summary = {
            'run_id': run_id,
            'program': run_info['program'],
            'start_time': datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': datetime.datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S'),
            'duration': time_str,
            'status': status,
            'checkpoints_total': len(self.run_status[run_id].get('checkpoints', [])),
            'checkpoints_completed': len([cp for cp in self.run_status[run_id].get('checkpoints', []) if cp.get('completed', False)])
        }
        
        run_status_logger.info(f"运行摘要: {run_summary}")
        
        return self.run_status[run_id]
        self.run_status[run_id]['status'] = status
        
        # 清理运行状态（可选，取决于是否需要保留历史记录）
        # del self.run_status[run_id]
    
    def start_checkpoint(self, logger_name, run_id, checkpoint_name, details=None):
        """开始一个检查点
        
        Args:
            logger_name (str): 日志记录器名称
            run_id (str): 运行ID，由log_program_start返回
            checkpoint_name (str): 检查点名称
            details (str, optional): 额外详情，默认为None
            
        Returns:
            str: 检查点ID
        """
        # 检查是否启用运行状态跟踪
        if not self.config.get('run_status_tracking', {}).get('enabled', False):
            return None
            
        # 检查是否记录检查点事件
        if not self.config.get('run_status_tracking', {}).get('checkpoint_events', False):
            return None
        
        # 检查运行ID是否存在
        if run_id not in self.run_status:
            return None
        
        logger = self.get_logger(logger_name)
        run_status_logger = self.get_logger('run_status')
        
        # 生成检查点ID
        checkpoint_id = f"{checkpoint_name}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 记录检查点开始信息
        message = f"开始检查点: {checkpoint_name}"
        if details:
            message += f", 详情: {details}"
        
        logger.info(message)
        run_status_logger.info(message)
        
        # 保存检查点信息
        checkpoint_info = {
            'id': checkpoint_id,
            'name': checkpoint_name,
            'start_time': time.time(),
            'completed': False,
            'status': '进行中'
        }
        if details:
            checkpoint_info['details'] = details
        
        # 确保checkpoints列表存在
        if 'checkpoints' not in self.run_status[run_id]:
            self.run_status[run_id]['checkpoints'] = []
            
        self.run_status[run_id]['checkpoints'].append(checkpoint_info)
        
        return checkpoint_id
    
    def complete_checkpoint(self, logger_name, run_id, checkpoint_id, status="成功", details=None):
        """完成一个检查点
        
        Args:
            logger_name (str): 日志记录器名称
            run_id (str): 运行ID，由log_program_start返回
            checkpoint_id (str): 检查点ID，由start_checkpoint返回
            status (str, optional): 检查点状态，默认为"成功"
            details (str, optional): 额外详情，默认为None
            
        Returns:
            bool: 是否成功完成检查点
        """
        # 检查是否启用运行状态跟踪
        if not self.config.get('run_status_tracking', {}).get('enabled', False):
            return False
            
        # 检查是否记录检查点事件
        if not self.config.get('run_status_tracking', {}).get('checkpoint_events', False):
            return False
        
        # 检查运行ID是否存在
        if run_id not in self.run_status:
            return False
        
        logger = self.get_logger(logger_name)
        run_status_logger = self.get_logger('run_status')
        
        # 查找检查点
        checkpoint = None
        for cp in self.run_status[run_id].get('checkpoints', []):
            if cp.get('id') == checkpoint_id:
                checkpoint = cp
                break
        
        if not checkpoint:
            logger.warning(f"找不到检查点ID: {checkpoint_id}")
            return False
        
        # 计算检查点执行时间
        start_time = checkpoint.get('start_time', time.time())
        end_time = time.time()
        duration = end_time - start_time
        
        # 格式化执行时间
        if duration < 1:  # 小于1秒
            time_str = f"{duration * 1000:.2f}毫秒"
        elif duration < 60:  # 小于1分钟
            time_str = f"{duration:.2f}秒"
        elif duration < 3600:  # 小于1小时
            minutes = int(duration // 60)
            seconds = duration % 60
            time_str = f"{minutes}分{seconds:.2f}秒"
        else:  # 大于等于1小时
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = duration % 60
            time_str = f"{hours}小时{minutes}分{seconds:.2f}秒"
        
        # 记录检查点完成信息
        message = f"完成检查点: {checkpoint.get('name')}, 状态: {status}, 耗时: {time_str}"
        if details:
            message += f", 详情: {details}"
        
        # 根据状态选择日志级别
        if status == "成功":
            logger.info(message)
            run_status_logger.info(message)
        elif status == "警告":
            logger.warning(message)
            run_status_logger.warning(message)
        else:  # 失败或其他状态
            logger.error(message)
            run_status_logger.error(message)
        
        # 更新检查点信息
        checkpoint.update({
            'end_time': end_time,
            'duration': duration,
            'duration_str': time_str,
            'completed': True,
            'status': status
        })
        if details:
            checkpoint['details'] = details if not checkpoint.get('details') else f"{checkpoint.get('details')}; {details}"
        
        return True
        
    def log_checkpoint(self, logger_name, run_id, checkpoint_name, status="成功", details=None):
        """记录关键检查点（兼容旧版本）
        
        Args:
            logger_name (str): 日志记录器名称
            run_id (str): 运行ID，由log_program_start返回
            checkpoint_name (str): 检查点名称
            status (str, optional): 检查点状态，默认为"成功"
            details (str, optional): 额外详情，默认为None
        """
        # 检查是否启用运行状态跟踪
        if not self.config.get('run_status_tracking', {}).get('enabled', False):
            return
            
        # 检查是否记录检查点事件
        if not self.config.get('run_status_tracking', {}).get('checkpoint_events', False):
            return
        
        # 检查运行ID是否存在
        if run_id not in self.run_status:
            return
        
        logger = self.get_logger(logger_name)
        run_status_logger = self.get_logger('run_status')
        
        # 记录检查点信息
        message = f"检查点: {checkpoint_name}, 状态: {status}"
        if details:
            message += f", 详情: {details}"
        
        # 根据状态选择日志级别
        if status == "成功":
            logger.info(message)
            run_status_logger.info(message)
        elif status == "警告":
            logger.warning(message)
            run_status_logger.warning(message)
        else:  # 失败或其他状态
            logger.error(message)
            run_status_logger.error(message)
        
        # 保存检查点信息
        checkpoint_info = {
            'name': checkpoint_name,
            'time': time.time(),
            'status': status,
            'completed': True
        }
        if details:
            checkpoint_info['details'] = details
        
        # 确保checkpoints列表存在
        if 'checkpoints' not in self.run_status[run_id]:
            self.run_status[run_id]['checkpoints'] = []
            
        self.run_status[run_id]['checkpoints'].append(checkpoint_info)
    
    def log_exception(self, logger_name, error_message, exception, include_traceback=True, notify=False):
        """记录异常信息
        
        Args:
            logger_name (str): 日志记录器名称
            error_message (str): 错误消息
            exception (Exception): 异常对象
            include_traceback (bool, optional): 是否包含堆栈跟踪，默认为True
            notify (bool, optional): 是否需要通知，默认为False
        """
        logger = self.get_logger(logger_name)
        
        # 获取异常类型
        exception_type = type(exception).__name__
        
        # 构建日志消息
        message = f"{error_message}: [{exception_type}] {str(exception)}"
        
        # 添加堆栈跟踪
        if include_traceback:
            tb_str = traceback.format_exc()
            message += f"\n堆栈跟踪:\n{tb_str}"
        
        # 记录日志
        logger.error(message)
        
        # 记录到运行状态日志
        run_status_logger = self.get_logger('run_status')
        run_status_logger.error(f"异常: {logger_name} - {error_message}: [{exception_type}] {str(exception)}")
        
        # 如果需要通知，可以在这里添加通知逻辑
        # 例如发送邮件、短信等
        if notify:
            self._send_error_notification(logger_name, error_message, exception, tb_str if include_traceback else None)
    
    def _send_error_notification(self, logger_name, error_message, exception, traceback_str=None):
        """发送错误通知
        
        Args:
            logger_name (str): 日志记录器名称
            error_message (str): 错误消息
            exception (Exception): 异常对象
            traceback_str (str, optional): 堆栈跟踪字符串，默认为None
        """
        # 这里可以实现通知逻辑，例如发送邮件、短信等
        # 目前只记录一条日志，表示已通知
        notify_logger = self.get_logger('notification')
        notify_logger.warning(f"需要通知的错误: {logger_name} - {error_message}: {str(exception)}")
        
    def get_system_info(self):
        """获取系统信息
        
        Returns:
            dict: 系统信息字典
        """
        try:
            # 获取基本系统信息
            system_info = {
                'platform': sys.platform,
                'python_version': sys.version,
                'hostname': os.uname().nodename if hasattr(os, 'uname') else platform.node(),
                'cpu_cores': psutil.cpu_count(logical=True),
                'cpu_physical': psutil.cpu_count(logical=False),
                'memory_total': f"{psutil.virtual_memory().total / (1024 * 1024 * 1024):.2f}GB",
                'disk_total': f"{psutil.disk_usage(os.path.abspath(os.sep)).total / (1024 * 1024 * 1024):.2f}GB"
            }
            
            # 获取更多详细信息
            try:
                import platform
                system_info.update({
                    'os_name': platform.system(),
                    'os_version': platform.version(),
                    'os_release': platform.release(),
                    'machine': platform.machine()
                })
            except Exception:
                pass
                
            return system_info
        except Exception as e:
            # 如果获取系统信息失败，返回基本信息
            return {
                'platform': sys.platform,
                'error': f"获取系统信息失败: {str(e)}"
            }
            
    def monitor_database(self, logger_name, db_type, operation, start_time, end_time=None, status="成功", details=None):
        """监控数据库操作
        
        记录数据库操作的执行时间和状态，用于性能监控和问题排查
        
        Args:
            logger_name (str): 日志记录器名称
            db_type (str): 数据库类型，如 'postgresql', 'redis' 等
            operation (str): 操作描述，如 'query', 'insert', 'update' 等
            start_time (float): 开始时间戳
            end_time (float, optional): 结束时间戳，默认为None，表示当前时间
            status (str, optional): 执行状态，默认为"成功"
            details (str, optional): 额外详情，默认为None
        """
        logger = self.get_logger(logger_name)
        db_logger = self.get_logger('database')
        
        # 如果未提供结束时间，则使用当前时间
        if end_time is None:
            end_time = time.time()
        
        # 计算执行时间
        execution_time = end_time - start_time
        
        # 格式化时间
        if execution_time < 0.1:  # 小于0.1秒
            time_str = f"{execution_time * 1000:.2f}毫秒"
        elif execution_time < 1:  # 小于1秒
            time_str = f"{execution_time * 1000:.2f}毫秒"
        else:  # 大于等于1秒
            time_str = f"{execution_time:.2f}秒"
        
        # 构建日志消息
        message = f"数据库操作: [{db_type}] {operation}, 状态: {status}, 执行时间: {time_str}"
        if details:
            message += f", 详情: {details}"
        
        # 根据状态和执行时间选择日志级别
        if status != "成功":
            logger.error(message)
            db_logger.error(message)
        elif execution_time > 1.0:  # 执行时间超过1秒，记录为警告
            logger.warning(message)
            db_logger.warning(message)
        else:
            logger.info(message)
            db_logger.info(message)
        
        # 如果是性能监控模块启用，记录到性能日志
        if self.config.get('performance_monitoring', {}).get('enabled', False):
            performance_logger = self.get_logger('performance')
            performance_data = {
                'type': 'database',
                'db_type': db_type,
                'operation': operation,
                'execution_time': execution_time,
                'execution_time_str': time_str,
                'status': status,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            if details:
                performance_data['details'] = details
            
            performance_logger.info(f"数据库性能: {performance_data}")
        
        return execution_time


# 创建全局日志管理器实例
logger_manager = LoggerManager(os.path.join(project_root, 'config', 'logger.yaml'))


class LogContext:
    """日志上下文管理器
    
    用于跟踪代码块的执行情况，自动记录开始和结束时间，以及异常信息
    
    Example:
        with LogContext('data_storage', '数据导入', run_id) as ctx:
            # 执行代码
            ctx.log_info('正在处理数据...')
    """
    
    def __init__(self, logger_name, context_name, run_id=None, checkpoint=False, details=None):
        """初始化日志上下文
        
        Args:
            logger_name (str): 日志记录器名称
            context_name (str): 上下文名称
            run_id (str, optional): 运行ID，默认为None
            checkpoint (bool, optional): 是否作为检查点记录，默认为False
            details (str, optional): 额外详情，默认为None
        """
        self.logger_name = logger_name
        self.context_name = context_name
        self.run_id = run_id
        self.checkpoint = checkpoint
        self.details = details
        self.checkpoint_id = None
        self.logger = logger_manager.get_logger(logger_name)
        self.start_time = None
    
    def __enter__(self):
        """进入上下文
        
        Returns:
            LogContext: 上下文对象
        """
        self.start_time = time.time()
        
        # 记录开始信息
        message = f"开始执行: {self.context_name}"
        if self.details:
            message += f", 详情: {self.details}"
        self.logger.info(message)
        
        # 如果需要作为检查点记录
        if self.checkpoint and self.run_id:
            self.checkpoint_id = logger_manager.start_checkpoint(
                self.logger_name,
                self.run_id,
                self.context_name,
                self.details
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常回溯
            
        Returns:
            bool: 是否处理了异常
        """
        end_time = time.time()
        duration = end_time - self.start_time
        
        # 格式化执行时间
        if duration < 1:  # 小于1秒
            time_str = f"{duration * 1000:.2f}毫秒"
        elif duration < 60:  # 小于1分钟
            time_str = f"{duration:.2f}秒"
        elif duration < 3600:  # 小于1小时
            minutes = int(duration // 60)
            seconds = duration % 60
            time_str = f"{minutes}分{seconds:.2f}秒"
        else:  # 大于等于1小时
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = duration % 60
            time_str = f"{hours}小时{minutes}分{seconds:.2f}秒"
        
        # 处理异常情况
        if exc_type is not None:
            # 记录异常信息
            error_message = f"执行失败: {self.context_name}, 耗时: {time_str}, 异常: {exc_val}"
            self.logger.error(error_message)
            
            # 记录详细异常信息
            logger_manager.log_exception(self.logger_name, f"{self.context_name} 执行失败", exc_val)
            
            # 如果是检查点，标记为失败
            if self.checkpoint and self.run_id and self.checkpoint_id:
                logger_manager.complete_checkpoint(
                    self.logger_name,
                    self.run_id,
                    self.checkpoint_id,
                    "失败",
                    f"异常: {exc_val}"
                )
            
            # 不处理异常，让异常继续传播
            return False
        else:
            # 记录成功信息
            message = f"执行完成: {self.context_name}, 耗时: {time_str}"
            self.logger.info(message)
            
            # 如果是检查点，标记为成功
            if self.checkpoint and self.run_id and self.checkpoint_id:
                logger_manager.complete_checkpoint(
                    self.logger_name,
                    self.run_id,
                    self.checkpoint_id,
                    "成功"
                )
            
            return True
    
    def log_info(self, message):
        """记录信息
        
        Args:
            message (str): 信息消息
        """
        self.logger.info(message)
    
    def log_warning(self, message):
        """记录警告
        
        Args:
            message (str): 警告消息
        """
        self.logger.warning(message)
    
    def log_error(self, message, exception=None):
        """记录错误
        
        Args:
            message (str): 错误消息
            exception (Exception, optional): 异常对象，默认为None
        """
        if exception:
            logger_manager.log_error(self.logger_name, message, exception)
        else:
            self.logger.error(message)


def get_logger(name):
    """获取指定名称的日志记录器（便捷函数）
    
    Args:
        name (str): 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器对象
    """
    return logger_manager.get_logger(name)


def log_execution_time(logger_name, func_name, start_time, end_time=None, status="完成", details=None):
    """记录函数执行时间（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        func_name (str): 函数名称
        start_time (float): 开始时间戳
        end_time (float, optional): 结束时间戳，默认为None，表示当前时间
        status (str, optional): 执行状态，默认为"完成"
        details (str, optional): 额外详情，默认为None
    """
    logger_manager.log_execution_time(logger_name, func_name, start_time, end_time, status, details)


def track_execution(logger_name, run_id=None, checkpoint=False):
    """函数执行跟踪装饰器
    
    用于跟踪函数的执行时间和状态，自动记录日志
    
    Args:
        logger_name (str): 日志记录器名称
        run_id (str, optional): 运行ID，默认为None，表示不关联到特定运行
        checkpoint (bool, optional): 是否作为检查点记录，默认为False
        
    Returns:
        function: 装饰器函数
    
    Example:
        @track_execution('data_storage')
        def process_data(data):
            # 处理数据
            return result
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数名
            func_name = func.__name__
            
            # 记录开始时间
            start_time = time.time()
            checkpoint_id = None
            
            # 如果需要作为检查点记录
            if checkpoint and run_id:
                checkpoint_id = logger_manager.start_checkpoint(
                    logger_name, 
                    run_id, 
                    f"函数:{func_name}", 
                    f"参数: {args}, {kwargs}"
                )
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录结束时间
                end_time = time.time()
                
                # 记录执行时间
                logger_manager.log_execution_time(
                    logger_name, 
                    func_name, 
                    start_time, 
                    end_time, 
                    "完成"
                )
                
                # 如果是检查点，标记为完成
                if checkpoint and run_id and checkpoint_id:
                    logger_manager.complete_checkpoint(
                        logger_name, 
                        run_id, 
                        checkpoint_id, 
                        "成功", 
                        f"返回值类型: {type(result).__name__}"
                    )
                
                return result
            except Exception as e:
                # 记录结束时间
                end_time = time.time()
                
                # 记录执行时间和异常
                error_details = f"异常: {str(e)}"
                logger_manager.log_execution_time(
                    logger_name, 
                    func_name, 
                    start_time, 
                    end_time, 
                    "失败", 
                    error_details
                )
                
                # 记录详细异常信息
                logger_manager.log_exception(logger_name, f"函数 {func_name} 执行失败", e)
                
                # 如果是检查点，标记为失败
                if checkpoint and run_id and checkpoint_id:
                    logger_manager.complete_checkpoint(
                        logger_name, 
                        run_id, 
                        checkpoint_id, 
                        "失败", 
                        error_details
                    )
                
                # 重新抛出异常
                raise
        
        return wrapper
    
    return decorator


def log_task_start(logger_name, task_name, details=None):
    """记录任务开始（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        task_name (str): 任务名称
        details (str, optional): 额外详情，默认为None
        
    Returns:
        float: 开始时间戳
    """
    return logger_manager.log_task_start(logger_name, task_name, details)


def log_task_end(logger_name, task_name, start_time, status="完成", details=None):
    """记录任务结束（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        task_name (str): 任务名称
        start_time (float): 开始时间戳
        status (str, optional): 执行状态，默认为"完成"
        details (str, optional): 额外详情，默认为None
        
    Returns:
        float: 结束时间戳
    """
    return logger_manager.log_task_end(logger_name, task_name, start_time, status, details)


def log_program_start(logger_name, program_name, version=None, args=None):
    """记录程序启动（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        program_name (str): 程序名称
        version (str, optional): 程序版本，默认为None
        args (dict, optional): 启动参数，默认为None
        
    Returns:
        str: 运行ID，用于标识本次运行
    """
    return logger_manager.log_program_start(logger_name, program_name, version, args)


def log_program_end(logger_name, run_id, status="正常结束", details=None):
    """记录程序结束（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        run_id (str): 运行ID，由log_program_start返回
        status (str, optional): 结束状态，默认为"正常结束"
        details (str, optional): 额外详情，默认为None
        
    Returns:
        dict: 包含程序运行完整信息的字典
    """
    return logger_manager.log_program_end(logger_name, run_id, status, details)


def start_checkpoint(logger_name, run_id, checkpoint_name, details=None):
    """开始一个检查点（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        run_id (str): 运行ID，由log_program_start返回
        checkpoint_name (str): 检查点名称
        details (str, optional): 额外详情，默认为None
        
    Returns:
        str: 检查点ID
    """
    return logger_manager.start_checkpoint(logger_name, run_id, checkpoint_name, details)


def complete_checkpoint(logger_name, run_id, checkpoint_id, status="成功", details=None):
    """完成一个检查点（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        run_id (str): 运行ID，由log_program_start返回
        checkpoint_id (str): 检查点ID，由start_checkpoint返回
        status (str, optional): 检查点状态，默认为"成功"
        details (str, optional): 额外详情，默认为None
        
    Returns:
        bool: 是否成功完成检查点
    """
    return logger_manager.complete_checkpoint(logger_name, run_id, checkpoint_id, status, details)


def log_checkpoint(logger_name, run_id, checkpoint_name, status="成功", details=None):
    """记录关键检查点（便捷函数，兼容旧版本）
    
    Args:
        logger_name (str): 日志记录器名称
        run_id (str): 运行ID，由log_program_start返回
        checkpoint_name (str): 检查点名称
        status (str, optional): 检查点状态，默认为"成功"
        details (str, optional): 额外详情，默认为None
    """
    logger_manager.log_checkpoint(logger_name, run_id, checkpoint_name, status, details)


def log_error(logger_name, error_message, exception=None):
    """记录错误信息（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        error_message (str): 错误消息
        exception (Exception, optional): 异常对象，默认为None
    """
    logger_manager.log_error(logger_name, error_message, exception)


def log_warning(logger_name, warning_message):
    """记录警告信息（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        warning_message (str): 警告消息
    """
    logger_manager.log_warning(logger_name, warning_message)


def log_info(logger_name, info_message):
    """记录信息（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        info_message (str): 信息消息
    """
    logger_manager.log_info(logger_name, info_message)


def log_debug(logger_name, debug_message):
    """记录调试信息（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        debug_message (str): 调试消息
    """
    logger_manager.log_debug(logger_name, debug_message)


def log_program_start(logger_name, program_name, version=None, args=None):
    """记录程序启动（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        program_name (str): 程序名称
        version (str, optional): 程序版本，默认为None
        args (dict, optional): 启动参数，默认为None
        
    Returns:
        str: 运行ID，用于标识本次运行
    """
    return logger_manager.log_program_start(logger_name, program_name, version, args)


def log_program_end(logger_name, run_id, status="正常结束", details=None):
    """记录程序结束（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        run_id (str): 运行ID，由log_program_start返回
        status (str, optional): 结束状态，默认为"正常结束"
        details (str, optional): 额外详情，默认为None
    """
    logger_manager.log_program_end(logger_name, run_id, status, details)


def log_checkpoint(logger_name, run_id, checkpoint_name, status="成功", details=None):
    """记录关键检查点（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        run_id (str): 运行ID，由log_program_start返回
        checkpoint_name (str): 检查点名称
        status (str, optional): 检查点状态，默认为"成功"
        details (str, optional): 额外详情，默认为None
    """
    logger_manager.log_checkpoint(logger_name, run_id, checkpoint_name, status, details)


def log_exception(logger_name, error_message, exception, include_traceback=True, notify=False):
    """记录异常信息（便捷函数）
    
    Args:
        logger_name (str): 日志记录器名称
        error_message (str): 错误消息
        exception (Exception): 异常对象
        include_traceback (bool, optional): 是否包含堆栈跟踪，默认为True
        notify (bool, optional): 是否需要通知，默认为False
    """
    logger_manager.log_exception(logger_name, error_message, exception, include_traceback, notify)


def get_system_info():
    """获取系统信息（便捷函数）
    
    Returns:
        dict: 系统信息字典
    """
    return logger_manager.get_system_info()


def monitor_database(logger_name, db_type, operation, start_time, end_time=None, status="成功", details=None):
    """监控数据库操作（便捷函数）
    
    记录数据库操作的执行时间和状态，用于性能监控和问题排查
    
    Args:
        logger_name (str): 日志记录器名称
        db_type (str): 数据库类型，如 'postgresql', 'redis' 等
        operation (str): 操作描述，如 'query', 'insert', 'update' 等
        start_time (float): 开始时间戳
        end_time (float, optional): 结束时间戳，默认为None，表示当前时间
        status (str, optional): 执行状态，默认为"成功"
        details (str, optional): 额外详情，默认为None
        
    Returns:
        float: 执行时间（秒）
    """
    return logger_manager.monitor_database(logger_name, db_type, operation, start_time, end_time, status, details)


def db_operation(logger_name, db_type, operation=None, details=None):
    """数据库操作装饰器
    
    用于跟踪数据库操作的执行时间和状态，自动记录日志
    
    Args:
        logger_name (str): 日志记录器名称
        db_type (str): 数据库类型，如 'postgresql', 'redis' 等
        operation (str, optional): 操作描述，默认为None，将使用函数名
        details (str, optional): 额外详情，默认为None
        
    Returns:
        function: 装饰器函数
    
    Example:
        @db_operation('data_storage', 'postgresql', '查询股票数据')
        def query_stock_data(code):
            # 数据库操作
            return result
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取操作名称
            op_name = operation if operation else func.__name__
            
            # 记录开始时间
            start_time = time.time()
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录数据库操作
                monitor_database(
                    logger_name,
                    db_type,
                    op_name,
                    start_time,
                    details=details if details else f"参数: {args}, {kwargs}"
                )
                
                return result
            except Exception as e:
                # 记录失败的数据库操作
                monitor_database(
                    logger_name,
                    db_type,
                    op_name,
                    start_time,
                    status="失败",
                    details=f"异常: {str(e)}"
                )
                
                # 记录异常
                log_exception(logger_name, f"数据库操作失败: {op_name}", e)
                
                # 重新抛出异常
                raise
        
        return wrapper
    
    return decorator


# 示例：如何使用日志系统
def example_usage():
    """日志系统使用示例
    
    此函数展示了如何使用日志系统的各种功能
    """
    # 获取日志记录器
    logger = get_logger('example')
    
    # 记录程序启动
    run_id = log_program_start('example', '示例程序', '1.0.0', {'arg1': 'value1'})
    
    try:
        # 记录任务开始
        logger.info('开始执行示例任务')
        
        # 使用装饰器跟踪函数执行
        @track_execution('example', run_id, checkpoint=True)
        def example_function(x, y):
            logger.info(f'计算 {x} + {y}')
            return x + y
        
        # 调用函数
        result = example_function(10, 20)
        logger.info(f'计算结果: {result}')
        
        # 使用上下文管理器跟踪代码块执行
        with LogContext('example', '数据处理', run_id, checkpoint=True) as ctx:
            ctx.log_info('正在处理数据...')
            # 模拟数据处理
            time.sleep(1)
            ctx.log_info('数据处理完成')
        
        # 手动创建和完成检查点
        cp_id = start_checkpoint('example', run_id, '文件导出')
        try:
            # 模拟文件导出
            logger.info('正在导出文件...')
            time.sleep(1)
            logger.info('文件导出完成')
            complete_checkpoint('example', run_id, cp_id, '成功', '导出了10个文件')
        except Exception as e:
            complete_checkpoint('example', run_id, cp_id, '失败', f'异常: {str(e)}')
            raise
        
        # 监控数据库操作示例
        # 1. PostgreSQL查询示例
        db_start_time = time.time()
        try:
            # 模拟数据库查询
            logger.info('执行PostgreSQL查询...')
            time.sleep(0.5)  # 模拟查询耗时
            # 记录数据库操作
            monitor_database(
                'example', 
                'postgresql', 
                'SELECT * FROM 日线行情 WHERE 股票代码 = \'000001\'', 
                db_start_time, 
                details='查询股票日线数据'
            )
        except Exception as e:
            # 记录失败的数据库操作
            monitor_database(
                'example', 
                'postgresql', 
                'SELECT查询', 
                db_start_time, 
                status='失败', 
                details=f'异常: {str(e)}'
            )
        
        # 2. Redis操作示例
        redis_start = time.time()
        try:
            # 模拟Redis操作
            logger.info('执行Redis缓存操作...')
            time.sleep(0.1)  # 模拟操作耗时
            # 记录数据库操作
            monitor_database(
                'example', 
                'redis', 
                'SET', 
                redis_start, 
                details='缓存股票列表数据'
            )
        except Exception as e:
            # 记录失败的数据库操作
            monitor_database(
                'example', 
                'redis', 
                'SET', 
                redis_start, 
                status='失败', 
                details=f'异常: {str(e)}'
            )
        
        # 3. 使用数据库操作装饰器示例
        # 定义带有数据库操作装饰器的函数
        @db_operation('example', 'postgresql', '查询股票列表', '获取所有A股股票列表')
        def query_stock_list():
            logger.info('查询股票列表...')
            # 模拟数据库查询
            time.sleep(0.3)
            return ['000001', '000002', '000003']
        
        @db_operation('example', 'redis', '获取缓存')
        def get_cached_data(key):
            logger.info(f'获取缓存数据: {key}')
            # 模拟Redis操作
            time.sleep(0.1)
            return {'data': 'cached_value'}
        
        # 调用带装饰器的函数
        stocks = query_stock_list()
        logger.info(f'获取到股票列表: {stocks}')
        
        cached_data = get_cached_data('market_summary')
        logger.info(f'获取到缓存数据: {cached_data}')
        
        # 获取并记录系统信息
        system_info = get_system_info()
        logger.info(f'系统信息: {system_info}')
        
        # 记录程序结束
        log_program_end('example', run_id, '正常结束', '所有任务已完成')
        
    except Exception as e:
        # 记录异常
        log_exception('example', '程序执行异常', e, notify=True)
        # 记录程序异常结束
        log_program_end('example', run_id, '异常结束', f'发生错误: {str(e)}')



# 上下文管理器：跟踪代码块执行
class CodeBlockTracker:
    """代码块执行跟踪上下文管理器
    
    用于跟踪代码块的执行情况，记录开始和结束时间，以及执行状态
    
    Example:
        with CodeBlockTracker("module_name", "操作名称") as tracker:
            # 执行代码
            tracker.checkpoint("步骤1完成")
            # 继续执行代码
    """
    
    def __init__(self, logger_name, block_name, run_id=None):
        """初始化代码块跟踪器
        
        Args:
            logger_name (str): 日志记录器名称
            block_name (str): 代码块名称
            run_id (str, optional): 运行ID，默认为None，将自动生成
        """
        self.logger_name = logger_name
        self.block_name = block_name
        self.run_id = run_id
        self.start_time = None
        self.checkpoints = []
    
    def __enter__(self):
        """进入上下文
        
        Returns:
            CodeBlockTracker: 返回自身，便于在with语句中使用
        """
        # 如果没有提供运行ID，则自动生成
        if not self.run_id:
            self.run_id = log_program_start(self.logger_name, self.block_name)
        else:
            # 记录代码块开始
            log_checkpoint(self.logger_name, self.run_id, f"{self.block_name}开始", status="成功")
        
        # 记录开始时间
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常回溯
            
        Returns:
            bool: 是否处理了异常
        """
        # 计算执行时间
        end_time = time.time()
        duration = end_time - self.start_time
        
        # 检查是否发生异常
        if exc_type is not None:
            # 记录异常
            log_exception(self.logger_name, f"{self.block_name}执行异常", exc_val)
            log_checkpoint(self.logger_name, self.run_id, f"{self.block_name}结束", status="失败", details=str(exc_val))
            log_program_end(self.logger_name, self.run_id, status="异常结束", details=str(exc_val))
        else:
            # 记录正常结束
            log_checkpoint(self.logger_name, self.run_id, f"{self.block_name}结束", status="成功", details=f"执行时间: {duration:.2f}秒")
            log_program_end(self.logger_name, self.run_id, status="正常结束")
        
        # 不处理异常，让异常继续传播
        return False
    
    def checkpoint(self, checkpoint_name, status="成功", details=None):
        """记录检查点
        
        Args:
            checkpoint_name (str): 检查点名称
            status (str, optional): 检查点状态，默认为"成功"
            details (str, optional): 额外详情，默认为None
            
        Returns:
            CodeBlockTracker: 返回自身，便于链式调用
        """
        log_checkpoint(self.logger_name, self.run_id, checkpoint_name, status, details)
        self.checkpoints.append({
            'name': checkpoint_name,
            'time': time.time(),
            'status': status
        })
        return self


# 装饰器：记录函数执行时间
def time_logger(logger_name, func_name=None):
    """函数执行时间记录装饰器
    
    Args:
        logger_name (str): 日志记录器名称
        func_name (str, optional): 函数名称，默认为None，使用被装饰函数的名称
        
    Returns:
        function: 装饰器函数
    """
    def decorator(func):
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数名称
            name = func_name if func_name else func.__name__
            
            # 记录开始时间
            start_time = time.time()
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录结束时间
                log_execution_time(logger_name, name, start_time)
                
                return result
            except Exception as e:
                # 记录异常
                log_execution_time(logger_name, name, start_time, status="失败", details=str(e))
                raise
        return wrapper
    return decorator


# 装饰器：跟踪函数执行过程中的检查点
def checkpoint_tracker(logger_name, program_name=None):
    """函数执行检查点跟踪装饰器
    
    用于跟踪函数执行过程中的关键检查点，记录函数的完整执行流程
    
    Args:
        logger_name (str): 日志记录器名称
        program_name (str, optional): 程序名称，默认为None，使用被装饰函数的名称
        
    Returns:
        function: 装饰器函数
    """
    def decorator(func):
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数名称
            name = program_name if program_name else func.__name__
            
            # 记录程序启动
            run_id = log_program_start(logger_name, name)
            
            # 记录初始检查点
            log_checkpoint(logger_name, run_id, f"{name}开始", status="成功")
            
            try:
                # 执行函数
                result = func(*args, **kwargs, _run_id=run_id, _logger_name=logger_name)
                
                # 记录成功完成检查点
                log_checkpoint(logger_name, run_id, f"{name}完成", status="成功")
                
                # 记录程序结束
                log_program_end(logger_name, run_id, status="正常结束")
                
                return result
            except Exception as e:
                # 记录异常检查点
                log_checkpoint(logger_name, run_id, f"{name}异常", status="失败", details=str(e))
                
                # 记录异常详情
                log_exception(logger_name, f"{name}执行失败", e)
                
                # 记录程序结束
                log_program_end(logger_name, run_id, status="异常结束", details=str(e))
                
                # 重新抛出异常
                raise
        return wrapper
    return decorator


# 示例用法
if __name__ == "__main__":
    # 获取日志记录器
    logger = get_logger("test")
    
    # 记录不同级别的日志
    logger.debug("这是一条调试日志")
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    
    # 使用便捷函数
    log_info("test", "使用便捷函数记录信息")
    
    # 记录任务执行时间
    start_time = log_task_start("test", "测试任务")
    time.sleep(1)  # 模拟任务执行
    log_task_end("test", "测试任务", start_time)
    
    # 使用时间记录装饰器
    print("\n演示时间记录装饰器:")
    @time_logger("test")
    def test_function():
        time.sleep(0.5)  # 模拟函数执行
        print("函数执行完成")
    
    test_function()
    
    # 演示程序生命周期记录
    print("\n演示程序生命周期记录:")
    run_id = log_program_start("test", "示例程序", version="1.0.0", args={"mode": "test"})
    
    # 记录检查点
    print("记录检查点...")
    log_checkpoint("test", run_id, "初始化", status="成功", details="配置加载完成")
    
    # 模拟一些操作
    time.sleep(0.5)
    
    # 记录警告检查点
    log_checkpoint("test", run_id, "数据处理", status="警告", details="部分数据缺失")
    
    # 模拟一些操作
    time.sleep(0.5)
    
    # 记录异常
    try:
        # 模拟异常
        raise ValueError("示例异常")
    except Exception as e:
        log_exception("test", "处理数据时发生错误", e)
        log_checkpoint("test", run_id, "错误处理", status="失败", details="发生异常")
    
    # 记录程序结束
    log_program_end("test", run_id, status="部分完成", details="演示目的提前结束")
    
    # 演示检查点跟踪装饰器
    print("\n演示检查点跟踪装饰器:")
    
    # 定义一个使用检查点跟踪装饰器的函数
    @checkpoint_tracker("test", "数据处理流程")
    def process_data(_run_id=None, _logger_name=None):
        # 注意：_run_id和_logger_name是装饰器传入的参数，必须在函数定义中包含
        print("开始处理数据...")
        
        # 使用传入的运行ID记录检查点
        if _run_id and _logger_name:
            log_checkpoint(_logger_name, _run_id, "数据加载", status="成功")
        
        # 模拟数据处理
        time.sleep(0.5)
        
        # 记录另一个检查点
        if _run_id and _logger_name:
            log_checkpoint(_logger_name, _run_id, "数据转换", status="成功")
        
        # 模拟更多处理
        time.sleep(0.5)
        
        print("数据处理完成")
        return "处理结果"
    
    # 调用带检查点跟踪的函数
    try:
        result = process_data()
        print(f"处理结果: {result}")
    except Exception as e:
        print(f"处理失败: {e}")
    
    # 演示上下文管理器
    print("\n演示代码块跟踪上下文管理器:")
    try:
        # 使用上下文管理器跟踪代码块执行
        with CodeBlockTracker("test", "数据分析流程") as tracker:
            print("开始数据分析...")
            
            # 记录第一个检查点
            tracker.checkpoint("数据准备")
            time.sleep(0.3)  # 模拟操作
            
            # 记录第二个检查点
            tracker.checkpoint("数据分析中")
            time.sleep(0.3)  # 模拟操作
            
            # 记录带详情的检查点
            tracker.checkpoint("分析完成", details="共处理10条记录")
            print("数据分析完成")
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
    
    print("\n日志记录演示完成，请查看logs目录下的日志文件")
    print("性能监控（如已启用）将在后台线程中继续运行")
    print("实际应用中，性能监控会随主程序一起退出")