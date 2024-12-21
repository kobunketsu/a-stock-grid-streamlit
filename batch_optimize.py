import pandas as pd
import akshare as ak
from datetime import datetime
from stockdata import GridStrategyOptimizer
from progress_window import ProgressWindow
import threading

class BatchOptimizer:
    def __init__(self):
        # ETF配置：代码和价格区间
        self.etf_configs = {
            "159300": {"price_range": (3.9, 4.3)},
            "159845": {"price_range": (2.17, 2.44)},
            "159531": {"price_range": (0.869, 0.955)},
        }
        
        # 获取ETF名称
        try:
            etf_df = ak.fund_etf_spot_em()
            for symbol in self.etf_configs.keys():
                etf_name = etf_df[etf_df['代码'] == symbol]['名称'].values[0]
                self.etf_configs[symbol]["name"] = etf_name
                print(f"获取ETF名称: {symbol} - {etf_name}")
        except Exception as e:
            print(f"获取ETF名称时发生错误: {e}")
            # 如果获取失败，使用代码作为名称
            for symbol in self.etf_configs.keys():
                if "name" not in self.etf_configs[symbol]:
                    self.etf_configs[symbol]["name"] = symbol
        
        # 通用参数
        self.start_date = datetime(2024, 10, 10)
        self.end_date = datetime(2024, 12, 20)
        self.initial_cash = 100000  # 10万初始资金
        self.initial_positions = 0   # 0初始持仓
        self.ma_period = 55         # 55日均线
        self.ma_protection = True   # 开启均线保护
        
        # 存储优化结果
        self.results = []

    def optimize_single_etf(self, symbol: str, config: dict, progress_window=None):
        """
        优化单个ETF的参数
        """
        try:
            optimizer = GridStrategyOptimizer(
                symbol=symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                ma_period=self.ma_period,
                ma_protection=self.ma_protection,
                initial_positions=self.initial_positions,
                initial_cash=self.initial_cash,
                price_range=config["price_range"]
            )
            
            # 设置进度窗口
            optimizer.progress_window = progress_window
            
            # 运行优化
            results = optimizer.optimize(n_trials=100)
            
            if results:
                # 记录最佳结果
                best_result = {
                    "symbol": symbol,
                    "name": config["name"],
                    "profit_rate": results["best_profit_rate"],
                    "trade_count": results["best_trade_count"],
                    "failed_trades": results["best_failed_trades"],
                    "best_params": results["best_params"],
                    "price_range": config["price_range"]
                }
                self.results.append(best_result)
                
                # 保存详细的优化结果
                trials_df = pd.DataFrame([
                    {
                        "symbol": symbol,
                        "name": config["name"],
                        "number": trial.number,
                        "profit_rate": -trial.value,
                        "trade_count": trial.user_attrs["trade_count"],
                        "failed_trades": trial.user_attrs["failed_trades"],
                        **trial.params
                    }
                    for trial in results["study"].trials
                ])
                
                # 保存到CSV文件
                trials_df.to_csv(f"optimization_trials_{symbol}.csv", index=False)
                
        except Exception as e:
            print(f"优化 {symbol} ({config['name']}) 时发生错误: {e}")

    def run_batch_optimization(self):
        """
        运行批量优化
        """
        total_etfs = len(self.etf_configs)
        current_etf = 0
        
        # 创建进度窗口
        progress_window = ProgressWindow(total_etfs)
        progress_window.create_window()
        
        def optimize_all():
            nonlocal current_etf
            try:
                for symbol, config in self.etf_configs.items():
                    print(f"\n开始优化 {config['name']} ({symbol})")
                    self.optimize_single_etf(symbol, config)
                    current_etf += 1
                    progress_window.update_progress(current_etf)
                
                # 优化完成后，生成报告
                self.generate_report()
                
            finally:
                # 确保窗口正确关闭
                if progress_window and progress_window.root:
                    progress_window.root.after(100, progress_window.close)
        
        # 启动优化线程
        optimization_thread = threading.Thread(target=optimize_all)
        optimization_thread.start()
        
        # 主线程运行进度窗口
        progress_window.root.mainloop()

    def generate_report(self):
        """
        生成优化结果报告
        """
        if not self.results:
            print("没有可用的优化结果")
            return
            
        # 按收益率排序
        sorted_results = sorted(self.results, key=lambda x: x["profit_rate"], reverse=True)
        
        print("\n=== ETF网格交易优化结果排名 ===")
        print(f"回测区间: {self.start_date.strftime('%Y-%m-%d')} 至 {self.end_date.strftime('%Y-%m-%d')}")
        print(f"初始资金: {self.initial_cash:,} 元")
        print(f"初始持仓: {self.initial_positions} 股")
        print(f"均线设置: {self.ma_period}日均线保护\n")
        
        for i, result in enumerate(sorted_results, 1):
            print(f"\n第 {i} 名: {result['name']} ({result['symbol']})")
            print(f"收益率: {result['profit_rate']:.2f}%")
            print(f"交易次数: {result['trade_count']}")
            print(f"价格区间: {result['price_range']}")
            print("最佳参数组合:")
            for param, value in result['best_params'].items():
                if param in ['up_sell_rate', 'down_buy_rate', 'up_callback_rate', 'down_rebound_rate']:
                    print(f"  {param}: {value*100:.2f}%")
                else:
                    print(f"  {param}: {value}")
            print("失败交易统计:")
            for reason, count in result['failed_trades'].items():
                if count > 0:
                    print(f"  {reason}: {count}次")
        
        # 保存结果到CSV文件
        results_df = pd.DataFrame(sorted_results)
        results_df.to_csv("batch_optimization_results.csv", index=False)
        print("\n详细结果已保存到 batch_optimization_results.csv")

if __name__ == "__main__":
    batch_optimizer = BatchOptimizer()
    batch_optimizer.run_batch_optimization() 