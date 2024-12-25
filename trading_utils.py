import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any

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

def get_symbol_info(symbol: str) -> Tuple[Optional[str], str]:
    """
    获取证券信息
    @param symbol: 证券代码
    @return: (证券名称, 证券类型)的元组，如果未找到则返回(None, "ETF")
    """
    try:
        # 自动判断证券类型
        security_type = "ETF" if len(symbol) == 6 and symbol.startswith(("1", "5")) else "STOCK"
        
        if security_type == "ETF":
            df = ak.fund_etf_spot_em()
            if symbol in df['代码'].values:
                return df[df['代码'] == symbol]['名称'].values[0], security_type
        else:
            df = ak.stock_zh_a_spot_em()
            if symbol in df['代码'].values:
                return df[df['代码'] == symbol]['名称'].values[0], security_type
                
        return None, security_type
        
    except Exception as e:
        print(f"获取证券信息失败: {e}")
        return None, "ETF"

def calculate_price_range(symbol: str, start_date: str, end_date: str, security_type: str = "ETF") -> Tuple[Optional[float], Optional[float]]:
    """
    计算价格范围
    @param symbol: 证券代码
    @param start_date: 开始日期
    @param end_date: 结束日期
    @param security_type: 证券类型
    @return: (最小价格, 最大价格)的元组，如果计算失败则返回(None, None)
    """
    try:
        if security_type == "ETF":
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )
        else:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )
            
        if df.empty:
            return None, None
            
        price_min = df['最低'].min()
        price_max = df['最高'].max()
        return price_min, price_max
        
    except Exception as e:
        print(f"计算价格范围失败: {e}")
        return None, None

def is_valid_symbol(symbol: str) -> bool:
    """
    检查证券代码是否有效
    @param symbol: 证券代码
    @return: 是否有效
    """
    try:
        # 自动判断证券类型
        if len(symbol) == 6 and symbol.startswith(("1", "5")):
            df = ak.fund_etf_spot_em()
        else:
            df = ak.stock_zh_a_spot_em()
        return symbol in df['代码'].values
    except Exception:
        return False 