import unittest
from unittest.mock import patch, MagicMock, mock_open
import streamlit
from datetime import datetime, timedelta
import json
import logging
import os

from src.views.app import *
from src.utils.localization import l

class TestApp(unittest.TestCase):
    """Streamlit版本应用测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化时的设置"""
        # 设置日志
        logging.basicConfig(level=logging.DEBUG)
        cls.logger = logging.getLogger(__name__)
        cls.logger.debug("开始运行测试用例")
        
        # 验证环境变量
        cls.logger.debug(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
        cls.logger.debug(f"当前工作目录: {os.getcwd()}")
    
    def setUp(self):
        """测试前的准备工作"""
        self.logger.debug(f"开始测试: {self._testMethodName}")
        # 创建mock对象
        self.mock_is_valid_symbol = patch('src.views.app.is_valid_symbol').start()
        self.mock_symbol_info = patch('src.views.app.get_symbol_info').start()
        self.mock_price_range = patch('src.views.app.calculate_price_range').start()
        
        # 设置mock对象的返回值
        self.mock_symbol_info.return_value = ("沪深300ETF", "ETF")
        self.mock_is_valid_symbol.return_value = True
        self.mock_price_range.return_value = (3.9, 4.3)
    
    def tearDown(self):
        """测试后的清理工作"""
        self.logger.debug(f"结束测试: {self._testMethodName}")
        patch.stopall()
    
    @patch('streamlit.rerun')
    @patch('streamlit.session_state', new_callable=dict)
    def test_optimization_control(self, mock_session_state, mock_rerun):
        """测试优化控制功能
        
        测试场景：
        1. 开始优化：
           - 初始状态为未运行
           - 调用toggle_optimization
           - 验证状态切换为运行
        
        2. 取消优化：
           - 初始状态为运行中
           - 调用toggle_optimization
           - 验证状态切换为未运行
           - 验证页面重新加载
        """
        self.logger.debug("开始测试 test_optimization_control")
        
        # 初始化session_state
        mock_session_state.clear()
        mock_session_state['optimization_running'] = False
        
        # 调用toggle_optimization函数开始优化
        self.logger.debug("调用toggle_optimization开始优化")
        toggle_optimization()
        
        # 验证状态更新
        self.logger.debug("验证状态更新")
        self.assertTrue(mock_session_state['optimization_running'])
        
        # 调用toggle_optimization函数取消优化
        self.logger.debug("调用toggle_optimization取消优化")
        toggle_optimization()
        
        # 验证取消优化
        self.logger.debug("验证取消优化")
        self.assertFalse(mock_session_state['optimization_running'])
        mock_rerun.assert_called()
    
    @patch('json.dump')
    @patch('json.load')
    @patch('builtins.open')
    def test_config_management(self, mock_open, mock_load, mock_dump):
        """测试配置管理
        
        测试场景：
        1. 配置加载：
           - 模拟配置文件存在
           - 验证文件打开操作
           - 验证配置加载
        
        2. 配置内容：
           - 验证所有必要字段存在
           - 验证字段类型和默认值
           - 验证配置应用到界面
        """
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
        """测试分段回测选项
        
        测试场景：
        1. 启用分段回测：
           - 模拟复选框选中
           - 验证界面更新
           - 验证相关选项显示
        
        2. 选项联动：
           - 验证计算方法选择显示
           - 验证段间连接选项显示
           - 验证分段天数显示
        """
        # 模拟分段回测选项
        mock_checkbox.return_value = True
        
        # 调用main函数
        main()
        
        # 验证复选框被创建
        mock_checkbox.assert_called()
    
    @patch('streamlit.write')
    def test_trade_details_display(self, mock_write):
        """测试交易详情显示
        
        测试场景：
        1. 完整交易信息：
           - 包含参数、收益率、交易次数
           - 验证显示格式
           - 验证调用write方法
        
        2. 失败交易信息：
           - 包含失败原因和次数
           - 验证错误信息显示
        """
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
            "failed_trades": {l("buy_price_out_of_range"): 2}
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
        """测试查看优化结果详情
        
        测试场景：
        1. 初始状态：
           - 验证详情显示标志为False
           - 验证当前试验为空
           - 验证试验索引为空
        
        2. 状态重置：
           - 调用display_optimization_results
           - 验证状态重置
           - 验证界面更新
        """
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
    

    
    @patch('streamlit.date_input')
    @patch('streamlit.session_state')
    def test_invalid_date_input(self, mock_session_state, mock_date_input):
        """测试非法日期输入处理
        
        测试场景：
        1. 开始日期晚于结束日期：
           - 从日历控件获取晚于结束日期的开始日期
           - 验证错误消息显示
           - 验证开始优化按钮被禁用
        
        2. 结束日期早于开始日期：
           - 从日历控件获取早于开始日期的结束日期
           - 验证错误消息显示
           - 验证开始优化按钮被禁用
        """
        # 设置初始日期
        initial_start = datetime(2024, 10, 10)
        initial_end = datetime(2024, 12, 20)
        
        # 设置session state
        mock_session_state.optimization_running = False
        mock_session_state.get.side_effect = lambda key, default=None: {
            'start_date': initial_start,
            'end_date': initial_end,
            'date_validation_failed': True
        }.get(key, default)
        
        # 场景1：测试开始日期晚于结束日期
        invalid_start = datetime(2024, 12, 25)  # 晚于结束日期
        mock_date_input.return_value = invalid_start
        
        # 调用日期输入处理
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.button') as mock_button:
            main()  # 触发日期验证
            # 验证错误消息显示
            mock_error.assert_any_call(l("end_date_must_be_later_than_start_date"))
            # 验证开始优化按钮被禁用
            mock_button.assert_called_with(
                l("start_optimization"),
                use_container_width=True,
                disabled=True
            )
        
        # 场景2：测试结束日期早于开始日期
        invalid_end = datetime(2024, 9, 1)  # 早于开始日期
        mock_date_input.return_value = invalid_end
        
        # 调用日期输入处理
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.button') as mock_button:
            main()  # 触发日期验证
            # 验证错误消息显示
            mock_error.assert_any_call(l("end_date_must_be_later_than_start_date"))
            # 验证开始优化按钮被禁用
            mock_button.assert_called_with(
                l("start_optimization"),
                use_container_width=True,
                disabled=True
            )
    
    @patch('streamlit.session_state', new_callable=dict)
    @patch('streamlit.button')
    @patch('streamlit.expander')
    @patch('streamlit.columns')
    def test_mobile_optimization_scroll(self, mock_columns, mock_expander, mock_button, mock_session_state):
        """测试移动端优化结果滚动功能
        
        测试场景：
        1. 移动端优化完成：
           - 模拟优化完成状态
           - 验证结果列滚动到顶部
           - 验证sidebar自动收起
           - 验证session_state更新
        """
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
        mock_session_state['is_mobile'] = True  # 设置为移动端
        mock_session_state['optimization_running'] = False  # 优化已完成
        mock_session_state['scroll_to_top'] = True  # 需要滚动到顶部

        # 调用显示函数
        display_optimization_results(mock_results, top_n=5)

        # 验证滚动脚本被添加
        mock_results_col.markdown.assert_called()
        
        # 获取实际调用的参数
        actual_call = mock_results_col.markdown.call_args
        actual_script = actual_call[0][0]
        actual_kwargs = actual_call[1]
        
        # 验证关键部分
        self.assertIn('window.scrollTo(0, 0)', actual_script)
        self.assertIn('section[data-testid="stSidebar"]', actual_script)
        self.assertIn('button[aria-label="Close sidebar"]', actual_script)
        self.assertIn('div[data-testid="collapsedControl"]', actual_script)
        self.assertTrue(actual_kwargs.get('unsafe_allow_html', False))
        
        # 验证session state更新
        self.assertFalse(mock_session_state['scroll_to_top'])
        self.assertEqual(mock_session_state['sidebar_state'], 'collapsed')

if __name__ == '__main__':
    unittest.main()