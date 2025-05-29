#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
东方财富网-数据中心-特色数据-千股千评
提供一次性获取个股的千股千评全部数据的接口
"""

import time
import json
from typing import Dict, Optional, Union, List

import pandas as pd
import requests


def get_stock_comment_all(symbol: str = "600000") -> Dict[str, pd.DataFrame]:
    """
    东方财富网-数据中心-特色数据-千股千评-获取个股的全部千股千评数据
    包括：综合评价、主力控盘、市场热度等多个维度的数据
    
    :param symbol: 股票代码，如：600000
    :return: 包含多个DataFrame的字典，每个DataFrame对应一个数据维度
    """
    result = {}
    
    # 1. 获取主力控盘-机构参与度数据
    try:
        jgcyd_df = get_stock_comment_jgcyd(symbol)
        result["机构参与度"] = jgcyd_df
    except Exception as e:
        print(f"获取机构参与度数据失败: {e}")
    
    # 2. 获取综合评价-历史评分数据
    try:
        lspf_df = get_stock_comment_lspf(symbol)
        result["历史评分"] = lspf_df
    except Exception as e:
        print(f"获取历史评分数据失败: {e}")
    
    # 3. 获取市场热度-用户关注指数数据
    try:
        focus_df = get_stock_comment_focus(symbol)
        result["用户关注指数"] = focus_df
    except Exception as e:
        print(f"获取用户关注指数数据失败: {e}")
    
    # 4. 获取市场热度-市场参与意愿数据
    try:
        desire_df = get_stock_comment_desire(symbol)
        if desire_df is not None and not desire_df.empty:
            result["市场参与意愿"] = desire_df
    except Exception as e:
        print(f"获取市场参与意愿数据失败: {e}")
    
    # 5. 获取市场热度-日度市场参与意愿数据
    try:
        desire_daily_df = get_stock_comment_desire_daily(symbol)
        result["日度市场参与意愿"] = desire_daily_df
    except Exception as e:
        print(f"获取日度市场参与意愿数据失败: {e}")
    
    # 6. 获取市场热度-市场成本数据
    try:
        cost_df = get_stock_comment_cost(symbol)
        if cost_df is not None and not cost_df.empty:
            result["市场成本"] = cost_df
    except Exception as e:
        print(f"获取市场成本数据失败: {e}")
    
    return result


def get_stock_comment_jgcyd(symbol: str = "600000") -> pd.DataFrame:
    """
    东方财富网-数据中心-特色数据-千股千评-主力控盘-机构参与度
    
    :param symbol: 股票代码
    :return: 机构参与度数据
    """
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_DMSK_TS_STOCKEVALUATE",
        "filter": f'(SECURITY_CODE="{symbol}")',
        "columns": "ALL",
        "source": "WEB",
        "client": "WEB",
        "sortColumns": "TRADE_DATE",
        "sortTypes": "-1",
    }
    r = requests.get(url, params=params)
    data_json = r.json()
    temp_df = pd.DataFrame(data_json["result"]["data"])
    temp_df = temp_df[["TRADE_DATE", "ORG_PARTICIPATE"]]
    temp_df.columns = ["交易日", "机构参与度"]
    temp_df["交易日"] = pd.to_datetime(temp_df["交易日"], errors="coerce").dt.date
    temp_df.sort_values(["交易日"], inplace=True)
    temp_df.reset_index(inplace=True, drop=True)
    temp_df["机构参与度"] = pd.to_numeric(temp_df["机构参与度"], errors="coerce") * 100
    return temp_df


def get_stock_comment_lspf(symbol: str = "600000") -> pd.DataFrame:
    """
    东方财富网-数据中心-特色数据-千股千评-综合评价-历史评分
    
    :param symbol: 股票代码
    :return: 历史评分数据
    """
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "filter": f'(SECURITY_CODE="{symbol}")',
        "columns": "ALL",
        "source": "WEB",
        "client": "WEB",
        "reportName": "RPT_STOCK_HISTORYMARK",
        "sortColumns": "DIAGNOSE_DATE",
        "sortTypes": "1",
    }
    r = requests.get(url=url, params=params)
    data_json = r.json()
    temp_df = pd.DataFrame(data_json["result"]["data"])
    temp_df.rename(
        columns={
            "TOTAL_SCORE": "评分",
            "DIAGNOSE_DATE": "交易日",
        },
        inplace=True,
    )
    temp_df = temp_df[["交易日", "评分"]]
    temp_df["交易日"] = pd.to_datetime(temp_df["交易日"], errors="coerce").dt.date
    temp_df.sort_values(by=["交易日"], inplace=True)
    temp_df.reset_index(inplace=True, drop=True)
    temp_df["评分"] = pd.to_numeric(temp_df["评分"], errors="coerce")
    return temp_df


def get_stock_comment_focus(symbol: str = "600000") -> pd.DataFrame:
    """
    东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数
    
    :param symbol: 股票代码
    :return: 用户关注指数数据
    """
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "filter": f'(SECURITY_CODE="{symbol}")',
        "columns": "ALL",
        "source": "WEB",
        "client": "WEB",
        "reportName": "RPT_STOCK_MARKETFOCUS",
        "sortColumns": "TRADE_DATE",
        "sortTypes": "-1",
        "pageSize": "30",
    }
    r = requests.get(url=url, params=params)
    data_json = r.json()
    temp_df = pd.DataFrame(data_json["result"]["data"])
    temp_df.rename(
        columns={
            "MARKET_FOCUS": "用户关注指数",
            "TRADE_DATE": "交易日",
        },
        inplace=True,
    )
    temp_df = temp_df[["交易日", "用户关注指数"]]
    temp_df["交易日"] = pd.to_datetime(temp_df["交易日"], errors="coerce").dt.date
    temp_df.sort_values(by=["交易日"], inplace=True)
    temp_df.reset_index(inplace=True, drop=True)
    temp_df["用户关注指数"] = pd.to_numeric(temp_df["用户关注指数"], errors="coerce")
    return temp_df


def get_stock_comment_desire(symbol: str = "600000") -> Optional[pd.DataFrame]:
    """
    东方财富网-数据中心-特色数据-千股千评-市场热度-市场参与意愿
    
    :param symbol: 股票代码
    :return: 市场参与意愿数据，如果获取失败则返回None
    """
    url = f"https://data.eastmoney.com/stockcomment/api/{symbol}.json"
    try_count = 10
    data_json = None
    
    while try_count:
        try:
            r = requests.get(url)
            data_json = r.json()
            break
        except (requests.exceptions.JSONDecodeError, json.JSONDecodeError):
            try_count -= 1
            time.sleep(1)
            continue
    
    # 如果无法获取数据或数据结构不符合预期，返回None
    if not data_json or "ApiResults" not in data_json or "scrd" not in data_json["ApiResults"] or "desire" not in data_json["ApiResults"]["scrd"]:
        return None
    
    # 尝试获取日期字符串
    try:
        # 检查数据结构并安全获取日期
        if isinstance(data_json["ApiResults"]["scrd"]["desire"], list) and len(data_json["ApiResults"]["scrd"]["desire"]) > 0:
            if isinstance(data_json["ApiResults"]["scrd"]["desire"][0], list) and len(data_json["ApiResults"]["scrd"]["desire"][0]) > 0:
                if isinstance(data_json["ApiResults"]["scrd"]["desire"][0][0], dict) and "UpdateTime" in data_json["ApiResults"]["scrd"]["desire"][0][0]:
                    date_str = (
                        data_json["ApiResults"]["scrd"]["desire"][0][0]["UpdateTime"]
                        .split(" ")[0]
                        .replace("/", "-")
                    )
                else:
                    # 尝试其他可能的结构
                    date_str = time.strftime("%Y-%m-%d")
            else:
                date_str = time.strftime("%Y-%m-%d")
        else:
            date_str = time.strftime("%Y-%m-%d")
    except Exception:
        # 如果无法获取日期，使用当前日期
        date_str = time.strftime("%Y-%m-%d")
    
    # 尝试获取数据
    try:
        if len(data_json["ApiResults"]["scrd"]["desire"]) > 1 and isinstance(data_json["ApiResults"]["scrd"]["desire"][1], dict):
            xdata = data_json["ApiResults"]["scrd"]["desire"][1].get("XData", [])
            ydata = data_json["ApiResults"]["scrd"]["desire"][1].get("Ydata", {})
            
            major_data = ydata.get("MajorPeopleNumChg", [])
            all_data = ydata.get("PeopleNumChange", [])
            retail_data = ydata.get("RetailPeopleNumChg", [])
            
            # 确保所有数据长度一致
            min_length = min(len(xdata), len(major_data), len(all_data), len(retail_data))
            
            if min_length > 0:
                temp_df = pd.DataFrame({
                    "日期时间": xdata[:min_length],
                    "大户": major_data[:min_length],
                    "全部": all_data[:min_length],
                    "散户": retail_data[:min_length]
                })
                
                temp_df["日期时间"] = date_str + " " + temp_df["日期时间"]
                temp_df["日期时间"] = pd.to_datetime(temp_df["日期时间"], errors="coerce")
                temp_df.sort_values(by=["日期时间"], inplace=True)
                temp_df.reset_index(inplace=True, drop=True)
                temp_df["大户"] = pd.to_numeric(temp_df["大户"], errors="coerce")
                temp_df["全部"] = pd.to_numeric(temp_df["全部"], errors="coerce")
                temp_df["散户"] = pd.to_numeric(temp_df["散户"], errors="coerce")
                return temp_df
    except Exception:
        pass
    
    return None


def get_stock_comment_desire_daily(symbol: str = "600000") -> pd.DataFrame:
    """
    东方财富网-数据中心-特色数据-千股千评-市场热度-日度市场参与意愿
    
    :param symbol: 股票代码
    :return: 日度市场参与意愿数据
    """
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "filter": f'(SECURITY_CODE="{symbol}")',
        "columns": "ALL",
        "source": "WEB",
        "client": "WEB",
        "reportName": "RPT_STOCK_PARTICIPATION",
        "sortColumns": "TRADE_DATE",
        "sortTypes": "-1",
        "pageSize": "30",
    }
    r = requests.get(url=url, params=params)
    data_json = r.json()
    temp_df = pd.DataFrame(data_json["result"]["data"])
    temp_df.rename(
        columns={
            "PARTICIPATION_WISH_5DAYSCHANGE": "5日平均参与意愿变化",
            "PARTICIPATION_WISH_CHANGE": "当日意愿上升",
            "TRADE_DATE": "交易日",
        },
        inplace=True,
    )
    temp_df = temp_df[["交易日", "当日意愿上升", "5日平均参与意愿变化"]]
    temp_df["交易日"] = pd.to_datetime(temp_df["交易日"], errors="coerce").dt.date
    temp_df.sort_values(by=["交易日"], inplace=True)
    temp_df.reset_index(inplace=True, drop=True)
    temp_df["当日意愿上升"] = pd.to_numeric(temp_df["当日意愿上升"], errors="coerce")
    temp_df["5日平均参与意愿变化"] = pd.to_numeric(
        temp_df["5日平均参与意愿变化"], errors="coerce"
    )
    return temp_df


def get_stock_comment_cost(symbol: str = "600000") -> Optional[pd.DataFrame]:
    """
    东方财富网-数据中心-特色数据-千股千评-市场热度-市场成本
    
    :param symbol: 股票代码
    :return: 市场成本数据，如果获取失败则返回None
    """
    url = f"https://data.eastmoney.com/stockcomment/api/{symbol}.json"
    try_count = 10
    data_json = None
    
    while try_count:
        try:
            r = requests.get(url)
            data_json = r.json()
            break
        except (requests.exceptions.JSONDecodeError, json.JSONDecodeError):
            try_count -= 1
            time.sleep(1)
            continue
    
    # 如果无法获取数据或数据结构不符合预期，返回None
    if not data_json or "ApiResults" not in data_json or "scrd" not in data_json["ApiResults"] or "cost" not in data_json["ApiResults"]["scrd"]:
        return None
    
    # 尝试获取日期字符串
    try:
        # 检查数据结构并安全获取日期
        if isinstance(data_json["ApiResults"]["scrd"]["cost"], list) and len(data_json["ApiResults"]["scrd"]["cost"]) > 0:
            if isinstance(data_json["ApiResults"]["scrd"]["cost"][0], list) and len(data_json["ApiResults"]["scrd"]["cost"][0]) > 0:
                if isinstance(data_json["ApiResults"]["scrd"]["cost"][0][0], dict) and "UpdateDate" in data_json["ApiResults"]["scrd"]["cost"][0][0]:
                    date_str = (
                        data_json["ApiResults"]["scrd"]["cost"][0][0]["UpdateDate"]
                        .split(" ")[0]
                        .replace("/", "-")
                    )
                else:
                    # 尝试其他可能的结构
                    date_str = time.strftime("%Y-%m-%d")
            else:
                date_str = time.strftime("%Y-%m-%d")
        else:
            date_str = time.strftime("%Y-%m-%d")
    except Exception:
        # 如果无法获取日期，使用当前日期
        date_str = time.strftime("%Y-%m-%d")
    
    # 尝试获取数据
    try:
        if len(data_json["ApiResults"]["scrd"]["cost"]) > 1 and isinstance(data_json["ApiResults"]["scrd"]["cost"][1], dict):
            xdata = data_json["ApiResults"]["scrd"]["cost"][1].get("XData", [])
            ydata = data_json["ApiResults"]["scrd"]["cost"][1].get("Ydata", {})
            
            avg_buy_price = ydata.get("AvgBuyPrice", [])
            five_day_avg_buy_price = ydata.get("FiveDayAvgBuyPrice", [])
            
            # 确保所有数据长度一致
            min_length = min(len(xdata), len(avg_buy_price), len(five_day_avg_buy_price))
            
            if min_length > 0:
                temp_df = pd.DataFrame({
                    "日期": xdata[:min_length],
                    "市场成本": avg_buy_price[:min_length],
                    "5日市场成本": five_day_avg_buy_price[:min_length]
                })
                
                temp_df["日期"] = date_str[:4] + "-" + temp_df["日期"]
                temp_df["日期"] = pd.to_datetime(temp_df["日期"], errors="coerce").dt.date
                temp_df.sort_values(by=["日期"], inplace=True)
                temp_df.reset_index(inplace=True, drop=True)
                temp_df["市场成本"] = pd.to_numeric(temp_df["市场成本"], errors="coerce")
                temp_df["5日市场成本"] = pd.to_numeric(temp_df["5日市场成本"], errors="coerce")
                return temp_df
    except Exception:
        pass
    
    return None


if __name__ == "__main__":
    # 测试代码
    result = get_stock_comment_all(symbol="600000")
    for key, df in result.items():
        print(f"\n{key}数据:")
        print(df.head())