import unittest
from unittest.mock import patch, MagicMock, call
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import json
import os
import pandas as pd
from progress_window import ProgressWindow
from stock_grid_optimizer import GridStrategyOptimizer
from trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol

class MockVar:
    """模拟 Tkinter 的 StringVar"""
    def __init__(self, master=None, value=None, name=None):
        self._value = str(value) if value is not None else ""
        self._trace_callbacks = {}
        
    def get(self):
        return self._value
        
    def set(self, value):
        old_value = self._value
        self._value = str(value)
        # 调用所有注册的回调函数
        for mode, callbacks in self._trace_callbacks.items():
            if mode == 'write':
                for callback in callbacks:
                    callback()
    
    def trace_add(self, mode, callback):
        """添加变量跟踪回调函数"""
        if mode not in self._trace_callbacks:
            self._trace_callbacks[mode] = []
        self._trace_callbacks[mode].append(callback)
    
    def trace_remove(self, mode, callback):
        """移除变量跟踪回调函数"""
        if mode in self._trace_callbacks:
            try:
                self._trace_callbacks[mode].remove(callback)
            except ValueError:
                pass

class MockBooleanVar:
    """模拟 Tkinter 的 BooleanVar"""
    def __init__(self, master=None, value=None, name=None):
        self._value = bool(value) if value is not None else False
        self._trace_callbacks = {}
        
    def get(self):
        return self._value
        
    def set(self, value):
        old_value = self._value
        self._value = bool(value)
        # 调用所有注册的回调函数
        for mode, callbacks in self._trace_callbacks.items():
            if mode == 'write':
                for callback in callbacks:
                    callback()
    
    def trace_add(self, mode, callback):
        """添加变量跟踪回调函数"""
        if mode not in self._trace_callbacks:
            self._trace_callbacks[mode] = []
        self._trace_callbacks[mode].append(callback)
    
    def trace_remove(self, mode, callback):
        """移除变量跟踪回调函数"""
        if mode in self._trace_callbacks:
            try:
                self._trace_callbacks[mode].remove(callback)
            except ValueError:
                pass

@patch('tkinter.StringVar', MockVar)
@patch('tkinter.BooleanVar', MockBooleanVar)  # 使用新的MockBooleanVar
class TestProgressWindow(unittest.TestCase):
    """Tkinter版本进度窗口测试类"""
    
    @patch('tkinter.Tk')
    @patch('tkinter.ttk.Progressbar')
    @patch('tkinter.ttk.Label')
    @patch('tkinter.scrolledtext.ScrolledText')
    @patch('trading_utils.get_symbol_info')
    @patch('trading_utils.calculate_price_range')
    @patch('json.load')
    @patch('json.dump')
    @patch('builtins.open')
    def setUp(self, mock_open, mock_dump, mock_load, mock_price_range, mock_symbol_info, 
             mock_text, mock_label, mock_progressbar, mock_tk):
        """测试前的准备工作"""
        # 模拟配置文件
        mock_load.return_value = {
            "symbol": "159300",
            "symbol_name": "沪深300ETF",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "ma_period": "55",
            "ma_protection": True,
            "initial_positions": "5000",
            "initial_cash": "100000",
            "min_buy_times": "2",
            "price_range_min": "3.9",
            "price_range_max": "4.3",
            "n_trials": "100",
            "top_n": "5",
            "profit_calc_method": "mean",
            "connect_segments": False
        }
        
        # 模拟证券信息
        mock_symbol_info.return_value = ("沪深300ETF", "ETF")
        
        # 模拟价格范围
        mock_price_range.return_value = (3.9, 4.3)
        
        # 模拟Tk窗口和组件
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        
        # 模拟ScrolledText
        mock_text_instance = MagicMock()
        mock_text.return_value = mock_text_instance
        mock_text_instance.get.return_value = ""
        
        # 创建进度窗口实例
        self.progress_window = ProgressWindow(total_trials=100)
        
        # 设置root窗口
        self.progress_window.root = mock_root
        
        # 保存mock对象以供测试使用
        self.mock_root = mock_root
        self.mock_text = mock_text_instance
        self.mock_symbol_info = mock_symbol_info
        self.mock_price_range = mock_price_range
        self.mock_dump = mock_dump
        self.mock_load = mock_load
        self.mock_open = mock_open
        
        # 初始化所有Tkinter变量
        self.progress_window.symbol_var = MockVar(value="159300")
        self.progress_window.symbol_name_var = MockVar(value="沪深300ETF")
        self.progress_window.start_date_var = MockVar(value="2024-10-10")
        self.progress_window.end_date_var = MockVar(value="2024-12-20")
        self.progress_window.ma_period_var = MockVar(value="55")
        self.progress_window.ma_protection_var = MockBooleanVar(value=True)  # 使用MockBooleanVar
        self.progress_window.initial_positions_var = MockVar(value="0")
        self.progress_window.initial_cash_var = MockVar(value="100000")
        self.progress_window.min_buy_times_var = MockVar(value="2")
        self.progress_window.price_range_min_var = MockVar(value="3.9")
        self.progress_window.price_range_max_var = MockVar(value="4.3")
        self.progress_window.n_trials_var = MockVar(value="100")
        self.progress_window.top_n_var = MockVar(value="5")
        self.progress_window.profit_calc_method_var = MockVar(value="mean")
        self.progress_window.connect_segments_var = MockBooleanVar(value=False)  # 使用MockBooleanVar
        self.progress_window.enable_segments = MockBooleanVar(value=False)  # 使用MockBooleanVar
        self.progress_window.search_var = MockVar(value="")
        self.progress_window.segment_mode = MockVar(value="平均值")
        
        # 创建窗口
        with patch('tkinter.StringVar', MockVar), patch('tkinter.BooleanVar', MockBooleanVar):
            self.progress_window.create_window()
        
        # 重新设置变量的值
        self.progress_window.symbol_var.set("159300")
        self.progress_window.symbol_name_var.set("沪深300ETF")
        self.progress_window.start_date_var.set("2024-10-10")
        self.progress_window.end_date_var.set("2024-12-20")
        self.progress_window.ma_period_var.set("55")
        self.progress_window.ma_protection_var.set(True)
        self.progress_window.initial_positions_var.set("0")
        self.progress_window.initial_cash_var.set("100000")
        self.progress_window.min_buy_times_var.set("2")
        self.progress_window.price_range_min_var.set("3.9")
        self.progress_window.price_range_max_var.set("4.3")
        self.progress_window.n_trials_var.set("100")
        self.progress_window.top_n_var.set("5")
        self.progress_window.profit_calc_method_var.set("mean")
        self.progress_window.connect_segments_var.set(False)
        self.progress_window.enable_segments.set(False)
        self.progress_window.search_var.set("")
        
        # 验证变量初始化
        self.assertEqual(self.progress_window.symbol_var.get(), "159300")
        self.assertEqual(self.progress_window.symbol_name_var.get(), "沪深300ETF")
        self.assertEqual(self.progress_window.start_date_var.get(), "2024-10-10")
        self.assertEqual(self.progress_window.end_date_var.get(), "2024-12-20")
        self.assertEqual(self.progress_window.ma_period_var.get(), "55")
        self.assertEqual(self.progress_window.ma_protection_var.get(), True)
        self.assertEqual(self.progress_window.initial_positions_var.get(), "0")
        self.assertEqual(self.progress_window.initial_cash_var.get(), "100000")
        self.assertEqual(self.progress_window.min_buy_times_var.get(), "2")
        self.assertEqual(self.progress_window.price_range_min_var.get(), "3.9")
        self.assertEqual(self.progress_window.price_range_max_var.get(), "4.3")
        self.assertEqual(self.progress_window.n_trials_var.get(), "100")
        self.assertEqual(self.progress_window.top_n_var.get(), "5")
        self.assertEqual(self.progress_window.profit_calc_method_var.get(), "mean")
        self.assertEqual(self.progress_window.connect_segments_var.get(), False)
        self.assertEqual(self.progress_window.enable_segments.get(), False)
        self.assertEqual(self.progress_window.search_var.get(), "")
    
    def tearDown(self):
        """测试后的清理工作"""
        if hasattr(self, 'progress_window'):
            self.progress_window.is_closed = True
            if hasattr(self.progress_window, 'root') and self.progress_window.root:
                try:
                    self.progress_window.root.destroy()
                except Exception:
                    pass  # 忽略销毁失败的错误
    
    @patch('tkinter.messagebox.showerror')
    def test_initialization(self, mock_error):
        """测试窗口初始化"""
        # 验证基本属性
        self.assertEqual(self.progress_window.total_trials, 100)
        self.assertFalse(self.progress_window.is_closed)
        self.assertIsNone(self.progress_window.start_time)
        
        # 验证变量初始化
        self.assertEqual(self.progress_window.symbol_var.get(), "159300")
        self.assertEqual(self.progress_window.initial_cash_var.get(), "100000")
        
        # 验证错误处理
        self.progress_window.symbol_var.set("")
        self.progress_window.update_symbol_info()
        mock_error.assert_not_called()
    
    @patch('tkinter.messagebox.showerror')
    def test_error_handling(self, mock_error):
        """测试错误处理"""
        # 测试API错误
        self.mock_symbol_info.side_effect = Exception("API错误")
        # 模拟 messagebox.showerror 的调用
        mock_error.side_effect = lambda title, message: None
        # 模拟 print 函数，因为目标代码使用 print 而不是 messagebox
        with patch('builtins.print') as mock_print:
            self.progress_window.update_symbol_info('code')
            # 验证是否调用了 print
            mock_print.assert_called()
        mock_error.reset_mock()
        
        # 测试配置文件错误
        self.mock_open.side_effect = Exception("文件错误")
        self.progress_window.load_config()  # 应该不会抛出异常
        
        # 测试无效的进度更新
        self.progress_window.is_closed = True
        self.progress_window.update_progress(-1)  # 应该不会抛出异常
    
    def test_config_file_operations(self):
        """测试配置文件操作"""
        # 模拟配置文件不存在的情况
        self.mock_open.side_effect = FileNotFoundError
        self.progress_window.load_config()
        # 验证使用了默认值
        self.assertEqual(self.progress_window.symbol_var.get(), "159300")
        
        # 模拟配置文件损坏的情况
        self.mock_open.side_effect = None
        self.mock_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        self.progress_window.load_config()
        # 验证使用了默认值
        self.assertEqual(self.progress_window.symbol_var.get(), "159300")
        
        # 模拟保存配置文件失败的情况
        self.mock_dump.side_effect = Exception("保存失败")
        self.progress_window.save_config()  # 应该不会抛出异常
    
    def test_validate_symbol(self):
        """测试证券代码验证"""
        # 测试空证券代码
        self.progress_window.symbol_var.set("")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "请输入证券代码")
        
        # 测试无效的证券代码
        self.progress_window.error_message = None
        self.progress_window.symbol_var.set("invalid")
        self.mock_symbol_info.return_value = (None, "ETF")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "请输入有效的证券代码")
    
    def test_validate_date(self):
        """测试日期格式验证"""
        # 设置有效的证券代码
        self.mock_symbol_info.return_value = ("沪深300ETF", "ETF")
        self.progress_window.symbol_var.set("159300")
        
        # 测试无效的日期格式
        self.progress_window.error_message = None
        self.progress_window.start_date_var.set("invalid-date")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "日期格式无效")
    
    def test_validate_initial_cash(self):
        """测试初始资金验证"""
        # 设置基本有效参数
        self._set_valid_basic_params()
        
        # 测试负数初始资金
        self.progress_window.error_message = None
        self.progress_window.initial_cash_var.set("-1000")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "initial_cash must be greater than or equal to 0")
        
        # 测试初始资金为0（应该是有效的）
        self.progress_window.error_message = None
        self.progress_window.initial_cash_var.set("0")
        self.progress_window.start_optimization()
        self.assertIsNone(self.progress_window.error_message)
    
    def test_validate_min_buy_times(self):
        """测试最小买入次数验证"""
        # 设置基本有效参数
        self._set_valid_basic_params()
        
        # 确保优化未在运行
        self.progress_window.optimization_running = False
        
        # 测试无效的最小买入次数（0）
        self.progress_window.error_message = None
        self.progress_window.min_buy_times_var.set("0")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "min_buy_times must be greater than 0")
        
        # 测试无效的最小买入次数（负数）
        self.progress_window.error_message = None
        self.progress_window.min_buy_times_var.set("-1")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "min_buy_times must be greater than 0")
        
        # 测试有效的最小买入次数
        self.progress_window.error_message = None
        self.progress_window.min_buy_times_var.set("1")
        self.progress_window.start_optimization()
        self.assertIsNone(self.progress_window.error_message)
    
    def test_validate_price_range(self):
        """测试价格区间验证"""
        # 设置基本有效参数
        self._set_valid_basic_params()
        
        # 测试无效的价格区间
        self.progress_window.error_message = None
        self.progress_window.price_range_min_var.set("4.3")
        self.progress_window.price_range_max_var.set("3.9")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "price_range_min must be less than price_range_max")
    
    def test_validate_n_trials(self):
        """测试优化次数验证"""
        # 设置基本有效参数
        self._set_valid_basic_params()
        
        # 测试无效的试验次数
        self.progress_window.error_message = None
        self.progress_window.n_trials_var.set("-1")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "n_trials must be greater than 0")
    
    def test_validate_top_n(self):
        """测试显示结果数量验证"""
        # 设置基本有效参数
        self._set_valid_basic_params()
        
        # 测试无效的 top_n
        self.progress_window.error_message = None
        self.progress_window.top_n_var.set("-1")
        self.progress_window.start_optimization()
        self.assertEqual(self.progress_window.error_message, "top_n must be greater than 0")
    
    def _set_valid_basic_params(self):
        """设置基本的有效参数，用于参数验证测试"""
        # 设置有效的证券代码
        self.mock_symbol_info.return_value = ("沪深300ETF", "ETF")
        self.progress_window.symbol_var.set("159300")
        
        # 设置有效的日期
        self.progress_window.start_date_var.set("2024-10-10")
        self.progress_window.end_date_var.set("2024-12-20")
        
        # 设置其他基本参数
        self.progress_window.ma_period_var.set("55")
        self.progress_window.initial_positions_var.set("0")
        self.progress_window.initial_cash_var.set("100000")
        self.progress_window.min_buy_times_var.set("2")
        self.progress_window.price_range_min_var.set("3.9")
        self.progress_window.price_range_max_var.set("4.3")
        self.progress_window.n_trials_var.set("100")
        self.progress_window.top_n_var.set("5")
    
    def test_trade_details_display(self):
        """测试交易详情显示"""
        # 模拟交易详情数据
        class MockTrial:
            def __init__(self):
                self.params = {
                    'up_sell_rate': 0.01,
                    'up_callback_rate': 0.003,
                    'down_buy_rate': 0.01,
                    'down_rebound_rate': 0.003,
                    'shares_per_trade': 1000
                }
                self.value = -10.5  # 负的收益率
                self.user_attrs = {
                    'trade_count': 50,
                    'segment_results': [
                        {
                            'start_date': '2024-01-01',
                            'end_date': '2024-01-10',
                            'profit_rate': 5.2,
                            'trades': 25,
                            'failed_trades': {'买入价格超范围': 2}
                        }
                    ]
                }
        
        # 显示交易详情
        self.progress_window.show_trade_details(MockTrial())
        
        # 验证调用
        self.mock_text.config.assert_called()
        self.mock_text.delete.assert_called_with('1.0', tk.END)
    
    def test_segment_options(self):
        """测试分段回测选项"""
        # 启用分段回测
        self.progress_window.enable_segments.set(True)
        self.progress_window.toggle_segment_options()
        
        # 禁用分段回测
        self.progress_window.enable_segments.set(False)
        self.progress_window.toggle_segment_options()
    
    @patch('json.dump')
    def test_window_closing(self, mock_dump):
        """测试窗口关闭"""
        self.progress_window._on_closing()
        self.assertTrue(self.progress_window.is_closed)
        mock_dump.assert_called()
    
    def test_progress_update(self):
        """测试进度更新"""
        # 设置开始时间
        self.progress_window.start_time = datetime.now() - timedelta(minutes=5)
        
        # 更新进度
        self.progress_window.update_progress(50)
        
        # 验证进度更新
        self.assertEqual(self.progress_window.current_trial, 50)
    
    def test_optimization_control(self):
        """测试优化控制功能"""
        # 测试开始优化
        self.progress_window.optimization_running = False
        with patch.object(self.progress_window, 'start_optimization'):
            self.progress_window.toggle_optimization()
            self.assertTrue(self.progress_window.optimization_running)
        
        # 测试取消优化
        self.progress_window.toggle_optimization()
        self.assertFalse(self.progress_window.optimization_running)
    
    @patch('json.dump')
    def test_config_management(self, mock_dump):
        """测试配置管理"""
        # 测试保存配置
        test_config = {
            "symbol": "159300",
            "initial_cash": "100000",
            "ma_protection": True
        }
        
        # 设置初始值
        self.progress_window.symbol_var.set("159300")
        self.progress_window.initial_cash_var.set("100000")
        self.progress_window.ma_protection_var.set(True)
        
        self.progress_window.save_config()
        mock_dump.assert_called()

if __name__ == '__main__':
    unittest.main() 