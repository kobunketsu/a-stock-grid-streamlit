import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
from ma_utils import calculate_ma_price

class TestMAUtils(unittest.TestCase):
    """均线工具测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.symbol = "159300"
        self.start_date = datetime(2024, 1, 1)
        self.ma_period = 20
        
        # 生成模拟数据
        dates = pd.date_range(start=self.start_date - timedelta(days=self.ma_period*2), 
                            end=self.start_date, 
                            freq='B')
        
        # 创建模拟价格数据
        self.mock_data = pd.DataFrame({
            '日期': dates,
            '收盘': [10.0 + i*0.1 for i in range(len(dates))],
            '开盘': [10.0 + i*0.1 for i in range(len(dates))],
            '最高': [10.0 + i*0.1 + 0.05 for i in range(len(dates))],
            '最低': [10.0 + i*0.1 - 0.05 for i in range(len(dates))],
            '成交量': [1000000 for _ in range(len(dates))],
            '成交额': [10000000 for _ in range(len(dates))]
        })

    @patch('akshare.fund_etf_hist_em')
    def test_calculate_ma_normal(self, mock_hist_data):
        """测试正常计算均线"""
        mock_hist_data.return_value = self.mock_data
        
        close_price, ma_price = calculate_ma_price(
            self.symbol,
            self.start_date,
            self.ma_period
        )
        
        self.assertIsNotNone(close_price)
        self.assertIsNotNone(ma_price)
        self.assertIsInstance(close_price, float)
        self.assertIsInstance(ma_price, float)

    @patch('akshare.stock_zh_a_hist')
    def test_calculate_ma_stock(self, mock_hist_data):
        """测试股票均线计算"""
        mock_hist_data.return_value = self.mock_data
        
        close_price, ma_price = calculate_ma_price(
            "000001",
            self.start_date,
            self.ma_period,
            security_type="STOCK"
        )
        
        self.assertIsNotNone(close_price)
        self.assertIsNotNone(ma_price)
        mock_hist_data.assert_called_once()

    @patch('akshare.fund_etf_hist_em')
    def test_calculate_ma_empty_data(self, mock_hist_data):
        """测试空数据情况"""
        mock_hist_data.return_value = pd.DataFrame()
        
        close_price, ma_price = calculate_ma_price(
            self.symbol,
            self.start_date,
            self.ma_period
        )
        
        self.assertIsNone(close_price)
        self.assertIsNone(ma_price)

    @patch('akshare.fund_etf_hist_em')
    def test_calculate_ma_different_periods(self, mock_hist_data):
        """测试不同均线周期"""
        mock_hist_data.return_value = self.mock_data
        
        # 测试不同的均线周期
        periods = [5, 10, 20, 30]
        for period in periods:
            close_price, ma_price = calculate_ma_price(
                self.symbol,
                self.start_date,
                period
            )
            
            self.assertIsNotNone(close_price)
            self.assertIsNotNone(ma_price)

    @patch('akshare.fund_etf_hist_em')
    def test_calculate_ma_error_handling(self, mock_hist_data):
        """测试错误处理"""
        # 模拟API异常
        mock_hist_data.side_effect = Exception("API错误")
        
        close_price, ma_price = calculate_ma_price(
            self.symbol,
            self.start_date,
            self.ma_period
        )
        
        self.assertIsNone(close_price)
        self.assertIsNone(ma_price)

if __name__ == '__main__':
    unittest.main() 