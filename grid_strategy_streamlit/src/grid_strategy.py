import pandas as pd
import numpy as np
from datetime import datetime
import akshare as ak
import logging

class GridStrategy:
    """网格交易策略类"""
    
    def __init__(self, symbol="159300", symbol_name="300ETF"):
        """
        初始化网格交易策略
        """
        self.symbol = symbol
        self.symbol_name = symbol_name
        self.base_price = None
        self.price_range = None
        self.up_sell_rate = 0.0045
        self.up_callback_rate = 0.01
        self.down_buy_rate = 0.01
        self.down_rebound_rate = 0.004
        self.shares_per_trade = 1000
        self.initial_positions = 0
        self.positions = self.initial_positions
        self.initial_cash = 100000
        self.cash = self.initial_cash
        self.trades = []
        self.failed_trades = {
            "无持仓": 0,
            "卖出价格超范围": 0,
            "现金不足": 0,
            "买入价格超范围": 0
        }
        self.final_profit_rate = 0.0
        self.multiple_trade = True
        self.verbose = False
        self.ma_period = None
        self.ma_protection = False
        self.ma_data = None
        self.security_type = "ETF"
        
        # 记录最大最小值
        self.max_positions = 0
        self.min_positions = float('inf')
        self.max_cash = 0
        self.min_cash = float('inf')
    
    def _validate_parameters(self):
        """验证参数有效性"""
        if self.initial_cash <= 0:
            raise ValueError("初始资金必须大于0")
        if self.initial_positions < 0:
            raise ValueError("初始持仓不能为负数")
        if not self.price_range or self.price_range[0] >= self.price_range[1]:
            raise ValueError("价格区间无效")
        if not self.base_price:
            raise ValueError("基准价格未设置")
    
    def _check_ma_protection(self, price, ma_price, is_buy):
        """
        检查均线保护条件
        
        Args:
            price (float): 当前价格
            ma_price (float): 均线价格
            is_buy (bool): 是否为买入操作
            
        Returns:
            bool: 是否允许交易
        """
        if not self.ma_protection or ma_price is None:
            return True
            
        if is_buy:
            return price >= ma_price  # 价格在均线以上才能买入
        else:
            return price <= ma_price  # 价格在均线以下才能卖出
    
    def buy(self, price, date):
        """
        执行买入操作
        
        Args:
            price (float): 买入价格
            date (str): 交易日期
            
        Returns:
            bool: 买入是否成功
        """
        # 转换日期格式
        if isinstance(date, pd.Timestamp):
            date = date.strftime('%Y-%m-%d')
        elif not isinstance(date, str):
            raise ValueError("日期格式无效")
            
        # 检查是否为未来日期
        if datetime.strptime(date, '%Y-%m-%d') > datetime.now():
            return False
            
        # 检查价格是否在区间内
        if price < self.price_range[0]:
            self.failed_trades["买入价格超范围"] += 1
            return False
            
        # 检查现金是否足够
        cost = price * self.shares_per_trade
        if cost > self.cash:
            self.failed_trades["现金不足"] += 1
            return False
            
        # 执行买入
        self.cash -= cost
        self.positions += self.shares_per_trade
        self.trades.append({
            "日期": date,
            "操作": "买入",
            "价格": price,
            "数量": self.shares_per_trade,
            "金额": cost
        })
        
        # 更新最大最小值
        self.max_positions = max(self.max_positions, self.positions)
        self.min_positions = min(self.min_positions, self.positions)
        self.max_cash = max(self.max_cash, self.cash)
        self.min_cash = min(self.min_cash, self.cash)
        
        return True
    
    def sell(self, price, date):
        """
        执行卖出操作
        
        Args:
            price (float): 卖出价格
            date (str): 交易日期
            
        Returns:
            bool: 卖出是否成功
        """
        # 转换日期格式
        if isinstance(date, pd.Timestamp):
            date = date.strftime('%Y-%m-%d')
        elif not isinstance(date, str):
            raise ValueError("日期格式无效")
            
        # 检查是否为未来日期
        if datetime.strptime(date, '%Y-%m-%d') > datetime.now():
            return False
            
        # 检查价格是否在区间内
        if price > self.price_range[1]:
            self.failed_trades["卖出价格超范围"] += 1
            return False
            
        # 检查持仓是否足够
        if self.positions < self.shares_per_trade:
            self.failed_trades["无持仓"] += 1
            return False
            
        # 执行卖出
        income = price * self.shares_per_trade
        self.cash += income
        self.positions -= self.shares_per_trade
        self.trades.append({
            "日期": date,
            "操作": "卖出",
            "价格": price,
            "数量": self.shares_per_trade,
            "金额": income
        })
        
        # 更新最大最小值
        self.max_positions = max(self.max_positions, self.positions)
        self.min_positions = min(self.min_positions, self.positions)
        self.max_cash = max(self.max_cash, self.cash)
        self.min_cash = min(self.min_cash, self.cash)
        
        return True
    
    def calculate_profit(self, current_price, verbose=False):
        """
        计算当前收益
        
        Args:
            current_price (float): 当前价格
            verbose (bool): 是否打印详细信息
            
        Returns:
            float: 收益率
        """
        # 计算当前总资产
        total_assets = self.cash + self.positions * current_price
        
        # 计算初始总资产
        initial_total = self.initial_cash + self.initial_positions * self.base_price
        
        # 计算收益率
        profit = total_assets - initial_total
        self.final_profit_rate = (profit / initial_total) * 100
        
        if verbose:
            print(f"\n当前总资产: {total_assets:.2f}")
            print(f"初始总资产: {initial_total:.2f}")
            print(f"总收益: {profit:.2f}")
            print(f"收益���: {self.final_profit_rate:.2f}%")
            print(f"\n最大持仓: {self.max_positions}")
            print(f"最小持仓: {self.min_positions}")
            print(f"最大现金: {self.max_cash:.2f}")
            print(f"最小现金: {self.min_cash:.2f}")
            print("\n失败交易统计:")
            for reason, count in self.failed_trades.items():
                if count > 0:
                    print(f"{reason}: {count}次")
        
        return self.final_profit_rate
    
    def backtest(self, start_date, end_date, verbose=False):
        """
        执行回测
        
        Args:
            start_date (str): 开始日期
            end_date (str): 结束日期
            verbose (bool): 是否打印详细信息
            
        Returns:
            float: 回测收益率
        """
        # 验证参数
        self._validate_parameters()
        
        # 获取历史数据
        try:
            if self.security_type == "ETF":
                logging.info(f"获取ETF历史数据: {self.symbol}, {start_date} - {end_date}")
                # 修改ETF数据获取方式，与tk版本保持一致
                hist_data = ak.fund_etf_hist_em(
                    symbol=self.symbol,
                    start_date=start_date.replace('-', ''),
                    end_date=end_date.replace('-', ''),
                    adjust="qfq"
                )
                if hist_data is None or hist_data.empty:
                    logging.error(f"获取ETF历史数据失败: {self.symbol}")
                    raise ValueError(f"获取ETF历史数据失败: {self.symbol}")
                logging.info(f"获取到 {len(hist_data)} 条ETF历史数据")
                logging.info(f"数据列: {hist_data.columns.tolist()}")
            else:  # 股票
                logging.info(f"获取股票历史数据: {self.symbol}, {start_date} - {end_date}")
                hist_data = ak.stock_zh_a_hist(symbol=self.symbol, start_date=start_date, end_date=end_date)
                if hist_data is None or hist_data.empty:
                    logging.error(f"获取股票历史数据失败: {self.symbol}")
                    raise ValueError(f"获取股票历史数据失败: {self.symbol}")
                logging.info(f"获取到 {len(hist_data)} 条股票历史数据")
                
            # 确保日期列为索引且按时间升序排列
            if '日期' in hist_data.columns:
                hist_data['日期'] = pd.to_datetime(hist_data['日期'])
                hist_data = hist_data.set_index('日期').sort_index()
            elif 'trade_date' in hist_data.columns:
                hist_data['trade_date'] = pd.to_datetime(hist_data['trade_date'])
                hist_data = hist_data.set_index('trade_date').sort_index()
            
            # 统一列名
            column_mapping = {
                '开盘': '开盘',
                'open': '开盘',
                '收盘': '收盘',
                'close': '收盘',
                '最高': '最高',
                'high': '最高',
                '最低': '最低',
                'low': '最低'
            }
            hist_data = hist_data.rename(columns=column_mapping)
            
            logging.info(f"处理后的数据列: {hist_data.columns.tolist()}")
            
            # 初始化上一次触发价格
            last_trigger_price_up = self.base_price
            last_trigger_price_down = self.base_price
            
            # 遍历每个交易日
            for index, row in hist_data.iterrows():
                daily_prices = [
                    (row['开盘'], '开盘'),
                    (row['最高'], '最高'),
                    (row['最低'], '最低'),
                    (row['收盘'], '收盘')
                ]
                
                date_str = index.strftime('%Y-%m-%d')
                
                # 处理每个价格点
                for current_price, price_type in daily_prices:
                    if verbose:
                        logging.info(f"\n检查{price_type}价格点: {current_price:.3f}")
                    
                    # 处理卖出逻辑
                    if self.positions > 0:
                        sell_trigger_price = last_trigger_price_up * (1 + self.up_sell_rate)
                        if current_price >= sell_trigger_price:
                            # 计算倍数
                            price_diff = (current_price - sell_trigger_price) / sell_trigger_price
                            multiple = int(price_diff / self.up_sell_rate) + 1
                            multiple = min(multiple, self.positions // self.shares_per_trade)
                            
                            execute_price = sell_trigger_price * (1 - self.up_callback_rate)
                            if execute_price <= current_price:
                                for _ in range(multiple):
                                    if self.sell(execute_price, date_str):
                                        last_trigger_price_up = execute_price
                                        last_trigger_price_down = execute_price
                                        if verbose:
                                            logging.info(f"触发卖出 - 触发价: {sell_trigger_price:.3f}, 执行价: {execute_price:.3f}")
                                            logging.info(f"交易份额: {self.shares_per_trade * multiple}, 当前总持仓: {self.positions}")
                            else:
                                if verbose:
                                    logging.info(f"\n无法卖出 - 执行价 {execute_price:.3f} 高于当前价格 {current_price:.3f}")
                                self.failed_trades["卖出价格超范围"] += 1
                    
                    # 处理买入逻辑
                    if self.cash >= self.shares_per_trade * current_price:
                        buy_trigger_price = last_trigger_price_down * (1 - self.down_buy_rate)
                        if current_price <= buy_trigger_price:
                            # 计算倍数
                            price_diff = (buy_trigger_price - current_price) / buy_trigger_price
                            multiple = int(price_diff / self.down_buy_rate) + 1
                            max_shares = int(self.cash / current_price)
                            multiple = min(multiple, max_shares // self.shares_per_trade)
                            
                            execute_price = buy_trigger_price * (1 + self.down_rebound_rate)
                            if execute_price >= current_price:
                                for _ in range(multiple):
                                    if self.buy(execute_price, date_str):
                                        last_trigger_price_up = execute_price
                                        last_trigger_price_down = execute_price
                                        if verbose:
                                            logging.info(f"触发买入 - 触发价: {buy_trigger_price:.3f}, 执行价: {execute_price:.3f}")
                                            logging.info(f"交易份额: {self.shares_per_trade * multiple}, 当前总持仓: {self.positions}")
                            else:
                                if verbose:
                                    logging.info(f"\n无法买入 - 执行价 {execute_price:.3f} 低于当前价格 {current_price:.3f}")
                                self.failed_trades["买入价格超范围"] += 1
                    
                    # 更新均线数据
                    if self.ma_protection:
                        ma_price = None
                        if len(hist_data.loc[:index]) >= self.ma_period:
                            ma_price = hist_data.loc[:index]['收盘'].tail(self.ma_period).mean()
                        self.ma_data = ma_price
            
            # 计算最终收益
            final_price = hist_data.iloc[-1]['收盘']
            return self.calculate_profit(final_price, verbose)
            
        except Exception as e:
            logging.error(f"回测失败: {e}")
            raise e 