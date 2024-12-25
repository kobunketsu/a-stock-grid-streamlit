import unittest
from unittest.mock import patch
import pandas as pd
from datetime import datetime, timedelta
from src.grid_strategy import GridStrategy

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
// ... existing code ... 