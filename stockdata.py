import optuna
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from grid_strategy import GridStrategy  # 导入GridStrategy类

class GridStrategyOptimizer:
    def __init__(self, start_date: datetime = datetime(2024, 11, 1), 
                 end_date: datetime = datetime(2024, 12, 20)):
        # 固定参数
        self.fixed_params = {
            "symbol": "560610",
            "symbol_name": "A500ETF",
            "base_price": 0.960,
            "price_range": (0.910, 1.010),
            "initial_positions": 50000,
            "initial_cash": 50000,
            "start_date": start_date,  # 使用传入的参数
            "end_date": end_date      # 使用传入的参数
        }
        
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
                "max": 50000,
                "step": 1000
            }
        }

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
        # 生成试验参数
        params = {
            "up_sell_rate": trial.suggest_float(
                "up_sell_rate",
                self.param_ranges["up_sell_rate"]["min"],
                self.param_ranges["up_sell_rate"]["max"],
                step=self.param_ranges["up_sell_rate"]["step"]
            ),
            "down_buy_rate": trial.suggest_float(
                "down_buy_rate",
                self.param_ranges["down_buy_rate"]["min"],
                self.param_ranges["down_buy_rate"]["max"],
                step=self.param_ranges["down_buy_rate"]["step"]
            ),
            "up_callback_rate": trial.suggest_float(
                "up_callback_rate",
                self.param_ranges["up_callback_rate"]["min"],
                self.param_ranges["up_callback_rate"]["max"],
                step=self.param_ranges["up_callback_rate"]["step"]
            ),
            "down_rebound_rate": trial.suggest_float(
                "down_rebound_rate",
                self.param_ranges["down_rebound_rate"]["min"],
                self.param_ranges["down_rebound_rate"]["max"],
                step=self.param_ranges["down_rebound_rate"]["step"]
            ),
            "shares_per_trade": trial.suggest_int(
                "shares_per_trade",
                self.param_ranges["shares_per_trade"]["min"],
                self.param_ranges["shares_per_trade"]["max"],
                step=self.param_ranges["shares_per_trade"]["step"]
            )
        }
        
        # 运行回测
        profit_rate, stats = self.run_backtest(params)
        
        # 记录中间结果
        trial.set_user_attr("trade_count", stats["trade_count"])
        trial.set_user_attr("failed_trades", str(stats["failed_trades"]))
        
        return -profit_rate  # 返回负值因为Optuna默认最小化

    def optimize(self, n_trials: int = 100) -> Dict[str, Any]:
        """
        执行参数优化
        """
        study = optuna.create_study(
            study_name="grid_strategy_optimization",
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        study.optimize(self.objective, n_trials=n_trials)
        
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
            "study": study
        }
        
        return optimization_results

    def print_results(self, results: Dict[str, Any]) -> None:
        """
        打印优���结果
        """
        print("\n=== 参数优化结果 ===")
        print(f"\n回测区间: {self.fixed_params['start_date'].strftime('%Y-%m-%d')} 至 "
              f"{self.fixed_params['end_date'].strftime('%Y-%m-%d')}")
        
        print(f"\n最佳参数组合:")
        for param, value in results["best_params"].items():
            print(f"{param}: {value:.6f}" if isinstance(value, float) else f"{param}: {value}")
        
        print(f"\n最佳收益率: {results['best_profit_rate']:.2f}%")
        print(f"交易次数: {results['best_trade_count']}")
        print("\n失败交易统计:")
        for reason, count in results["best_failed_trades"].items():
            if count > 0:
                print(f"{reason}: {count}次")

if __name__ == "__main__":
    # 在创建优化器实例时指定回测区间
    optimizer = GridStrategyOptimizer(
        start_date=datetime(2024, 10, 15),
        end_date=datetime(2024, 12, 20)
    )
    
    results = optimizer.optimize(n_trials=100)
    optimizer.print_results(results)
    
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
