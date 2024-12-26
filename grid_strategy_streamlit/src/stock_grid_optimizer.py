import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import optuna
from typing import Dict, List, Tuple, Optional, Any
import logging
from grid_strategy import GridStrategy
from trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol

class GridStrategyOptimizer:
    def __init__(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        security_type: str = "ETF",
        initial_positions: int = 0,
        initial_cash: float = 100000,
        min_buy_times: int = 2,
        price_range: Optional[Tuple[float, float]] = None,
        ma_period: Optional[int] = None,
        ma_protection: bool = False,
        profit_calc_method: str = "mean",
        connect_segments: bool = False
    ):
        """
        初始化网格策略优化器
        
        Args:
            symbol: 证券代码
            start_date: 回测开始日期
            end_date: 回测结束日期
            security_type: 证券类型，"ETF"或"STOCK"
            initial_positions: 初始持仓数量
            initial_cash: 初始资金
            min_buy_times: 最小买入次数
            price_range: 价格区间元组(最小值, 最大值)
            ma_period: 移动平均周期
            ma_protection: 是否启用移动平均保护
            profit_calc_method: 收益率计算方法，"mean"或"median"
            connect_segments: 是否连接分段
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.security_type = security_type
        self.initial_positions = initial_positions
        self.initial_cash = initial_cash
        self.min_buy_times = min_buy_times
        self.price_range = price_range
        self.ma_period = ma_period
        self.ma_protection = ma_protection
        self.profit_calc_method = profit_calc_method
        self.connect_segments = connect_segments
        
        # 验证参数
        self._validate_parameters()
        
        # 获取历史数据
        self.historical_data = self._get_historical_data()
        
        # 如果启用了移动平均保护，计算移动平均价格并更新价格区间
        if self.ma_protection and self.ma_period:
            ma_price = self._calculate_ma_price(self.ma_period)
            self._update_price_range_with_ma(ma_price)
            
        # 计算最大可买入股数
        self.max_shares = int(self.initial_cash / (self.price_range[0] * self.min_buy_times))
    
    def _validate_parameters(self) -> None:
        """验证初始化参数"""
        if not self.symbol:
            raise ValueError("证券代码不能为空")
        if not is_valid_symbol(self.symbol):
            raise ValueError("无效的证券代码")
        if not self.start_date or not self.end_date:
            raise ValueError("开始日期和结束日期不能为空")
        if self.start_date >= self.end_date:
            raise ValueError("开始日期必须早于结束日期")
        if self.initial_cash <= 0:
            raise ValueError("初始资金必须大于0")
        if self.min_buy_times < 1:
            raise ValueError("最小买入次数必须大于0")
        if self.price_range and self.price_range[0] >= self.price_range[1]:
            raise ValueError("价格区间最小值必须小于最大值")
        if self.ma_period and self.ma_period < 1:
            raise ValueError("移动平均周期必须大于0")
        if self.profit_calc_method not in ["mean", "median"]:
            raise ValueError("收益率计算方法必须是'mean'或'median'")
    
    def _get_historical_data(self) -> pd.DataFrame:
        """获取历史数据"""
        try:
            if self.security_type == "ETF":
                return self._get_etf_price_data(self.symbol, self.start_date)
            else:
                return self._get_stock_price_data(self.symbol, self.start_date)
        except Exception as e:
            logging.error(f"获取历史数据失败: {str(e)}")
            raise
    
    def _get_etf_price_data(self, symbol: str, start_date: datetime) -> pd.DataFrame:
        """获取ETF历史数据"""
        try:
            df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date.strftime("%Y%m%d"))
            df = df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount"
            })
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date")
        except Exception as e:
            logging.error(f"获取ETF数据失败: {str(e)}")
            raise
    
    def _get_stock_price_data(self, symbol: str, start_date: datetime) -> pd.DataFrame:
        """获取股票历史数据"""
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date.strftime("%Y%m%d"))
            df = df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount"
            })
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date")
        except Exception as e:
            logging.error(f"获取股票数据失败: {str(e)}")
            raise
    
    def _calculate_ma_price(self, ma_period: int) -> float:
        """计算移动平均价格"""
        try:
            if len(self.historical_data) < ma_period:
                raise ValueError(f"历史数据长度({len(self.historical_data)})小于移动平均周期({ma_period})")
            ma_series = self.historical_data["close"].rolling(window=ma_period).mean()
            return ma_series.iloc[-1]
        except Exception as e:
            logging.error(f"计算移动平均价格失败: {str(e)}")
            raise
    
    def _update_price_range_with_ma(self, ma_price: float) -> None:
        """根据移动平均价格更新价格区间"""
        try:
            if not self.price_range:
                self.price_range = (ma_price * 0.9, ma_price * 1.1)
            else:
                self.price_range = (
                    max(self.price_range[0], ma_price * 0.9),
                    min(self.price_range[1], ma_price * 1.1)
                )
        except Exception as e:
            logging.error(f"更新价格区间失败: {str(e)}")
            raise
    
    def _get_trading_days(self, start_date: datetime, end_date: datetime) -> List[str]:
        """获取交易日列表"""
        try:
            trading_days = self.historical_data[
                (self.historical_data["date"] >= start_date) &
                (self.historical_data["date"] <= end_date)
            ]["date"].tolist()
            return [day.strftime("%Y-%m-%d") for day in trading_days]
        except Exception as e:
            logging.error(f"获取交易日列表失败: {str(e)}")
            raise
    
    def optimize(self, n_trials: int = 100) -> Optional[Dict[str, Any]]:
        """
        使用Optuna优化策略参数
        
        Args:
            n_trials: 优化次数
            
        Returns:
            dict: 优化结果，包含最佳参数和收益率等信息
        """
        try:
            def objective(trial):
                # 生成参数
                params = {
                    "up_sell_rate": trial.suggest_float("up_sell_rate", 0.01, 0.05, step=0.001),
                    "up_callback_rate": trial.suggest_float("up_callback_rate", 0.001, 0.01, step=0.001),
                    "down_buy_rate": trial.suggest_float("down_buy_rate", 0.01, 0.05, step=0.001),
                    "down_rebound_rate": trial.suggest_float("down_rebound_rate", 0.001, 0.01, step=0.001),
                    "shares_per_trade": trial.suggest_int("shares_per_trade", 100, self.max_shares, step=100)
                }
                
                # 验证参数
                if params["up_callback_rate"] >= params["up_sell_rate"]:
                    return float("inf")
                if params["down_rebound_rate"] >= params["down_buy_rate"]:
                    return float("inf")
                
                # 创建策略实例
                strategy = GridStrategy(
                    symbol=self.symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    security_type=self.security_type,
                    initial_positions=self.initial_positions,
                    initial_cash=self.initial_cash,
                    price_range=self.price_range,
                    ma_period=self.ma_period,
                    ma_protection=self.ma_protection,
                    profit_calc_method=self.profit_calc_method,
                    connect_segments=self.connect_segments,
                    **params
                )
                
                # 执行回测
                results = strategy.backtest()
                
                # 记录交易统计信息
                trial.set_user_attr("trade_count", results["trade_count"])
                trial.set_user_attr("failed_trades", str(results["failed_trades"]))
                if "segment_results" in results:
                    trial.set_user_attr("segment_results", str(results["segment_results"]))
                
                # 返回负收益率(因为Optuna默认最小化目标)
                return -results["profit_rate"]
            
            # 创建学习实例
            study = optuna.create_study(direction="minimize")
            
            # 执行优化
            study.optimize(objective, n_trials=n_trials)
            
            # 对trials按收益率排序
            sorted_trials = sorted(study.trials, key=lambda t: t.value)
            
            return {
                "study": study,
                "sorted_trials": sorted_trials
            }
            
        except Exception as e:
            logging.error(f"优化过程发生错误: {str(e)}")
            return None
