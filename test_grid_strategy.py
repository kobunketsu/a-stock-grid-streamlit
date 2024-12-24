import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
from grid_strategy import GridStrategy

class TestGridStrategy(unittest.TestCase):
    """网格策略测试类"""
    
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
        
        # 生成模拟数据
        dates = pd.date_range(start="2024-01-01", end="2024-01-10", freq='D')
        self.mock_hist_data = pd.DataFrame({
            '日期': dates,
            '开盘': [4.0, 4.1, 4.0, 3.9, 4.0, 4.1, 4.2, 4.1, 4.0, 3.9],
            '收盘': [4.0, 4.1, 4.0, 3.9, 4.0, 4.1, 4.2, 4.1, 4.0, 3.9],
            '最高': [4.1, 4.2, 4.1, 4.0, 4.1, 4.2, 4.3, 4.2, 4.1, 4.0],
            '最低': [3.9, 4.0, 3.9, 3.8, 3.9, 4.0, 4.1, 4.0, 3.9, 3.8],
            '成交量': [1000000] * len(dates),
            '成交额': [4000000] * len(dates)
        })

    def test_initialization(self):
        """测试策略初始化"""
        # 测试正常初始化
        self.assertEqual(self.strategy.symbol, "159300")
        self.assertEqual(self.strategy.symbol_name, "沪深300ETF")
        self.assertEqual(self.strategy.initial_positions, 5000)
        self.assertEqual(self.strategy.initial_cash, 100000)
        
        # 测试参数验证
        strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        strategy.initial_cash = -1000  # 负数现金
        with self.assertRaises(ValueError):
            strategy.backtest()
        
        strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        strategy.initial_positions = -1000  # 负数持仓
        with self.assertRaises(ValueError):
            strategy.backtest()
        
        strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        strategy.price_range = (4.3, 3.9)  # 无���的价格区间
        with self.assertRaises(ValueError):
            strategy.backtest()

    def test_buy_operation(self):
        """测试买入操作"""
        # 测试正常买入
        result = self.strategy.buy(4.0, "2024-01-01")
        self.assertTrue(result)
        self.assertEqual(len(self.strategy.trades), 1)
        self.assertEqual(self.strategy.positions, 6000)
        self.assertEqual(self.strategy.cash, 96000)
        
        # 测试价格超出范围的买入
        result = self.strategy.buy(3.8, "2024-01-01")
        self.assertFalse(result)
        self.assertEqual(self.strategy.failed_trades["买入价格超范围"], 1)
        
        # 测试现金不足的买入
        self.strategy.cash = 0
        result = self.strategy.buy(4.0, "2024-01-01")
        self.assertFalse(result)
        self.assertEqual(self.strategy.failed_trades["现金不足"], 1)

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
        self.assertEqual(self.strategy.failed_trades["无持仓"], 1)

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

    def test_trade_recording(self):
        """测试交易记录功能"""
        # 重置交易记录
        self.strategy.trades = []
        self.strategy.failed_trades = {
            "无持仓": 0,
            "卖出价格超范围": 0,
            "现金不足": 0,
            "买入价格超范围": 0
        }
        
        # 执行一些交易
        self.strategy.buy(4.0, "2024-01-01")
        self.strategy.sell(4.1, "2024-01-02")
        
        # 验证交易记录
        self.assertEqual(len(self.strategy.trades), 2)
        self.assertEqual(self.strategy.trades[0]["操作"], "买入")
        self.assertEqual(self.strategy.trades[1]["操作"], "卖出")
        
        # 验证交易统计
        self.assertEqual(len(self.strategy.failed_trades), 4)  # 四种失败类型
        self.assertEqual(sum(self.strategy.failed_trades.values()), 0)  # 无失败交易
        
        # 测试失败交易记录
        self.strategy.positions = 0
        self.strategy.sell(4.0, "2024-01-03")
        self.assertEqual(self.strategy.failed_trades["无持仓"], 1)

    def test_price_calculation(self):
        """测试价格计算"""
        # 测试买入价格计算
        base_price = 4.0
        down_rate = 0.01
        rebound_rate = 0.003
        
        trigger_price = base_price * (1 - down_rate)
        exec_price = trigger_price * (1 + rebound_rate)
        
        self.assertEqual(
            self.strategy._calculate_buy_prices(base_price),
            (trigger_price, exec_price)
        )
        
        # 测试卖出价格计算
        up_rate = 0.01
        callback_rate = 0.003
        
        trigger_price = base_price * (1 + up_rate)
        exec_price = trigger_price * (1 - callback_rate)
        
        self.assertEqual(
            self.strategy._calculate_sell_prices(base_price),
            (trigger_price, exec_price)
        )

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效日期
        with self.assertRaises(ValueError):
            self.strategy.backtest(
                start_date="2024-13-01",  # 无效月��
                end_date="2024-01-10"
            )
        
        # 测试结束日期早于开始日期
        with self.assertRaises(ValueError):
            self.strategy.backtest(
                start_date="2024-01-10",
                end_date="2024-01-01"
            )
        
        # 测试无效的价格区间
        self.strategy.price_range = (4.0, 3.0)  # 最高价小于最低价
        with self.assertRaises(ValueError):
            self.strategy.backtest()

    def test_boundary_conditions(self):
        """测试边界条件"""
        # 测试零持仓初始化
        strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        strategy.initial_positions = 0
        strategy.positions = 0
        strategy.base_price = 4.0
        strategy.price_range = (3.9, 4.3)
        strategy.initial_cash = 100000
        strategy.cash = 100000
        self.assertEqual(strategy.positions, 0)
        
        # 测试零现金初始化
        strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        strategy.initial_cash = 0
        strategy.cash = 0
        strategy.base_price = 4.0
        strategy.price_range = (3.9, 4.3)
        strategy.initial_positions = 5000
        strategy.positions = 5000
        self.assertEqual(strategy.cash, 0)
        
        # 测试最小交易单位
        strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        strategy.shares_per_trade = 100
        strategy.base_price = 4.0
        strategy.price_range = (3.9, 4.3)
        strategy.initial_cash = 100000
        strategy.cash = 100000
        strategy.initial_positions = 5000
        strategy.positions = 5000
        self.assertEqual(strategy.shares_per_trade, 100)
        
        # 测试价格区间边界
        strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        strategy.base_price = 4.0
        strategy.price_range = (3.9, 4.3)
        strategy.initial_cash = 100000
        strategy.cash = 100000
        strategy.initial_positions = 5000
        strategy.positions = 5000
        strategy.shares_per_trade = 1000
        
        result = strategy.buy(strategy.price_range[0], "2024-01-01")  # 最低价买入
        self.assertTrue(result)
        result = strategy.sell(strategy.price_range[1], "2024-01-01")  # 最高价卖出
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main() 