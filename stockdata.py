import optuna
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from grid_strategy import GridStrategy  # 导入GridStrategy类
import akshare as ak
import tkinter as tk
from tkinter import ttk
import threading

class ProgressWindow:
    def __init__(self, total_trials):
        self.total_trials = total_trials
        self.current_trial = 0
        self.root = None
        self.progress = None
        self.percent_label = None
        self.label = None
        
    def create_window(self):
        """在主线程中创建窗口"""
        self.root = tk.Tk()
        self.root.title("优化进度")
        self.root.geometry("300x150")
        
        # 设置窗口在屏幕中央
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 300) // 2
        y = (screen_height - 150) // 2
        self.root.geometry(f"300x150+{x}+{y}")
        
        # 进度标签
        self.label = ttk.Label(self.root, text="正在优化参数...", font=('Arial', 10))
        self.label.pack(pady=10)
        
        # 进度条
        self.progress = ttk.Progressbar(
            self.root, 
            orient="horizontal",
            length=200, 
            mode="determinate"
        )
        self.progress.pack(pady=10)
        
        # 百分比标签
        self.percent_label = ttk.Label(self.root, text="0%", font=('Arial', 10))
        self.percent_label.pack(pady=5)
        
    def update_progress(self, trial_number):
        if self.root is None:
            return
        self.current_trial = trial_number
        progress = (self.current_trial / self.total_trials) * 100
        self.progress["value"] = progress
        self.percent_label["text"] = f"{progress:.1f}%"
        self.root.update()
        
    def close(self):
        if self.root is not None:
            self.root.destroy()

class GridStrategyOptimizer:
    # 添加类常量
    REBOUND_RATE_MAX_RATIO = 0.3  # 回调/反弹率相对于主要率的最大比例
    
    def __init__(self, start_date: datetime = datetime(2024, 11, 1), 
                 end_date: datetime = datetime(2024, 12, 20)):
        # 获取ETF基金名称
        try:
            # 获取所有ETF基金列表
            etf_df = ak.fund_etf_spot_em()
            # 查找对应的ETF基金名称
            etf_name = etf_df[etf_df['代码'] == '560610']['名称'].values[0]
        except Exception as e:
            print(f"获取ETF名称失败: {e}")
            etf_name = "未知ETF"  # 如果获取失败则使用默认名称
        
        # 固定参数
        self.fixed_params = {
            "symbol": "560610",
            "symbol_name": etf_name,  # 使用获取到的ETF名称
            "base_price": 0.960,
            "price_range": (0.910, 1.010),
            "initial_positions": 50000,
            "initial_cash": 50000,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # 计算最大可交易股数
        max_shares = int(self.fixed_params["initial_cash"] / self.fixed_params["base_price"])
        
        # 可调参数的范围定义
        self.param_ranges = {
            "up_sell_rate": {
                "min": 0.003,
                "max": 0.03,
                "step": 0.0005
            },
            "down_buy_rate": {
                "min": 0.003,
                "max": 0.03,
                "step": 0.0005
            },
            "up_callback_rate": {
                "min": 0.001,
                "max": 0.01,
                "step": 0.0005
            },
            "down_rebound_rate": {
                "min": 0.001,
                "max": 0.01,
                "step": 0.0005
            },
            "shares_per_trade": {
                "min": 1000,
                "max": max_shares,  # 使用计算得到的最大股数
                "step": 1000
            }
        }

        self.progress_window = None  # 添加progress_window属性

    def run_backtest(self, params: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        运行回测并返回收益率和统计信息
        """
        strategy = GridStrategy(
            symbol=self.fixed_params["symbol"],
            symbol_name=self.fixed_params["symbol_name"]
        )
        
        # 设置固定参数
        strategy.base_price = self.fixed_params["base_price"]
        strategy.price_range = self.fixed_params["price_range"]
        strategy.initial_positions = self.fixed_params["initial_positions"]
        strategy.positions = strategy.initial_positions
        strategy.initial_cash = self.fixed_params["initial_cash"]
        strategy.cash = strategy.initial_cash
        
        # 设置可调参数
        strategy.up_sell_rate = params["up_sell_rate"]
        strategy.down_buy_rate = params["down_buy_rate"]
        strategy.up_callback_rate = params["up_callback_rate"]
        strategy.down_rebound_rate = params["down_rebound_rate"]
        strategy.shares_per_trade = params["shares_per_trade"]
        
        # 使用固定的时间区间执行回测
        strategy.backtest(
            start_date=self.fixed_params["start_date"],
            end_date=self.fixed_params["end_date"]
        )
        
        # 获取回测统计信息
        stats = {
            "profit_rate": strategy.final_profit_rate,
            "trade_count": len(strategy.trades),
            "failed_trades": strategy.failed_trades,
            "params": params,
            "backtest_period": {
                "start": self.fixed_params["start_date"].strftime('%Y-%m-%d'),
                "end": self.fixed_params["end_date"].strftime('%Y-%m-%d')
            }
        }
        
        return strategy.final_profit_rate, stats

    def objective(self, trial: optuna.Trial) -> float:
        """
        Optuna优化目标函数
        """
        # 先生成主要参数
        up_sell_rate = trial.suggest_float(
            "up_sell_rate",
            self.param_ranges["up_sell_rate"]["min"],
            self.param_ranges["up_sell_rate"]["max"],
            step=self.param_ranges["up_sell_rate"]["step"]
        )
        
        down_buy_rate = trial.suggest_float(
            "down_buy_rate",
            self.param_ranges["down_buy_rate"]["min"],
            self.param_ranges["down_buy_rate"]["max"],
            step=self.param_ranges["down_buy_rate"]["step"]
        )
        
        # 基于主要参数动态设置回调/反弹率的范围
        up_callback_max = min(
            up_sell_rate * self.REBOUND_RATE_MAX_RATIO,
            self.param_ranges["up_callback_rate"]["max"]
        )
        up_callback_min = self.param_ranges["up_callback_rate"]["min"]
        
        # 确保最大值不小于最小值
        if up_callback_max < up_callback_min:
            up_callback_max = up_callback_min
        
        up_callback_rate = trial.suggest_float(
            "up_callback_rate",
            up_callback_min,
            up_callback_max,
            step=self.param_ranges["up_callback_rate"]["step"]
        )
        
        down_rebound_max = min(
            down_buy_rate * self.REBOUND_RATE_MAX_RATIO,
            self.param_ranges["down_rebound_rate"]["max"]
        )
        down_rebound_min = self.param_ranges["down_rebound_rate"]["min"]
        
        # 确保最大值不小于最小值
        if down_rebound_max < down_rebound_min:
            down_rebound_max = down_rebound_min
        
        down_rebound_rate = trial.suggest_float(
            "down_rebound_rate",
            down_rebound_min,
            down_rebound_max,
            step=self.param_ranges["down_rebound_rate"]["step"]
        )
        
        shares_per_trade = trial.suggest_int(
            "shares_per_trade",
            self.param_ranges["shares_per_trade"]["min"],
            self.param_ranges["shares_per_trade"]["max"],
            step=self.param_ranges["shares_per_trade"]["step"]
        )
        
        params = {
            "up_sell_rate": up_sell_rate,
            "down_buy_rate": down_buy_rate,
            "up_callback_rate": up_callback_rate,
            "down_rebound_rate": down_rebound_rate,
            "shares_per_trade": shares_per_trade
        }
        
        # 运行回测
        profit_rate, stats = self.run_backtest(params)
        
        # 记录中间结果
        trial.set_user_attr("trade_count", stats["trade_count"])
        trial.set_user_attr("failed_trades", str(stats["failed_trades"]))
        
        return -profit_rate  # 返回负值因为Optuna默认最小化

    def optimize(self, n_trials: int = 2000) -> Dict[str, Any]:
        """
        分阶段执行参数优化
        """
        def callback(study, trial):
            if self.progress_window:  # 添加检查
                self.progress_window.update_progress(trial.number)
        
        # 第一阶段：粗略搜索
        study = optuna.create_study(
            study_name="grid_strategy_optimization_phase1",
            direction="minimize",
            sampler=optuna.samplers.TPESampler(
                seed=42,
                n_startup_trials=100,
                multivariate=True
            )
        )
        
        # 第一阶段优化
        study.optimize(self.objective, n_trials=n_trials, callbacks=[callback])
        
        # 获取第一阶段最佳参数周围的范围
        best_params = study.best_params
        refined_ranges = self._get_refined_ranges(best_params)
        
        # 第二阶段：精细搜索
        study_refined = optuna.create_study(
            study_name="grid_strategy_optimization_phase2",
            direction="minimize",
            sampler=optuna.samplers.TPESampler(
                seed=43,
                n_startup_trials=50,
                multivariate=True
            )
        )
        
        # 第二阶段优化
        study_refined.optimize(
            lambda trial: self._refined_objective(trial, refined_ranges), 
            n_trials=n_trials//2,
            callbacks=[callback]
        )
        
        # 关闭进度窗口
        self.progress_window.close()
        
        return self._combine_results(study, study_refined)

    def _get_refined_ranges(self, best_params):
        """
        根据最佳参数缩小搜索范围
        """
        refined_ranges = {}
        for param, value in best_params.items():
            refined_ranges[param] = {
                "min": max(value * 0.8, self.param_ranges[param]["min"]),
                "max": min(value * 1.2, self.param_ranges[param]["max"]),
                "step": self.param_ranges[param]["step"]
            }
        return refined_ranges

    def _refined_objective(self, trial: optuna.Trial, refined_ranges: Dict[str, Dict[str, float]]) -> float:
        """
        精细搜索目标函数
        """
        # 先生成主要参数
        up_sell_rate = trial.suggest_float(
            "up_sell_rate",
            refined_ranges["up_sell_rate"]["min"],
            refined_ranges["up_sell_rate"]["max"],
            step=refined_ranges["up_sell_rate"]["step"]
        )
        
        down_buy_rate = trial.suggest_float(
            "down_buy_rate",
            refined_ranges["down_buy_rate"]["min"],
            refined_ranges["down_buy_rate"]["max"],
            step=refined_ranges["down_buy_rate"]["step"]
        )
        
        # 基于主要参数动态设置回调/反弹率的范围
        up_callback_max = min(
            up_sell_rate * self.REBOUND_RATE_MAX_RATIO,
            refined_ranges["up_callback_rate"]["max"]
        )
        up_callback_min = refined_ranges["up_callback_rate"]["min"]
        
        # 确保最大值不小于最小值
        if up_callback_max < up_callback_min:
            up_callback_max = up_callback_min
        
        up_callback_rate = trial.suggest_float(
            "up_callback_rate",
            up_callback_min,
            up_callback_max,
            step=refined_ranges["up_callback_rate"]["step"]
        )
        
        down_rebound_max = min(
            down_buy_rate * self.REBOUND_RATE_MAX_RATIO,
            refined_ranges["down_rebound_rate"]["max"]
        )
        down_rebound_min = refined_ranges["down_rebound_rate"]["min"]
        
        # 确保最大值不小于最小值
        if down_rebound_max < down_rebound_min:
            down_rebound_max = down_rebound_min
        
        down_rebound_rate = trial.suggest_float(
            "down_rebound_rate",
            down_rebound_min,
            down_rebound_max,
            step=refined_ranges["down_rebound_rate"]["step"]
        )
        
        shares_per_trade = trial.suggest_int(
            "shares_per_trade",
            refined_ranges["shares_per_trade"]["min"],
            refined_ranges["shares_per_trade"]["max"],
            step=refined_ranges["shares_per_trade"]["step"]
        )
        
        params = {
            "up_sell_rate": up_sell_rate,
            "down_buy_rate": down_buy_rate,
            "up_callback_rate": up_callback_rate,
            "down_rebound_rate": down_rebound_rate,
            "shares_per_trade": shares_per_trade
        }
        
        # 运行回测
        profit_rate, stats = self.run_backtest(params)
        
        # 记录中间结果
        trial.set_user_attr("trade_count", stats["trade_count"])
        trial.set_user_attr("failed_trades", str(stats["failed_trades"]))
        
        return -profit_rate

    def _combine_results(self, study: optuna.Study, study_refined: optuna.Study) -> Dict[str, Any]:
        """
        合并两个阶段的结果
        """
        # 获取最佳结果
        best_params = study.best_params
        best_value = -study.best_value
        best_trial = study.best_trial
        
        # 整理优化结果
        optimization_results = {
            "best_params": best_params,
            "best_profit_rate": best_value,
            "best_trade_count": best_trial.user_attrs["trade_count"],
            "best_failed_trades": eval(best_trial.user_attrs["failed_trades"]),
            "study": study,
            "study_refined": study_refined
        }
        
        return optimization_results

    def print_results(self, results: Dict[str, Any], top_n: int = 5) -> None:
        """
        打印优化结果并运行最佳参数组合的详细回测
        @param results: 优化结果
        @param top_n: 显示前N个最佳结果
        """
        print("\n=== 参数优化结果 ===")
        print(f"\n回测区间: {self.fixed_params['start_date'].strftime('%Y-%m-%d')} 至 "
              f"{self.fixed_params['end_date'].strftime('%Y-%m-%d')}")
        
        # 获取所有试验结果
        trials = results["study"].trials
        
        # 使用参数组合作为键来去重
        unique_trials = {}
        for trial in trials:
            # 将参数值转换为元组作为字典键
            params_tuple = tuple((k, round(v, 6) if isinstance(v, float) else v) 
                               for k, v in sorted(trial.params.items()))
            if params_tuple not in unique_trials or trial.value < unique_trials[params_tuple].value:
                unique_trials[params_tuple] = trial
        
        # 对去重后的结果排序
        sorted_trials = sorted(unique_trials.values(), key=lambda t: t.value)[:top_n]
        
        # 定义需要转换为百分比的参数名称
        rate_params = ['up_sell_rate', 'down_buy_rate', 'up_callback_rate', 'down_rebound_rate']
        
        print(f"\n=== 前 {top_n} 个最佳参数组合（已去重） ===")
        for i, trial in enumerate(sorted_trials, 1):
            profit_rate = -trial.value  # 转换回正的收益率
            print(f"\n第 {i} 名:")
            print(f"收益率: {profit_rate:.2f}%")
            print(f"交易次数: {trial.user_attrs['trade_count']}")
            print("参数组合:")
            for param, value in trial.params.items():
                if param in rate_params:
                    # 将rate类型参数转换为百分比显示
                    print(f"  {param}: {value*100:.2f}%")
                else:
                    # 非rate类型参数保持原样显示
                    print(f"  {param}: {value}")
            print("失败交易统计:")
            failed_trades = eval(trial.user_attrs["failed_trades"])
            for reason, count in failed_trades.items():
                if count > 0:
                    print(f"  {reason}: {count}次")
        
        print("\n=== 使用最佳参数运行详细回测 ===")
        # 使用最佳参数运行详细回测
        best_strategy = GridStrategy(
            symbol=self.fixed_params["symbol"],
            symbol_name=self.fixed_params["symbol_name"]
        )
        
        # 设置固定参数
        best_strategy.base_price = self.fixed_params["base_price"]
        best_strategy.price_range = self.fixed_params["price_range"]
        best_strategy.initial_positions = self.fixed_params["initial_positions"]
        best_strategy.positions = best_strategy.initial_positions
        best_strategy.initial_cash = self.fixed_params["initial_cash"]
        best_strategy.cash = best_strategy.initial_cash
        
        # 设置最佳参数
        best_strategy.up_sell_rate = results["best_params"]["up_sell_rate"]
        best_strategy.down_buy_rate = results["best_params"]["down_buy_rate"]
        best_strategy.up_callback_rate = results["best_params"]["up_callback_rate"]
        best_strategy.down_rebound_rate = results["best_params"]["down_rebound_rate"]
        best_strategy.shares_per_trade = results["best_params"]["shares_per_trade"]
        
        # 运行详细回测
        best_strategy.backtest(
            start_date=self.fixed_params["start_date"],
            end_date=self.fixed_params["end_date"],
            verbose=False  # 启用详细打印
        )

if __name__ == "__main__":
    # 在创建优化器实例时指定回测区间
    optimizer = GridStrategyOptimizer(
        start_date=datetime(2024, 10, 15),
        end_date=datetime(2024, 12, 20)
    )
    
    # 创建进度窗口
    progress_window = ProgressWindow(2000 * 1.5)  # 1.5倍考虑两个阶段
    
    # 创建一个新线程运行优化过程
    def run_optimization():
        results = optimizer.optimize(n_trials=2000)
        optimizer.print_results(results, top_n=5)
        
        # 保存优化过程中的所有试验结果
        trials_df = pd.DataFrame([
            {
                "number": trial.number,
                "profit_rate": -trial.value,
                "trade_count": trial.user_attrs["trade_count"],
                "failed_trades": trial.user_attrs["failed_trades"],
                "start_date": optimizer.fixed_params["start_date"].strftime('%Y-%m-%d'),
                "end_date": optimizer.fixed_params["end_date"].strftime('%Y-%m-%d'),
                **trial.params
            }
            for trial in results["study"].trials
        ])
        
        # 保存到CSV文件
        trials_df.to_csv("optimization_trials.csv", index=False)
        
        # 优化完成后关闭进度窗口
        progress_window.root.after(100, progress_window.close)
    
    # 在主线程中创建窗口
    progress_window.create_window()
    
    # 将进度窗口传递给优化器
    optimizer.progress_window = progress_window
    
    # 启动优化线程
    optimization_thread = threading.Thread(target=run_optimization)
    optimization_thread.start()
    
    # 主线程进入tkinter主循环
    progress_window.root.mainloop()
