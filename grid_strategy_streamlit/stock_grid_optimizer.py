import optuna
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from grid_strategy import GridStrategy
from segment_utils import build_segments

class GridStrategyOptimizer:
    def __init__(self, symbol, security_type="STOCK", start_date=None, end_date=None, 
                 ma_period=20, ma_protection=True, initial_positions=0, initial_cash=100000,
                 min_buy_times=3, price_range=(0.91, 1.01), profit_calc_method="mean",
                 connect_segments=False):
        """
        网格交易策略优化器
        
        Args:
            symbol (str): 证券代码
            security_type (str): 证券类型，"STOCK"或"ETF"
            start_date (datetime): 回测开始日期
            end_date (datetime): 回测结束日期
            ma_period (int): MA周期
            ma_protection (bool): 是否启用MA保护
            initial_positions (int): 初始持仓
            initial_cash (float): 初始资金
            min_buy_times (int): 最小买入次数
            price_range (tuple): 价格区间(最小值, 最大值)
            profit_calc_method (str): 收益计算方式，"mean"或"median"
            connect_segments (bool): 是否连接子区间的资金和持仓
        """
        self.symbol = symbol
        self.security_type = security_type
        self.start_date = start_date
        self.end_date = end_date
        self.ma_period = ma_period
        self.ma_protection = ma_protection
        self.initial_positions = initial_positions
        self.initial_cash = initial_cash
        self.min_buy_times = min_buy_times
        self.price_range = price_range
        self.profit_calc_method = profit_calc_method
        self.connect_segments = connect_segments
        
        # 获取证券名称
        try:
            if security_type == "ETF":
                df = ak.fund_etf_spot_em()
                self.symbol_name = df[df["代码"] == symbol]["名称"].values[0]
            else:
                df = ak.stock_zh_a_spot_em()
                self.symbol_name = df[df["代码"] == symbol]["名称"].values[0]
        except Exception as e:
            print(f"获取证券名称失败: {e}")
            self.symbol_name = symbol
        
        # 初始化进度窗口
        self.progress_window = None
    
    def objective(self, trial):
        """
        优化目标函数
        
        Args:
            trial: optuna试验对象
            
        Returns:
            float: 负的收益率（最小化目标）
        """
        # 生成参数
        params = {
            'up_sell_rate': trial.suggest_float('up_sell_rate', 0.003, 0.0036, step=0.0005),
            'down_buy_rate': trial.suggest_float('down_buy_rate', 0.0148, 0.0222, step=0.0005),
            'up_callback_rate': trial.suggest_float('up_callback_rate', 0.001, 0.00105, step=0.0005),
            'down_rebound_rate': trial.suggest_float('down_rebound_rate', 0.0028, 0.0042, step=0.0005),
            'shares_per_trade': trial.suggest_int('shares_per_trade', 160, 240, step=100)
        }
        
        # 如果启用了分段回测
        if self.profit_calc_method:
            # 构建时间段
            segments = build_segments(
                start_date=self.start_date,
                end_date=self.end_date,
                segment_days=60,  # 固定为60天
                overlap_days=0  # 不重叠
            )
            
            # 用于存储每段的结果
            segment_results = []
            
            # 记录上一段的结束状态
            last_cash = self.initial_cash
            last_positions = self.initial_positions
            
            # 遍历每个时间段
            for i, (seg_start, seg_end) in enumerate(segments):
                # 创建策略实例
                strategy = GridStrategy(
                    symbol=self.symbol,
                    symbol_name=self.symbol_name
                )
                
                # 设置策略参数
                for param, value in params.items():
                    setattr(strategy, param, value)
                
                # 设置其他参数
                strategy.ma_period = self.ma_period
                strategy.ma_protection = self.ma_protection
                
                # 如果启用了区间连接，使用上一段的结束状态
                if self.connect_segments and i > 0:
                    strategy.initial_cash = last_cash
                    strategy.cash = last_cash
                    strategy.initial_positions = last_positions
                    strategy.positions = last_positions
                else:
                    strategy.initial_cash = self.initial_cash
                    strategy.cash = self.initial_cash
                    strategy.initial_positions = self.initial_positions
                    strategy.positions = self.initial_positions
                
                # 设置基准价格和价格范围
                strategy.base_price = self.price_range[0]
                strategy.price_range = self.price_range
                
                # 运行回测
                profit_rate = strategy.backtest(seg_start, seg_end)
                
                # 记录本段结果
                segment_results.append({
                    'start_date': seg_start.strftime('%Y-%m-%d'),
                    'end_date': seg_end.strftime('%Y-%m-%d'),
                    'profit_rate': profit_rate,
                    'trades': len(strategy.trades),
                    'failed_trades': strategy.failed_trades
                })
                
                # 更新上一段的结束状态
                last_cash = strategy.cash
                last_positions = strategy.positions
            
            # 保存分段结果到trial的user_attrs
            trial.set_user_attrs({'segment_results': segment_results})
            
            # 根据指定方法计算总收益率
            if self.profit_calc_method == "mean":
                total_profit = np.mean([seg['profit_rate'] for seg in segment_results])
            else:  # median
                total_profit = np.median([seg['profit_rate'] for seg in segment_results])
            
            # 计算总交易次数
            total_trades = sum(seg['trades'] for seg in segment_results)
            trial.set_user_attrs({'trade_count': total_trades})
            
            # 汇总失败交易
            failed_trades = {}
            for seg in segment_results:
                for reason, count in seg['failed_trades'].items():
                    failed_trades[reason] = failed_trades.get(reason, 0) + count
            trial.set_user_attrs({'failed_trades': str(failed_trades)})
            
            return -total_profit  # 转为负值用于最小化
            
        else:
            # 单段回测
            strategy = GridStrategy(
                symbol=self.symbol,
                symbol_name=self.symbol_name
            )
            
            # 设置策略参数
            for param, value in params.items():
                setattr(strategy, param, value)
            
            # 设置其他参数
            strategy.ma_period = self.ma_period
            strategy.ma_protection = self.ma_protection
            strategy.initial_positions = self.initial_positions
            strategy.positions = self.initial_positions
            strategy.initial_cash = self.initial_cash
            strategy.cash = self.initial_cash
            
            # 设置基准价格和价格范围
            strategy.base_price = self.price_range[0]
            strategy.price_range = self.price_range
            
            # 运行回测
            profit_rate = strategy.backtest(self.start_date, self.end_date)
            
            # 记录交易次数和失败交易
            trial.set_user_attrs({'trade_count': len(strategy.trades)})
            trial.set_user_attrs({'failed_trades': str(strategy.failed_trades)})
            
            return -profit_rate  # 转为负值用于最小化
    
    def optimize(self, n_trials=100):
        """
        运行优化
        
        Args:
            n_trials (int): 优化次数
            
        Returns:
            dict: 优化结果
        """
        try:
            # 创建study对象
            study = optuna.create_study(direction="minimize")
            
            # 运行优化
            study.optimize(self.objective, n_trials=n_trials)
            
            # 获取所有trials并按value排序
            sorted_trials = sorted(study.trials, key=lambda t: t.value)
            
            return {
                "best_trial": study.best_trial,
                "sorted_trials": sorted_trials
            }
            
        except Exception as e:
            print(f"优化过程中发生错误: {e}")
            return None
