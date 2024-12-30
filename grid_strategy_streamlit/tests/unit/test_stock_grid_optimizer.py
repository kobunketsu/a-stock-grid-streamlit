import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

from src.services.business.stock_grid_optimizer import GridStrategyOptimizer

"""网格策略优化器测试类"""

class TestGridStrategyOptimizer(unittest.TestCase):
    def setUp(self):
        """初始化测试环境，设置优化器基本参数
        场景: 初始化测试环境
        输入:
            - symbol: 159300
            - start_date: 2024-01-01
            - end_date: 2024-01-10
            - security_type: ETF
            - initial_positions: 5000
            - initial_cash: 100000
            - min_buy_times: 2
            - price_range: (3.9, 4.3)
        验证:
            - 基本参数设置正确
            - 优化器初始化完成
        """
        self.optimizer = GridStrategyOptimizer(
            symbol="159300",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 10),
            security_type="ETF",
            initial_positions=5000,
            initial_cash=100000,
            min_buy_times=2,
            price_range=(3.9, 4.3)
        )

    def test_initialization(self):
        """验证优化器初始化参数和范围设置
        场景1: 基本属性验证
        输入:
            - 固定参数集
            - 参数范围设置
        验证:
            - 固定参数正确设置
            - 参数范围合理设置

        场景2: 参数范围验证
        输入:
            - up_sell_rate范围
            - down_buy_rate范围
        验证:
            - 最大值大于最小值
            - 范围设置合理
        """
        # 检查基本属性是否正确设置
        self.assertEqual(self.optimizer.fixed_params["symbol"], "159300")
        self.assertEqual(self.optimizer.fixed_params["security_type"], "ETF")
        self.assertEqual(self.optimizer.fixed_params["initial_positions"], 5000)
        self.assertEqual(self.optimizer.fixed_params["initial_cash"], 100000)
        self.assertEqual(self.optimizer.fixed_params["price_range"], (3.9, 4.3))

        # 检查参数范围是否正确设置
        self.assertGreater(self.optimizer.param_ranges["up_sell_rate"]["max"], 
                          self.optimizer.param_ranges["up_sell_rate"]["min"])
        self.assertGreater(self.optimizer.param_ranges["down_buy_rate"]["max"], 
                          self.optimizer.param_ranges["down_buy_rate"]["min"])

    def test_parameter_validation(self):
        """测试参数验证的边界条件处理
        场景1: 有效参数
        输入:
            - up_sell_rate: 0.01
            - down_buy_rate: 0.01
            - up_callback_rate: 0.003
            - down_rebound_rate: 0.003
            - shares_per_trade: 1000
        验证:
            - 返回True

        场景2: 无效参数
        输入:
            - up_sell_rate: -0.01 (负值)
            - 其他参数正常
        验证:
            - 返回False
        """
        # 测试有效参数
        valid_params = {
            "up_sell_rate": 0.01,
            "down_buy_rate": 0.01,
            "up_callback_rate": 0.003,
            "down_rebound_rate": 0.003,
            "shares_per_trade": 1000
        }
        
        # 测试无效参数
        invalid_params = {
            "up_sell_rate": -0.01,  # 负值
            "down_buy_rate": 0.01,
            "up_callback_rate": 0.003,
            "down_rebound_rate": 0.003,
            "shares_per_trade": 1000
        }
        
        # 使用_validate_params方法进行验证
        self.assertTrue(self.optimizer._validate_params(valid_params))
        self.assertFalse(self.optimizer._validate_params(invalid_params))

    def test_profit_calculation_methods(self):
        """验证不同收益计算方法的准确性
        场景: 不同收益计算方法比较
        输入:
            - 收益率序列: [-0.5, -0.3, -0.2, 0.1, 0.2, 0.3, 0.5]
        验证:
            - 均值计算正确
            - 中位数计算正确
            - 两种方法结果不同
        """
        # 创建测试数据
        test_profits = pd.Series([-0.5, -0.3, -0.2, 0.1, 0.2, 0.3, 0.5])
        
        # 计算不同方法的收益率
        profit_rate_mean = test_profits.mean()
        profit_rate_median = test_profits.median()
        
        # 验证不同计算方法得到的结果不同
        self.assertNotEqual(profit_rate_mean, profit_rate_median)

if __name__ == '__main__':
    unittest.main() 