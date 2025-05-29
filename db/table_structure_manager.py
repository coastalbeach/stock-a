#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
表结构管理器

提供表结构完整性检查和自动修复功能，支持动态添加新的列和检测表结构不完整的情况。
该工具使得维护数据库表结构变得更加便捷，无需手动编写SQL语句。
"""

import os
import sys
import yaml
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Union, Optional, Tuple

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent)  # db/table_structure_manager.py -> stock-a
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据库管理器
from db.postgresql_manager import PostgreSQLManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TableStructureManager')


class TableStructureManager:
    """表结构管理器类
    
    提供表结构完整性检查和自动修复功能，支持动态添加新的列和检测表结构不完整的情况
    """
    
    def __init__(self, db_manager=None):
        """初始化表结构管理器
        
        Args:
            db_manager (PostgreSQLManager, optional): 数据库管理器实例，如果为None则自动创建
        """
        self.db = db_manager if db_manager else PostgreSQLManager()
        self.tables_config = self._load_tables_config()
        logger.info("表结构管理器初始化完成")
    
    def _load_tables_config(self) -> Dict[str, Any]:
        """加载表配置
        
        Returns:
            Dict[str, Any]: 表配置字典
        """
        config_path = os.path.join(project_root, 'config', 'tables.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.debug(f"成功加载表配置，共 {len(config.get('tables', {}))} 个表")
            return config
        except Exception as e:
            logger.error(f"加载表配置失败: {e}")
            return {'tables': {}}
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表信息
        
        Args:
            table_name (str): 表名
            
        Returns:
            Dict[str, Any]: 表信息字典，包含列定义、主键、索引等
        """
        tables = self.tables_config.get('tables', {})
        if table_name in tables:
            return tables[table_name]
        else:
            logger.warning(f"表 {table_name} 在配置中不存在")
            return {}
    
    def get_table_columns(self, table_name: str) -> List[Tuple[str, str]]:
        """获取表的当前列结构
        
        Args:
            table_name (str): 表名

        Returns:
            List[Tuple[str, str]]: 列名和数据类型的元组列表
        """
        query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """
        results = self.db.query(query, (table_name,))
        return [(row[0], row[1]) for row in results] if results else []
    
    def get_expected_columns(self, table_name: str) -> List[Tuple[str, str]]:
        """获取表的预期列结构（从配置中）
        
        Args:
            table_name (str): 表名
            
        Returns:
            List[Tuple[str, str]]: 预期的列名和数据类型的元组列表
        """
        table_info = self.get_table_info(table_name)
        columns = table_info.get('columns', {})
        return [(col_name, col_info.get('type', 'text')) for col_name, col_info in columns.items()]
    
    def check_table_structure(self, table_name: str) -> Dict[str, Any]:
        """检查表结构是否完整
        
        Args:
            table_name (str): 表名
            
        Returns:
            Dict[str, Any]: 检查结果，包含是否完整、缺失列等信息
        """
        # 检查表是否存在
        if not self.db.table_exists(table_name):
            return {
                'complete': False,
                'exists': False,
                'missing_columns': [],
                'message': f"表 {table_name} 不存在"
            }
        
        # 获取当前列和预期列
        current_columns = self.get_table_columns(table_name)
        expected_columns = self.get_expected_columns(table_name)
        
        # 如果配置中没有该表的信息，则认为结构完整
        if not expected_columns:
            return {
                'complete': True,
                'exists': True,
                'missing_columns': [],
                'message': f"表 {table_name} 在配置中不存在，无法检查结构完整性"
            }
        
        # 检查缺失的列
        current_column_names = [col[0] for col in current_columns]
        missing_columns = []
        
        for col_name, col_type in expected_columns:
            if col_name not in current_column_names:
                missing_columns.append((col_name, col_type))
        
        # 返回检查结果
        if missing_columns:
            return {
                'complete': False,
                'exists': True,
                'missing_columns': missing_columns,
                'message': f"表 {table_name} 缺少 {len(missing_columns)} 个列"
            }
        else:
            return {
                'complete': True,
                'exists': True,
                'missing_columns': [],
                'message': f"表 {table_name} 结构完整"
            }
    
    def add_column(self, table_name: str, column_name: str, data_type: str = "double precision") -> bool:
        """向表中添加新列
        
        Args:
            table_name (str): 表名
            column_name (str): 列名
            data_type (str, optional): 数据类型。默认为"double precision"。

        Returns:
            bool: 操作是否成功
        """
        # 检查列是否已存在
        columns = self.get_table_columns(table_name)
        column_names = [col[0] for col in columns]
        if column_name in column_names:
            logger.info(f"列 '{column_name}' 已存在于表 '{table_name}' 中。")
            return True

        # 添加新列
        query = f'ALTER TABLE public."{table_name}" ADD COLUMN "{column_name}" {data_type};'
        try:
            self.db.execute(query)
            logger.info(f"成功向表 '{table_name}' 添加列 '{column_name}'。")
            return True
        except Exception as e:
            logger.error(f"向表 '{table_name}' 添加列 '{column_name}' 失败: {e}")
            return False
    
    def fix_table_structure(self, table_name: str) -> Dict[str, Any]:
        """修复表结构，添加缺失的列
        
        Args:
            table_name (str): 表名
            
        Returns:
            Dict[str, Any]: 修复结果，包含成功添加的列、失败的列等信息
        """
        # 检查表结构
        check_result = self.check_table_structure(table_name)
        
        if check_result['complete']:
            return {
                'success': True,
                'added_columns': [],
                'failed_columns': [],
                'message': f"表 {table_name} 结构已完整，无需修复"
            }
        
        if not check_result['exists']:
            return {
                'success': False,
                'added_columns': [],
                'failed_columns': [],
                'message': f"表 {table_name} 不存在，无法修复"
            }
        
        # 添加缺失的列
        added_columns = []
        failed_columns = []
        
        for col_name, col_type in check_result['missing_columns']:
            success = self.add_column(table_name, col_name, col_type)
            if success:
                added_columns.append((col_name, col_type))
            else:
                failed_columns.append((col_name, col_type))
        
        # 返回修复结果
        if failed_columns:
            return {
                'success': len(failed_columns) == 0,
                'added_columns': added_columns,
                'failed_columns': failed_columns,
                'message': f"表 {table_name} 修复部分完成，成功添加 {len(added_columns)} 个列，失败 {len(failed_columns)} 个列"
            }
        else:
            return {
                'success': True,
                'added_columns': added_columns,
                'failed_columns': [],
                'message': f"表 {table_name} 修复完成，成功添加 {len(added_columns)} 个列"
            }
    
    def get_column_data_fill_guidance(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """获取列数据填充指导
        
        Args:
            table_name (str): 表名
            column_name (str): 列名
            
        Returns:
            Dict[str, Any]: 填充指导信息，包含SQL示例等
        """
        # 获取表的主键
        table_info = self.get_table_info(table_name)
        primary_key = table_info.get('primary_key', [])
        
        if not primary_key:
            # 尝试从数据库获取主键信息
            query = """
            SELECT a.attname
            FROM   pg_index i
            JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                 AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = %s::regclass
            AND    i.indisprimary;
            """
            results = self.db.query(query, (table_name,))
            primary_key = [row[0] for row in results] if results else []
        
        # 获取表的行数
        count_query = f'SELECT COUNT(*) FROM public."{table_name}";'
        count_result = self.db.query_one(count_query)
        row_count = count_result[0] if count_result else 0
        
        # 构建填充指导
        guidance = {
            'table_name': table_name,
            'column_name': column_name,
            'row_count': row_count,
            'primary_key': primary_key,
            'examples': []
        }
        
        # 添加SQL示例
        if primary_key:
            pk_str = '", "'.join(primary_key)
            guidance['examples'].append({
                'description': '使用UPDATE语句填充固定值',
                'sql': f'UPDATE public."{table_name}" SET "{column_name}" = 0;'
            })
            
            guidance['examples'].append({
                'description': '使用UPDATE语句根据其他列计算值',
                'sql': f'UPDATE public."{table_name}" SET "{column_name}" = "其他列" * 1.5;'
            })
            
            guidance['examples'].append({
                'description': '使用UPDATE语句根据条件填充不同值',
                'sql': f'UPDATE public."{table_name}" SET "{column_name}" = CASE WHEN "条件列" > 100 THEN 1 ELSE 0 END;'
            })
            
            guidance['examples'].append({
                'description': '从其他表导入数据',
                'sql': f'UPDATE public."{table_name}" t1 SET "{column_name}" = t2."源列" FROM "源表" t2 WHERE t1."{primary_key[0]}" = t2."对应键";'
            })
        
        return guidance
    
    def check_and_fix_all_tables(self) -> Dict[str, Any]:
        """检查并修复所有表的结构
        
        Returns:
            Dict[str, Any]: 所有表的检查和修复结果
        """
        results = {}
        tables = self.tables_config.get('tables', {})
        
        for table_name in tables:
            # 检查表结构
            check_result = self.check_table_structure(table_name)
            
            # 如果表不完整，尝试修复
            if not check_result['complete'] and check_result['exists']:
                fix_result = self.fix_table_structure(table_name)
                results[table_name] = {
                    'check': check_result,
                    'fix': fix_result
                }
                
                # 如果有添加的列，提供填充指导
                if fix_result['added_columns']:
                    guidance = {}
                    for col_name, _ in fix_result['added_columns']:
                        guidance[col_name] = self.get_column_data_fill_guidance(table_name, col_name)
                    results[table_name]['guidance'] = guidance
            else:
                results[table_name] = {
                    'check': check_result
                }
        
        return results
    
    def add_indicator_columns(self, indicators_config: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """根据配置添加多个指标列
        
        Args:
            indicators_config (Dict[str, Dict[str, Any]]): 指标配置，格式为 {"指标名": {"类型": "数据类型", "表": ["表名列表"]}}
                如果"表"字段为空或不存在，则默认添加到所有技术指标表

        Returns:
            Dict[str, Any]: 操作结果统计
        """
        results = {"成功": 0, "失败": 0, "已存在": 0, "详情": {}}
        
        for indicator_name, config in indicators_config.items():
            data_type = config.get("类型", "double precision")
            target_tables = config.get("表", [])
            
            # 如果没有指定目标表，则尝试添加到所有技术指标表
            if not target_tables:
                target_tables = ["股票技术指标", "行业技术指标", "指数技术指标"]
            
            table_results = {}
            for table in target_tables:
                # 检查表是否存在
                if not self.db.table_exists(table):
                    table_results[table] = {"状态": "失败", "原因": f"表 {table} 不存在"}
                    results["失败"] += 1
                    continue
                
                # 检查列是否已存在
                columns = self.get_table_columns(table)
                column_names = [col[0] for col in columns]
                if indicator_name in column_names:
                    table_results[table] = {"状态": "已存在"}
                    results["已存在"] += 1
                    continue
                
                # 添加新列
                success = self.add_column(table, indicator_name, data_type)
                if success:
                    table_results[table] = {"状态": "成功"}
                    results["成功"] += 1
                else:
                    table_results[table] = {"状态": "失败", "原因": f"添加列失败"}
                    results["失败"] += 1
            
            results["详情"][indicator_name] = table_results
        
        return results
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
            logger.info("数据库连接已关闭")


def main():
    """主函数"""
    manager = TableStructureManager()
    
    # 检查并修复所有表的结构
    results = manager.check_and_fix_all_tables()
    
    # 输出结果
    for table_name, result in results.items():
        check_result = result['check']
        print(f"表 {table_name}: {check_result['message']}")
        
        if 'fix' in result:
            fix_result = result['fix']
            print(f"  修复结果: {fix_result['message']}")
            
            if 'guidance' in result:
                print("  数据填充指导:")
                for col_name, guidance in result['guidance'].items():
                    print(f"    列 {col_name}:")
                    print(f"      行数: {guidance['row_count']}")
                    print(f"      主键: {', '.join(guidance['primary_key'])}")
                    print(f"      SQL示例:")
                    for example in guidance['examples']:
                        print(f"        {example['description']}:")
                        print(f"        {example['sql']}")
    
    # 关闭数据库连接
    manager.close()


if __name__ == "__main__":
    main()