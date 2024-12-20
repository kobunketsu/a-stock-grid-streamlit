import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class GridStrategy:
    def __init__(self, symbol="560610", symbol_name="国开ETF"):
        self.symbol = symbol          # ETF代码
        self.symbol_name = symbol_name  # ETF名称
        self.base_price = 0.960  # 基准价
        self.price_range = (0.910, 1.010)  # 价格区间
        self.up_sell_rate = 0.0065  # 上涨卖出比例
        self.up_callback_rate = 0.0020  # 上涨回调比例
        self.down_buy_rate = 0.0065  # 下跌买入比例
        self.down_rebound_rate = 0.0020  # 下跌反弹比例
        self.shares_per_trade = 6000  # 每次交易股数
        self.initial_positions = 30000  # 初始持仓数量
        self.positions = self.initial_positions  # 当前持仓数量
        self.initial_cash = 30000  # 初始现金
        self.cash = self.initial_cash  # 当前现金
        self.trades = []  # 交易记录
        # 添加无法交易统计
        self.failed_trades = {
            "无持仓": 0,
            "卖出价格超范围": 0,
            "现金不足": 0,
            "买入价格超范围": 0
        }
        
    def backtest(self, start_date=None, end_date=None):
        # 获取历史数据
        if start_date is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=20)
        
        # 转换日期格式为API要求的格式 "YYYY-MM-DD HH:mm:ss"
        start_date_str = f"{start_date.strftime('%Y-%m-%d')} 09:32:00"
        end_date_str = f"{end_date.strftime('%Y-%m-%d')} 15:00:00"
        
        try:
            print(f"\n开始回测 {self.symbol_name}({self.symbol})")
            print(f"回测区间: {start_date_str} - {end_date_str}")
            
            # 使用东方财富分钟数据接口
            df = ak.fund_etf_hist_min_em(
                symbol=self.symbol,
                start_date=start_date_str,  # 格式: "YYYY-MM-DD HH:mm:ss"
                end_date=end_date_str,      # 格式: "YYYY-MM-DD HH:mm:ss"
                period='1',  # 1分钟数据
                adjust=""    # 不复权
            )
            
            if df.empty:
                raise Exception("未获取到任何数据")
            
            # 重置索引
            df = df.reset_index(drop=True)
            
            # 记录上一次触发价格
            last_trigger_price_up = self.base_price
            last_trigger_price_down = self.base_price
            
            # 遍历每分钟数据进行回测
            for i, row in df.iterrows():
                current_price = row['收盘']  # 使用收盘价作为当前价格
                
                # 计算涨跌幅
                if i > 0:
                    prev_close = df.iloc[i-1]['收盘']
                    change_rate = ((current_price - prev_close) / prev_close) * 100
                    change_symbol = "+" if change_rate > 0 else "-" if change_rate < 0 else ""
                else:
                    change_rate = 0
                    change_symbol = ""
                
                # 打印当前分钟行情数据
                print(f"\n=== {row['时间']} 行情 ===")
                print(f"开盘: {row['开盘']:.3f}")
                print(f"最高: {row['最高']:.3f}")
                print(f"最低: {row['最低']:.3f}")
                print(f"收盘: {current_price:.3f}")
                print(f"涨跌幅: {change_symbol}{abs(change_rate):.2f}%")
                amplitude = ((row['最高'] - row['最低']) / current_price) * 100
                print(f"振幅: {amplitude:.2f}%")
                
                trades_before = len(self.trades)
                
                # 检查卖出条件
                if self.positions > 0:
                    sell_trigger_price = last_trigger_price_up * (1 + self.up_sell_rate)
                    if current_price >= sell_trigger_price:  # 使用收盘价判断
                        execute_price = current_price  # 以当前收盘价执行
                        self.sell(execute_price, row['时间'])
                        last_trigger_price_up = execute_price
                else:
                    print("\n无法卖出 - 当前无持仓")
                    self.failed_trades["无持仓"] += 1
                
                # 检查买入条件
                buy_trigger_price = last_trigger_price_down * (1 - self.down_buy_rate)
                if current_price <= buy_trigger_price:  # 使用收盘价判断
                    execute_price = current_price  # 以当前收盘价执行
                    required_cash = execute_price * self.shares_per_trade
                    if self.cash >= required_cash:
                        self.buy(execute_price, row['时间'])
                        last_trigger_price_down = execute_price
                    else:
                        print(f"\n无法买入 - 所需资金 {required_cash:.2f}, 当前现金 {self.cash:.2f}")
                        self.failed_trades["现金不足"] += 1
                
                # 打印交易记录和状态
                trades_after = len(self.trades)
                if trades_after > trades_before:
                    print("\n当前分钟交易:")
                    for trade in self.trades[trades_before:trades_after]:
                        print(f"{trade['操作']} - 价格: {trade['价格']:.3f}, 数量: {trade['数量']}, 金额: {trade['金额']:.2f}")
                else:
                    print("\n当前分钟无交易")
                
                print(f"当前分钟结束持仓: {self.positions}, 现金: {self.cash:.2f}")
            
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
        # 计算初始总资产（现金 + 初始持仓市值）
        initial_total = self.initial_cash + (self.initial_positions * self.base_price)
        # 计算最终总资产（现金 + 当前持仓市值）
        final_assets = self.cash + (self.positions * last_price)
        profit = final_assets - initial_total
        profit_rate = (profit / initial_total) * 100
        
        print("\n=== 回测结果 ===")
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
        
        print("\n=== 交易记录 ===")
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            print(trades_df)
        else:
            print("无交易记录")

if __name__ == "__main__":
    # 创建策略实例时指定ETF
    strategy = GridStrategy(symbol="560610", symbol_name="国开ETF")
    # 回测最近20天
    end_date = datetime.now()
    start_date = end_date - timedelta(days=20)
    strategy.backtest(start_date, end_date)
