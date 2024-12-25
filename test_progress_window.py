import unittest
from unittest.mock import patch, MagicMock, call
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import json
import os
import pandas as pd
from progress_window import ProgressWindow

class TestProgressWindow(unittest.TestCase):
    """Tkinter版本进度窗口测试类"""
    
    @patch('akshare.fund_etf_spot_em')
    def setUp(self, mock_etf_api):
        """测试前的准备工作"""
        # 模拟ETF数据
        mock_etf_api.return_value = pd.DataFrame({
            '代码': ['159300'],
            '名称': ['沪深300ETF']
        })
        
        self.progress_window = ProgressWindow(total_trials=100)
        self.progress_window.create_window()
        
    def tearDown(self):
        """测试后的清理工作"""
        try:
            if hasattr(self, 'progress_window') and self.progress_window.root:
                self.progress_window.root.destroy()
        except Exception:
            pass
    
    def test_initialization(self):
        """测试窗口初始化"""
        # 验证基本属性
        self.assertEqual(self.progress_window.total_trials, 100)
        self.assertFalse(self.progress_window.is_closed)
        self.assertIsNone(self.progress_window.start_time)
        
        # 验证UI组件
        self.assertIsInstance(self.progress_window.root, tk.Tk)
        self.assertIsInstance(self.progress_window.progress, ttk.Progressbar)
        self.assertIsInstance(self.progress_window.label, ttk.Label)
        self.assertEqual(self.progress_window.label["text"], "等待开始...")
        
        # 验证变量初始化
        self.assertIsInstance(self.progress_window.symbol_var, tk.StringVar)
        self.assertEqual(self.progress_window.symbol_var.get(), "159300")
        self.assertIsInstance(self.progress_window.initial_cash_var, tk.StringVar)
        self.assertEqual(self.progress_window.initial_cash_var.get(), "100000")
    
    def test_parameter_validation(self):
        """测试参数验证"""
        # 测试空证券代码
        self.progress_window.symbol_var.set("")
        with patch('tkinter.messagebox.showerror') as mock_error:
            self.progress_window.start_optimization()
            mock_error.assert_called_with("参数错误", "请输入证券代码")
        
        # 测试无效的日期格式
        self.progress_window.symbol_var.set("159300")
        self.progress_window.start_date_var.set("invalid-date")
        with patch('tkinter.messagebox.showerror') as mock_error:
            # 创建一个模拟的Entry组件
            mock_entry = MagicMock()
            mock_entry.get.return_value = "invalid-date"
            self.progress_window.validate_date(mock_entry)
            mock_error.assert_called_with("输入错误", "无效的日期格式")
        
        # 测试无效的初始资金
        self.progress_window.symbol_var.set("159300")
        self.progress_window.start_date_var.set("2024-01-01")
        self.progress_window.end_date_var.set("2024-12-31")
        self.progress_window.initial_cash_var.set("-1000")
        with patch('tkinter.messagebox.showerror') as mock_error:
            with patch('datetime.datetime.strptime', return_value=datetime.now()):
                self.progress_window.start_optimization()
                mock_error.assert_called_with("参数错误", "初始资金必须大于0")
        
        # 测试无效的最大回撤
        self.progress_window.initial_cash_var.set("100000")
        self.progress_window.max_drawdown_var.set("150")
        with patch('tkinter.messagebox.showerror') as mock_error:
            with patch('datetime.datetime.strptime', return_value=datetime.now()):
                self.progress_window.start_optimization()
                mock_error.assert_called_with("参数错误", "最大回撤必须在0-100之间")
    
    def test_progress_update(self):
        """测试进度更新"""
        # 设置开始时间
        self.progress_window.start_time = datetime.now() - timedelta(minutes=5)
        
        # 更新进度
        self.progress_window.update_progress(50)
        
        # 验证进度更新
        self.assertEqual(self.progress_window.current_trial, 50)
        
        # 验证标签文本更新
        self.assertIn("耗时:", self.progress_window.time_label["text"])
        self.assertIn("预计剩余:", self.progress_window.eta_label["text"])
        self.assertIn("%", self.progress_window.percent_label["text"])
    
    def test_optimization_control(self):
        """测试优化控制功能"""
        # 测试开始优化
        self.progress_window.optimization_running = False
        self.progress_window.toggle_optimization()
        self.assertTrue(self.progress_window.optimization_running)
        self.assertEqual(self.progress_window.start_button["text"], "取消优化")
        
        # 测试取消优化
        self.progress_window.toggle_optimization()
        self.assertFalse(self.progress_window.optimization_running)
        self.assertEqual(self.progress_window.start_button["text"], "开始优化")
        self.assertEqual(self.progress_window.label["text"], "优化已取消")
    
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
        
        # 测试加载配置
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(test_config))):
            self.progress_window.load_config()
            self.assertEqual(self.progress_window.symbol_var.get(), "159300")
    
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
        
        # 验证显示内容
        details_text = self.progress_window.trade_details.get("1.0", tk.END)
        self.assertIn("总收益率: 10.50%", details_text)
        self.assertIn("上涨卖出: 1.00%", details_text)
        self.assertIn("交易次数: 50", details_text)
    
    def test_search_functionality(self):
        """测试搜索功能"""
        # 设置测试文本
        self.progress_window.trade_details.config(state='normal')
        test_text = "这是一个测试文本\n包含多个测试关键词\n测试文本结束"
        self.progress_window.trade_details.insert("1.0", test_text)
        self.progress_window.trade_details.config(state='disabled')
        
        # 测试搜索
        self.progress_window.search_var.set("测试")
        self.progress_window.search_text()
        
        # 验证搜索结果
        self.assertIn("找到 3 个匹配", self.progress_window.search_count_label["text"])
    
    def test_segment_options(self):
        """测试分段回测选项"""
        # 启用分段回测
        self.progress_window.enable_segments.set(True)
        self.progress_window.toggle_segment_options()
        
        # 验证控件状态
        self.assertEqual(str(self.progress_window.segment_mode_combo["state"]), "readonly")
        self.assertEqual(str(self.progress_window.connect_checkbox["state"]), "normal")
        
        # 禁用分段回测
        self.progress_window.enable_segments.set(False)
        self.progress_window.toggle_segment_options()
        
        # 验证控件状态
        self.assertEqual(str(self.progress_window.segment_mode_combo["state"]), "disabled")
        self.assertEqual(str(self.progress_window.connect_checkbox["state"]), "disabled")
    
    def test_font_size_adjustment(self):
        """测试字体大小调整"""
        # 获取初始字体大小
        initial_font = self.progress_window.trade_details["font"]
        
        # 增加字体大小
        self.progress_window.increase_font_size()
        new_font = self.progress_window.trade_details["font"]
        self.assertNotEqual(initial_font, new_font)
        
        # 减小字体大小
        self.progress_window.decrease_font_size()
        final_font = self.progress_window.trade_details["font"]
        self.assertEqual(initial_font, final_font)
    
    def test_window_closing(self):
        """测试窗口关闭"""
        with patch('json.dump') as mock_dump:
            self.progress_window._on_closing()
            self.assertTrue(self.progress_window.is_closed)
            mock_dump.assert_called()  # 验证配置保存
    
    def test_optimization_results_display(self):
        """测试优化结果显示"""
        # 创建模拟优化结果
        class MockTrial:
            def __init__(self, value):
                self.value = value
                self.params = {
                    'up_sell_rate': 0.01,
                    'up_callback_rate': 0.003,
                    'down_buy_rate': 0.01,
                    'down_rebound_rate': 0.003,
                    'shares_per_trade': 1000
                }
                self.user_attrs = {'trade_count': 50}
        
        results = {
            "sorted_trials": [
                MockTrial(-15.5),  # 15.5% 收益
                MockTrial(-10.2),  # 10.2% 收益
                MockTrial(-5.8)    # 5.8% 收益
            ]
        }
        
        # 显示结果
        self.progress_window.display_optimization_results(results)
        
        # 验证结果显示
        for widget in self.progress_window.params_container.winfo_children():
            if isinstance(widget, ttk.LabelFrame):
                self.assertIn("收益率:", widget["text"])
    
    @patch('akshare.fund_etf_spot_em')
    def test_symbol_info_update(self, mock_etf_api):
        """测试证券信息更新"""
        # 模拟ETF数据
        mock_etf_api.return_value = pd.DataFrame({
            '代码': ['159300'],
            '名称': ['沪深300ETF']
        })
        
        # 更新证券信息
        self.progress_window.symbol_var.set('159300')
        self.progress_window.update_symbol_info('code')
        
        # 验证更新结果
        self.assertEqual(self.progress_window.symbol_name_var.get(), '沪深300ETF')
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效的进度更新
        with self.assertRaises(Exception):
            self.progress_window.update_progress(-1)
        
        # 测试无效的配置保存
        with patch('json.dump') as mock_dump:
            mock_dump.side_effect = Exception("保存失败")
            self.progress_window.save_config()
            # 验证错误被正确处理
    
    @patch('tkinter.Tk.focus_get')
    def test_keyboard_shortcuts(self, mock_focus_get):
        """测试键盘快捷键"""
        # 测试搜索快捷键
        self.progress_window.root.focus_set()  # 确保窗口有焦点
        
        # 使用after来确保事件处理完成
        def check_focus():
            self.progress_window.root.event_generate('<Command-f>')
            self.assertEqual(self.progress_window.root.focus_get(), self.progress_window.search_entry)
        
        self.progress_window.root.after(100, check_focus)
        self.progress_window.root.update()
        
        # 测试开始/取消优化快捷键
        self.progress_window.optimization_running = False
        self.progress_window.root.event_generate('<Command-Return>')
        self.progress_window.root.update()
        
        # 验证状态
        self.assertTrue(hasattr(self.progress_window, 'optimization_running'))
    
    def test_optimization_error_handling(self):
        """测试优化过程中的错误处理"""
        # 设置有效的参数
        self.progress_window.symbol_var.set("159300")
        self.progress_window.start_date_var.set("2024-01-01")
        self.progress_window.end_date_var.set("2024-12-31")
        self.progress_window.initial_cash_var.set("100000")
        
        # 模拟优化过程中的异常
        with patch('threading.Thread') as mock_thread:
            def mock_thread_init(*args, **kwargs):
                target = kwargs.get('target')
                if target:
                    target()
                return MagicMock()
            
            mock_thread.side_effect = mock_thread_init
            
            # 模拟优化器
            mock_optimizer = MagicMock()
            mock_optimizer.optimize.side_effect = Exception("优化过程出错")
            
            with patch('stock_grid_optimizer.GridStrategyOptimizer', return_value=mock_optimizer):
                with patch('tkinter.messagebox.showerror') as mock_error:
                    with patch('datetime.datetime.strptime', return_value=datetime.now()):
                        self.progress_window.start_optimization()
                        mock_error.assert_called_with("优化错误", "优化过程出错")
                        self.assertEqual(self.progress_window.label["text"], "优化失败")
                        self.assertEqual(self.progress_window.start_button["text"], "开始优化")
                        self.assertFalse(self.progress_window.optimization_running)
    
    def test_optimization_cleanup(self):
        """测试优化过程的清理工作"""
        # 设置初始状态
        self.progress_window.optimization_running = True
        self.progress_window.start_button.configure(text="取消优化")
        self.progress_window.label["text"] = "正在优化..."
        self.progress_window.progress["value"] = 50
        self.progress_window.percent_label["text"] = "50%"
        self.progress_window.time_label["text"] = "耗时: 0:01:00"
        self.progress_window.eta_label["text"] = "预计剩余: 0:01:00"
        self.progress_window.root.update()
        
        # 触发清理
        self.progress_window.cleanup()
        
        # 等待UI更新
        self.progress_window.root.after(100)
        self.progress_window.root.update()
        
        # 验证状态
        self.assertFalse(self.progress_window.optimization_running, "优化运行标志应该被重置为False")
        self.assertEqual(self.progress_window.start_button["text"], "开始优化", "按钮文本应该被重置为'开始优化'")
        self.assertEqual(self.progress_window.label["text"], "优化已取消", "标签文本应该显示'优化已取消'")
        self.assertEqual(self.progress_window.progress["value"], 0, "进度条应该被重置为0")
        self.assertEqual(self.progress_window.percent_label["text"], "0%", "进度百分比应该被重置为0%")
        self.assertEqual(self.progress_window.time_label["text"], "耗时: 0:00:00", "耗时应该被重置")
        self.assertEqual(self.progress_window.eta_label["text"], "预计剩余: --:--:--", "预计剩余时间应该被重置")
    
    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复机制"""
        # 测试无效的证券代码
        self.progress_window.symbol_var.set("invalid")
        self.progress_window.update_symbol_info('code')
        self.assertEqual(self.progress_window.symbol_name_var.get(), "未找到证券")
        
        # 测试无效的日期格式
        self.progress_window.start_date_var.set("invalid-date")
        with patch('tkinter.messagebox.showerror') as mock_error:
            self.progress_window.validate_date(ttk.Entry(self.progress_window.root))
            mock_error.assert_called_with("输入错误", "无效的日期格式")
        
        # 测试配置文件读取错误
        with patch('builtins.open', side_effect=Exception("读取错误")):
            self.progress_window.load_config()  # 应该优雅地处理错误
            
        # 测试配置文件保存错误
        with patch('json.dump', side_effect=Exception("保存错误")):
            self.progress_window.save_config()  # 应该优雅地处理错误
    
    def test_config_file_operations(self):
        """测试配置文件的完整读写操作"""
        # 准备测试配置数据
        test_config = {
            "symbol": "159300",
            "symbol_name": "沪深300ETF",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "ma_period": "55",
            "ma_protection": True,
            "initial_positions": "0",
            "initial_cash": "100000",
            "min_buy_times": "2",
            "price_range_min": "3.9",
            "price_range_max": "4.3",
            "n_trials": "100",
            "top_n": "5",
            "profit_calc_method": "mean",
            "connect_segments": False
        }
        
        # 模拟保存配置
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            self.progress_window.save_config()
            mock_file.assert_called_once()
        
        # 模拟加载配置
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(test_config))):
            self.progress_window.load_config()
            self.assertEqual(self.progress_window.symbol_var.get(), "159300")
            self.assertEqual(self.progress_window.initial_cash_var.get(), "100000")
    
    def test_ui_interaction_edge_cases(self):
        """测试UI交互的边界情况"""
        # 测试搜索框为空的情况
        self.progress_window.search_var.set("")
        self.progress_window.search_text()
        self.assertEqual(self.progress_window.search_count_label["text"], "")
        
        # 测试字体大小调整的边界
        # 设置初始字体
        self.progress_window.trade_details.configure(font=('Courier', 11))
        
        # 测试增加到最大值
        for _ in range(25):  # 尝试增加超过最大限制
            self.progress_window.increase_font_size()
        
        # 测试减小到最小值
        for _ in range(25):  # 尝试减小超过最小限制
            self.progress_window.decrease_font_size()
    
    def test_keyboard_shortcuts(self):
        """测试键盘快捷键"""
        # 测试搜索快捷键
        self.progress_window.root.focus_set()  # 确保窗口有焦点
        
        # 使用after来确保事件处理完成
        def check_focus():
            self.progress_window.root.event_generate('<Command-f>')
            self.assertEqual(self.progress_window.root.focus_get(), self.progress_window.search_entry)
        
        self.progress_window.root.after(100, check_focus)
        self.progress_window.root.update()
        
        # 测试开始/取消优化快捷键
        self.progress_window.optimization_running = False
        self.progress_window.root.event_generate('<Command-Return>')
        self.progress_window.root.update()
        
        # 验证状态
        self.assertTrue(hasattr(self.progress_window, 'optimization_running'))
    
    def test_optimization_cancellation(self):
        """测试优化过程的取消"""
        # 设置初始状态
        self.progress_window.optimization_running = True
        self.progress_window.start_button.configure(text="取消优化")
        
        # 执行取消
        self.progress_window.cancel_optimization()
        self.progress_window.root.update()  # 确保UI更新完成
        
        # 验证状态
        self.assertFalse(self.progress_window.optimization_running)
        self.assertEqual(self.progress_window.label["text"], "优化已取消")
        self.assertEqual(self.progress_window.progress["value"], 0)
        self.assertEqual(self.progress_window.percent_label["text"], "0%")
        self.assertEqual(self.progress_window.time_label["text"], "耗时: 0:00:00")
        self.assertEqual(self.progress_window.eta_label["text"], "预计剩余: --:--:--")
    
    def test_ui_update_during_optimization(self):
        """测试优化过程中的UI更新"""
        # 设置初始状态
        self.progress_window.optimization_running = True
        self.progress_window.start_time = datetime.now() - timedelta(minutes=1)
        
        # 模拟优化过程中的UI更新
        with patch('tkinter.Tk.update') as mock_update:
            # 更新进度
            self.progress_window.update_progress(50)
            
            # 验证UI更新被调用
            mock_update.assert_called()
            
            # 验证标签更新
            self.assertIn("50", self.progress_window.percent_label["text"])
            self.assertIn("耗时:", self.progress_window.time_label["text"])
            self.assertIn("预计剩余:", self.progress_window.eta_label["text"])
    
    def test_config_file_error_handling(self):
        """测试配置文件错误处理"""
        # 测试配置文件不存在的情况
        with patch('os.path.exists', return_value=False):
            self.progress_window.load_config()
            # 验证使用默认值
            self.assertEqual(self.progress_window.symbol_var.get(), "159300")
        
        # 测试配置文件损坏的情况
        with patch('builtins.open', unittest.mock.mock_open(read_data="invalid json")):
            self.progress_window.load_config()
            # 验证错误被正确处理
            self.assertEqual(self.progress_window.symbol_var.get(), "159300")
        
        # 测试配置文件写入失败的情况
        with patch('builtins.open', side_effect=PermissionError):
            self.progress_window.save_config()
            # 验证错误被正确处理
    
    def test_optimization_thread_management(self):
        """测试优化线程管理"""
        # 模拟优化线程
        mock_thread = MagicMock()
        self.progress_window.optimization_thread = mock_thread
        
        # 测试线程状态检查
        with patch('threading.Thread.is_alive', return_value=True):
            self.progress_window._check_thread_and_close()
            self.assertFalse(self.progress_window.is_closed)
        
        # 测试线程结束后的窗口关闭
        with patch('threading.Thread.is_alive', return_value=False):
            with patch('tkinter.Tk.destroy') as mock_destroy:
                self.progress_window._check_thread_and_close()
                mock_destroy.assert_called_once()
    
    def test_window_cleanup_on_error(self):
        """测试发生错误时的窗口清理"""
        # 设置初始状态
        self.progress_window.optimization_running = True
        self.progress_window.start_button.configure(text="取消优化")
        self.progress_window.label["text"] = "正在优化..."
        
        # 模拟错误发生
        with patch('tkinter.messagebox.showerror') as mock_error:
            # 触发一个错误
            self.progress_window.update_progress(-1)  # 无效的进度值
            
            # 验证错误处理和清理
            mock_error.assert_called()
            self.assertFalse(self.progress_window.optimization_running)
            self.assertEqual(self.progress_window.start_button["text"], "开始优化")
    
    def test_optimization_parameter_validation(self):
        """测试优化参数验证"""
        # 测试无效的最小买入次数
        self.progress_window.min_buy_times_var.set("-1")
        with patch('tkinter.messagebox.showerror') as mock_error:
            self.progress_window.start_optimization()
            mock_error.assert_called()
        
        # 测试无效的价格范围
        self.progress_window.min_buy_times_var.set("2")
        self.progress_window.price_range_min_var.set("5.0")
        self.progress_window.price_range_max_var.set("4.0")
        with patch('tkinter.messagebox.showerror') as mock_error:
            self.progress_window.start_optimization()
            mock_error.assert_called()
    
    def test_optimization_results_sorting(self):
        """测试优化结果排序功能"""
        # 创建模拟优化结果
        class MockTrial:
            def __init__(self, value):
                self.value = value
                self.params = {
                    'up_sell_rate': 0.01,
                    'up_callback_rate': 0.003,
                    'down_buy_rate': 0.01,
                    'down_rebound_rate': 0.003,
                    'shares_per_trade': 1000
                }
                self.user_attrs = {'trade_count': 50}
        
        results = {
            "sorted_trials": [
                MockTrial(-15.5),  # 15.5% 收益
                MockTrial(-10.2),  # 10.2% 收益
                MockTrial(-5.8)    # 5.8% 收益
            ]
        }
        
        # 测试升序排序
        self.progress_window.sort_ascending = True
        self.progress_window.display_optimization_results(results)
        first_result = self.progress_window.params_container.winfo_children()[0]
        self.assertIn("5.8%", first_result["text"])
        
        # 测试降序排序
        self.progress_window.sort_ascending = False
        self.progress_window.display_optimization_results(results)
        first_result = self.progress_window.params_container.winfo_children()[0]
        self.assertIn("15.5%", first_result["text"])
    
    def test_segment_days_update(self):
        """测试分段天数更新功能"""
        # 启用分段回测
        self.progress_window.enable_segments.set(True)
        
        # 测试有效的最小买入次数
        self.progress_window.min_buy_times_var.set("5")
        self.progress_window.update_segment_days()
        self.assertNotEqual(self.progress_window.segment_days_label["text"], "")
        
        # 测试无效的最小买入次数
        self.progress_window.min_buy_times_var.set("invalid")
        self.progress_window.update_segment_days()
        self.assertEqual(self.progress_window.segment_days_label["text"], "")
        
        # 测试禁用分段回测
        self.progress_window.enable_segments.set(False)
        self.progress_window.update_segment_days()
        self.assertEqual(self.progress_window.segment_days_label["text"], "")
    
    def test_entry_focus_handling(self):
        """测试输入框焦点处理"""
        # 创建模拟输入框
        mock_entry = MagicMock()
        mock_entry.winfo_exists.return_value = True
        mock_entry.focus_set = MagicMock()
        mock_entry.selection_range = MagicMock()
        mock_entry.update_idletasks = MagicMock()
        
        # 测试焦点处理
        event = MagicMock()
        result = self.progress_window.handle_entry_focus(event, mock_entry)
        
        # 验证焦点处理
        self.assertEqual(result, "break")
        self.progress_window.root.after(100)  # 等待延迟执行
        mock_entry.focus_set.assert_called_once()
        mock_entry.selection_range.assert_called_with(0, tk.END)
        mock_entry.update_idletasks.assert_called_once()
    
    def test_symbol_info_update_with_price_range(self):
        """测试证券信息更新和价格范围计算"""
        # 模拟历史数据
        mock_hist_data = pd.DataFrame({
            '最低': [3.5, 3.8, 3.6],
            '最高': [4.2, 4.5, 4.3]
        })
        
        with patch('akshare.fund_etf_hist_em', return_value=mock_hist_data):
            # 更新新的证券代码
            self.progress_window.symbol_var.set('159301')  # 使用一个新的代码
            self.progress_window.update_symbol_info('code')
            
            # 验证价格范围更新
            self.assertEqual(self.progress_window.price_range_min_var.get(), "3.500")
            self.assertEqual(self.progress_window.price_range_max_var.get(), "4.500")
    
    def test_optimization_cancellation_during_run(self):
        """测试优化运行过程中的取消操作"""
        # 设置初始状态
        self.progress_window.optimization_running = True
        self.progress_window.start_time = datetime.now()
        
        # 模拟优化线程
        mock_thread = MagicMock()
        self.progress_window.optimization_thread = mock_thread
        
        # 执行取消
        self.progress_window.cancel_optimization()
        
        # 验证状态
        self.assertFalse(self.progress_window.optimization_running)
        self.assertEqual(self.progress_window.progress["value"], 0)
        self.assertEqual(self.progress_window.label["text"], "优化已取消")
        
        # 验证UI更新
        self.assertEqual(self.progress_window.percent_label["text"], "0%")
        self.assertEqual(self.progress_window.time_label["text"], "耗时: 0:00:00")
        self.assertEqual(self.progress_window.eta_label["text"], "预计剩余: --:--:--")
    
    def test_trade_details_scroll_controls(self):
        """测试交易详情滚动控制"""
        # 设置一些测试文本
        self.progress_window.trade_details.config(state='normal')
        self.progress_window.trade_details.insert('1.0', '测试内容\n' * 100)
        self.progress_window.trade_details.config(state='disabled')
        
        # 测试滚动到开始
        event = MagicMock()
        result = self.progress_window.scroll_to_start(event)
        self.assertEqual(result, 'break')
        self.assertEqual(
            self.progress_window.trade_details.index(tk.INSERT),
            '1.0'
        )
        
        # 测试滚动到结束
        result = self.progress_window.scroll_to_end(event)
        self.assertEqual(result, 'break')
        self.assertEqual(
            self.progress_window.trade_details.index(tk.INSERT),
            tk.END
        )
    
    def test_strategy_details_display_with_segments(self):
        """测试带分段的策略详情显示"""
        # 启用分段回测
        self.progress_window.enable_segments.set(True)
        self.progress_window.profit_calc_method_var.set("平均值")
        
        # 设置测试参数
        test_params = {
            'up_sell_rate': 0.01,
            'up_callback_rate': 0.003,
            'down_buy_rate': 0.01,
            'down_rebound_rate': 0.003,
            'shares_per_trade': 1000
        }
        
        # 模拟分段回测结果
        with patch('grid_strategy.GridStrategy') as mock_strategy:
            instance = mock_strategy.return_value
            instance.backtest.return_value = 10.5
            instance.trades = []
            instance.failed_trades = {'买入价格超范围': 2}
            
            # 显示策略详情
            self.progress_window.show_strategy_details(test_params)
            
            # 验证显示内容
            details_text = self.progress_window.trade_details.get("1.0", tk.END)
            self.assertIn("分段回测", details_text)
            self.assertIn("买入价格超范围: 2次", details_text)
    
    def test_symbol_validation_and_update(self):
        """测试证券代码验证和更新"""
        # 测试有效的ETF代码
        with patch('akshare.fund_etf_spot_em') as mock_etf_api:
            mock_etf_api.return_value = pd.DataFrame({
                '代码': ['159300', '159301'],
                '名称': ['沪深300ETF', '测试ETF']
            })
            
            # 验证有效代码
            self.assertTrue(self.progress_window.is_valid_symbol('159300'))
            
            # 验证无效代码
            self.assertFalse(self.progress_window.is_valid_symbol('invalid'))
            
            # 测试从名称更新代码
            self.progress_window.symbol_name_var.set('测试ETF')
            self.progress_window.update_symbol_info('name')
            self.assertEqual(self.progress_window.symbol_var.get(), '159301')
    
    def test_input_validation_and_error_handling(self):
        """测试输入验证和错误处理"""
        # 测试日期验证
        entry = ttk.Entry(self.progress_window.root)
        entry.insert(0, "2024-13-32")  # 无效日期
        self.progress_window.validate_date(entry)
        self.assertEqual(entry['foreground'], 'red')
        
        # 测试证券代码验证
        entry = ttk.Entry(self.progress_window.root)
        entry.insert(0, "invalid")
        self.progress_window.validate_symbol(entry)
        self.assertEqual(entry['foreground'], 'red')
        
        # 测试所有输入的验证
        self.progress_window.symbol_var.set("invalid")
        self.assertFalse(self.progress_window.validate_all_inputs())
    
    def test_optimization_edge_cases(self):
        """测试优化过程的边界情况"""
        # 测试优化运行时启动新的优化
        self.progress_window.optimization_running = True
        with patch('threading.Thread') as mock_thread:
            self.progress_window.start_optimization()
            mock_thread.assert_not_called()
        
        # 测试无效的优化参数
        self.progress_window.optimization_running = False
        self.progress_window.n_trials_var.set("0")
        with patch('tkinter.messagebox.showerror') as mock_error:
            self.progress_window.start_optimization()
            mock_error.assert_called()
    
    def test_window_state_management(self):
        """测试窗口状态管理"""
        # 测试窗口关闭时的配置保存
        with patch('json.dump') as mock_dump:
            self.progress_window._on_closing()
            mock_dump.assert_called_once()
            self.assertTrue(self.progress_window.is_closed)
        
        # 测试窗口清理
        self.progress_window.cleanup()
        self.assertFalse(self.progress_window.optimization_running)
        self.assertEqual(self.progress_window.progress["value"], 0)
    
    def test_search_functionality_edge_cases(self):
        """测试搜索功能的边界情况"""
        # 设置测试文本
        self.progress_window.trade_details.config(state='normal')
        test_text = "测试文本\n" * 10
        self.progress_window.trade_details.insert("1.0", test_text)
        self.progress_window.trade_details.config(state='disabled')
        
        # 测试空搜索
        self.progress_window.search_var.set("")
        self.progress_window.search_text()
        self.assertEqual(self.progress_window.search_count_label["text"], "")
        
        # 测试未找到的搜索
        self.progress_window.search_var.set("不存在的文本")
        self.progress_window.search_text()
        self.assertIn("找到 0 个匹配", self.progress_window.search_count_label["text"])
        
        # 测试向上搜索
        self.progress_window.search_var.set("测试")
        self.progress_window.search_text('up')
        self.assertIn("找到", self.progress_window.search_count_label["text"])
    
    def test_font_size_adjustment_limits(self):
        """测试字体大小调整的限制"""
        # 获取初始字体大小
        initial_font = self.progress_window.trade_details["font"]
        
        # 测试增加到最大限制
        for _ in range(50):  # 尝试增加超过最大限制
            self.progress_window.increase_font_size()
        
        # 验证字体大小不超过最大值
        max_font = self.progress_window.trade_details["font"]
        self.assertNotEqual(initial_font, max_font)
        
        # 测试减小到最小限制
        for _ in range(50):  # 尝试减小超过最小限制
            self.progress_window.decrease_font_size()
        
        # 验证字体大小不小于最小值
        min_font = self.progress_window.trade_details["font"]
        self.assertNotEqual(max_font, min_font)

if __name__ == '__main__':
    unittest.main() 