import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def calculate_ma_price(symbol: str, start_date: datetime, ma_period: int, security_type: str = "ETF") -> tuple:
    """
    计算均线价格
    @param symbol: 证券代码
    @param start_date: 开始日期
    @param ma_period: 均线周期
    @param security_type: 证券类型 ("ETF" 或 "STOCK")
    @return: (收盘价, 均线价格)的元组，如果计算失败则返回(None, None)
    """
    try:
        # 计算均线所需的开始日期
        start_date_for_ma = start_date - timedelta(days=ma_period * 2)
        start_date_str = start_date_for_ma.strftime('%Y-%m-%d')
        end_date_str = start_date.strftime('%Y-%m-%d')
        
        if security_type == "STOCK":
            df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date_str, end_date=end_date_str, adjust="qfq")
        else:
            df = ak.fund_etf_hist_em(symbol=symbol, start_date=start_date_str, end_date=end_date_str, adjust="qfq")
        
        if df.empty:
            print("未获取到任何数据")
            return None, None
        
        # 确保日期列为索引且按时间升序排列
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期').sort_index()
        elif 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.set_index('trade_date').sort_index()
        
        # 计算移动平均线
        df['MA'] = df['收盘'].rolling(window=ma_period).mean()
        
        # 获取开始日期的收盘价和均线价格
        target_date_data = df.loc[df.index <= start_date]
        if target_date_data.empty:
            print("目标日期没有数据")
            return None, None
            
        last_data = target_date_data.iloc[-1]
        close_price = float(last_data['收盘'])
        ma_price = float(last_data['MA'])
        
        return close_price, ma_price
    except Exception as e:
        print(f"计算均线价格时发生错误: {e}")
        return None, None 