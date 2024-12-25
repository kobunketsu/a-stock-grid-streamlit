import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple
from src.grid_strategy import GridStrategy

class GridStrategyOptimizer:
    """网格策略优化器"""
    
    def __init__(self, symbol: str, start_date: datetime, end_date: datetime,
                 security_type: str = "ETF", initial_positions: int = 0,
                 initial_cash: float = 100000, min_buy_times: int = 2,
                 price_range: Tuple[float, float] = None):
        """
        初始化优化器
        @param symbol: 证券代码
        @param start_date: 开始日期
        @param end_date: 结束日期
        @param security_type: 证券类型
        @param initial_positions: 初始持仓
        @param initial_cash: 初始资金
        @param min_buy_times: 最小买入次数
        @param price_range: 价格区间
        """
        self.fixed_params = {
            "symbol": symbol,
            "security_type": security_type,
            "initial_positions": initial_positions,
            "initial_cash": initial_cash,
            "price_range": price_range
        }
        
        self.start_date = start_date
        self.end_date = end_date
        self.min_buy_times = min_buy_times
        
        # 参数范围设置
        self.param_ranges = {
            "up_sell_rate": {"min": 0.005, "max": 0.02, "step": 0.001},
            "down_buy_rate": {"min": 0.005, "max": 0.02, "step": 0.001},
            "up_callback_rate": {"min": 0.001, "max": 0.01, "step": 0.001},
            "down_rebound_rate": {"min": 0.001, "max": 0.01, "step": 0.001},
            "shares_per_trade": {"min": 100, "max": 2000, "step": 100}
        }
        
        # 优化结果
        self.best_params = None
        self.best_profit_rate = float('-inf')
        self.optimization_results = []
    
    def _validate_params(self, params: Dict[str, Any]) -> bool:
        """
        验证参数是否有效
        @param params: 参数字典
        @return: 是否有效
        """
        try:
            # 检查参数是否在有效范围内
            for param_name, value in params.items():
                if param_name in self.param_ranges:
                    param_range = self.param_ranges[param_name]
                    if value < param_range["min"] or value > param_range["max"]:
                        return False
            
            # 检查回调率是否小于网格率
            if params["up_callback_rate"] >= params["up_sell_rate"] or \
               params["down_rebound_rate"] >= params["down_buy_rate"]:
                return False
            
            return True
        except Exception as e:
            print(f"参数��证失败: {e}")
            return False
    
    def optimize(self, method: str = "grid", **kwargs) -> Dict[str, Any]:
        """
        执行优化
        @param method: 优化方法 ("grid" 或 "random")
        @param kwargs: 其他参数
        @return: 最优参数
        """
        if method == "grid":
            return self._grid_search(**kwargs)
        elif method == "random":
            return self._random_search(**kwargs)
        else:
            raise ValueError(f"不支持的优化方法: {method}")
    
    def _grid_search(self, **kwargs) -> Dict[str, Any]:
        """
        网格搜索优化
        @param kwargs: 其他参数
        @return: 最优参数
        """
        # 生成参数网格
        param_grid = []
        for param_name, param_range in self.param_ranges.items():
            values = np.arange(
                param_range["min"],
                param_range["max"] + param_range["step"],
                param_range["step"]
            )
            param_grid.append((param_name, values))
        
        # 遍历参数组合
        total_combinations = np.prod([len(values) for _, values in param_grid])
        print(f"总参数组合数: {total_combinations}")
        
        best_params = None
        best_profit_rate = float('-inf')
        
        for i, params in enumerate(self._generate_param_combinations(param_grid)):
            if not self._validate_params(params):
                continue
            
            # 创建策略实例
            strategy = GridStrategy(
                symbol=self.fixed_params["symbol"],
                security_type=self.fixed_params["security_type"]
            )
            
            # 设置参数
            for param_name, value in params.items():
                setattr(strategy, param_name, value)
            
            for param_name, value in self.fixed_params.items():
                if value is not None:
                    setattr(strategy, param_name, value)
            
            # 执行回测
            try:
                profit_rate = strategy.backtest(
                    start_date=self.start_date,
                    end_date=self.end_date,
                    verbose=False
                )
                
                # 更新最优结果
                if profit_rate > best_profit_rate:
                    best_profit_rate = profit_rate
                    best_params = params.copy()
                
                # 记录结果
                self.optimization_results.append({
                    "params": params.copy(),
                    "profit_rate": profit_rate
                })
                
                # 打印进度
                if (i + 1) % 100 == 0:
                    print(f"已完成: {i + 1}/{total_combinations}")
                
            except Exception as e:
                print(f"回测失败: {e}")
                continue
        
        self.best_params = best_params
        self.best_profit_rate = best_profit_rate
        
        return best_params
    
    def _random_search(self, n_iter: int = 1000, **kwargs) -> Dict[str, Any]:
        """
        随机搜索优化
        @param n_iter: 迭代次数
        @param kwargs: 其他参数
        @return: 最优参数
        """
        best_params = None
        best_profit_rate = float('-inf')
        
        for i in range(n_iter):
            # 随机生成参数
            params = {}
            for param_name, param_range in self.param_ranges.items():
                value = np.random.uniform(param_range["min"], param_range["max"])
                # 对于shares_per_trade，确保是100的整数倍
                if param_name == "shares_per_trade":
                    value = round(value / 100) * 100
                params[param_name] = value
            
            if not self._validate_params(params):
                continue
            
            # 创建策略实例
            strategy = GridStrategy(
                symbol=self.fixed_params["symbol"],
                security_type=self.fixed_params["security_type"]
            )
            
            # 设置参数
            for param_name, value in params.items():
                setattr(strategy, param_name, value)
            
            for param_name, value in self.fixed_params.items():
                if value is not None:
                    setattr(strategy, param_name, value)
            
            # 执行回测
            try:
                profit_rate = strategy.backtest(
                    start_date=self.start_date,
                    end_date=self.end_date,
                    verbose=False
                )
                
                # 更新最优结果
                if profit_rate > best_profit_rate:
                    best_profit_rate = profit_rate
                    best_params = params.copy()
                
                # 记录结果
                self.optimization_results.append({
                    "params": params.copy(),
                    "profit_rate": profit_rate
                })
                
                # 打印进度
                if (i + 1) % 100 == 0:
                    print(f"已完成: {i + 1}/{n_iter}")
                
            except Exception as e:
                print(f"回测失败: {e}")
                continue
        
        self.best_params = best_params
        self.best_profit_rate = best_profit_rate
        
        return best_params
    
    def _generate_param_combinations(self, param_grid: List[Tuple[str, np.ndarray]]):
        """
        生成参数组合
        @param param_grid: 参数网格
        @yield: 参数组合
        """
        if not param_grid:
            yield {}
        else:
            param_name, values = param_grid[0]
            for value in values:
                for sub_params in self._generate_param_combinations(param_grid[1:]):
                    yield {param_name: value, **sub_params}
    
    def get_optimization_results(self) -> pd.DataFrame:
        """
        获取优化结果
        @return: 包含所有优化结果的DataFrame
        """
        if not self.optimization_results:
            return pd.DataFrame()
        
        # 结果转换为DataFrame
        results = []
        for result in self.optimization_results:
            row = {**result["params"], "profit_rate": result["profit_rate"]}
            results.append(row)
        
        df = pd.DataFrame(results)
        
        # 按收益率排序
        df = df.sort_values("profit_rate", ascending=False)
        
        return df 