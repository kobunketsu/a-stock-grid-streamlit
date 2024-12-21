from progress_window import ProgressWindow
import optuna
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from grid_strategy import GridStrategy  # 导入GridStrategy类
import akshare as ak
import tkinter as tk
from tkinter import ttk
import threading
import io
from contextlib import redirect_stdout

class GridStrategyOptimizer:
    # 添加类常量
    REBOUND_RATE_MAX_RATIO = 0.3  # 回调/反弹率相对于主要率的最大比例
    
    def __init__(self, symbol: str = "560610",
                 start_date: datetime = datetime(2024, 11, 1), 
                 end_date: datetime = datetime(2024, 12, 20),
                 ma_period: int = None,  # 均线周期
                 ma_protection: bool = False,  # 是否开启均线保护
                 initial_positions: int = 50000,  # 初始持仓
                 initial_cash: int = 50000,  # 初始资金
                 price_range: tuple = (0.910, 1.010)):  # 价格范围
        
        # 先初始化基本参数
        self.start_date = start_date
        self.end_date = end_date
        
        # 验证价格范围
        if not self._validate_price_range(price_range):
            raise ValueError(f"无效的价格范围: {price_range}")
        
        # 获取ETF基金名称和初始价格
        try:
            # 获取所有ETF基金列表
            etf_df = ak.fund_etf_spot_em()
            # 查找对应的ETF基金名称
            etf_name = etf_df[etf_df['代码'] == symbol]['名称'].values[0]
            
            # 获取开始日期的价格数据
            start_date_str = start_date.strftime('%Y%m%d')
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                start_date=start_date_str,
                end_date=start_date_str
            )
            
            if not df.empty:
                # 计算开盘价和收盘价的中间价格
                base_price = (df.iloc[0]['开盘'] + df.iloc[0]['收盘']) / 2
                print(f"使用开始日期的中间价格作为基准价: {base_price:.3f}")
            else:
                base_price = 0.960  # 如果获取失败，使用默认值
                print(f"无法获取开始日期价格，使用默认基准价: {base_price}")
                
        except Exception as e:
            print(f"获取ETF名称或价格失败: {e}")
            etf_name = "未知ETF"
            base_price = 0.960  # 使用默认值
            
        # 初始化固定参数
        self.fixed_params = {
            "symbol": symbol,
            "symbol_name": etf_name,
            "base_price": base_price,
            "price_range": price_range,
            "initial_positions": initial_positions,
            "initial_cash": initial_cash,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # 如果开启均线保护且提供了均线周期，则更新价格范围
        if ma_protection and ma_period:
            ma_price = self._calculate_ma_price(ma_period)
            if ma_price:
                self._update_price_range_with_ma(ma_price)
        
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

    def _validate_price_range(self, price_range: tuple) -> bool:
        """
        验证价格范围是否有效
        @param price_range: (最小价格, 最大价格)的元组
        @return: 价格范围是否有效
        """
        try:
            min_price, max_price = price_range
            
            # 检查是否为数字
            if not (isinstance(min_price, (int, float)) and isinstance(max_price, (int, float))):
                print(f"价格范围必须是数字: {price_range}")
                return False
            
            # 检查是否为正数
            if min_price <= 0 or max_price <= 0:
                print(f"价格必须为正数: {price_range}")
                return False
            
            # 检查最小值是否小于最大值
            if min_price >= max_price:
                print(f"最小价格必须小于最大价格: {price_range}")
                return False
            
            return True
            
        except Exception as e:
            print(f"验证价格范围时发生错误: {e}")
            return False

    def _calculate_ma_price(self, ma_period: int) -> Optional[float]:
        """
        计算开始时间的均线价格
        @param ma_period: 均线周期
        @return: 计算得到的均线价格，失败时返回None
        """
        try:
            # 获取历史数据，考虑预留更多数据以计算均线
            start_date_str = (self.start_date - timedelta(days=ma_period*2))\
                .strftime('%Y%m%d')
            end_date_str = self.start_date.strftime('%Y%m%d')  # 只需要计算到开始日期
            
            # 获取历史数据
            df = ak.fund_etf_hist_em(
                symbol=self.fixed_params["symbol"],
                start_date=start_date_str,
                end_date=end_date_str
            )
            
            # 确保日期列为索引且按时间升序排列
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期').sort_index()
            
            # 计算移动平均线
            df['MA'] = df['收盘'].rolling(window=ma_period).mean()
            
            # 获取开始日期的收盘价和均线价格
            start_date_data = df.loc[df.index <= self.start_date].iloc[-1]
            close_price = start_date_data['收盘']
            ma_price = start_date_data['MA']
            
            if np.isnan(ma_price):
                print(f"计算均线价格结果为 NaN，使用默认价格范围")
                return None
                
            print(f"开始日期 {self.start_date.strftime('%Y-%m-%d')} 的价格情况:")
            print(f"收盘价: {close_price:.3f}")
            print(f"{ma_period}日均线: {ma_price:.3f}")
            return (close_price, ma_price)
            
        except Exception as e:
            print(f"计算均线价格时发生错误: {e}")
            return None

    def _update_price_range_with_ma(self, price_data: Tuple[float, float]) -> None:
        """
        根据价格和均线的关系更新价格范围
        @param price_data: (收盘价, 均线价格)的元组
        """
        if not price_data:
            return
            
        close_price, ma_price = price_data
        default_range = self.fixed_params["price_range"]
        
        if close_price > ma_price:
            # 价格在均线上方，将均线价格设为最小值
            new_range = (ma_price, default_range[1])
            print(f"价格在均线上方，设置最小���格为均线价格: {ma_price:.3f}")
        else:
            # 价格在均线下方，将均线价格设为最大值
            new_range = (default_range[0], ma_price)
            print(f"价格在均线下方，设置最大价格为均线价格: {ma_price:.3f}")
            
        # 验证新的价格范围
        if self._validate_price_range(new_range):
            self.fixed_params["price_range"] = new_range
            print(f"更新后的价格范围: {new_range}")
        else:
            print(f"保持原有价格范围: {default_range}")

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
        total_trials = n_trials * 1.5  # 总试验次数（包括两个阶段）
        current_trial = 0
        self.optimization_running = True  # 添加运行状态标志

        def callback(study, trial):
            if self.progress_window and self.optimization_running:
                try:
                    nonlocal current_trial
                    current_trial += 1
                    # 计算总体进度
                    self.progress_window.update_progress(current_trial)
                except Exception as e:
                    # 如果更新进度条失败，说明窗口已关闭
                    self.optimization_running = False
                    print(f"进度更新已停止: {e}")
        
        try:
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
            
            if not self.optimization_running:
                return None  # 如果优化被中断，提前返回
            
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
            
            # 只在优化仍在运行时更新最终进度
            if self.optimization_running and self.progress_window:
                try:
                    self.progress_window.update_progress(total_trials)
                except Exception:
                    pass
            
            return self._combine_results(study, study_refined)
            
        except Exception as e:
            print(f"优化过程发生错误: {e}")
            return None
        finally:
            self.optimization_running = False

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
        """
        # 创建一个StringIO对象来捕获输出
        output = io.StringIO()
        with redirect_stdout(output):
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
                verbose=True  # 启用详细打印
            )
        
        # 获取捕获的输出
        captured_output = output.getvalue()
        
        # 同时打印到控制台
        print(captured_output)
        
        # 如果存在进度窗口，将输出存储到窗口对象中
        if self.progress_window:
            self.progress_window.capture_output(captured_output)
            # 启用查看交易详情按钮
            self.progress_window.root.after(0, self.progress_window.enable_trade_details_button)


if __name__ == "__main__":
    # 在创建优化器实例时指定所有参数
    optimizer = GridStrategyOptimizer(
        symbol="159300",  # ETF代码
        start_date=datetime(2024, 10, 10),
        end_date=datetime(2024, 12, 20),
        ma_period=55,
        ma_protection=True,
        initial_positions=0,  # 初始持仓
        initial_cash=100000,  # 初始资金
        price_range=(3.9, 4.3)  # 价格范围
    )
    n_trials = 100
    total_trials = int(n_trials * 1.5)  # 计算总试验次数
    
    # 创建进度窗口，使用��试验次数
    progress_window = ProgressWindow(total_trials)
    
    # 创建一个新线程运行优化过程
    def run_optimization():
        try:
            results = optimizer.optimize(n_trials=n_trials)
            if results:  # 只在优化成功完成时处理结果
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
                
                # 使用 after 方法在主线程中更新UI
                if progress_window and progress_window.root:
                    progress_window.root.after(0, lambda: progress_window.update_label("优化参数完毕！"))
        except Exception as e:
            # 发生错误时更新UI显示错误信息
            if progress_window and progress_window.root:
                progress_window.root.after(0, lambda: progress_window.update_label(f"优化失败: {str(e)}"))
        finally:
            # 确保进度条显示100%
            if progress_window and progress_window.root:
                progress_window.root.after(0, lambda: progress_window.update_progress(total_trials))
    
    # 在主线程中创建窗口
    progress_window.create_window()
    
    # 将进度窗口传递给优化器
    optimizer.progress_window = progress_window
    
    # 启动优化线程
    optimization_thread = threading.Thread(target=run_optimization)
    optimization_thread.start()
    
    # 主线程进入tkinter主循环
    progress_window.root.mainloop()
