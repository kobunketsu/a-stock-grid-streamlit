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
        strategy.price_range = (4.3, 3.9)  # 无�����的价格区间
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
        
        # 算收益
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
        self.strategy.sell(4.0, "2024-01-03")  # 这会记录一个无持仓失败
        self.assertEqual(self.strategy.failed_trades["无持仓"], 1)
        
        # 测试买入价格超范围
        self.strategy.buy(3.8, "2024-01-03")  # 价格低于最低价
        self.assertEqual(self.strategy.failed_trades["买入价格超范围"], 1)

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
                start_date="2024-13-01",  # 无效月
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

    def test_ma_protection_edge_cases(self):
        """测试均线保护的边界条件"""
        self.strategy.ma_protection = True
        self.strategy.ma_period = 5
        
        # 测试价格等于均线的情况
        self.assertTrue(self.strategy._check_ma_protection(4.0, 4.0, True))
        self.assertTrue(self.strategy._check_ma_protection(4.0, 4.0, False))
        
        # 测试均线为None的情况
        self.assertTrue(self.strategy._check_ma_protection(4.0, None, True))
        self.assertTrue(self.strategy._check_ma_protection(4.0, None, False))
        
        # 测试ma_protection为False的情况
        self.strategy.ma_protection = False
        self.assertTrue(self.strategy._check_ma_protection(4.0, 4.0, True))
        self.assertTrue(self.strategy._check_ma_protection(4.0, 4.0, False))

    def test_trade_failure_recording(self):
        """测试交易失败记录"""
        # 测试买入失败记录
        self.strategy.cash = 0  # 设置现金为0
        self.strategy.buy(4.0, "2024-01-01")
        self.assertEqual(self.strategy.failed_trades["现金不足"], 1)
        
        # 测试卖出失败记录
        self.strategy.positions = 0  # 设置持仓为0
        self.strategy.sell(4.0, "2024-01-01")
        self.assertEqual(self.strategy.failed_trades["无持仓"], 1)
        
        # 测试价格超出范围的失败记录
        self.strategy.buy(3.8, "2024-01-01")  # 低于最低价
        self.assertEqual(self.strategy.failed_trades["买入价格超范围"], 1)
        
        self.strategy.sell(4.4, "2024-01-01")  # 高于最高价
        self.assertEqual(self.strategy.failed_trades["卖出价格超范围"], 1)

    def test_profit_calculation_edge_cases(self):
        """测试收益计算的边界条件"""
        # 测试无交易的情况
        profit_rate = self.strategy.calculate_profit(4.0, verbose=True)
        self.assertEqual(profit_rate, 0.0)
        
        # 测试亏损的情况
        self.strategy.buy(4.0, "2024-01-01")
        profit_rate = self.strategy.calculate_profit(3.9, verbose=True)
        self.assertTrue(profit_rate < 0)
        
        # 测试盈利的情况
        self.strategy.sell(4.1, "2024-01-02")
        profit_rate = self.strategy.calculate_profit(4.1, verbose=True)
        self.assertTrue(profit_rate > 0)

    def test_backtest_error_handling(self):
        """测试回测错误处理"""
        # 测试无效的日期格式
        with self.assertRaises(ValueError):
            self.strategy.backtest("invalid_date", "2024-01-10")
        
        # 测试结束日期早于开始日期
        with self.assertRaises(ValueError):
            self.strategy.backtest("2024-01-10", "2024-01-01")
        
        # 测试效的价格区间
        self.strategy.price_range = (4.3, 3.9)  # 最高价小于最低价
        with self.assertRaises(ValueError):
            self.strategy.backtest()
        
        # 测试负数现金
        self.strategy.initial_cash = -1000
        with self.assertRaises(ValueError):
            self.strategy.backtest()
        
        # 测试负数持仓
        self.strategy.initial_cash = 100000
        self.strategy.initial_positions = -1000
        with self.assertRaises(ValueError):
            self.strategy.backtest()

    @patch('akshare.fund_etf_hist_em')
    def test_backtest_market_conditions(self, mock_hist_data):
        """测试不同市场条件下的回测"""
        # 测试上涨行情
        dates = pd.date_range(start="2024-01-01", end="2024-01-05", freq='D')
        uptrend_data = pd.DataFrame({
            '日期': dates,
            '开盘': [4.0, 4.1, 4.2, 4.3, 4.4],
            '收盘': [4.1, 4.2, 4.3, 4.4, 4.5],
            '最高': [4.2, 4.3, 4.4, 4.5, 4.6],
            '最低': [4.0, 4.1, 4.2, 4.3, 4.4]
        })
        mock_hist_data.return_value = uptrend_data
        profit_rate = self.strategy.backtest(verbose=True)
        self.assertTrue(profit_rate > 0)
        
        # 测试下跌行情
        downtrend_data = pd.DataFrame({
            '日期': dates,
            '开盘': [4.4, 4.3, 4.2, 4.1, 4.0],
            '收盘': [4.3, 4.2, 4.1, 4.0, 3.9],
            '最高': [4.4, 4.3, 4.2, 4.1, 4.0],
            '最低': [4.2, 4.1, 4.0, 3.9, 3.8]
        })
        mock_hist_data.return_value = downtrend_data
        profit_rate = self.strategy.backtest(verbose=True)
        self.assertTrue(profit_rate < 0)
        
        # 测试震荡行情
        sideways_data = pd.DataFrame({
            '日期': dates,
            '开盘': [4.0, 4.1, 4.0, 4.1, 4.0],
            '收盘': [4.1, 4.0, 4.1, 4.0, 4.1],
            '最高': [4.2, 4.2, 4.2, 4.2, 4.2],
            '最低': [3.9, 3.9, 3.9, 3.9, 3.9]
        })
        mock_hist_data.return_value = sideways_data
        profit_rate = self.strategy.backtest(verbose=True)
        self.assertIsInstance(profit_rate, float)

    def test_verbose_output(self):
        """测试详细输出模式"""
        # 测试买入操作的详细输出
        self.strategy.verbose = True
        self.strategy.buy(4.0, "2024-01-01")
        
        # 测试卖出操作的详细输出
        self.strategy.sell(4.1, "2024-01-01")
        
        # 测试失败操作的详细输出
        self.strategy.cash = 0
        self.strategy.buy(4.0, "2024-01-01")
        
        self.strategy.positions = 0
        self.strategy.sell(4.0, "2024-01-01")

    def test_empty_data_handling(self):
        """测试空数据处理"""
        with patch('akshare.fund_etf_hist_em') as mock_hist_data:
            # 测试空DataFrame
            mock_hist_data.return_value = pd.DataFrame()
            with self.assertRaises(Exception):
                self.strategy.backtest()
            
            # 测试无效的日期格式
            with self.assertRaises(ValueError):
                self.strategy.backtest("invalid", "2024-01-10")

    def test_stock_data_handling(self):
        """测试股票数据处理"""
        self.strategy.security_type = "STOCK"
        with patch('akshare.stock_zh_a_hist') as mock_hist_data:
            dates = pd.date_range(start="2024-01-01", end="2024-01-05", freq='D')
            mock_data = pd.DataFrame({
                '日期': dates,
                '开盘': [4.0] * len(dates),
                '收盘': [4.1] * len(dates),
                '最高': [4.2] * len(dates),
                '最低': [3.9] * len(dates)
            })
            mock_hist_data.return_value = mock_data
            
            profit_rate = self.strategy.backtest(verbose=True)
            self.assertIsInstance(profit_rate, float)

    def test_multiple_trade_handling(self):
        """测试多次交易处理"""
        # 测试多次买入
        self.strategy.multiple_trade = True
        self.strategy.cash = 100000
        result = self.strategy.buy(3.8, "2024-01-01")
        self.assertFalse(result)  # 价格超出范围
        
        # 测试多次卖出
        self.strategy.positions = 5000
        result = self.strategy.sell(4.4, "2024-01-01")
        self.assertFalse(result)  # 价格超出范围

    def test_main_function(self):
        """测试主函数"""
        with patch('akshare.fund_etf_hist_em') as mock_hist_data:
            dates = pd.date_range(start="2024-01-01", end="2024-01-05", freq='D')
            mock_data = pd.DataFrame({
                '日期': dates,
                '开盘': [4.0] * len(dates),
                '收盘': [4.1] * len(dates),
                '最高': [4.2] * len(dates),
                '最低': [3.9] * len(dates)
            })
            mock_hist_data.return_value = mock_data
            
            # 测试主函数
            if __name__ == '__main__':
                strategy = GridStrategy()
                strategy.backtest('2024-01-01', '2024-01-05')
                strategy.backtest()  # 使用默认日期范围

    def test_extreme_price_conditions(self):
        """测试极端价格条件"""
        # 测试价格为0的情况
        self.assertFalse(self.strategy.buy(0, "2024-01-01"))
        self.assertFalse(self.strategy.sell(0, "2024-01-01"))
        
        # 测试负价格
        self.assertFalse(self.strategy.buy(-1, "2024-01-01"))
        self.assertFalse(self.strategy.sell(-1, "2024-01-01"))
        
        # 测试极大价格
        self.assertFalse(self.strategy.buy(1000000, "2024-01-01"))
        self.assertFalse(self.strategy.sell(1000000, "2024-01-01"))

    def test_invalid_date_handling(self):
        """测试无效日期处理"""
        # 测试无效日期格式
        with self.assertRaises(ValueError):
            self.strategy.buy(4.0, "invalid_date")
            
        # 测试空日期
        with self.assertRaises(ValueError):
            self.strategy.sell(4.0, "")
            
        # 测试未来日期
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        self.assertFalse(self.strategy.buy(4.0, future_date))

    def test_position_limits(self):
        """测试持仓限制"""
        # 测试负持仓
        self.strategy.positions = -100
        self.assertFalse(self.strategy.sell(4.0, "2024-01-01"))
        
        # 测试正常买入不受持仓限制
        self.strategy.positions = 1000000  # 设置一个很大的持仓量
        self.strategy.cash = 1000000  # 确保有足够的现金
        self.assertTrue(self.strategy.buy(4.0, "2024-01-01"))  # 应该可以继续买入

    def test_cash_limits(self):
        """测试资金限制"""
        # 测试现金不足
        self.strategy.cash = 0
        self.assertFalse(self.strategy.buy(4.0, "2024-01-01"))
        
        # 测试负现金
        self.strategy.cash = -1000
        self.assertFalse(self.strategy.buy(4.0, "2024-01-01"))
        
        # 测试超大现金
        self.strategy.cash = float('inf')
        self.assertTrue(self.strategy.buy(4.0, "2024-01-01"))

if __name__ == '__main__':
    unittest.main() 