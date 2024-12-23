import pandas as pd
from datetime import datetime
import akshare as ak

# 批次天数映射
BATCH_TO_DAYS_MAP = {
    1: 60,
    2: 30,
    3: 20,
    4: 10,
    5: 5
}

def build_segments(start_date: datetime, end_date: datetime, min_buy_times: int):
    """构建时间段"""
    # 规范化min_buy_times
    if min_buy_times not in BATCH_TO_DAYS_MAP:
        min_buy_times = min(max(min_buy_times, 1), 5)
    
    segment_days = BATCH_TO_DAYS_MAP[min_buy_times]
    
    # 获取交易日历
    try:
        df_calendar = ak.tool_trade_date_hist_sina()
        df_calendar['trade_date'] = pd.to_datetime(df_calendar['trade_date'])
        mask = (df_calendar['trade_date'] >= pd.to_datetime(start_date)) & \
               (df_calendar['trade_date'] <= pd.to_datetime(end_date))
        trading_days = pd.DatetimeIndex(df_calendar.loc[mask].sort_values('trade_date')['trade_date'].values)
    except Exception as e:
        print(f"获取交易日历失败: {e}")
        trading_days = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 构建时间段
    segments = []
    total_days = len(trading_days)
    start_idx = 0
    
    if total_days == 0:
        return [(start_date, end_date)]
    
    while start_idx < total_days:
        end_idx = min(start_idx + segment_days, total_days)
        seg_start = trading_days[start_idx]
        seg_end = trading_days[end_idx - 1]
        segments.append((seg_start, seg_end))
        start_idx = end_idx
    
    return segments 

def get_segment_days(min_buy_times: int) -> int:
    """获取对应的天数"""
    if min_buy_times not in BATCH_TO_DAYS_MAP:
        min_buy_times = min(max(min_buy_times, 1), 5)
    return BATCH_TO_DAYS_MAP[min_buy_times] 