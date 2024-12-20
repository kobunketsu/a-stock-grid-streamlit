import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class GridStrategy:
    def __init__(self):
        self.etf_code = "560610"  # ETF代码
        self.etf_name = "A500ETF"  # ETF名称
        self.base_price = 0.960  # 基准价
        self.price_range = (0.910, 1.010)  # 价格区间
        self.up_sell_rate = 0.0064  # 上涨卖出比例
        self.up_callback_rate = 0.003  # 上涨回调比例
        self.down_buy_rate = 0.0094  # 下跌买入比例
        self.down_rebound_rate = 0.003  # 下跌反弹比例
        self.shares_per_trade = 5000  # 每次交易股数
        self.initial_positions = 50000  # 初始持仓数量
        self.positions = self.initial_positions  # 当前持仓数量
        self.initial_cash = 50000  # 初始现金
        self.cash = self.initial_cash  # 当前现金
        self.trades = []  # 交易记录
        # 添加无法交易统计
        self.failed_trades = {
            "无持仓": 0,
            "卖出价格超范围": 0,
            "现金不足": 0,
            "买入价格超范围": 0
        }
        self.multiple_trade = True  # 是否启用倍数交易
        
    def backtest(self, start_date=None, end_date=None):
        """
        执行回测
        :param start_date: 开始日期，格式：'YYYY-MM-DD'
        :param end_date: 结束日期，格式：'YYYY-MM-DD'
        """
        # 处理日期参数
        if start_date is None or end_date is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=20)
        else:
            # 将字符串日期转换为datetime对象
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"\n=== {self.etf_name}({self.etf_code}) 回测报告 ===")
        print(f"回测区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        try:
            df = ak.fund_etf_hist_em(
                symbol=self.etf_code,
                period="daily",
                start_date=start_date_str,
                end_date=end_date_str,
                adjust="qfq"
            )
            
            # 遍历每个交易日进行回测
            for i, row in df.iterrows():
                # 获取当日价格点
                daily_prices = [
                    (row['开盘'], '开盘'),
                    (row['最高'], '最高'),
                    (row['最低'], '最低'),
                    (row['收盘'], '收盘')
                ]
                
                # 记录上一次触发价格（如果是当天第一次交易）
                if i == 0:
                    last_trigger_price_up = self.base_price
                    last_trigger_price_down = self.base_price
                    
                trades_before = len(self.trades)
                
                print(f"\n=== {row['日期']} 行情 ===")
                print(f"开盘: {row['开盘']:.3f}")
                print(f"最高: {row['最高']:.3f}")
                print(f"最低: {row['最低']:.3f}")
                print(f"收盘: {row['收盘']:.3f}")
                
                # 遍历日内价格点
                for current_price, price_type in daily_prices:
                    print(f"\n检查{price_type}价格点: {current_price:.3f}")
                    
                    # 检查卖出条件
                    if self.positions > 0:
                        sell_trigger_price = last_trigger_price_up * (1 + self.up_sell_rate)
                        if current_price >= sell_trigger_price:
                            price_diff = (current_price - sell_trigger_price) / sell_trigger_price
                            multiple = int(price_diff / self.up_sell_rate) + 1 if self.multiple_trade else 1
                            multiple = min(multiple, self.positions // self.shares_per_trade)  # 不能超过持仓量
                            
                            execute_price = sell_trigger_price * (1 - self.up_callback_rate)
                            if execute_price <= current_price:
                                if self.positions >= self.shares_per_trade * multiple:
                                    for _ in range(multiple):
                                        self.sell(execute_price, row['日期'])
                                    last_trigger_price_up = execute_price
                                    last_trigger_price_down = execute_price
                                    print(f"触发卖出 - 触发价: {sell_trigger_price:.3f}, 执行价: {execute_price:.3f}")
                                    print(f"交易份额: {self.shares_per_trade * multiple}, 当前总持仓: {self.positions}")
                                else:
                                    print(f"\n无法卖出 - 当前持仓{self.positions}不足")
                                    self.failed_trades["无持仓"] += 1
                            else:
                                print(f"\n无法卖出 - 执行价 {execute_price:.3f} 高于当前价格 {current_price:.3f}")
                                self.failed_trades["卖出价格超范围"] += 1
                    else:
                        print("\n无法卖出 - 当前无持仓")
                        self.failed_trades["无持仓"] += 1
                    
                    # 检查买入条件
                    buy_trigger_price = last_trigger_price_down * (1 - self.down_buy_rate)
                    print(f"\n当前价格: {current_price:.3f}")
                    print(f"上次触发价: {last_trigger_price_down:.3f}")
                    print(f"买入触发价: {buy_trigger_price:.3f}")
                    
                    if current_price <= buy_trigger_price:
                        # 计算可以买入的倍数
                        price_diff = (buy_trigger_price - current_price) / buy_trigger_price
                        multiple = int(price_diff / self.down_buy_rate) + 1 if self.multiple_trade else 1
                        
                        execute_price = buy_trigger_price * (1 + self.down_rebound_rate)
                        required_cash = execute_price * self.shares_per_trade * multiple
                        
                        print(f"价格差异: {price_diff:.4f}")
                        print(f"计算执行价: {execute_price:.3f}")
                        print(f"交易倍数: {multiple}")
                        print(f"所需资金: {required_cash:.2f}, 当前现金: {self.cash:.2f}")
                        
                        if self.cash >= required_cash:
                            for _ in range(multiple):
                                self.buy(execute_price, row['日期'])
                            last_trigger_price_down = execute_price
                            print(f"触发买入 - 触发价: {buy_trigger_price:.3f}, 执行价: {execute_price:.3f}")
                            print(f"交易份额: {self.shares_per_trade * multiple}, 当前总持仓: {self.positions}")
                        else:
                            # 尝试减少倍数
                            while multiple > 0 and self.cash < required_cash:
                                multiple -= 1
                                required_cash = execute_price * self.shares_per_trade * multiple
                            
                            if multiple > 0:
                                for _ in range(multiple):
                                    self.buy(execute_price, row['日期'])
                                last_trigger_price_down = execute_price
                                print(f"触发部分买入 - 触发价: {buy_trigger_price:.3f}, 执行价: {execute_price:.3f}")
                                print(f"交易份额: {self.shares_per_trade * multiple}, 当前总持仓: {self.positions}")
                            else:
                                print(f"\n无法买入 - 所需资金 {required_cash:.2f}, 当前现金 {self.cash:.2f}")
                                self.failed_trades["现金不足"] += 1
                
                # 打印当日交易记录和交易后状态
                trades_after = len(self.trades)
                if trades_after > trades_before:
                    print("\n当日交易:")
                    for trade in self.trades[trades_before:trades_after]:
                        print(f"{trade['操作']} - 价格: {trade['价格']:.3f}, 数量: {trade['数量']}, 金额: {trade['金额']:.2f}")
                else:
                    print("\n当日无交易")
                
                print(f"当日结束持仓: {self.positions}, 现金: {self.cash:.2f}")
            
            # 计算收益
            self.calculate_profit(df.iloc[-1]['收盘'])
            
        except Exception as e:
            print(f"回测过程中发生错误: {str(e)}")
    
    def buy(self, price, date):
        cost = price * self.shares_per_trade
        if self.cash >= cost:
            self.cash -= cost
            self.positions += self.shares_per_trade
            self.trades.append({
                '日期': date,
                '操作': '买入',
                '价格': price,
                '数量': self.shares_per_trade,
                '金额': cost
            })
    
    def sell(self, price, date):
        if self.positions >= self.shares_per_trade:
            income = price * self.shares_per_trade
            self.cash += income
            self.positions -= self.shares_per_trade
            self.trades.append({
                '日期': date,
                '操作': '卖出',
                '价格': price,
                '数量': self.shares_per_trade,
                '金额': income
            })
    
    def calculate_profit(self, last_price):
        print(f"\n=== {self.etf_name}({self.etf_code}) 回测结果 ===")
        # 计算初始总资产（现金 + 初始持仓市值）
        initial_total = self.initial_cash + (self.initial_positions * self.base_price)
        # 计算最终总资产（现金 + 当前持仓市值）
        final_assets = self.cash + (self.positions * last_price)
        profit = final_assets - initial_total
        profit_rate = (profit / initial_total) * 100
        
        print(f"初始现金: {self.initial_cash:,.2f}")
        print(f"初始持仓: {self.initial_positions}股 (按{self.base_price:.3f}元计算)")
        print(f"初始总资产: {initial_total:,.2f}")
        print(f"最终现金: {self.cash:,.2f}")
        print(f"最终持仓: {self.positions}股 (按{last_price:.3f}元计算)")
        print(f"最终总资产: {final_assets:,.2f}")
        print(f"总收益: {profit:,.2f}")
        print(f"收益率: {profit_rate:.2f}%")
        
        print("\n=== 交易统计 ===")
        print(f"成功交易次数: {len(self.trades)}")
        print("\n未成交统计:")
        for reason, count in self.failed_trades.items():
            if count > 0:
                print(f"{reason}: {count}次")
        
        print(f"\n=== {self.etf_name}({self.etf_code}) 交易记录 ===")
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            print(trades_df)
        else:
            print("无交易记录")

if __name__ == "__main__":
    strategy = GridStrategy()
    # 示例：指定日期范围进行回测
    strategy.backtest('2024-10-15', '2024-12-20')
    
    # 或者使用默认的最近20天
    # strategy.backtest()
