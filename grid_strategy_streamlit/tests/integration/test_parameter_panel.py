import unittest
from unittest.mock import patch, MagicMock
import streamlit as st
from datetime import datetime
import logging

from src.utils.localization import l
from src.views.parameter_panel import (
    validate_symbol, validate_date, validate_initial_cash,
    validate_min_buy_times, validate_price_range, validate_n_trials,
    validate_top_n,update_symbol_info,update_segment_days
)

class TestParameterPanel(unittest.TestCase):
    """参数面板测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化时的设置"""
        # 设置日志
        logging.basicConfig(level=logging.DEBUG)
        cls.logger = logging.getLogger(__name__)
        cls.logger.debug("开始运行参数面板测试用例")
    
    def setUp(self):
        """测试前的准备工作"""
        self.logger.debug(f"开始测试: {self._testMethodName}")
    
    def tearDown(self):
        """测试后的清理工作"""
        self.logger.debug(f"结束测试: {self._testMethodName}")
        patch.stopall()
    
    @patch('src.views.parameter_panel.get_symbol_by_name')
    @patch('src.views.parameter_panel.get_symbol_info')
    @patch('streamlit.session_state')
    def test_update_symbol_by_input_name_or_code(self, mock_session_state, mock_get_symbol_info, mock_get_symbol_by_name):
        """测试通过股票名称或代码更新股票信息
        
        测试场景：
        1. 有效股票代码：
           - 输入000001，返回平安银行信息和价格区间
           - 验证仅调用get_symbol_info
        
        2. 有效股票名称：
           - 输入双成药业，返回股票信息和价格区间
           - 验证仅调用get_symbol_info
        
        3. 无效股票代码：
           - 输入无效代码，返回None
           - 验证错误处理
        
        4. API异常：
           - 模拟API异常，返回None
           - 验证异常处理
        """
        self.logger.debug("开始测试 test_update_symbol_by_input_name_or_code")
        
        # 场景1：通过股票代码更新
        self.logger.debug("场景1：通过股票代码更新")
        mock_get_symbol_info.return_value = ("平安银行", "STOCK")
        
        name, price_range = update_symbol_info("000001")
        
        mock_get_symbol_info.assert_called_once_with("000001")
        mock_get_symbol_by_name.assert_not_called()
        self.assertEqual(name, "平安银行")
        self.assertIsNotNone(price_range)
        
        # 场景2：通过股票名称更新
        self.logger.debug("场景2：通过股票名称更新")
        mock_get_symbol_info.reset_mock()
        mock_get_symbol_by_name.reset_mock()
        mock_get_symbol_by_name.return_value = "002693"
        mock_get_symbol_info.return_value = ("双成药业", "STOCK")
        
        name, price_range = update_symbol_info("双成药业")
        
        mock_get_symbol_by_name.assert_not_called()  # 因为直接使用代码更新
        mock_get_symbol_info.assert_called_once_with("双成药业")
        self.assertEqual(name, "双成药业")
        self.assertIsNotNone(price_range)
        
        # 场景3：无效的股票代码
        self.logger.debug("场景3：无效的股票代码")
        mock_get_symbol_info.reset_mock()
        mock_get_symbol_by_name.reset_mock()
        mock_get_symbol_info.return_value = (None, None)
        
        name, price_range = update_symbol_info("invalid_code")
        
        mock_get_symbol_info.assert_called_once_with("invalid_code")
        mock_get_symbol_by_name.assert_not_called()
        self.assertIsNone(name)
        self.assertIsNone(price_range)
        
        # 场景4：API异常
        self.logger.debug("场景4：API异常")
        mock_get_symbol_info.reset_mock()
        mock_get_symbol_by_name.reset_mock()
        mock_get_symbol_info.side_effect = Exception("API错误")
        
        name, price_range = update_symbol_info("000001")
        
        mock_get_symbol_info.assert_called_once_with("000001")
        mock_get_symbol_by_name.assert_not_called()
        self.assertIsNone(name)
        self.assertIsNone(price_range)

    def test_validate_symbol(self):
        """测试证券代码验证
        
        测试场景：
        1. 空代码：
           - 输入空字符串
           - 验证返回False
        
        2. 无效代码：
           - 输入无效代码
           - 验证API返回False
           - 验证返回False
        
        3. 有效代码：
           - 输入159300
           - 验证API返回True
           - 验证返回True
        """
        # 测试空证券代码
        self.assertFalse(validate_symbol(""))
        
        # 测试无效的证券代码
        with patch('src.views.parameter_panel.is_valid_symbol', return_value=False):
            self.assertFalse(validate_symbol("invalid"))
        
        # 测试有效的证券代码
        with patch('src.views.parameter_panel.is_valid_symbol', return_value=True):
            self.assertTrue(validate_symbol("159300"))
    
    def test_validate_date(self):
        """测试日期验证
        
        测试场景：
        1. 无效日期范围：
           - 结束日期早于开始日期
           - 验证返回False
        
        2. 有效日期范围：
           - 结束日期晚于开始日期
           - 验证返回True
        """
        # 测试结束日期早于开始日期
        start_date = datetime(2024, 12, 20)
        end_date = datetime(2024, 10, 10)
        self.assertFalse(validate_date(start_date, end_date))
        
        # 测试有效的日期范围
        start_date = datetime(2024, 10, 10)
        end_date = datetime(2024, 12, 20)
        self.assertTrue(validate_date(start_date, end_date))
    
    def test_validate_initial_cash(self):
        """测试初始资金验证
        
        测试场景：
        1. 无效金额：
           - 输入负数-1000
           - 验证返回False
        
        2. 边界值：
           - 输入0
           - 验证返回True
        
        3. 有效金额：
           - 输入100000
           - 验证返回True
        """
        # 测试负数初始资金
        self.assertFalse(validate_initial_cash(-1000))
        
        # 测试初始资金为0（应该是有效的）
        self.assertTrue(validate_initial_cash(0))
        
        # 测试有效的初始资金
        self.assertTrue(validate_initial_cash(100000))
    
    def test_validate_min_buy_times(self):
        """测试最小买入次数验证
        
        测试场景：
        1. 无效次数（0）：
           - 输入0，返回False
           - 验证边界值处理
        
        2. 无效次数（负数）：
           - 输入-1，返回False
           - 验证负数处理
        
        3. 有效次数：
           - 输入1，返回True
           - 验证正常值处理
        """
        # 测试无效的最小买入次数（0）
        self.assertFalse(validate_min_buy_times(0))
        
        # 测试无效的最小买入次数（负数）
        self.assertFalse(validate_min_buy_times(-1))
        
        # 测试有效的最小买入次数
        self.assertTrue(validate_min_buy_times(1))
    
    def test_validate_price_range(self):
        """测试价格区间验证
        
        测试场景：
        1. 无效区间：
           - 输入最小值4.3，最大值3.9
           - 验证区间反转处理
        
        2. 有效区间：
           - 输入最小值3.9，最大值4.3
           - 验证正常区间处理
        """
        # 测试无效的价格区间（最小值大于最大值）
        self.assertFalse(validate_price_range(4.3, 3.9))
        
        # 测试有效的价格区间
        self.assertTrue(validate_price_range(3.9, 4.3))
    
    def test_validate_n_trials(self):
        """测试优化次数验证
        
        测试场景：
        1. 无效次数（负数）：
           - 输入-1，返回False
           - 验证负数处理
        
        2. 无效次数（0）：
           - 输入0，返回False
           - 验证边界值处理
        
        3. 有效次数：
           - 输入100，返回True
           - 验证正常值处理
        """
        # 测试无效的试验次数（负数）
        self.assertFalse(validate_n_trials(-1))
        
        # 测试无效的试验次数（0）
        self.assertFalse(validate_n_trials(0))
        
        # 测试有效的试验次数
        self.assertTrue(validate_n_trials(100))
    
    def test_validate_top_n(self):
        """测试显示结果数量验证
        
        测试场景：
        1. 无效数量（负数）：
           - 输入-1，返回False
           - 验证负数处理
        
        2. 无效数量（0）：
           - 输入0，返回False
           - 验证边界值处理
        
        3. 有效数量：
           - 输入5，返回True
           - 验证正常值处理
        """
        # 测试无效的top_n（负数）
        self.assertFalse(validate_top_n(-1))
        
        # 测试无效的top_n（0）
        self.assertFalse(validate_top_n(0))
        
        # 测试有效的top_n
        self.assertTrue(validate_top_n(5))
    
    @patch('streamlit.error')
    @patch('src.views.parameter_panel.is_valid_symbol')
    def test_error_handling(self, mock_is_valid_symbol, mock_error):
        """测试错误处理
        
        测试场景：
        1. API错误：
           - 模拟is_valid_symbol抛出异常
           - 验证错误信息显示
           - 验证异常处理
        
        2. 日期验证错误：
           - 输入结束日期早于开始日期
           - 验证错误信息显示
           - 验证日期验证逻辑
        """
        # 测试API错误
        mock_is_valid_symbol.side_effect = Exception("API错误")
        validate_symbol("159300")
        mock_error.assert_called_with(l("failed_to_validate_symbol_format").format("API错误"))
        
        # 重置mock
        mock_is_valid_symbol.side_effect = None
        mock_error.reset_mock()
        
        # 测试日期验证错误
        validate_date(datetime(2024, 12, 20), datetime(2024, 10, 10))
        mock_error.assert_called_with(l("end_date_must_be_later_than_start_date"))

if __name__ == '__main__':
    unittest.main() 