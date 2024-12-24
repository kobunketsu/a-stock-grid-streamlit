import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_trading_days(start_date, end_date):
    """获取交易日列表"""
    # 生成日期范围内的所有日期
    date_range = pd.date_range(start=start_date, end=end_date)
    
    # 过滤出工作日（周一到周五）
    trading_days = date_range[date_range.dayofweek < 5]
    
    return trading_days

def build_segments(start_date, end_date, segment_days=60, overlap_days=0):
    """构建时间段列表
    
    Args:
        start_date (datetime): 开始日期
        end_date (datetime): 结束日期
        segment_days (int): 每个时间段的天数
        overlap_days (int): 重叠的天数
        
    Returns:
        list: 时间段列表，每个元素为(segment_start, segment_end)元组
    """
    # 获取交易日列表
    trading_days = get_trading_days(start_date, end_date)
    
    # 计算实际的时间段长度（考虑周末）
    actual_segment_days = segment_days
    actual_overlap_days = overlap_days
    
    segments = []
    current_start = trading_days[0]
    
    while current_start <= trading_days[-1]:
        # 找到当前开始日期在交易日列表中的索引
        start_idx = trading_days.get_loc(current_start)
        
        # 计算结束日期的索引
        end_idx = min(start_idx + actual_segment_days, len(trading_days))
        
        # 获取结束日期
        segment_end = trading_days[end_idx - 1]
        
        # 添加时间段
        segments.append((current_start.to_pydatetime(), segment_end.to_pydatetime()))
        
        # 更新下一个时间段的开始日期
        if end_idx >= len(trading_days):
            break
            
        # 计算下一个开始日期的索引
        next_start_idx = end_idx - actual_overlap_days
        current_start = trading_days[next_start_idx]
    
    return segments
