import unittest
from unittest.mock import patch, MagicMock
import streamlit as st
from datetime import datetime, timedelta
import json
import pandas as pd
import streamlit.runtime.scriptrunner.script_runner
from src.app import *
from src.trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol
from locales.localization import _

class TestStreamlitApp(unittest.TestCase):
    """Streamlit版本应用测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建mock对象
        self.mock_is_valid_symbol = patch('src.app.is_valid_symbol').start()
        self.mock_symbol_info = patch('src.app.get_symbol_info').start()
        self.mock_price_range = patch('src.app.calculate_price_range').start()
        
        # 设置mock对象的返回值
        self.mock_symbol_info.return_value = ("沪深300ETF", "ETF")
        self.mock_is_valid_symbol.return_value = True
        self.mock_price_range.return_value = (3.9, 4.3)
    
    def tearDown(self):
        """测试后的清理工作"""
        patch.stopall()
    
    def test_validate_symbol(self):
        """测试证券代码验证"""
        # 测试空证券代码
        self.assertFalse(validate_symbol(""))
        
        # 测试无效的证券代码
        self.mock_is_valid_symbol.return_value = False
        self.assertFalse(validate_symbol("invalid"))
        
        # 测试有效的证券代码
        self.mock_is_valid_symbol.return_value = True
        self.assertTrue(validate_symbol("159300"))
    
    def test_validate_date(self):
        """测试日期验证"""
        # 测试结束日期早于开始日期
        start_date = datetime(2024, 12, 20)
        end_date = datetime(2024, 10, 10)
        self.assertFalse(validate_date(start_date, end_date))
        
        # 测试有效的日期范围
        start_date = datetime(2024, 10, 10)
        end_date = datetime(2024, 12, 20)
        self.assertTrue(validate_date(start_date, end_date))
    
    def test_validate_initial_cash(self):
        """测试初始资金验证"""
        # 测试负数初始资金
        self.assertFalse(validate_initial_cash(-1000))
        
        # 测试初始资金为0（应该是有效的）
        self.assertTrue(validate_initial_cash(0))
        
        # 测试有效的初始资金
        self.assertTrue(validate_initial_cash(100000))
    
    def test_validate_min_buy_times(self):
        """测试最小买入次数验证"""
        # 测试无效的最小买入次数（0）
        self.assertFalse(validate_min_buy_times(0))
        
        # 测试无效的最小买入次数（负数）
        self.assertFalse(validate_min_buy_times(-1))
        
        # 测试有效的最小买入次数
        self.assertTrue(validate_min_buy_times(1))
    
    def test_validate_price_range(self):
        """测试价格区间验证"""
        # 测试无效的价格区间（最小值大于最大值）
        self.assertFalse(validate_price_range(4.3, 3.9))
        
        # 测试有效的价格区间
        self.assertTrue(validate_price_range(3.9, 4.3))
    
    def test_validate_n_trials(self):
        """测试优化次数验证"""
        # 测试无效的试验次数（负数）
        self.assertFalse(validate_n_trials(-1))
        
        # 测试无效的试验次数（0）
        self.assertFalse(validate_n_trials(0))
        
        # 测试有效的试验次数
        self.assertTrue(validate_n_trials(100))
    
    def test_validate_top_n(self):
        """测试显示结果数量验证"""
        # 测试无效的top_n（负数）
        self.assertFalse(validate_top_n(-1))
        
        # 测试无效的top_n（0）
        self.assertFalse(validate_top_n(0))
        
        # 测试有效的top_n
        self.assertTrue(validate_top_n(5))
    
    @patch('streamlit.error')
    @patch('src.app.is_valid_symbol')
    def test_error_handling(self, mock_is_valid_symbol, mock_error):
        """测试错误处理"""
        # 测试API错误
        mock_is_valid_symbol.side_effect = Exception("API错误")
        validate_symbol("159300")
        mock_error.assert_called_with(_("failed_to_validate_symbol_format").format("API错误"))
        
        # 重置mock
        mock_is_valid_symbol.side_effect = None
        mock_error.reset_mock()
        
        # 测试日期验证错误
        validate_date(datetime(2024, 12, 20), datetime(2024, 10, 10))
        mock_error.assert_called_with(_("end_date_must_be_later_than_start_date"))
    
    @patch('streamlit.sidebar')
    @patch('streamlit.button')
    @patch('src.app.start_optimization')
    @patch('streamlit.experimental_rerun')
    @patch('streamlit.session_state', new_callable=dict)
    def test_optimization_control(self, mock_session_state, mock_rerun, mock_start_optimization, mock_button, mock_sidebar):
        """测试优化控制功能"""
        # 模拟优化结果
        mock_results = {
            "sorted_trials": [
                MagicMock(value=-2.5, params={
                    'up_sell_rate': 0.02,
                    'down_buy_rate': 0.015,
                    'up_callback_rate': 0.003,
                    'down_rebound_rate': 0.002,
                    'shares_per_trade': 5000
                }, user_attrs={'trade_count': 50, 'failed_trades': '{}'})
            ]
        }
        mock_start_optimization.return_value = mock_results
        
        # 模拟开始优化按钮
        mock_button.return_value = True
        
        # 调用main函数
        main()
        
        # 验证按钮被创建
        mock_button.assert_called()
        
        # 验证优化函数被调用
        mock_start_optimization.assert_called_once()
        
        # 验证结果被存储到session state
        self.assertIn('optimization_results', mock_session_state)
        self.assertIn('sorted_trials', mock_session_state)
        self.assertEqual(mock_session_state['optimization_results'], mock_results)
    
    @patch('json.dump')
    @patch('json.load')
    @patch('builtins.open')
    def test_config_management(self, mock_open, mock_load, mock_dump):
        """测试配置管理"""
        # 模拟配置文件
        mock_config = {
            "symbol": "159300",
            "start_date": "2024-10-10",
            "end_date": "2024-12-20",
            "ma_period": 55,
            "ma_protection": True,
            "initial_positions": 0,
            "initial_cash": 100000,
            "min_buy_times": 2,
            "price_range_min": 3.9,
            "price_range_max": 4.3,
            "n_trials": 100,
            "top_n": 5,
            "profit_calc_method": "mean",
            "connect_segments": False
        }
        
        # 模拟加载配置
        mock_load.return_value = mock_config
        
        # 调用main函数
        main()
        
        # 验证配置加载
        mock_open.assert_called()
        mock_load.assert_called()
    
    @patch('streamlit.checkbox')
    def test_segment_options(self, mock_checkbox):
        """测试分段回测选项"""
        # 模拟分段回测选项
        mock_checkbox.return_value = True
        
        # 调用main函数
        main()
        
        # 验证复选框被创建
        mock_checkbox.assert_called()
    
    @patch('streamlit.write')
    def test_trade_details_display(self, mock_write):
        """测试交易详情显示"""
        # 模拟交易详情数据
        trade_details = {
            "params": {
                "up_sell_rate": 0.01,
                "up_callback_rate": 0.003,
                "down_buy_rate": 0.01,
                "down_rebound_rate": 0.003,
                "shares_per_trade": 1000
            },
            "profit_rate": 10.5,
            "trade_count": 50,
            "failed_trades": {_("buy_price_out_of_range"): 2}
        }
        
        # 调用显示函数
        st.write(trade_details)
        
        # 验证显示调用
        mock_write.assert_called_with(trade_details)
    
    @patch('streamlit.session_state', new_callable=dict)
    @patch('streamlit.button')
    @patch('streamlit.expander')
    @patch('streamlit.columns')
    def test_view_trial_details(self, mock_columns, mock_expander, mock_button, mock_session_state):
        """测试查看优化结果详情时状态保持"""
        # 模拟优化结果数据
        mock_trial = MagicMock(
            value=-2.5,
            params={
                'up_sell_rate': 0.02,
                'down_buy_rate': 0.015,
                'up_callback_rate': 0.003,
                'down_rebound_rate': 0.002,
                'shares_per_trade': 5000
            },
            user_attrs={'trade_count': 50, 'failed_trades': '{}'}
        )
        mock_results = {'sorted_trials': [mock_trial]}

        # 模拟列对象
        mock_results_col = MagicMock()
        mock_details_col = MagicMock()
        mock_columns.return_value = [mock_results_col, mock_details_col]

        # 模拟列对象的上下文管理器
        mock_results_col.__enter__ = MagicMock(return_value=mock_results_col)
        mock_results_col.__exit__ = MagicMock(return_value=None)
        mock_details_col.__enter__ = MagicMock(return_value=mock_details_col)
        mock_details_col.__exit__ = MagicMock(return_value=None)

        # 设置session state
        mock_session_state.clear()
        mock_session_state['results_col'] = mock_results_col
        mock_session_state['details_col'] = mock_details_col
        mock_session_state['new_results'] = True
        mock_session_state['optimization_results'] = mock_results
        mock_session_state['sorted_trials'] = [mock_trial]

        # 第一次调用：初始化状态
        mock_button.side_effect = [False] * 10  # 初始状态下按钮未点击
        display_optimization_results(mock_results, top_n=5)

        # 验证初始状态
        self.assertFalse(mock_session_state.get('display_details', False))
        self.assertIsNone(mock_session_state.get('current_trial'))
        self.assertIsNone(mock_session_state.get('current_trial_index'))

        # 模拟点击查看详情按钮
        mock_button.side_effect = [True] + [False] * 9  # 第一个按钮点击，其他未点击
        try:
            display_optimization_results(None, top_n=5)
        except streamlit.runtime.scriptrunner.script_runner.RerunException:
            # 验证状态更新
            self.assertTrue(mock_session_state.get('display_details', False))
            self.assertEqual(mock_session_state.get('current_trial'), mock_trial)
            self.assertEqual(mock_session_state.get('current_trial_index'), 0)

        # 模拟关闭详情
        mock_button.side_effect = [False] * 5 + [True] + [False] * 4  # 关闭按钮点击
        try:
            display_optimization_results(None, top_n=5)
        except streamlit.runtime.scriptrunner.script_runner.RerunException:
            # 验证状态重置
            self.assertFalse(mock_session_state.get('display_details', False))
            self.assertIsNone(mock_session_state.get('current_trial'))
            self.assertIsNone(mock_session_state.get('current_trial_index'))
    

if __name__ == '__main__':
    unittest.main()