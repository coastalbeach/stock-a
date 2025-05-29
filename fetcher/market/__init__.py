#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
市场数据获取模块

包含市场总貌数据、板块实时数据、行业板块数据和地区交易数据的获取功能
"""

from .board_realtime import BoardRealtime
from .sector_data import SectorData

__all__ = ['BoardRealtime', 'SectorData']