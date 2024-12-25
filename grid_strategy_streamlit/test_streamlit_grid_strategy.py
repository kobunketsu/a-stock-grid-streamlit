import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
from grid_strategy import GridStrategy

class TestStreamlitGridStrategy(unittest.TestCase):
    """Streamlit版本网格策略测试类"""
    
    @patch('streamlit.session_state', {})
    def setUp(self):
        """测试前的准备工作"""
        # 初始化session_state
        if 'strategy' not in st.session_state:
            st.session_state.strategy = GridStrategy(symbol="159300", symbol_name="沪深300ETF")
        
        self.strategy = st.session_state.strategy
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

    @patch('streamlit.write')
    def test_initialization(self, mock_write):
        """测试策略初始化"""
        # 测试正常初始化
        self.assertEqual(self.strategy.symbol, "159300")
        self.assertEqual(self.strategy.symbol_name, "沪深300ETF")
        self.assertEqual(self.strategy.initial_positions, 5000)
        self.assertEqual(self.strategy.initial_cash, 100000)
        
        # 测试参数验证
        with patch('streamlit.error') as mock_error:
            self.strategy.initial_cash = -1000  # 负数现金
            with self.assertRaises(ValueError):
                self.strategy.backtest()
            mock_error.assert_called_once()
        
        with patch('streamlit.error') as mock_error:
            self.strategy.initial_positions = -1000  # 负数持仓
            with self.assertRaises(ValueError):
                self.strategy.backtest()
            mock_error.assert_called_once()

    @patch('streamlit.write')
    def test_buy_operation(self, mock_write):
        """测试买入操作"""
        # 测试正常买入
        result = self.strategy.buy(4.0, "2024-01-01")
        self.assertTrue(result)
        self.assertEqual(len(self.strategy.trades), 1)
        self.assertEqual(self.strategy.positions, 6000)
        self.assertEqual(self.strategy.cash, 96000)
        
        # 测试价格超出范围的买入
        with patch('streamlit.warning') as mock_warning:
            result = self.strategy.buy(3.8, "2024-01-01")
            self.assertFalse(result)
            self.assertEqual(self.strategy.failed_trades["买入价格超范围"], 1)
            mock_warning.assert_called_once()

    @patch('streamlit.write')
    def test_sell_operation(self, mock_write):
        """测试卖出操作"""
        # 测试正常卖出
        result = self.strategy.sell(4.0, "2024-01-01")
        self.assertTrue(result)
        self.assertEqual(len(self.strategy.trades), 1)
        self.assertEqual(self.strategy.positions, 4000)
        self.assertEqual(self.strategy.cash, 104000)
        
        # 测试价格超出范围的卖出
        with patch('streamlit.warning') as mock_warning:
            result = self.strategy.sell(4.4, "2024-01-01")
            self.assertFalse(result)
            self.assertEqual(self.strategy.failed_trades["卖出价格超范围"], 1)
            mock_warning.assert_called_once()

    @patch('akshare.fund_etf_hist_em')
    @patch('streamlit.write')
    def test_backtest(self, mock_write, mock_hist_data):
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

    @patch('streamlit.write')
    def test_calculate_profit(self, mock_write):
        """测试收益计算"""
        with patch('streamlit.metric') as mock_metric:
            self.strategy.calculate_profit(4.2, verbose=True)
            mock_metric.assert_called()
            self.assertGreater(self.strategy.final_profit_rate, 0)

    @patch('streamlit.write')
    def test_ma_protection_edge_cases(self, mock_write):
        """测试均线保护的边界条件"""
        self.strategy.ma_protection = True
        self.strategy.ma_period = 5
        
        # 测试价格等于均线的情况
        self.assertTrue(self.strategy._check_ma_protection(4.0, 4.0, True))
        self.assertTrue(self.strategy._check_ma_protection(4.0, 4.0, False))

    @patch('streamlit.write')
    def test_trade_failure_recording(self, mock_write):
        """测试交易失败记录"""
        with patch('streamlit.warning') as mock_warning:
            # 测试买入失败记录
            self.strategy.cash = 0  # 设置现金为0
            self.strategy.buy(4.0, '2024-01-01')
            self.assertEqual(self.strategy.failed_trades['现金不足'], 1)
            mock_warning.assert_called()

    @patch('streamlit.write')
    def test_empty_data_handling(self, mock_write):
        """测试空数据处理"""
        with patch('akshare.fund_etf_hist_em') as mock_hist_data:
            # 设置返回空数据
            mock_hist_data.return_value = pd.DataFrame()
            
            # 测试空数据异常
            with self.assertRaises(Exception):
                self.strategy.backtest('2024-01-01', '2024-01-05')

if __name__ == '__main__':
    unittest.main() 