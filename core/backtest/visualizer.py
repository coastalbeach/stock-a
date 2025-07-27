# -*- coding: utf-8 -*-
"""
回测结果可视化工具

负责生成回测结果的各种图表和报告
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import seaborn as sns
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager
from core.backtest.portfolio_manager import Trade
from core.backtest.performance_analyzer import PerformanceMetrics

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 设置绘图样式
sns.set_style("whitegrid")
plt.style.use('seaborn-v0_8')


class BacktestVisualizer:
    """回测结果可视化器"""
    
    def __init__(self, output_dir: str = "backtest_results", figsize: Tuple[int, int] = (12, 8)):
        """
        初始化可视化器
        
        Args:
            output_dir (str): 输出目录
            figsize (Tuple[int, int]): 图表大小
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.figsize = figsize
        
        # 颜色配置
        self.colors = {
            'portfolio': '#1f77b4',
            'benchmark': '#ff7f0e',
            'drawdown': '#d62728',
            'positive': '#2ca02c',
            'negative': '#d62728',
            'neutral': '#7f7f7f'
        }
        
        # 获取日志记录器
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger('visualizer')
        
        self.logger.info(f"可视化器初始化完成，输出目录: {self.output_dir}")
    
    def plot_portfolio_value(self, portfolio_values: List[Dict[str, Any]], 
                           benchmark_values: Optional[List[Dict[str, Any]]] = None,
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制投资组合价值曲线
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            benchmark_values (List[Dict[str, Any]], optional): 基准价值序列
            save_path (str, optional): 保存路径
            
        Returns:
            plt.Figure: 图表对象
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 处理投资组合数据
        df_portfolio = pd.DataFrame(portfolio_values)
        df_portfolio['日期'] = pd.to_datetime(df_portfolio['日期'])
        df_portfolio = df_portfolio.set_index('日期').sort_index()
        
        # 绘制投资组合价值
        ax.plot(df_portfolio.index, df_portfolio['总价值'], 
                color=self.colors['portfolio'], linewidth=2, label='投资组合价值')
        
        # 绘制基准价值（如果提供）
        if benchmark_values:
            df_benchmark = pd.DataFrame(benchmark_values)
            df_benchmark['日期'] = pd.to_datetime(df_benchmark['日期'])
            df_benchmark = df_benchmark.set_index('日期').sort_index()
            
            ax.plot(df_benchmark.index, df_benchmark['总价值'], 
                    color=self.colors['benchmark'], linewidth=2, label='基准价值')
        
        # 设置图表
        ax.set_title('投资组合价值变化', fontsize=16, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价值', fontsize=12)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # 格式化日期轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            fig.savefig(self.output_dir / 'portfolio_value.png', dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_returns(self, portfolio_values: List[Dict[str, Any]], 
                    benchmark_values: Optional[List[Dict[str, Any]]] = None,
                    save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制收益率曲线
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            benchmark_values (List[Dict[str, Any]], optional): 基准价值序列
            save_path (str, optional): 保存路径
            
        Returns:
            plt.Figure: 图表对象
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.figsize[0], self.figsize[1] * 1.2))
        
        # 处理投资组合数据
        df_portfolio = pd.DataFrame(portfolio_values)
        df_portfolio['日期'] = pd.to_datetime(df_portfolio['日期'])
        df_portfolio = df_portfolio.set_index('日期').sort_index()
        
        # 计算收益率
        portfolio_returns = df_portfolio['总价值'].pct_change().dropna()
        portfolio_cumulative = (1 + portfolio_returns).cumprod() - 1
        
        # 绘制累计收益率
        ax1.plot(portfolio_cumulative.index, portfolio_cumulative * 100, 
                color=self.colors['portfolio'], linewidth=2, label='投资组合')
        
        # 处理基准数据（如果提供）
        if benchmark_values:
            df_benchmark = pd.DataFrame(benchmark_values)
            df_benchmark['日期'] = pd.to_datetime(df_benchmark['日期'])
            df_benchmark = df_benchmark.set_index('日期').sort_index()
            
            benchmark_returns = df_benchmark['总价值'].pct_change().dropna()
            benchmark_cumulative = (1 + benchmark_returns).cumprod() - 1
            
            ax1.plot(benchmark_cumulative.index, benchmark_cumulative * 100, 
                    color=self.colors['benchmark'], linewidth=2, label='基准')
        
        ax1.set_title('累计收益率', fontsize=14, fontweight='bold')
        ax1.set_ylabel('收益率 (%)', fontsize=12)
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # 绘制日收益率分布
        ax2.hist(portfolio_returns * 100, bins=50, alpha=0.7, 
                color=self.colors['portfolio'], edgecolor='black')
        ax2.axvline(portfolio_returns.mean() * 100, color='red', linestyle='--', 
                   linewidth=2, label=f'均值: {portfolio_returns.mean()*100:.2f}%')
        
        ax2.set_title('日收益率分布', fontsize=14, fontweight='bold')
        ax2.set_xlabel('日收益率 (%)', fontsize=12)
        ax2.set_ylabel('频次', fontsize=12)
        ax2.legend(fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # 格式化日期轴
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            fig.savefig(self.output_dir / 'returns.png', dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_drawdown(self, portfolio_values: List[Dict[str, Any]], 
                     save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制回撤曲线
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            save_path (str, optional): 保存路径
            
        Returns:
            plt.Figure: 图表对象
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 处理数据
        df = pd.DataFrame(portfolio_values)
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.set_index('日期').sort_index()
        
        # 计算回撤
        cumulative_max = df['总价值'].expanding().max()
        drawdown = (df['总价值'] - cumulative_max) / cumulative_max * 100
        
        # 绘制回撤
        ax.fill_between(drawdown.index, drawdown, 0, 
                       color=self.colors['drawdown'], alpha=0.3, label='回撤')
        ax.plot(drawdown.index, drawdown, 
               color=self.colors['drawdown'], linewidth=1)
        
        # 标记最大回撤点
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        ax.scatter(max_dd_idx, max_dd_value, color='red', s=100, zorder=5)
        ax.annotate(f'最大回撤: {max_dd_value:.2f}%', 
                   xy=(max_dd_idx, max_dd_value), 
                   xytext=(10, 10), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        ax.set_title('投资组合回撤', fontsize=16, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('回撤 (%)', fontsize=12)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # 格式化日期轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            fig.savefig(self.output_dir / 'drawdown.png', dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_trade_analysis(self, trades: List[Trade], 
                          save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制交易分析图表
        
        Args:
            trades (List[Trade]): 交易记录列表
            save_path (str, optional): 保存路径
            
        Returns:
            plt.Figure: 图表对象
        """
        if not trades:
            fig, ax = plt.subplots(figsize=self.figsize)
            ax.text(0.5, 0.5, '无交易记录', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=16)
            ax.set_title('交易分析', fontsize=16, fontweight='bold')
            return fig
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(self.figsize[0] * 1.5, self.figsize[1] * 1.2))
        
        # 准备数据
        trade_data = []
        for trade in trades:
            trade_data.append({
                '交易ID': trade.trade_id,
                '股票代码': trade.stock_code,
                '开仓日期': trade.entry_date,
                '平仓日期': trade.exit_date,
                '盈亏': trade.pnl,
                '收益率': trade.return_rate,
                '持仓天数': trade.holding_days
            })
        
        df_trades = pd.DataFrame(trade_data)
        
        # 1. 盈亏分布
        profits = df_trades[df_trades['盈亏'] > 0]['盈亏']
        losses = df_trades[df_trades['盈亏'] <= 0]['盈亏']
        
        ax1.hist([profits, losses], bins=20, alpha=0.7, 
                color=[self.colors['positive'], self.colors['negative']], 
                label=['盈利', '亏损'])
        ax1.set_title('交易盈亏分布', fontsize=12, fontweight='bold')
        ax1.set_xlabel('盈亏金额', fontsize=10)
        ax1.set_ylabel('交易次数', fontsize=10)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 收益率分布
        ax2.hist(df_trades['收益率'] * 100, bins=20, alpha=0.7, 
                color=self.colors['portfolio'], edgecolor='black')
        ax2.axvline(df_trades['收益率'].mean() * 100, color='red', linestyle='--', 
                   label=f'均值: {df_trades["收益率"].mean()*100:.2f}%')
        ax2.set_title('交易收益率分布', fontsize=12, fontweight='bold')
        ax2.set_xlabel('收益率 (%)', fontsize=10)
        ax2.set_ylabel('交易次数', fontsize=10)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 持仓天数分布
        ax3.hist(df_trades['持仓天数'], bins=20, alpha=0.7, 
                color=self.colors['neutral'], edgecolor='black')
        ax3.axvline(df_trades['持仓天数'].mean(), color='red', linestyle='--', 
                   label=f'均值: {df_trades["持仓天数"].mean():.1f}天')
        ax3.set_title('持仓天数分布', fontsize=12, fontweight='bold')
        ax3.set_xlabel('持仓天数', fontsize=10)
        ax3.set_ylabel('交易次数', fontsize=10)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 累计盈亏曲线
        df_trades['累计盈亏'] = df_trades['盈亏'].cumsum()
        ax4.plot(range(len(df_trades)), df_trades['累计盈亏'], 
                color=self.colors['portfolio'], linewidth=2)
        ax4.fill_between(range(len(df_trades)), df_trades['累计盈亏'], 0, 
                        alpha=0.3, color=self.colors['portfolio'])
        ax4.set_title('累计盈亏曲线', fontsize=12, fontweight='bold')
        ax4.set_xlabel('交易序号', fontsize=10)
        ax4.set_ylabel('累计盈亏', fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            fig.savefig(self.output_dir / 'trade_analysis.png', dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_monthly_returns(self, portfolio_values: List[Dict[str, Any]], 
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制月度收益率热力图
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            save_path (str, optional): 保存路径
            
        Returns:
            plt.Figure: 图表对象
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 处理数据
        df = pd.DataFrame(portfolio_values)
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.set_index('日期').sort_index()
        
        # 计算月度收益率
        monthly_values = df['总价值'].resample('M').last()
        monthly_returns = monthly_values.pct_change().dropna()
        
        if len(monthly_returns) == 0:
            ax.text(0.5, 0.5, '数据不足以计算月度收益率', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=16)
            ax.set_title('月度收益率热力图', fontsize=16, fontweight='bold')
            return fig
        
        # 创建年月矩阵
        monthly_returns.index = pd.to_datetime(monthly_returns.index)
        monthly_returns_df = monthly_returns.to_frame('收益率')
        monthly_returns_df['年'] = monthly_returns_df.index.year
        monthly_returns_df['月'] = monthly_returns_df.index.month
        
        # 透视表
        pivot_table = monthly_returns_df.pivot(index='年', columns='月', values='收益率')
        pivot_table = pivot_table * 100  # 转换为百分比
        
        # 绘制热力图
        sns.heatmap(pivot_table, annot=True, fmt='.2f', cmap='RdYlGn', 
                   center=0, ax=ax, cbar_kws={'label': '收益率 (%)'})
        
        ax.set_title('月度收益率热力图', fontsize=16, fontweight='bold')
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('年份', fontsize=12)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            fig.savefig(self.output_dir / 'monthly_returns.png', dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_risk_metrics(self, metrics: PerformanceMetrics, 
                         save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制风险指标雷达图
        
        Args:
            metrics (PerformanceMetrics): 绩效指标
            save_path (str, optional): 保存路径
            
        Returns:
            plt.Figure: 图表对象
        """
        fig, ax = plt.subplots(figsize=self.figsize, subplot_kw=dict(projection='polar'))
        
        # 准备数据（标准化到0-1范围）
        risk_metrics = {
            '夏普比率': min(max(metrics.sharpe_ratio / 3, 0), 1),  # 假设3为优秀水平
            '索提诺比率': min(max(metrics.sortino_ratio / 3, 0), 1),
            '卡玛比率': min(max(metrics.calmar_ratio / 5, 0), 1),  # 假设5为优秀水平
            '信息比率': min(max(metrics.information_ratio / 2, 0), 1),
            '胜率': metrics.win_rate,
            '盈亏比': min(max(metrics.profit_factor / 3, 0), 1)  # 假设3为优秀水平
        }
        
        # 角度
        angles = np.linspace(0, 2 * np.pi, len(risk_metrics), endpoint=False).tolist()
        angles += angles[:1]  # 闭合图形
        
        # 数值
        values = list(risk_metrics.values())
        values += values[:1]  # 闭合图形
        
        # 绘制雷达图
        ax.plot(angles, values, 'o-', linewidth=2, color=self.colors['portfolio'])
        ax.fill(angles, values, alpha=0.25, color=self.colors['portfolio'])
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(risk_metrics.keys(), fontsize=10)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=8)
        ax.grid(True)
        
        ax.set_title('风险指标雷达图', fontsize=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            fig.savefig(self.output_dir / 'risk_metrics.png', dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_comprehensive_report(self, portfolio_values: List[Dict[str, Any]], 
                                  trades: List[Trade], metrics: PerformanceMetrics,
                                  benchmark_values: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        创建综合报告
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            trades (List[Trade]): 交易记录列表
            metrics (PerformanceMetrics): 绩效指标
            benchmark_values (List[Dict[str, Any]], optional): 基准价值序列
            
        Returns:
            str: 报告文件路径
        """
        try:
            # 生成所有图表
            self.plot_portfolio_value(portfolio_values, benchmark_values)
            self.plot_returns(portfolio_values, benchmark_values)
            self.plot_drawdown(portfolio_values)
            self.plot_trade_analysis(trades)
            self.plot_monthly_returns(portfolio_values)
            self.plot_risk_metrics(metrics)
            
            # 生成HTML报告
            html_content = self._generate_html_report(metrics)
            
            # 保存HTML报告
            report_path = self.output_dir / 'backtest_report.html'
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"综合报告已生成: {report_path}")
            return str(report_path)
            
        except Exception as e:
            self.logger.error(f"生成综合报告失败: {e}")
            return ""
    
    def _generate_html_report(self, metrics: PerformanceMetrics) -> str:
        """
        生成HTML报告
        
        Args:
            metrics (PerformanceMetrics): 绩效指标
            
        Returns:
            str: HTML内容
        """
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回测报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
            border-bottom: 3px solid #007acc;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #007acc;
            border-left: 4px solid #007acc;
            padding-left: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .chart-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .neutral {{ color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 回测绩效报告</h1>
        
        <h2>📈 核心指标</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">总收益率</div>
                <div class="metric-value {('positive' if metrics.total_return >= 0 else 'negative')}">
                    {metrics.total_return:.2%}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">年化收益率</div>
                <div class="metric-value {('positive' if metrics.annual_return >= 0 else 'negative')}">
                    {metrics.annual_return:.2%}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value negative">
                    {metrics.max_drawdown:.2%}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">夏普比率</div>
                <div class="metric-value {('positive' if metrics.sharpe_ratio >= 0 else 'negative')}">
                    {metrics.sharpe_ratio:.4f}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">胜率</div>
                <div class="metric-value">
                    {metrics.win_rate:.2%}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">盈亏比</div>
                <div class="metric-value {('positive' if metrics.profit_factor >= 1 else 'negative')}">
                    {metrics.profit_factor:.2f}
                </div>
            </div>
        </div>
        
        <h2>📊 图表分析</h2>
        
        <div class="chart-container">
            <h3>投资组合价值变化</h3>
            <img src="portfolio_value.png" alt="投资组合价值变化">
        </div>
        
        <div class="chart-container">
            <h3>收益率分析</h3>
            <img src="returns.png" alt="收益率分析">
        </div>
        
        <div class="chart-container">
            <h3>回撤分析</h3>
            <img src="drawdown.png" alt="回撤分析">
        </div>
        
        <div class="chart-container">
            <h3>交易分析</h3>
            <img src="trade_analysis.png" alt="交易分析">
        </div>
        
        <div class="chart-container">
            <h3>月度收益率热力图</h3>
            <img src="monthly_returns.png" alt="月度收益率热力图">
        </div>
        
        <div class="chart-container">
            <h3>风险指标雷达图</h3>
            <img src="risk_metrics.png" alt="风险指标雷达图">
        </div>
        
        <h2>📋 详细指标</h2>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f8f9fa;">
                <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">指标</th>
                <th style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">数值</th>
            </tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">年化波动率</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.volatility:.2%}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">VaR (95%)</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.var_95:.2%}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">CVaR (95%)</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.cvar_95:.2%}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">索提诺比率</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.sortino_ratio:.4f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">卡玛比率</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.calmar_ratio:.4f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">信息比率</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.information_ratio:.4f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">Beta</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.beta:.4f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">Alpha</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.alpha:.2%}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">跟踪误差</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.tracking_error:.2%}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">R²</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.r_squared:.4f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">总交易次数</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.total_trades}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">盈利交易</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.winning_trades}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">亏损交易</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.losing_trades}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">平均盈利</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.avg_win:.2f}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #dee2e6;">平均亏损</td><td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{metrics.avg_loss:.2f}</td></tr>
        </table>
        
        <div style="text-align: center; margin-top: 40px; color: #6c757d;">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_template