# -*- coding: utf-8 -*-
"""
基于文件的衍生指标运行器

使用新的文件指标加载器来运行衍生指标计算。
支持从JSON/YAML文件加载指标定义，实现指标定义与运行程序的完全分离。

特点：
1. 完全基于配置文件的指标定义
2. 支持复杂的数据源和计算逻辑
3. 灵活的参数配置和验证
4. 高性能的批量计算
5. 详细的日志和错误处理
"""

import os
import sys
import argparse
import logging
import traceback
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入项目模块
from core.analyzer.file_indicator_loader import get_file_indicator_loader
from db.enhanced_postgresql_manager import EnhancedPostgreSQLManager
from utils.config_loader import load_connection_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('file_based_indicator_runner.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class FileBasedIndicatorRunner:
    """基于文件的衍生指标运行器
    
    负责运行基于文件定义的衍生指标计算。
    """
    
    def __init__(self, db_config=None, indicators_dir=None, dry_run=False):
        """初始化运行器
        
        Args:
            db_config (dict, optional): 数据库连接配置
            indicators_dir (str, optional): 指标定义文件目录
            dry_run (bool): 是否为干运行模式
        """
        # 初始化数据库连接
        if db_config is None:
            self.db_config = load_connection_config()
        else:
            self.db_config = db_config
        
        self.reader = EnhancedPostgreSQLManager()
        self.writer = EnhancedPostgreSQLManager() if not dry_run else None
        self.dry_run = dry_run
        
        # 初始化文件指标加载器
        self.indicator_loader = get_file_indicator_loader()
        
        # 统计信息
        self.stats = {
            'total_indicators': 0,
            'successful_calculations': 0,
            'failed_calculations': 0,
            'total_entities': 0,
            'processing_time': 0
        }
        
        logger.info(f"文件指标运行器初始化完成，干运行模式: {dry_run}")
    
    def run(self, 
            entity_types: Optional[List[str]] = None,
            indicator_names: Optional[List[str]] = None,
            entity_ids: Optional[List[str]] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            max_workers: int = 4,
            batch_size: int = 100):
        """运行指标计算
        
        Args:
            entity_types: 实体类型列表，如['stock', 'industry', 'index']
            indicator_names: 指标名称列表
            entity_ids: 实体ID列表
            start_date: 开始日期
            end_date: 结束日期
            max_workers: 最大并发工作线程数
            batch_size: 批处理大小
        """
        start_time = datetime.now()
        
        try:
            # 获取要计算的指标
            indicators_to_run = self._get_indicators_to_run(
                entity_types=entity_types,
                indicator_names=indicator_names
            )
            
            if not indicators_to_run:
                logger.warning("没有找到要计算的指标")
                return
            
            logger.info(f"准备计算 {len(indicators_to_run)} 个指标")
            self.stats['total_indicators'] = len(indicators_to_run)
            
            # 获取要处理的实体
            entities_to_process = self._get_entities_to_process(
                indicators_to_run=indicators_to_run,
                entity_ids=entity_ids,
                start_date=start_date,
                end_date=end_date
            )
            
            if not entities_to_process:
                logger.warning("没有找到要处理的实体")
                return
            
            logger.info(f"准备处理 {len(entities_to_process)} 个实体")
            self.stats['total_entities'] = len(entities_to_process)
            
            # 并行计算指标
            self._run_parallel_calculation(
                entities_to_process=entities_to_process,
                max_workers=max_workers,
                batch_size=batch_size
            )
            
        except Exception as e:
            logger.error(f"运行指标计算失败: {e}")
            logger.error(traceback.format_exc())
            raise
        
        finally:
            # 记录统计信息
            end_time = datetime.now()
            self.stats['processing_time'] = (end_time - start_time).total_seconds()
            self._log_statistics()
    
    def _get_indicators_to_run(self, 
                              entity_types: Optional[List[str]] = None,
                              indicator_names: Optional[List[str]] = None) -> Dict[str, Dict]:
        """获取要计算的指标
        
        Args:
            entity_types: 实体类型列表
            indicator_names: 指标名称列表
            
        Returns:
            Dict[str, Dict]: 指标名称到定义的映射
        """
        all_indicators = self.indicator_loader.indicators
        indicators_to_run = {}
        
        for name, definition in all_indicators.items():
            # 检查指标名称过滤
            if indicator_names and name not in indicator_names:
                continue
            
            # 检查实体类型过滤
            if entity_types:
                indicator_entity_types = definition.get('applicable_entities', [])
                indicator_entity_type = definition.get('entity_type', 'common')
                
                # 如果指标适用于指定的实体类型，或者是通用指标
                if (any(et in indicator_entity_types for et in entity_types) or 
                    indicator_entity_type == 'common' or
                    indicator_entity_type in entity_types):
                    indicators_to_run[name] = definition
            else:
                indicators_to_run[name] = definition
        
        return indicators_to_run
    
    def _get_entities_to_process(self,
                                indicators_to_run: Dict[str, Dict],
                                entity_ids: Optional[List[str]] = None,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> List[Dict]:
        """获取要处理的实体
        
        Args:
            indicators_to_run: 要计算的指标
            entity_ids: 实体ID列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[Dict]: 实体处理任务列表
        """
        entities_to_process = []
        
        # 按实体类型分组指标
        indicators_by_entity_type = {}
        for name, definition in indicators_to_run.items():
            entity_type = definition.get('entity_type', 'common')
            applicable_entities = definition.get('applicable_entities', [entity_type])
            
            for et in applicable_entities:
                if et not in indicators_by_entity_type:
                    indicators_by_entity_type[et] = []
                indicators_by_entity_type[et].append((name, definition))
        
        # 为每个实体类型获取实体列表
        for entity_type, indicators in indicators_by_entity_type.items():
            try:
                entity_list = self._get_entity_list(entity_type, entity_ids)
                
                for entity_id in entity_list:
                    task = {
                        'entity_type': entity_type,
                        'entity_id': entity_id,
                        'indicators': indicators,
                        'start_date': start_date,
                        'end_date': end_date
                    }
                    entities_to_process.append(task)
                    
            except Exception as e:
                logger.error(f"获取实体列表失败 ({entity_type}): {e}")
        
        return entities_to_process
    
    def _get_entity_list(self, entity_type: str, entity_ids: Optional[List[str]] = None) -> List[str]:
        """获取指定类型的实体列表
        
        Args:
            entity_type: 实体类型
            entity_ids: 指定的实体ID列表
            
        Returns:
            List[str]: 实体ID列表
        """
        if entity_ids:
            return entity_ids
        
        # 根据实体类型查询数据库获取实体列表
        if entity_type == 'stock':
            table_name = '股票基本信息表'
            id_column = '股票代码'
            conditions = {'上市状态': '正常交易'}
        elif entity_type == 'industry':
            table_name = '行业基本信息表'
            id_column = '行业代码'
            conditions = {}
        elif entity_type == 'index':
            table_name = '指数基本信息表'
            id_column = '指数代码'
            conditions = {}
        else:
            logger.warning(f"未知实体类型: {entity_type}")
            return []
        
        try:
            df = self.reader.read_table_data(
                table_name=table_name,
                conditions=conditions,
                columns=[id_column]
            )
            
            if df.empty:
                logger.warning(f"未找到 {entity_type} 类型的实体")
                return []
            
            return df[id_column].tolist()
            
        except Exception as e:
            logger.error(f"查询实体列表失败 ({entity_type}): {e}")
            return []
    
    def _run_parallel_calculation(self,
                                 entities_to_process: List[Dict],
                                 max_workers: int = 4,
                                 batch_size: int = 100):
        """并行计算指标
        
        Args:
            entities_to_process: 实体处理任务列表
            max_workers: 最大并发工作线程数
            batch_size: 批处理大小
        """
        # 分批处理
        batches = [entities_to_process[i:i + batch_size] 
                  for i in range(0, len(entities_to_process), batch_size)]
        
        logger.info(f"分为 {len(batches)} 个批次进行处理")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有批次任务
            future_to_batch = {
                executor.submit(self._process_batch, batch): i 
                for i, batch in enumerate(batches)
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_batch):
                batch_index = future_to_batch[future]
                try:
                    batch_results = future.result()
                    logger.info(f"批次 {batch_index + 1}/{len(batches)} 处理完成")
                    
                    # 更新统计信息
                    for result in batch_results:
                        if result['success']:
                            self.stats['successful_calculations'] += 1
                        else:
                            self.stats['failed_calculations'] += 1
                            
                except Exception as e:
                    logger.error(f"批次 {batch_index + 1} 处理失败: {e}")
                    self.stats['failed_calculations'] += len(batches[batch_index])
    
    def _process_batch(self, batch: List[Dict]) -> List[Dict]:
        """处理一个批次的实体
        
        Args:
            batch: 批次任务列表
            
        Returns:
            List[Dict]: 处理结果列表
        """
        results = []
        
        for task in batch:
            try:
                result = self._process_entity_task(task)
                results.append(result)
            except Exception as e:
                logger.error(f"处理实体任务失败: {task['entity_id']}, 错误: {e}")
                results.append({
                    'entity_id': task['entity_id'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _process_entity_task(self, task: Dict) -> Dict:
        """处理单个实体任务
        
        Args:
            task: 实体任务
            
        Returns:
            Dict: 处理结果
        """
        entity_id = task['entity_id']
        entity_type = task['entity_type']
        indicators = task['indicators']
        start_date = task['start_date']
        end_date = task['end_date']
        
        logger.debug(f"处理实体: {entity_id} ({entity_type})")
        
        results = {}
        
        # 计算每个指标
        for indicator_name, indicator_definition in indicators:
            try:
                # 验证指标定义
                validation = self.indicator_loader.validate_indicator(indicator_name)
                if not validation['valid']:
                    logger.error(f"指标定义验证失败 ({indicator_name}): {validation['errors']}")
                    continue
                
                # 计算指标值
                indicator_values = self.indicator_loader.calculate_indicator(
                    indicator_name=indicator_name,
                    entity_id=entity_id,
                    start_date=start_date or '2020-01-01',
                    end_date=end_date or datetime.now().strftime('%Y-%m-%d')
                )
                
                if indicator_values is not None and not indicator_values.empty:
                    results[indicator_name] = indicator_values
                    logger.debug(f"指标计算成功: {indicator_name}, 数据点数: {len(indicator_values)}")
                else:
                    logger.warning(f"指标计算结果为空: {indicator_name}")
                
            except Exception as e:
                logger.error(f"计算指标失败 ({indicator_name}): {e}")
                logger.error(traceback.format_exc())
        
        # 存储结果
        if results and not self.dry_run:
            try:
                self._store_results(entity_id, entity_type, results, indicators)
                logger.debug(f"存储结果成功: {entity_id}")
            except Exception as e:
                logger.error(f"存储结果失败 ({entity_id}): {e}")
                return {
                    'entity_id': entity_id,
                    'success': False,
                    'error': f'存储失败: {str(e)}'
                }
        
        return {
            'entity_id': entity_id,
            'success': True,
            'indicators_calculated': len(results)
        }
    
    def _store_results(self, 
                      entity_id: str, 
                      entity_type: str, 
                      results: Dict[str, pd.Series],
                      indicators: List[tuple]):
        """存储计算结果
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            results: 计算结果
            indicators: 指标定义列表
        """
        # 按输出表分组结果
        results_by_table = {}
        
        for indicator_name, indicator_values in results.items():
            # 找到对应的指标定义
            indicator_definition = None
            for name, definition in indicators:
                if name == indicator_name:
                    indicator_definition = definition
                    break
            
            if not indicator_definition:
                continue
            
            # 获取输出配置
            output_config = indicator_definition.get('output', {})
            table_name = output_config.get('table')
            column_name = output_config.get('column')
            
            if not table_name or not column_name:
                logger.warning(f"指标 {indicator_name} 缺少输出配置")
                continue
            
            if table_name not in results_by_table:
                results_by_table[table_name] = {}
            
            results_by_table[table_name][column_name] = indicator_values
        
        # 存储到各个表
        for table_name, table_results in results_by_table.items():
            try:
                # 构建DataFrame
                df = pd.DataFrame(table_results)
                
                # 添加实体ID和日期列
                if entity_type == 'stock':
                    df['股票代码'] = entity_id
                elif entity_type == 'industry':
                    df['行业代码'] = entity_id
                elif entity_type == 'index':
                    df['指数代码'] = entity_id
                
                df['日期'] = df.index
                df = df.reset_index(drop=True)
                
                # 存储到数据库
                primary_keys = ['股票代码' if entity_type == 'stock' else 
                               '行业代码' if entity_type == 'industry' else '指数代码', '日期']
                self.writer.upsert_from_df(
                    df=df,
                    table_name=table_name,
                    primary_keys=primary_keys
                )
                
                logger.debug(f"存储到表 {table_name}: {len(df)} 行数据")
                
            except Exception as e:
                logger.error(f"存储到表 {table_name} 失败: {e}")
                raise
    
    def _log_statistics(self):
        """记录统计信息"""
        logger.info("=== 指标计算统计 ===")
        logger.info(f"总指标数: {self.stats['total_indicators']}")
        logger.info(f"总实体数: {self.stats['total_entities']}")
        logger.info(f"成功计算: {self.stats['successful_calculations']}")
        logger.info(f"失败计算: {self.stats['failed_calculations']}")
        logger.info(f"处理时间: {self.stats['processing_time']:.2f} 秒")
        
        if self.stats['total_entities'] > 0:
            success_rate = (self.stats['successful_calculations'] / 
                          (self.stats['successful_calculations'] + self.stats['failed_calculations'])) * 100
            logger.info(f"成功率: {success_rate:.2f}%")
        
        if self.dry_run:
            logger.info("注意: 这是干运行模式，未实际存储数据")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='基于文件的衍生指标运行器')
    
    # 基本参数
    parser.add_argument('--entity-types', nargs='+', 
                       choices=['stock', 'industry', 'index', 'common'],
                       help='实体类型列表')
    parser.add_argument('--indicators', nargs='+',
                       help='指标名称列表')
    parser.add_argument('--entity-ids', nargs='+',
                       help='实体ID列表')
    parser.add_argument('--start-date', type=str,
                       help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='结束日期 (YYYY-MM-DD)')
    
    # 性能参数
    parser.add_argument('--max-workers', type=int, default=4,
                       help='最大并发工作线程数')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='批处理大小')
    
    # 运行模式
    parser.add_argument('--dry-run', action='store_true',
                       help='干运行模式，不实际存储数据')
    
    # 日志级别
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='日志级别')
    
    # 配置文件
    parser.add_argument('--config', type=str,
                       help='数据库配置文件路径')
    parser.add_argument('--indicators-dir', type=str,
                       help='指标定义文件目录')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # 加载数据库配置
        db_config = None
        if args.config:
            db_config = load_connection_config(args.config)
        
        # 创建运行器
        runner = FileBasedIndicatorRunner(
            db_config=db_config,
            indicators_dir=args.indicators_dir,
            dry_run=args.dry_run
        )
        
        # 运行计算
        runner.run(
            entity_types=args.entity_types,
            indicator_names=args.indicators,
            entity_ids=args.entity_ids,
            start_date=args.start_date,
            end_date=args.end_date,
            max_workers=args.max_workers,
            batch_size=args.batch_size
        )
        
        logger.info("指标计算完成")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()