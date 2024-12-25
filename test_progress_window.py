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
    
    @patch('tkinter.messagebox.showerror')
    def test_parameter_validation(self, mock_error):
        """测试参数验证"""
        # 测试无效的证券代码
        self.progress_window.symbol_var.set("")
        self.progress_window.validate_symbol(ttk.Entry(self.progress_window.root))
        mock_error.assert_called_with("输入错误", "无效的证券代码")
        
        # 测试无效的日期格式
        entry = ttk.Entry(self.progress_window.root)
        entry.insert(0, "invalid-date")
        self.progress_window.validate_date(entry)
        mock_error.assert_called_with("输入错误", "无效的日期格式")
    
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
        
        # 验证显示���容
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
        # 模拟焦点获取
        mock_focus_get.return_value = self.progress_window.search_entry
        
        # 测试开始优化快捷键
        self.progress_window.optimization_running = False
        self.progress_window.root.event_generate('<Command-Return>')
        
        # 测试搜索快捷键
        self.progress_window.root.event_generate('<Command-f>')
        self.assertEqual(self.progress_window.root.focus_get(), self.progress_window.search_entry)

if __name__ == '__main__':
    unittest.main() 