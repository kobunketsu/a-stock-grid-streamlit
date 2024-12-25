import unittest
from unittest.mock import patch, MagicMock
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_progress_window import StreamlitProgressWindow

class TestStreamlitProgressWindow(unittest.TestCase):
    """Streamlit版本进度窗口测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 初始化进度窗口
        self.progress_window = StreamlitProgressWindow(total_trials=100)
        
        # 模拟Streamlit组件
        self.mock_progress_bar = MagicMock()
        self.mock_empty = MagicMock()
        self.mock_metrics = MagicMock()
        self.mock_text_area = MagicMock()
        
    @patch('streamlit.progress')
    @patch('streamlit.empty')
    def test_initialization(self, mock_empty, mock_progress):
        """测试进度窗口初始化"""
        # 验证初始化参数
        self.assertEqual(self.progress_window.total_trials, 100)
        self.assertFalse(self.progress_window.optimization_running)
        self.assertEqual(self.progress_window.current_trial, 0)
        
        # 验证Streamlit组件初始化
        mock_progress.assert_called_once()
        mock_empty.assert_called()

    @patch('streamlit.progress')
    def test_update_progress(self, mock_progress):
        """测试进度更新功能"""
        # 设置模拟进度条
        mock_progress_bar = MagicMock()
        mock_progress.return_value = mock_progress_bar
        
        # 更新进度
        self.progress_window.update_progress(50)
        
        # 验证进度更新
        self.assertEqual(self.progress_window.current_trial, 50)
        mock_progress_bar.progress.assert_called_with(0.5)  # 50%进度

    @patch('streamlit.empty')
    def test_status_updates(self, mock_empty):
        """测试状态更新功能"""
        # 设置模拟状态容器
        mock_container = MagicMock()
        mock_empty.return_value = mock_container
        
        # 更新状态
        self.progress_window.set_status("正在优化参数...")
        mock_container.info.assert_called_with("正在优化参数...")
        
        # 完成优化
        self.progress_window.update_progress(100)
        self.assertEqual(self.progress_window.status_text, "优化完成")

    @patch('streamlit.text_area')
    def test_output_capture(self, mock_text_area):
        """测试输出捕获功能"""
        # 设置模拟文本区域
        mock_text_area.return_value = self.mock_text_area
        
        # 写入输出
        test_output = "测试输出内容"
        self.progress_window.write(test_output)
        
        # 验证输出捕获
        self.assertEqual(self.progress_window.captured_output, test_output)
        mock_text_area.assert_called()

    @patch('streamlit.button')
    def test_stop_optimization(self, mock_button):
        """测试停止优化功能"""
        # 设置模拟按钮
        mock_button.return_value = True  # 模拟按钮点击
        
        # 启动优化
        self.progress_window.optimization_running = True
        
        # 触发停止
        self.progress_window.stop_optimization()
        
        # 验证状态
        self.assertFalse(self.progress_window.optimization_running)
        self.assertEqual(self.progress_window.status_text, "正在停止优化...")

    @patch('streamlit.columns')
    def test_metrics_display(self, mock_columns):
        """测试指标显示功能"""
        # 设置开始时间
        self.progress_window.start_time = datetime.now() - timedelta(minutes=5)
        
        # 更新进度
        self.progress_window.update_progress(50)
        
        # 验证指标显示
        mock_columns.assert_called()
        self.assertIn("%", self.progress_window.progress_metric.label)

    def test_error_handling(self):
        """测试错误处理功能"""
        # 测试无效进度值
        with self.assertRaises(ValueError):
            self.progress_window.update_progress(-1)
        
        with self.assertRaises(ValueError):
            self.progress_window.update_progress(101)  # 超过100%

    @patch('streamlit.empty')
    def test_dynamic_content_update(self, mock_empty):
        """测试动态内容更新功能"""
        # 设置模拟容器
        mock_container = MagicMock()
        mock_empty.return_value = mock_container
        
        # 更新内容
        test_content = "动态更新内容"
        self.progress_window.update_dynamic_content(test_content)
        
        # 验证内容更新
        mock_container.write.assert_called_with(test_content)

    def test_resource_cleanup(self):
        """测试资源清理功能"""
        # 模拟优化运行
        self.progress_window.optimization_running = True
        self.progress_window.start_time = datetime.now()
        self.progress_window.captured_output = "测试输出"
        
        # 清理资源
        self.progress_window.cleanup()
        
        # 验证状态重置
        self.assertFalse(self.progress_window.optimization_running)
        self.assertIsNone(self.progress_window.start_time)
        self.assertEqual(self.progress_window.captured_output, "")
        self.assertEqual(self.progress_window.status_text, "已清理")

if __name__ == '__main__':
    unittest.main() 