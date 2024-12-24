import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd
import numpy as np
from functools import reduce
import optuna
from grid_strategy import GridStrategy
from stock_grid_optimizer import GridStrategyOptimizer

class TestGridStrategyOptimizer(unittest.TestCase):
    """网格策略优化器测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 基本测试数据
        self.symbol = "159300"
        self.start_date = datetime(2023, 1, 1)
        self.end_date = datetime(2023, 12, 31)
        self.initial_cash = 1000000
        self.initial_positions = 50000
        self.min_buy_times = 3
        self.price_range = (0.91, 1.01)
        
        # 生成日期范围
        self.date_range = pd.date_range(start=self.start_date, end=self.end_date, freq='B')
        num_days = len(self.date_range)
        
        # 生成模拟价格数据
        base_price = 10.0
        open_prices = np.ones(num_days) * base_price
        close_prices = np.ones(num_days) * base_price
        high_prices = np.ones(num_days) * (base_price * 1.05)
        low_prices = np.ones(num_days) * (base_price * 0.95)
        volumes = np.ones(num_days) * 1000000
        amounts = volumes * base_price
        
        # 创建模拟行情数据
        self.mock_market_data = pd.DataFrame({
            "开盘": open_prices,
            "收盘": close_prices,
            "最高": high_prices,
            "最低": low_prices,
            "成交量": volumes,
            "成交额": amounts
        }, index=self.date_range)
        
        # 模拟ETF基金数据
        self.mock_etf_data = pd.DataFrame({
            "代码": ["159300"],
            "名称": ["沪深300ETF"],
            "最新价": [10.5],
            "涨跌幅": [0.5]
        })
        
        # 模拟股票数据
        self.mock_stock_data = pd.DataFrame({
            "代码": ["000001"],
            "名称": ["平安银行"],
            "最新价": [15.5],
            "涨跌幅": [1.2]
        })

    def test_init_basic(self):
        """测试基本初始化功能"""
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data), \
             patch('akshare.fund_etf_hist_em', return_value=self.mock_market_data):
            
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                initial_cash=self.initial_cash,
                initial_positions=self.initial_positions,
                min_buy_times=self.min_buy_times,
                price_range=self.price_range
            )
            
            # 验证基本属性
            self.assertEqual(optimizer.symbol, self.symbol)
            self.assertEqual(optimizer.start_date, self.start_date)
            self.assertEqual(optimizer.end_date, self.end_date)
            self.assertEqual(optimizer.initial_cash, self.initial_cash)
            self.assertEqual(optimizer.initial_positions, self.initial_positions)
            self.assertEqual(optimizer.min_buy_times, self.min_buy_times)
            self.assertEqual(optimizer.price_range, self.price_range)
            
            # 验证证券名称获取
            self.assertEqual(optimizer.symbol_name, "沪深300ETF")

    def test_init_validation(self):
        """测试初始化参数验证"""
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data):
            # 测试无效日期
            with self.assertRaises(ValueError):
                GridStrategyOptimizer(
                    symbol=self.symbol,
                    start_date=self.end_date,  # 开始日期晚于结束日期
                    end_date=self.start_date
                )
            
            # 测试无效价格范围
            with self.assertRaises(ValueError):
                GridStrategyOptimizer(
                    symbol=self.symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    price_range=(1.01, 0.91)  # 最小值大于最大值
                )
            
            # 测试无效初始资金
            with self.assertRaises(ValueError):
                GridStrategyOptimizer(
                    symbol=self.symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    initial_cash=-1000  # 负数资金
                )

    def test_parameter_ranges(self):
        """测试参数范围设置"""
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data):
            # 测试ETF参数范围
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 验证参数范围存在性
            self.assertIn("up_sell_rate", optimizer.param_ranges)
            self.assertIn("down_buy_rate", optimizer.param_ranges)
            self.assertIn("up_callback_rate", optimizer.param_ranges)
            self.assertIn("down_rebound_rate", optimizer.param_ranges)
            self.assertIn("shares_per_trade", optimizer.param_ranges)
            
            # 验证参数范围值
            self.assertLess(optimizer.param_ranges["up_sell_rate"]["min"], 
                          optimizer.param_ranges["up_sell_rate"]["max"])
            self.assertGreater(optimizer.param_ranges["shares_per_trade"]["min"], 0)
            
        # 测试股票参数范围
        with patch('akshare.stock_zh_a_spot_em', return_value=self.mock_stock_data):
            optimizer = GridStrategyOptimizer(
                symbol="000001",
                start_date=self.start_date,
                end_date=self.end_date,
                security_type="STOCK"
            )
            
            # 验证创业板股票特殊范围
            if optimizer.symbol.startswith("300"):
                self.assertGreaterEqual(
                    optimizer.param_ranges["up_sell_rate"]["max"],
                    optimizer.param_ranges["up_sell_rate"]["min"] * 2
                )

    def test_objective_function(self):
        """测试目标函数"""
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data), \
             patch('akshare.fund_etf_hist_em', return_value=self.mock_market_data):
            
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 创建模拟trial对象
            mock_trial = MagicMock()
            mock_trial.suggest_float.return_value = 0.01
            mock_trial.suggest_int.return_value = 1000
            
            # 测试目标函数
            result = optimizer.objective(mock_trial)
            
            # 验证返回值类型
            self.assertIsInstance(result, float)
            
            # 验证参数生成调用
            mock_trial.suggest_float.assert_called()
            mock_trial.suggest_int.assert_called()
            
            # 验证trial属性设置
            mock_trial.set_user_attr.assert_called()

    def test_optimization_process(self):
        """测试完整优化过程"""
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data), \
             patch('akshare.fund_etf_hist_em', return_value=self.mock_market_data):
            
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 运行优化
            results = optimizer.optimize(n_trials=5)  # 使用较少的trials加快测试
            
            # 验证结果结构
            self.assertIsNotNone(results)
            self.assertIn("best_trial", results)
            self.assertIn("sorted_trials", results)
            
            # 验证最佳trial
            best_trial = results["best_trial"]
            self.assertIsNotNone(best_trial.value)
            self.assertIsNotNone(best_trial.params)
            
            # 验证参数范围
            for param_name, param_value in best_trial.params.items():
                param_range = optimizer.param_ranges[param_name]
                self.assertGreaterEqual(param_value, param_range["min"])
                self.assertLessEqual(param_value, param_range["max"])

    def test_segment_optimization(self):
        """测试分段优化功能"""
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data), \
             patch('akshare.fund_etf_hist_em', return_value=self.mock_market_data):
            
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                profit_calc_method="mean",
                connect_segments=True
            )
            
            # 验证时间段生成
            segments = optimizer._generate_time_segments()
            self.assertGreater(len(segments), 0)
            
            # 验证每个时间段的有效性
            for start, end in segments:
                self.assertLess(start, end)
                self.assertGreaterEqual(start, self.start_date)
                self.assertLessEqual(end, self.end_date)
            
            # 测试分段优化
            results = optimizer.optimize(n_trials=3)
            self.assertIsNotNone(results)

    def test_ma_protection(self):
        """测试均线保护功能"""
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data), \
             patch('akshare.fund_etf_hist_em', return_value=self.mock_market_data):
            
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date,
                ma_period=20,
                ma_protection=True
            )
            
            # 验证MA相关属性
            self.assertEqual(optimizer.ma_period, 20)
            self.assertTrue(optimizer.ma_protection)
            
            # 测试MA价格计算
            ma_price = optimizer._calculate_ma_price(20)
            self.assertIsNotNone(ma_price)

    def test_error_handling(self):
        """测试错误处理"""
        with patch('akshare.fund_etf_spot_em', return_value=pd.DataFrame()):
            # 测试无效数据处理
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 验证默认值设置
            self.assertEqual(optimizer.symbol_name, self.symbol)
            
        # 测试优化过程错误处理
        with patch('akshare.fund_etf_spot_em', return_value=self.mock_etf_data), \
             patch('akshare.fund_etf_hist_em', return_value=pd.DataFrame()):
            
            optimizer = GridStrategyOptimizer(
                symbol=self.symbol,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # 验证空数据处理
            results = optimizer.optimize(n_trials=1)
            self.assertIsNone(results)

if __name__ == '__main__':
    unittest.main() 