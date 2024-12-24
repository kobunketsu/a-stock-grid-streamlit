import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

class GridStrategy:
    def __init__(self, symbol="560610", symbol_name="国开ETF"):
        self.symbol = symbol
        self.symbol_name = symbol_name
        self.base_price = None  # 移除硬编码的默认值
        self.price_range = None  # 移除硬编码的默认值
        self.up_sell_rate = 0.0045
        self.up_callback_rate = 0.01
        self.down_buy_rate = 0.01
        self.down_rebound_rate = 0.004
        self.shares_per_trade = 50000
        self.initial_positions = 50000
        self.positions = self.initial_positions
        self.initial_cash = 50000
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

    def buy(self, price, time):
        """
        执行买入操作
        """
        # 首先验证价格是否在允许范围内
        if not (self.price_range[0] <= price <= self.price_range[1]):
            if self.verbose:
                print(f"买入价格 {price:.3f} 超出允许范围 {self.price_range}")
            self.failed_trades["买入价格超范围"] += 1
            return False
            
        amount = price * self.shares_per_trade
        if self.cash >= amount:
            self.positions += self.shares_per_trade
            self.cash -= amount
            self.trades.append({
                "时间": time,
                "操作": "买入",
                "价格": price,
                "数量": self.shares_per_trade,
                "金额": amount
            })
            return True
        return False

    def sell(self, price, time):
        """
        执行卖出操作
        """
        # 首先验证价格是否在允许范围内
        if not (self.price_range[0] <= price <= self.price_range[1]):
            if self.verbose:
                print(f"卖出价格 {price:.3f} 超出允许范围 {self.price_range}")
            self.failed_trades["卖出价格超范围"] += 1
            return False
            
        if self.positions >= self.shares_per_trade:
            amount = price * self.shares_per_trade
            self.positions -= self.shares_per_trade
            self.cash += amount
            self.trades.append({
                "时间": time,
                "操作": "卖出",
                "价格": price,
                "数量": self.shares_per_trade,
                "金额": amount
            })
            return True
        return False

    def backtest(self, start_date=None, end_date=None, verbose=False):
        """
        执行回测
        """
        # 处理日期参数
        if start_date is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=20)
        else:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        try:
            if verbose:
                print(f"\n=== {self.symbol_name}({self.symbol}) 回测报告 ===")
                print(f"回测区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            
            # 根据证券类型获取历史数据
            if hasattr(self, 'security_type') and self.security_type == "STOCK":
                df = ak.stock_zh_a_hist(
                    symbol=self.symbol,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    adjust="qfq"
                )
            else:
                # 默认使用ETF数据接口
                df = ak.fund_etf_hist_em(
                    symbol=self.symbol,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    adjust="qfq"
                )
            
            if df.empty:
                raise Exception("未获取到任何数据")
            
            df = df.reset_index(drop=True)
            last_trigger_price_up = self.base_price
            last_trigger_price_down = self.base_price
            
            for i, row in df.iterrows():
                daily_prices = [
                    (row['开盘'], '开盘'),
                    (row['最高'], '最高'),
                    (row['最低'], '最低'),
                    (row['收盘'], '收盘')
                ]
                
                trades_before = len(self.trades)
                
                if verbose:
                    print(f"\n=== {row['日期']} 行情 ===")
                    print(f"开盘: {row['开盘']:.3f}")
                    print(f"最高: {row['最高']:.3f}")
                    print(f"最低: {row['最低']:.3f}")
                    print(f"收盘: {row['收盘']:.3f}")
                
                for current_price, price_type in daily_prices:
                    if verbose:
                        print(f"\n检查{price_type}价格点: {current_price:.3f}")
                    
                    # 处理卖出逻辑
                    if self.positions > 0:
                        sell_trigger_price = last_trigger_price_up * (1 + self.up_sell_rate)
                        if current_price >= sell_trigger_price:
                            # 计算倍数
                            price_diff = (current_price - sell_trigger_price) / sell_trigger_price
                            multiple = int(price_diff / self.up_sell_rate) + 1 if self.multiple_trade else 1
                            multiple = min(multiple, self.positions // self.shares_per_trade)
                            
                            execute_price = sell_trigger_price * (1 - self.up_callback_rate)
                            if execute_price <= current_price:
                                for _ in range(multiple):
                                    if self.sell(execute_price, row['日期']):
                                        last_trigger_price_up = execute_price
                                        last_trigger_price_down = execute_price
                                        if verbose:
                                            print(f"触发卖出 - 触发价: {sell_trigger_price:.3f}, 执行价: {execute_price:.3f}")
                                            print(f"交易份额: {self.shares_per_trade * multiple}, 当前总持仓: {self.positions}")
                            else:
                                if verbose:
                                    print(f"\n无法卖出 - 执行价 {execute_price:.3f} 高于当前价格 {current_price:.3f}")
                                self.failed_trades["卖出价格超范围"] += 1
                    else:
                        if verbose:
                            print("\n无法卖出 - 当前无持仓")
                        self.failed_trades["无持仓"] += 1
                    
                    # 处理买入逻辑
                    buy_trigger_price = last_trigger_price_down * (1 - self.down_buy_rate)
                    if verbose:
                        print(f"\n当前价格: {current_price:.3f}")
                        print(f"上次触发价: {last_trigger_price_down:.3f}")
                        print(f"买入触发价: {buy_trigger_price:.3f}")
                    
                    if current_price <= buy_trigger_price:
                        price_diff = (buy_trigger_price - current_price) / buy_trigger_price
                        multiple = int(price_diff / self.down_buy_rate) + 1 if self.multiple_trade else 1
                        
                        execute_price = buy_trigger_price * (1 + self.down_rebound_rate)
                        required_cash = execute_price * self.shares_per_trade * multiple
                        
                        if self.cash >= required_cash and current_price <= execute_price:
                            for _ in range(multiple):
                                if self.buy(execute_price, row['日期']):
                                    last_trigger_price_down = execute_price
                                    if verbose:
                                        print(f"触发买入 - 触发价: {buy_trigger_price:.3f}, 执行价: {execute_price:.3f}")
                                        print(f"交易份额: {self.shares_per_trade * multiple}, 当前总持仓: {self.positions}")
                        else:
                            if verbose:
                                print(f"\n无法买入 - 所需资金 {required_cash:.2f}, 当前现金 {self.cash:.2f}")
                            self.failed_trades["现金不足"] += 1
                
                # 打印当日交易记录
                if verbose:
                    trades_after = len(self.trades)
                    if trades_after > trades_before:
                        print("\n当日交易:")
                        for trade in self.trades[trades_before:trades_after]:
                            print(f"{trade['操作']} - 价格: {trade['价格']:.3f}, 数量: {trade['数量']}, 金额: {trade['金额']:.2f}")
                    else:
                        print("\n当日无交易")
                    print(f"当日结束持仓: {self.positions}, 现金: {self.cash:.2f}")
            
            # 计算最终收益
            self.calculate_profit(df.iloc[-1]['收盘'], verbose)
            
            return self.final_profit_rate
            
        except Exception as e:
            print(f"回测过程中发生错误: {str(e)}")
            raise

    def calculate_profit(self, last_price, verbose=False):
        """
        计算并打印回测结果
        """
        initial_total = self.initial_cash + (self.initial_positions * self.base_price)
        final_assets = self.cash + (self.positions * last_price)
        profit = final_assets - initial_total
        self.final_profit_rate = (profit / initial_total) * 100
        
        if verbose:
            print("\n=== 回测结果 ===")
            print("策略参数:")
            print(f"基准价格: {self.base_price:.3f}")
            print(f"价格区间: {self.price_range[0]:.3f} - {self.price_range[1]:.3f}")
            print(f"每上涨卖出: {self.up_sell_rate*100:.2f}%")
            print(f"上涨回调: {self.up_callback_rate*100:.2f}%")            
            print(f"每下跌买入: {self.down_buy_rate*100:.2f}%")
            print(f"下跌反弹: {self.down_rebound_rate*100:.2f}%")
            print(f"单次交易股数: {self.shares_per_trade:,}")
            
            print("\n资金状况:")
            print(f"初始现金: {self.initial_cash:,.2f}")
            print(f"初始持仓: {self.initial_positions}股 (按{self.base_price:.3f}元计算)")
            print(f"初始总资产: {initial_total:,.2f}")
            print(f"最终现金: {self.cash:,.2f}")
            print(f"最终持仓: {self.positions}股 (按{last_price:.3f}元计算)")
            print(f"最终总资产: {final_assets:,.2f}")
            print(f"总收益: {profit:,.2f}")
            print(f"收益率: {self.final_profit_rate:.2f}%")
            
            print("\n=== 交易统计 ===")
            print(f"成功交易次数: {len(self.trades)}")
            
            print("\n未成交统计:")
            for reason, count in self.failed_trades.items():
                if count > 0:
                    print(f"{reason}: {count}次")
            
            print(f"\n=== {self.symbol_name}({self.symbol}) 交易记录 ===")
            trades_df = pd.DataFrame(self.trades)
            if not trades_df.empty:
                print(trades_df)
            else:
                print("无交易记录")
        
        return self.final_profit_rate

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

if __name__ == "__main__":
    strategy = GridStrategy()
    # 可以指定日期范围
    strategy.backtest('2024-10-15', '2024-12-20')
    # 或使用默认的最近20天
    # strategy.backtest()