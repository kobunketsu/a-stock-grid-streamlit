import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

class GridStrategy:
    def __init__(self, symbol: str, symbol_name: str = None):
        """
        网格交易策略类
        
        Args:
            symbol (str): 证券代码
            symbol_name (str): 证券名称
        """
        self.symbol = symbol
        self.symbol_name = symbol_name if symbol_name else symbol
        
        # 初始化参数
        self.up_sell_rate = 0.01  # 上涨卖出比率
        self.up_callback_rate = 0.003  # 上涨回调比率
        self.down_buy_rate = 0.01  # 下跌买入比率
        self.down_rebound_rate = 0.003  # 下跌反弹比率
        self.shares_per_trade = 100  # 每次交易股数
        
        # 初始化资金和持仓
        self.initial_cash = 100000  # 初始资金
        self.initial_positions = 0  # 初始持仓
        self.cash = self.initial_cash  # 当前资金
        self.positions = self.initial_positions  # 当前持仓
        
        # 初始化价格相关参数
        self.base_price = None  # 基准价格
        self.price_range = (0.91, 1.01)  # 价格区间
        
        # 初始化均线保护参数
        self.ma_period = None  # MA周期
        self.ma_protection = False  # 是否启用MA保护
        
        # 初始化交易记录
        self.trades = []  # 成功交易记录
        self.failed_trades = {  # 失败交易统计
            "资金不足": 0,
            "持仓不足": 0,
            "价格超出范围": 0,
            "均线保护限制": 0
        }
        
        # 初始化其他参数
        self.verbose = False  # 是否打印详细信息
        
    def _get_price_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        获取价格数据
        
        Args:
            start_date (datetime): 开始日期
            end_date (datetime): 结束日期
            
        Returns:
            pd.DataFrame: 价格数据
        """
        try:
            # 如果是ETF基金
            if len(self.symbol) == 6 and self.symbol.startswith(("51", "56", "58", "15")):
                df = ak.fund_etf_hist_em(
                    symbol=self.symbol,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    adjust="qfq"
                )
            else:
                # 如果是股票
                df = ak.stock_zh_a_hist(
                    symbol=self.symbol,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    adjust="qfq"
                )
            
            # 确保日期列为索引且按时间升序排列
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期').sort_index()
            
            return df
            
        except Exception as e:
            print(f"获取价格数据失败: {e}")
            return pd.DataFrame()
            
    def _calculate_ma(self, df: pd.DataFrame) -> pd.Series:
        """
        计算移动平均线
        
        Args:
            df (pd.DataFrame): 价格数据
            
        Returns:
            pd.Series: MA数据
        """
        if not self.ma_period:
            return pd.Series(index=df.index)
            
        return df['收盘'].rolling(window=self.ma_period).mean()
        
    def _check_ma_protection(self, price: float, ma_price: float, is_buy: bool) -> bool:
        """
        检查均线保护条件
        
        Args:
            price (float): 当前价格
            ma_price (float): 均线价格
            is_buy (bool): 是否为买入操作
            
        Returns:
            bool: 是否允许交易
        """
        if not self.ma_protection or pd.isna(ma_price):
            return True
            
        if is_buy:
            # 买入时价格应低于均线
            return price <= ma_price
        else:
            # 卖出时价格应高于均线
            return price >= ma_price
            
    def _check_price_range(self, price: float) -> bool:
        """
        检查价格是否在允许范围内
        
        Args:
            price (float): 当前价格
            
        Returns:
            bool: 价格是否在范围内
        """
        min_price = self.base_price * self.price_range[0]
        max_price = self.base_price * self.price_range[1]
        return min_price <= price <= max_price
        
    def _try_buy(self, date: datetime, price: float, ma_price: float) -> bool:
        """
        尝试买入
        
        Args:
            date (datetime): 交易日期
            price (float): 买入价格
            ma_price (float): 均线价格
            
        Returns:
            bool: 是否买入成功
        """
        # 检查价格范围
        if not self._check_price_range(price):
            self.failed_trades["价格超出范围"] += 1
            if self.verbose:
                print(f"买入失败 - 价格超出范围: {price:.3f}")
            return False
            
        # 检查均线保护
        if not self._check_ma_protection(price, ma_price, True):
            self.failed_trades["均线保护限制"] += 1
            if self.verbose:
                print(f"买入失败 - 均线保护限制: 价格 {price:.3f} > 均线 {ma_price:.3f}")
            return False
            
        # 计算所需资金
        required_cash = price * self.shares_per_trade
        
        # 检查资金是否足够
        if self.cash < required_cash:
            self.failed_trades["资金不足"] += 1
            if self.verbose:
                print(f"买入失败 - 资金不足: 需要 {required_cash:.2f}，当前 {self.cash:.2f}")
            return False
            
        # 执行买入
        self.cash -= required_cash
        self.positions += self.shares_per_trade
        
        # 记录交易
        self.trades.append({
            "date": date,
            "type": "买入",
            "price": price,
            "shares": self.shares_per_trade,
            "amount": required_cash,
            "cash": self.cash,
            "positions": self.positions
        })
        
        if self.verbose:
            print(f"买入成功: {self.shares_per_trade}股 @ {price:.3f}")
            print(f"剩余资金: {self.cash:.2f}, 当前持仓: {self.positions}")
            
        return True
        
    def _try_sell(self, date: datetime, price: float, ma_price: float) -> bool:
        """
        尝试卖出
        
        Args:
            date (datetime): 交易日期
            price (float): 卖出价格
            ma_price (float): 均线价格
            
        Returns:
            bool: 是否卖出成功
        """
        # 检查价格范围
        if not self._check_price_range(price):
            self.failed_trades["价格超出范围"] += 1
            if self.verbose:
                print(f"卖出失败 - 价格超出范围: {price:.3f}")
            return False
            
        # 检查均线保护
        if not self._check_ma_protection(price, ma_price, False):
            self.failed_trades["均线保护限制"] += 1
            if self.verbose:
                print(f"卖出失败 - 均线保护限制: 价格 {price:.3f} < 均线 {ma_price:.3f}")
            return False
            
        # 检查持仓是否足够
        if self.positions < self.shares_per_trade:
            self.failed_trades["持仓不足"] += 1
            if self.verbose:
                print(f"卖出失败 - 持仓不足: 需要 {self.shares_per_trade}，当前 {self.positions}")
            return False
            
        # 计算卖出收入
        income = price * self.shares_per_trade
        
        # 执行卖出
        self.cash += income
        self.positions -= self.shares_per_trade
        
        # 记录交易
        self.trades.append({
            "date": date,
            "type": "卖出",
            "price": price,
            "shares": self.shares_per_trade,
            "amount": income,
            "cash": self.cash,
            "positions": self.positions
        })
        
        if self.verbose:
            print(f"卖出成功: {self.shares_per_trade}股 @ {price:.3f}")
            print(f"当前资金: {self.cash:.2f}, 剩余持仓: {self.positions}")
            
        return True
        
    def backtest(self, start_date: datetime, end_date: datetime, verbose: bool = False) -> float:
        """
        执行回测
        
        Args:
            start_date (datetime): 开始日期
            end_date (datetime): 结束日期
            verbose (bool): 是否打印详细信息
            
        Returns:
            float: 收益率
        """
        self.verbose = verbose
        
        if self.verbose:
            print(f"\n开始回测 {self.symbol_name}...")
            print(f"回测区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            print(f"初始资金: {self.initial_cash:.2f}")
            print(f"初始持仓: {self.initial_positions}")
            if self.ma_protection:
                print(f"均线保护: 开启 (MA{self.ma_period})")
            print("\n交易参数:")
            print(f"上涨卖出比率: {self.up_sell_rate*100:.2f}%")
            print(f"上涨回调比率: {self.up_callback_rate*100:.2f}%")
            print(f"下跌买入比率: {self.down_buy_rate*100:.2f}%")
            print(f"下跌反弹比率: {self.down_rebound_rate*100:.2f}%")
            print(f"每次交易股数: {self.shares_per_trade}")
            print(f"价格区间: {self.price_range}")
            
        # 获取价格数据
        df = self._get_price_data(start_date, end_date)
        if df.empty:
            print("未获取到价格数据")
            return 0
            
        # 计算均线
        df['MA'] = self._calculate_ma(df)
        
        # 初始化状态变量
        last_high = df.iloc[0]['收盘']  # 最近高点
        last_low = df.iloc[0]['收盘']  # 最近低点
        in_uptrend = True  # 是否处于上升趋势
        in_downtrend = True  # 是否处于下降趋势
        
        # 遍历每个交易日
        for date, row in df.iterrows():
            current_price = row['收盘']
            ma_price = row['MA']
            
            # 更新最高价和最低价
            if current_price > last_high:
                last_high = current_price
                in_uptrend = True
            elif current_price < last_low:
                last_low = current_price
                in_downtrend = True
                
            # 检查上涨回调卖出
            if in_uptrend and (last_high - current_price) / last_high >= self.up_callback_rate:
                if current_price / last_low >= (1 + self.up_sell_rate):
                    if self._try_sell(date, current_price, ma_price):
                        in_uptrend = False
                        last_high = current_price
                        
            # 检查下跌反弹买入
            if in_downtrend and (current_price - last_low) / last_low >= self.down_rebound_rate:
                if last_high / current_price >= (1 + self.down_buy_rate):
                    if self._try_buy(date, current_price, ma_price):
                        in_downtrend = False
                        last_low = current_price
                        
        # 计算收益率
        final_value = self.cash + self.positions * df.iloc[-1]['收盘']
        initial_value = self.initial_cash + self.initial_positions * df.iloc[0]['收盘']
        profit_rate = (final_value - initial_value) / initial_value * 100
        
        if self.verbose:
            print("\n回测结束")
            print(f"期末资金: {self.cash:.2f}")
            print(f"期末持仓: {self.positions}")
            print(f"期末总值: {final_value:.2f}")
            print(f"收益率: {profit_rate:.2f}%")
            print("\n交易统计:")
            print(f"总交易次数: {len(self.trades)}")
            print("失败交易统计:")
            for reason, count in self.failed_trades.items():
                if count > 0:
                    print(f"  {reason}: {count}次")
                    
        return profit_rate
        
    def get_trade_details(self) -> List[Dict[str, Any]]:
        """
        获取交易详情
        
        Returns:
            List[Dict[str, Any]]: 交易记录列表
        """
        return self.trades