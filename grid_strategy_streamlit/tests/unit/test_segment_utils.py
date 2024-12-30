import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import pandas as pd

from src.services.business.segment_utils import build_segments, get_segment_days, BATCH_TO_DAYS_MAP

class TestSegmentUtils(unittest.TestCase):
    """时间段工具测试类"""
    
    def setUp(self):
        """初始化测试环境，设置日期范围和模拟交易日历
        场景: 初始化测试环境
        输入:
            - start_date: 2024-01-01
            - end_date: 2024-03-31
            - 模拟交易日历数据
        验证:
            - 基本参数设置正确
            - 模拟数据生成完整
        """
        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2024, 3, 31)
        
        # 生成模拟交易日历数据
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq='B')
        self.mock_calendar = pd.DataFrame({
            'trade_date': dates,
            'open': 1  # 1表示交易日
        })

    def test_get_segment_days(self):
        """验证不同批次的时间段天数计算
        场景1: 正常批次
        输入:
            - 批次: 1-5
        验证:
            - 返回对应的天数

        场景2: 边界值处理
        输入:
            - 批次: 0 (小于最小值)
            - 批次: 6 (大于最大值)
            - 批次: -1 (负数)
        验证:
            - 返回合理的默认值
        """
        # 测试正常批次
        for batch, days in BATCH_TO_DAYS_MAP.items():
            self.assertEqual(get_segment_days(batch), days)
        
        # 测试边界值
        self.assertEqual(get_segment_days(0), BATCH_TO_DAYS_MAP[1])  # 小于最小值
        self.assertEqual(get_segment_days(6), BATCH_TO_DAYS_MAP[5])  # 大于最大值
        self.assertEqual(get_segment_days(-1), BATCH_TO_DAYS_MAP[1])  # 负数

    @patch('akshare.tool_trade_date_hist_sina')
    def test_build_segments_normal(self, mock_calendar):
        """测试正常情况下的时间段构建
        场景: 不同批次时间段构建
        输入:
            - 开始日期: 2024-01-01
            - 结束日期: 2024-03-31
            - 批次: 1-5
            - 模拟交易日历
        验证:
            - 时间段数量大于0
            - 时间段起止日期合理
            - 时间段在指定范围内
        """
        mock_calendar.return_value = self.mock_calendar
        
        # 测试不同的批次
        for batch in BATCH_TO_DAYS_MAP.keys():
            segments = build_segments(self.start_date, self.end_date, batch)
            
            # 验证时间段
            self.assertGreater(len(segments), 0)
            for start, end in segments:
                self.assertLessEqual(start, end)
                self.assertGreaterEqual(start, self.start_date)
                self.assertLessEqual(end, self.end_date)

    @patch('akshare.tool_trade_date_hist_sina')
    def test_build_segments_empty_calendar(self, mock_calendar):
        """验证空交易日历的处理
        场景: 交易日历为空
        输入:
            - 空DataFrame
            - 开始日期: 2024-01-01
            - 结束日期: 2024-03-31
        验证:
            - 返回单个时间段
            - 时间段为完整日期范围
        """
        mock_calendar.return_value = pd.DataFrame()
        
        segments = build_segments(self.start_date, self.end_date, 1)
        
        # 应该返回单个时间段
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0], (self.start_date, self.end_date))

    @patch('akshare.tool_trade_date_hist_sina')
    def test_build_segments_api_error(self, mock_calendar):
        """测试API错误时的异常处理
        场景: API调用异常
        输入:
            - API异常: "API错误"
            - 开始日期: 2024-01-01
            - 结束日期: 2024-03-31
        验证:
            - 使用工作日历作为备选
            - 返回有效的时间段
        """
        mock_calendar.side_effect = Exception("API错误")
        
        segments = build_segments(self.start_date, self.end_date, 1)
        
        # 应该使用工日日历作为备选
        self.assertGreater(len(segments), 0)
        for start, end in segments:
            self.assertLessEqual(start, end)

    def test_build_segments_invalid_dates(self):
        """验证无效日期输入的处理
        场景: 结束日期早于开始日期
        输入:
            - 开始日期: 2024-03-31
            - 结束日期: 2024-01-01
        验证:
            - 返回单个时间段
            - 保持原始日期顺序
        """
        # 结束日期早于开始日期
        segments = build_segments(self.end_date, self.start_date, 1)
        
        # 应该返回单个时间段
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0], (self.end_date, self.start_date))

    def test_build_segments_same_date(self):
        """测试起止日期相同的边界情况
        场景: 开始日期等于结束日期
        输入:
            - 开始日期: 2024-01-01
            - 结束日期: 2024-01-01
        验证:
            - 返回单个时间段
            - 起止日期相同
        """
        segments = build_segments(self.start_date, self.start_date, 1)
        
        # 应该返回单个时间段
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0], (self.start_date, self.start_date))

    @patch('akshare.tool_trade_date_hist_sina')
    def test_build_segments_boundary_conditions(self, mock_calendar):
        """验证时间段构建的边界条件处理
        场景1: 最小批次(最长周期)
        输入:
            - 批次: 1
            - 模拟交易日历
        验证:
            - 时间段数量合理
            - 周期长度正确

        场景2: 最大批次(最短周期)
        输入:
            - 批次: 5
            - 模拟交易日历
        验证:
            - 时间段数量大于最小批次
            - 周期长度正确
        """
        mock_calendar.return_value = self.mock_calendar
        
        # 测试最小批次（最长周期）
        min_batch_segments = build_segments(self.start_date, self.end_date, 1)
        self.assertGreater(len(min_batch_segments), 0)
        
        # 测试最大批次（最短周期）
        max_batch_segments = build_segments(self.start_date, self.end_date, 5)
        self.assertGreater(len(max_batch_segments), 0)
        
        # 最小批次长周期）应该产生更少的时间段
        self.assertGreater(len(max_batch_segments), len(min_batch_segments))
        
        # 验证时间段长度与周期的关系
        min_batch_days = (min_batch_segments[0][1] - min_batch_segments[0][0]).days
        max_batch_days = (max_batch_segments[0][1] - max_batch_segments[0][0]).days
        self.assertGreater(min_batch_days, max_batch_days)

if __name__ == '__main__':
    unittest.main() 