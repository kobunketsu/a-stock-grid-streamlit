import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

class GridStrategy:
    def __init__(self, symbol="560610", symbol_name="国开ETF"):
        self.symbol = symbol
        self.symbol_name = symbol_name
        self.base_price = 0.960  # 基准价
        self.price_range = (0.910, 1.010)  # 价格区间
        self.up_sell_rate = 0.0045  # 上涨卖出比例
        self.up_callback_rate = 0.01  # 上涨回调比例
        self.down_buy_rate = 0.01 # 下跌买入比例
        self.down_rebound_rate = 0.004  # 下跌反弹比例
        self.shares_per_trade = 50000  # 每次交易股数
        self.initial_positions = 50000  # 初始持仓数量
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
        self.multiple_trade = True  # 启用倍数交易

    def buy(self, price, time):
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

    def backtest(self, start_date=None, end_date=None):
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
            print(f"\n开始回测 {self.symbol_name}({self.symbol})")
            print(f"回测区间: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
            
            # 使用日线数据而不是分钟数据
            df = ak.fund_etf_hist_em(
                symbol=self.symbol,
                period="daily",
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
                # 获取当日价格点
                daily_prices = [
                    (row['开盘'], '开盘'),
                    (row['最高'], '最高'),
                    (row['最低'], '最低'),
                    (row['收盘'], '收盘')
                ]
                
                trades_before = len(self.trades)
                
                # 遍历日内价格点
                for current_price, price_type in daily_prices:
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
                            else:
                                self.failed_trades["卖出价格超范围"] += 1
                    else:
                        self.failed_trades["无持仓"] += 1
                    
                    # 处理买入逻辑
                    buy_trigger_price = last_trigger_price_down * (1 - self.down_buy_rate)
                    if current_price <= buy_trigger_price:
                        price_diff = (buy_trigger_price - current_price) / buy_trigger_price
                        multiple = int(price_diff / self.down_buy_rate) + 1 if self.multiple_trade else 1
                        
                        execute_price = buy_trigger_price * (1 + self.down_rebound_rate)
                        required_cash = execute_price * self.shares_per_trade * multiple
                        
                        if self.cash >= required_cash and current_price <= execute_price:
                            for _ in range(multiple):
                                if self.buy(execute_price, row['日期']):
                                    last_trigger_price_down = execute_price
                        else:
                            # 尝试减少倍数
                            while multiple > 0 and (self.cash < required_cash or current_price > execute_price):
                                multiple -= 1
                                required_cash = execute_price * self.shares_per_trade * multiple
                            
                            if multiple > 0:
                                for _ in range(multiple):
                                    if self.buy(execute_price, row['日期']):
                                        last_trigger_price_down = execute_price
                            else:
                                self.failed_trades["现金不足"] += 1
            
            # 计算最终收益
            self.calculate_profit(df.iloc[-1]['收盘'])
            
        except Exception as e:
            print(f"回测过程中发生错误: {str(e)}")
            raise

    def calculate_profit(self, last_price):
        initial_total = self.initial_cash + (self.initial_positions * self.base_price)
        final_assets = self.cash + (self.positions * last_price)
        profit = final_assets - initial_total
        self.final_profit_rate = (profit / initial_total) * 100
        
        print("\n=== 回测结果 ===")
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
        print("\n未��交统计:")
        for reason, count in self.failed_trades.items():
            if count > 0:
                print(f"{reason}: {count}次") 

if __name__ == "__main__":
    strategy = GridStrategy()
    # 可以指定日期范围
    strategy.backtest('2024-10-15', '2024-12-20')
    # 或使用默认的最近20天
    # strategy.backtest()