import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from grid_strategy import GridStrategy
from stock_grid_optimizer import GridStrategyOptimizer
import akshare as ak

class TestGridStrategy(unittest.TestCase):
    """网格交易策略测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        self.strategy.base_price = 4.0
        self.strategy.price_range = (3.9, 4.3)
        self.strategy.up_sell_rate = 0.01
        self.strategy.up_callback_rate = 0.003
        self.strategy.down_buy_rate = 0.01
        self.strategy.down_rebound_rate = 0.003
        self.strategy.shares_per_trade = 1000
        self.strategy.initial_positions = 5000
        self.strategy.positions = self.strategy.initial_positions
        self.strategy.initial_cash = 100000
        self.strategy.cash = self.strategy.initial_cash
        
        # 模拟历史数据
        self.mock_hist_data = pd.DataFrame({
            '日期': pd.date_range(start='2024-01-01', end='2024-01-10'),
            '开盘': [4.0, 4.1, 4.0, 3.9, 4.0, 4.1, 4.2, 4.1, 4.0, 3.9],
            '最高': [4.1, 4.2, 4.1, 4.0, 4.1, 4.2, 4.3, 4.2, 4.1, 4.0],
            '最低': [3.9, 4.0, 3.9, 3.8, 3.9, 4.0, 4.1, 4.0, 3.9, 3.8],
            '收盘': [4.0, 4.1, 4.0, 3.9, 4.0, 4.1, 4.2, 4.1, 4.0, 3.9]
        })

    def test_initialization(self):
        """测试策略初始化"""
        self.assertEqual(self.strategy.symbol, "159300")
        self.assertEqual(self.strategy.symbol_name, "沪深300ETF")
        self.assertEqual(self.strategy.initial_positions, 5000)
        self.assertEqual(self.strategy.initial_cash, 100000)
        self.assertEqual(len(self.strategy.trades), 0)
        self.assertDictEqual(self.strategy.failed_trades, {
            "无持仓": 0,
            "卖出价格超范围": 0,
            "现金不足": 0,
            "买入价格超范围": 0
        })

    def test_buy_operation(self):
        """测试买入操作"""
        # 测试正常买入
        result = self.strategy.buy(4.0, "2024-01-01")
        self.assertTrue(result)
        self.assertEqual(len(self.strategy.trades), 1)
        self.assertEqual(self.strategy.positions, 6000)
        self.assertEqual(self.strategy.cash, 96000)
        
        # 测试价格超出范围的买入
        result = self.strategy.buy(4.4, "2024-01-01")
        self.assertFalse(result)
        self.assertEqual(self.strategy.failed_trades["买入价格超范围"], 1)
        
        # 测试资金不足的买入
        self.strategy.cash = 100
        result = self.strategy.buy(4.0, "2024-01-01")
        self.assertFalse(result)

    def test_sell_operation(self):
        """测试卖出操作"""
        # 测试正常卖出
        result = self.strategy.sell(4.0, "2024-01-01")
        self.assertTrue(result)
        self.assertEqual(len(self.strategy.trades), 1)
        self.assertEqual(self.strategy.positions, 4000)
        self.assertEqual(self.strategy.cash, 104000)
        
        # 测试价格超出范围的卖出
        result = self.strategy.sell(4.4, "2024-01-01")
        self.assertFalse(result)
        self.assertEqual(self.strategy.failed_trades["卖出价格超范围"], 1)
        
        # 测试持仓不足的卖出
        self.strategy.positions = 0
        result = self.strategy.sell(4.0, "2024-01-01")
        self.assertFalse(result)

    @patch('akshare.fund_etf_hist_em')
    def test_backtest(self, mock_hist_data):
        """测试回测功能"""
        # 设置模拟数据
        mock_hist_data.return_value = self.mock_hist_data
        
        # 执行回测
        profit_rate = self.strategy.backtest(
            start_date="2024-01-01",
            end_date="2024-01-10",
            verbose=True
        )
        
        # 验证回测结果
        self.assertIsInstance(profit_rate, float)
        self.assertTrue(len(self.strategy.trades) > 0)
        
        # 验证mock函数被正确调用
        mock_hist_data.assert_called_once()

    def test_calculate_profit(self):
        """测试收益计算"""
        # 模拟一些交易
        self.strategy.buy(4.0, "2024-01-01")
        self.strategy.sell(4.1, "2024-01-02")
        
        # 计算收益
        profit_rate = self.strategy.calculate_profit(4.0, verbose=True)
        
        # 验证收益率计算
        self.assertIsInstance(profit_rate, float)
        self.assertEqual(profit_rate, self.strategy.final_profit_rate)

    def test_ma_protection(self):
        """测试均线保护功能"""
        self.strategy.ma_protection = True
        
        # 测试买入保护
        self.assertTrue(self.strategy._check_ma_protection(3.9, 4.0, True))
        self.assertFalse(self.strategy._check_ma_protection(4.1, 4.0, True))
        
        # 测试卖出保护
        self.assertTrue(self.strategy._check_ma_protection(4.1, 4.0, False))
        self.assertFalse(self.strategy._check_ma_protection(3.9, 4.0, False))

class TestGridStrategyOptimizer(unittest.TestCase):
    """网格策略优化器测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2024, 1, 10)
        self.optimizer = GridStrategyOptimizer(
            symbol="159300",
            start_date=self.start_date,
            end_date=self.end_date,
            security_type="ETF",
            ma_period=55,
            ma_protection=True,
            initial_positions=5000,
            initial_cash=100000,
            min_buy_times=2,
            price_range=(3.9, 4.3)
        )
        
        # 模拟历史数据
        self.mock_hist_data = pd.DataFrame({
            '日期': pd.date_range(start='2024-01-01', end='2024-01-10'),
            '开盘': [4.0] * 10,
            '最高': [4.1] * 10,
            '最低': [3.9] * 10,
            '收盘': [4.0] * 10,
            '名称': ['沪深300ETF'] * 10,
            '代码': ['159300'] * 10
        })

    @patch('akshare.fund_etf_hist_em')
    @patch('akshare.fund_etf_spot_em')
    def test_initialization(self, mock_spot_data, mock_hist_data):
        """测试优化器初始化"""
        # 设置模拟数据
        mock_spot_data.return_value = pd.DataFrame({
            '代码': ['159300'],
            '名称': ['沪深300ETF']
        })
        mock_hist_data.return_value = self.mock_hist_data
        
        # 验证初始化参数
        self.assertEqual(self.optimizer.fixed_params["symbol"], "159300")
        self.assertEqual(self.optimizer.fixed_params["security_type"], "ETF")
        self.assertEqual(self.optimizer.fixed_params["initial_cash"], 100000)
        self.assertEqual(self.optimizer.fixed_params["initial_positions"], 5000)

    def test_parameter_ranges(self):
        """测试参数范围设置"""
        # 验证ETF的参数范围
        self.assertIn("up_sell_rate", self.optimizer.param_ranges)
        self.assertIn("down_buy_rate", self.optimizer.param_ranges)
        self.assertIn("up_callback_rate", self.optimizer.param_ranges)
        self.assertIn("down_rebound_rate", self.optimizer.param_ranges)
        self.assertIn("shares_per_trade", self.optimizer.param_ranges)
        
        # 验证参数范围的合理性
        self.assertLess(
            self.optimizer.param_ranges["up_callback_rate"]["max"],
            self.optimizer.param_ranges["up_sell_rate"]["max"]
        )
        self.assertLess(
            self.optimizer.param_ranges["down_rebound_rate"]["max"],
            self.optimizer.param_ranges["down_buy_rate"]["max"]
        )

    @patch('akshare.fund_etf_hist_em')
    def test_run_backtest(self, mock_hist_data):
        """测试运行回测"""
        # 设置模拟数据
        mock_hist_data.return_value = self.mock_hist_data
        
        # 测试参数
        test_params = {
            "up_sell_rate": 0.01,
            "up_callback_rate": 0.003,
            "down_buy_rate": 0.01,
            "down_rebound_rate": 0.003,
            "shares_per_trade": 1000
        }
        
        # 运行回测
        profit_rate, stats = self.optimizer.run_backtest(test_params)
        
        # 验证回测结果
        self.assertIsInstance(profit_rate, float)
        self.assertIn("trade_count", stats)
        self.assertIn("failed_trades", stats)
        self.assertIn("segment_results", stats)

    @patch('optuna.create_study')
    def test_optimize(self, mock_create_study):
        """测试优化过程"""
        # 模拟Study对象
        mock_study = MagicMock()
        mock_study.best_params = {
            "up_sell_rate": 0.01,
            "up_callback_rate": 0.003,
            "down_buy_rate": 0.01,
            "down_rebound_rate": 0.003,
            "shares_per_trade": 1000
        }
        mock_study.best_value = -0.05  # 5%的收益率
        mock_study.best_trial = MagicMock()
        mock_study.best_trial.user_attrs = {
            "trade_count": 10,
            "failed_trades": str({"无持仓": 0, "现金不足": 0})
        }
        mock_create_study.return_value = mock_study
        
        # 执行优化
        results = self.optimizer.optimize(n_trials=10)
        
        # 验证优化结果
        self.assertIsNotNone(results)
        self.assertIn("study", results)
        self.assertIn("sorted_trials", results)

    def test_refined_ranges(self):
        """测试优化范围细化"""
        best_params = {
            "up_sell_rate": 0.01,
            "up_callback_rate": 0.003,
            "down_buy_rate": 0.01,
            "down_rebound_rate": 0.003,
            "shares_per_trade": 1000
        }
        
        refined_ranges = self.optimizer._get_refined_ranges(best_params)
        
        # 验证细化后的范围
        for param in best_params:
            self.assertIn(param, refined_ranges)
            if param != "shares_per_trade":  # 对于浮点数参数
                self.assertLess(refined_ranges[param]["min"], best_params[param])
                self.assertGreater(refined_ranges[param]["max"], best_params[param])
            else:  # 对于整数参数
                self.assertLessEqual(refined_ranges[param]["min"], best_params[param])
                self.assertGreaterEqual(refined_ranges[param]["max"], best_params[param])
                self.assertTrue(isinstance(refined_ranges[param]["min"], int))
                self.assertTrue(isinstance(refined_ranges[param]["max"], int))

    def test_segment_handling(self):
        """测试分段处理"""
        segments = self.optimizer._build_segments()
        
        # 验证分段结果
        self.assertIsInstance(segments, list)
        self.assertTrue(all(isinstance(seg, tuple) for seg in segments))
        self.assertTrue(all(len(seg) == 2 for seg in segments))
        
        # 验证分段的时间顺序
        for i in range(len(segments)-1):
            self.assertLess(segments[i][1], segments[i+1][0])

    def test_trading_days(self):
        """测试交易日获取"""
        trading_days = self.optimizer._get_trading_days(self.start_date, self.end_date)
        
        # 验证交易日列表
        self.assertIsInstance(trading_days, pd.DatetimeIndex)
        self.assertTrue(len(trading_days) > 0)
        self.assertTrue(all(isinstance(day, pd.Timestamp) for day in trading_days))

if __name__ == '__main__':
    unittest.main(verbosity=2) 