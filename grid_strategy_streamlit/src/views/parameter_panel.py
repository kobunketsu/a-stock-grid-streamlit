import streamlit as st
from datetime import datetime, timedelta
from typing import Tuple, Any
import logging

from src.utils.localization import l
from src.services.business.trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol, get_symbol_by_name
from src.utils.browser_utils import get_user_agent

def create_parameter_inputs(config: dict) -> Tuple[Any, ...]:
    """创建参数输入区域"""
    print("[DEBUG] Creating parameter inputs")
    with st.container():
        st.markdown("### " + l("param_settings"))
        
        # 证券名称或代码输入
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("symbol_name_or_code"))
        with input_col:
            current_symbol_name = st.session_state.get("symbol_name", config.get("symbol_name", ""))
            symbol_name = st.text_input(
                label="",
                value=current_symbol_name,
                placeholder=l("enter_symbol_name_or_code"),
                key="symbol_name_input"
            )
        
        # 日期选择
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("start_date"))
        with input_col:
            start_date = st.date_input(
                label="",
                value=datetime.strptime(config.get("start_date", "2024-10-10"), "%Y-%m-%d")
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("end_date"))
        with input_col:
            end_date = st.date_input(
                label="",
                value=datetime.strptime(config.get("end_date", "2024-12-20"), "%Y-%m-%d")
            )
        
        # 验证日期范围
        validate_date(start_date, end_date)
        
        # 策略参数
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("ma_period"))
        with input_col:
            ma_period = st.number_input(
                label="",
                value=config.get("ma_period", 55),
                min_value=1
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("ma_protection"))
        with input_col:
            ma_protection = st.checkbox(
                label="",
                value=config.get("ma_protection", True)
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("initial_positions"))
        with input_col:
            initial_positions = st.number_input(
                label="",
                value=config.get("initial_positions", 0),
                min_value=0
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("initial_cash"))
        with input_col:
            initial_cash = st.number_input(
                label="",
                value=config.get("initial_cash", 100000),
                min_value=0
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("min_buy_times"))
        with input_col:
            min_buy_times = st.number_input(
                label="",
                value=config.get("min_buy_times", 2),
                min_value=1
            )
        
        # 价格区间
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("min_value"))
        with input_col:
            price_range_min = st.number_input(
                label="",
                value=st.session_state.get("price_range_min", config.get("price_range_min", 3.9)),
                format="%.3f"
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("max_value"))
        with input_col:
            price_range_max = st.number_input(
                label="",
                value=st.session_state.get("price_range_max", config.get("price_range_max", 4.3)),
                format="%.3f"
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("optimization_trials"))
        with input_col:
            n_trials = st.number_input(
                label="",
                value=config.get("n_trials", 100),
                min_value=1
            )
        
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("display_top_n_results"))
        with input_col:
            top_n = st.number_input(
                label="",
                value=config.get("top_n", 5),
                min_value=1
            )
        
        # 分段设置
        label_col, input_col = st.columns([1, 1])
        with label_col:
            st.markdown("#### " + l("segmented_backtest"))
        with input_col:
            enable_segments = st.checkbox(
                label="",
                value=config.get("enable_segments", False)
            )
        
        if enable_segments:
            label_col, input_col = st.columns([1, 1])
            with label_col:
                st.markdown("#### " + l("calculation_method"))
            with input_col:
                profit_calc_method = st.selectbox(
                    label="",
                    options=["mean", "median"],
                    index=0 if config.get("profit_calc_method", "mean") == "mean" else 1
                )
            
            label_col, input_col = st.columns([1, 1])
            with label_col:
                st.markdown("#### " + l("connect_segments"))
            with input_col:
                connect_segments = st.checkbox(
                    label="",
                    value=config.get("connect_segments", False)
                )
            
            # 显示每段天数
            segment_days = update_segment_days(min_buy_times)
            if segment_days:
                st.info(segment_days)
        else:
            profit_calc_method = "mean"
            connect_segments = False
            
        return (start_date, end_date, ma_period, ma_protection, initial_positions, 
                initial_cash, min_buy_times, price_range_min, price_range_max, 
                n_trials, top_n, enable_segments, profit_calc_method, connect_segments)

def handle_symbol_name_update():
    """处理证券名称更新"""
    try:
        # 检查是否需要通过股票名称更新股票代码
        symbol_name_input = st.session_state.get("symbol_name_input", "")
        last_symbol_name = st.session_state.get("last_symbol_name", "")
        print(f"[DEBUG] Checking symbol name update - current: {symbol_name_input}, last: {last_symbol_name}")
        
        if symbol_name_input and symbol_name_input != last_symbol_name:
            print(f"[DEBUG] Symbol name changed from {last_symbol_name} to {symbol_name_input}")
            # 通过名称获取代码
            symbol_code, security_type = get_symbol_by_name(symbol_name_input)
            print(f"[DEBUG] Got symbol code: {symbol_code}, type: {security_type}")
            
            if symbol_code:
                # 更新session state
                st.session_state["internal_symbol"] = symbol_code
                print(f"[DEBUG] Updated internal_symbol to: {symbol_code}")
                
                # 获取股票信息
                name, security_type = get_symbol_info(symbol_code)
                print(f"[DEBUG] Got symbol info - name: {name}")
                
                if name:
                    st.session_state["symbol_name"] = name
                    st.session_state["last_symbol_name"] = name
                    
                    # 获取价格区间
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    price_range = calculate_price_range(
                        symbol_code,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                        security_type
                    )
                    print(f"[DEBUG] Got price range: {price_range}")
                    
                    if price_range[0] is not None:
                        st.session_state["price_range_min"] = price_range[0]
                        st.session_state["price_range_max"] = price_range[1]
                        print(f"[DEBUG] Updated session state with price range: {price_range}")
                        
    except Exception as e:
        print(f"[ERROR] Error in symbol name update: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")
        st.error(f"发生错误: {str(e)}")

def validate_date(start_date: datetime, end_date: datetime) -> bool:
    """验证日期范围"""
    try:
        print(f"[DEBUG] Validating date range - start_date: {start_date}, end_date: {end_date}")
        if start_date >= end_date:
            print("[DEBUG] Date validation failed: end_date must be later than start_date")
            st.error(l("end_date_must_be_later_than_start_date"))
            st.session_state['date_validation_failed'] = True
            return False
        print("[DEBUG] Date validation passed")
        st.session_state['date_validation_failed'] = False
        return True
    except Exception as e:
        print(f"[ERROR] Date validation error: {str(e)}")
        st.error(l("date_validation_error_format").format(str(e)))
        st.session_state['date_validation_failed'] = True
        return False

def update_segment_days(min_buy_times: int) -> str:
    """更新分段天数示"""
    try:
        from segment_utils import get_segment_days
        days = get_segment_days(min_buy_times)
        return f"{l('days_per_segment')}: {days} {l('trading_days')}"
    except Exception as e:
        logging.error(f"计算分段天数失败: {str(e)}")
        return "" 

def validate_all_inputs(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    ma_period: int,
    initial_positions: int,
    initial_cash: float,
    min_buy_times: int,
    price_range_min: float,
    price_range_max: float,
    n_trials: int,
    top_n: int
) -> bool:
    """验证所有输入参数"""
    try:
        # 验证证券代码
        if not validate_symbol(symbol):
            return False
            
        # 验证日期范围
        if not validate_date(start_date, end_date):
            return False
            
        # 验证MA周期
        if ma_period <= 0:
            st.error(l("ma_period_must_be_greater_than_0"))
            return False
            
        # 验证初始持仓
        if initial_positions < 0:
            st.error(l("initial_positions_must_be_greater_than_or_equal_to_0"))
            return False
            
        # 验证初始资金
        if not validate_initial_cash(initial_cash):
            return False
            
        # 验证最小买入次数
        if not validate_min_buy_times(min_buy_times):
            return False
            
        # 验证价格区间
        if not validate_price_range(price_range_min, price_range_max):
            return False
            
        # 验证优化次数
        if not validate_n_trials(n_trials):
            return False
            
        # 验证显示结果数量
        if not validate_top_n(top_n):
            return False
            
        return True
        
    except Exception as e:
        st.error(l("parameter_validation_error_format").format(str(e)))
        return False

def validate_symbol(symbol: str) -> bool:
    """验证证券代码"""
    try:
        print(f"[DEBUG] Validating symbol: {symbol}")
        if not symbol:
            print("[DEBUG] Symbol is empty")
            st.error(l("please_enter_symbol_name_or_code"))
            return False
        
        if not is_valid_symbol(symbol):
            print(f"[DEBUG] Symbol {symbol} is not valid")
            st.error(l("please_enter_valid_symbol_code"))
            return False
        
        print(f"[DEBUG] Symbol {symbol} is valid")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error validating symbol: {str(e)}")
        st.error(l("failed_to_validate_symbol_format").format(str(e)))
        return False

def validate_initial_cash(initial_cash: int) -> bool:
    """验证初始资金"""
    try:
        if initial_cash < 0:
            st.error(l("initial_cash_must_be_greater_than_or_equal_to_0"))
            return False
        return True
    except Exception as e:
        st.error(l("initial_cash_validation_error_format").format(str(e)))
        return False

def validate_min_buy_times(min_buy_times: int) -> bool:
    """验证最小买入次数"""
    try:
        if min_buy_times <= 0:
            st.error(l("min_buy_times_must_be_greater_than_0"))
            return False
        return True
    except Exception as e:
        st.error(l("min_buy_times_validation_error_format").format(str(e)))
        return False

def validate_price_range(price_range_min: float, price_range_max: float) -> bool:
    """验证价格区间"""
    try:
        if price_range_min >= price_range_max:
            st.error(l("price_range_min_must_be_less_than_price_range_max"))
            return False
        return True
    except Exception as e:
        st.error(l("price_range_validation_error_format").format(str(e)))
        return False

def validate_n_trials(n_trials: int) -> bool:
    """验证优化次数"""
    try:
        if n_trials <= 0:
            st.error(l("n_trials_must_be_greater_than_0"))
            return False
        return True
    except Exception as e:
        st.error(l("n_trials_validation_error_format").format(str(e)))
        return False

def validate_top_n(top_n: int) -> bool:
    """验证显示结果数量"""
    try:
        if top_n <= 0:
            st.error(l("top_n_must_be_greater_than_0"))
            return False
        return True
    except Exception as e:
        st.error(l("top_n_validation_error_format").format(str(e)))
        return False 