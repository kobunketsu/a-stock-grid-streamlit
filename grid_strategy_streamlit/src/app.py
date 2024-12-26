import streamlit as st
from datetime import datetime, timedelta
import json
import os
import logging
import pandas as pd
import sys
from typing import Dict, Optional, Tuple, Any

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from grid_strategy import GridStrategy
from trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol
import optuna
from locales.localization import _
from stock_grid_optimizer import GridStrategyOptimizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 获取项目根目录的路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT_DIR, "data", "grid_strategy_config.json")

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
    """
    验证所有输入参数
    """
    try:
        # 验证证券代码
        if not validate_symbol(symbol):
            return False
            
        # 验证日期范围
        if not validate_date(start_date, end_date):
            return False
            
        # 验证MA周期
        if ma_period <= 0:
            st.error(_("ma_period_must_be_greater_than_0"))
            return False
            
        # 验证初始持仓
        if initial_positions < 0:
            st.error(_("initial_positions_must_be_greater_than_or_equal_to_0"))
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
        st.error(_("parameter_validation_error_format").format(str(e)))
        return False

def display_optimization_results(results: Dict[str, Any], top_n: int) -> None:
    """
    Display optimization results in Streamlit
    
    Args:
        results: Dictionary containing optimization results
        top_n: Number of top results to display
    """
    if not results:
        return
        
    st.header(_("optimization_results"))
    
    # 获取前N个结果并过滤掉收益率<=0的结果
    valid_trials = [trial for trial in results["sorted_trials"] if -trial.value > 0]
    sorted_trials = sorted(valid_trials, key=lambda t: t.value)[:top_n]
    
    if not sorted_trials:
        st.write(_("no_parameter_combinations_with_profit_greater_than_0_found"))
        return
    
    # 参数名称映射，与tk版保持一致
    param_names = {
        'up_sell_rate': _('up_sell'),
        'up_callback_rate': _('up_callback'),            
        'down_buy_rate': _('down_buy'),
        'down_rebound_rate': _('down_rebound'),
        'shares_per_trade': _('shares_per_trade')
    }
    
    # 显示所有参数组合
    for i, trial in enumerate(sorted_trials, 1):
        profit_rate = -trial.value
        st.subheader(_("parameter_combination_format").format(i, profit_rate))
        
        # 按照param_names的顺序显示参数
        for key in param_names.keys():
            value = trial.params[key]
            if key == 'shares_per_trade':
                st.write(f"- {param_names[key]}: {value:,}")
            else:
                st.write(f"- {param_names[key]}: {value*100:.2f}%")
        
        st.write(f"{_('trade_count')}: {trial.user_attrs['trade_count']}")
        
        # 显示失败交易统计
        st.write(_("failed_trade_statistics"))
        failed_trades = eval(trial.user_attrs["failed_trades"])
        for reason, count in failed_trades.items():
            if count > 0:
                st.write(f"- {_(reason)}: {count} {_('times')}")
        
        # 显示分段结果（如果有）
        if "segment_results" in trial.user_attrs:
            st.write(_("segment_results"))
            segment_results = eval(trial.user_attrs["segment_results"])
            for j, result in enumerate(segment_results, 1):
                st.write(f"\n{_('segment')} {j}:")
                st.write(f"- {_('period')}: {result['start_date']} {_('to')} {result['end_date']}")
                st.write(f"- {_('profit_rate')}: {result['profit_rate']:.2f}%")
                st.write(f"- {_('trade_count')}: {result['trades']}")
                if result['failed_trades']:
                    st.write(_("failed_trade_statistics"))
                    for reason, count in result['failed_trades'].items():
                        if count > 0:
                            st.write(f"  - {_(reason)}: {count} {_('times')}")
        
        # 添加查看详细交易记录的按钮
        if st.button(_("view_details"), key=f"details_{i}"):
            display_trade_details(trial)
            
        # 添加分隔线
        if i < len(sorted_trials):
            st.markdown("---")

def display_trade_details(trial: Any) -> None:
    """
    Display trade details for a specific trial
    
    Args:
        trial: Trial object containing trading details
    """
    if not trial:
        return
        
    st.subheader(_("trade_details"))
    
    # 获取参数和收益率
    params = trial.params
    profit_rate = -trial.value
    
    # 显示参数组合信息
    st.write(_("parameter_combination_details"))
    st.write(f"{_('total_profit_rate')}: {profit_rate:.2f}%\n")
    
    # 参数名称映射
    param_names = {
        'up_sell_rate': _('up_sell'),
        'up_callback_rate': _('up_callback'),            
        'down_buy_rate': _('down_buy'),
        'down_rebound_rate': _('down_rebound'),
        'shares_per_trade': _('shares_per_trade')
    }
    
    # 显示参数详情
    st.write(_("parameter_details"))
    for key, value in params.items():
        if key == 'shares_per_trade':
            st.write(f"{param_names[key]}: {value:,}")
        else:
            st.write(f"{param_names[key]}: {value*100:.2f}%")
    
    # 显示交易统计信息
    st.write(f"{_('trade_count')}: {trial.user_attrs.get('trade_count', 'N/A')}")
    
    # 显示分段回测结果（如果有）
    if 'segment_results' in trial.user_attrs:
        st.write("=== " + _("segmented_backtest_details") + " ===")
        segment_results = eval(trial.user_attrs["segment_results"])
        for i, segment in enumerate(segment_results, 1):
            st.write(f"\n{_('segment')} {i}:")
            st.write(f"{_('time_period')}: {segment['start_date']} - {segment['end_date']}")
            st.write(f"{_('profit_rate')}: {segment['profit_rate']:.2f}%")
            st.write(f"{_('trade_count')}: {segment['trades']}")
            
            # 显示失败交易统计（如果有）
            if segment.get('failed_trades'):
                st.write("\n" + _("failed_trade_statistics") + ":")
                for reason, count in segment['failed_trades'].items():
                    if count > 0:
                        st.write(f"  {_(reason)}: {count} {_('times')}")
    
    # 显示交易记录（如果有）
    if 'trade_records' in trial.user_attrs:
        st.write("\n=== " + _("trade_records") + " ===")
        trade_records = eval(trial.user_attrs["trade_records"])
        for record in trade_records:
            st.write(record)

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 创建默认配置
            default_config = {
                "symbol": "159300",
                "symbol_name": "",
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
                "enable_segments": False,
                "profit_calc_method": "mean",
                "connect_segments": False
            }
            save_config(default_config)
            return default_config
    except Exception as e:
        st.error(_("config_load_error_format").format(str(e)))
        return {}

def save_config(config):
    """保存配置文件"""
    try:
        # 确保配置文件目录存在
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(_("config_save_error_format").format(str(e)))

def validate_symbol(symbol: str) -> bool:
    """验证证券代码"""
    try:
        if not symbol:
            st.error(_("please_enter_symbol_code"))
            return False
        
        if not is_valid_symbol(symbol):
            st.error(_("please_enter_valid_symbol_code"))
            return False
        
        return True
        
    except Exception as e:
        st.error(_("failed_to_validate_symbol_format").format(str(e)))
        return False

def update_symbol_info(symbol: str) -> Tuple[str, Tuple[float, float]]:
    """
    更新证券信息，返回证券名称和价格区间
    """
    try:
        # 获取证券信息
        name, security_type = get_symbol_info(symbol)
        if name is None:
            st.error(_("symbol_not_found"))
            return None, None
        
        # 获取价格区间
        price_min, price_max = calculate_price_range(symbol, datetime.now() - timedelta(days=30), datetime.now(), security_type)
        if price_min is None or price_max is None:
            st.error(_("failed_to_get_price_range"))
            return name, None
        
        return name, (price_min, price_max)
        
    except Exception as e:
        st.error(_("failed_to_update_symbol_info_format").format(str(e)))
        return None, None

def validate_date(start_date: datetime, end_date: datetime) -> bool:
    """验证日期范围"""
    try:
        if start_date >= end_date:
            st.error(_("end_date_must_be_later_than_start_date"))
            return False
        return True
    except Exception as e:
        st.error(_("date_validation_error_format").format(str(e)))
        return False

def validate_initial_cash(initial_cash: int) -> bool:
    """验证初始资金"""
    try:
        if initial_cash < 0:
            st.error(_("initial_cash_must_be_greater_than_or_equal_to_0"))
            return False
        return True
    except Exception as e:
        st.error(_("initial_cash_validation_error_format").format(str(e)))
        return False

def validate_min_buy_times(min_buy_times: int) -> bool:
    """验证最小买入次数"""
    try:
        if min_buy_times <= 0:
            st.error(_("min_buy_times_must_be_greater_than_0"))
            return False
        return True
    except Exception as e:
        st.error(_("min_buy_times_validation_error_format").format(str(e)))
        return False

def validate_price_range(price_range_min: float, price_range_max: float) -> bool:
    """验证价格区间"""
    try:
        if price_range_min >= price_range_max:
            st.error(_("price_range_min_must_be_less_than_price_range_max"))
            return False
        return True
    except Exception as e:
        st.error(_("price_range_validation_error_format").format(str(e)))
        return False

def validate_n_trials(n_trials: int) -> bool:
    """验证优化次数"""
    try:
        if n_trials <= 0:
            st.error(_("n_trials_must_be_greater_than_0"))
            return False
        return True
    except Exception as e:
        st.error(_("n_trials_validation_error_format").format(str(e)))
        return False

def validate_top_n(top_n: int) -> bool:
    """验证显示结果数量"""
    try:
        if top_n <= 0:
            st.error(_("top_n_must_be_greater_than_0"))
            return False
        return True
    except Exception as e:
        st.error(_("top_n_validation_error_format").format(str(e)))
        return False

def optimize_strategy(optimizer, config):
    """
    使用optuna优化策略参数
    
    Args:
        optimizer: GridStrategyOptimizer 实例
        config: 配置参数字典
    
    Returns:
        dict: 优化结果，包含最佳参数和收益率等信息
    """
    try:
        # 运行优化
        results = optimizer.optimize(n_trials=config["n_trials"])
        
        if results is None:
            st.error(_("optimization_cancelled"))
            return None
            
        # 返回优化结果
        return results
        
    except Exception as e:
        st.error(_("optimization_error_format").format(str(e)))
        logging.error(f"优化过程发生错误: {str(e)}")
        return None

def start_optimization(
    symbol: str,
    symbol_name: str,
    start_date: datetime,
    end_date: datetime,
    ma_period: int,
    ma_protection: bool,
    initial_positions: int,
    initial_cash: float,
    min_buy_times: int,
    price_range_min: float,
    price_range_max: float,
    n_trials: int,
    top_n: int,
    profit_calc_method: str = "mean",
    connect_segments: bool = False,
    progress_bar=None,
    status_text=None
) -> Optional[Dict]:
    """
    执行优化过程
    """
    try:
        # 参数验证
        if not validate_all_inputs(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            ma_period=ma_period,
            initial_positions=initial_positions,
            initial_cash=initial_cash,
            min_buy_times=min_buy_times,
            price_range_min=price_range_min,
            price_range_max=price_range_max,
            n_trials=n_trials,
            top_n=top_n
        ):
            return None
            
        # 更新状态
        if status_text:
            status_text.text(_("initializing_optimization"))
        if progress_bar:
            progress_bar.progress(0)
        
        # 创建优化器实例
        optimizer = GridStrategyOptimizer(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            security_type="ETF" if symbol.startswith("1") else "STOCK",
            ma_period=ma_period,
            ma_protection=ma_protection,
            initial_positions=initial_positions,
            initial_cash=initial_cash,
            min_buy_times=min_buy_times,
            price_range=(price_range_min, price_range_max),
            profit_calc_method=profit_calc_method,
            connect_segments=connect_segments
        )
        
        # 设置进度回调
        def progress_callback(study, trial):
            if progress_bar:
                progress = (len(study.trials) / n_trials) * 100
                progress_bar.progress(int(progress))
            if status_text:
                status_text.text(_("optimization_progress_format").format(
                    len(study.trials),
                    n_trials,
                    -study.best_value if study.best_value is not None else 0
                ))
        
        # 执行优化
        study = optuna.create_study(direction="minimize")
        study.optimize(optimizer.objective, n_trials=n_trials, callbacks=[progress_callback])
        
        # 整理结果
        results = {
            "study": study,
            "sorted_trials": sorted(study.trials, key=lambda t: t.value)
        }
        
        if status_text:
            status_text.text(_("optimization_completed"))
        if progress_bar:
            progress_bar.progress(100)
        
        return results
        
    except Exception as e:
        st.error(_("optimization_error_format").format(str(e)))
        logging.error(f"优化过程发生错误: {str(e)}")
        return None

def update_segment_days(min_buy_times: int) -> str:
    """
    更新分段天数显示
    """
    try:
        from segment_utils import get_segment_days
        days = get_segment_days(min_buy_times)
        return f"{_('days_per_segment')}: {days} {_('trading_days')}"
    except Exception as e:
        logging.error(f"计算分段天数失败: {str(e)}")
        return ""

def main():
    """
    Main function for the Streamlit app
    """
    st.set_page_config(
        page_title=_("app_title"),
        page_icon="📈",
        layout="wide"
    )
    
    st.title(_("app_title"))
    
    # Load configuration
    config = load_config()
    
    # Create three columns for the layout
    params_col, results_col, details_col = st.columns([1, 2, 1])
    
    # Left column - Parameters
    with params_col:
        # Basic parameters
        symbol = st.text_input(_("symbol_code"), value=config.get("symbol", "159300"), key="symbol_input")
        
        # 证券代码改变时更新信息
        if symbol != config.get("symbol", ""):
            if validate_symbol(symbol):
                name, price_range = update_symbol_info(symbol)
                if name:
                    st.session_state.symbol_name = name
                    if price_range:
                        st.session_state.price_range_min = price_range[0]
                        st.session_state.price_range_max = price_range[1]
        
        symbol_name = st.text_input(_("symbol_name"), 
                                  value=st.session_state.get("symbol_name", config.get("symbol_name", "")),
                                  disabled=True)
        start_date = st.date_input(_("start_date"), 
                                 value=datetime.strptime(config.get("start_date", "2024-10-10"), "%Y-%m-%d"))
        end_date = st.date_input(_("end_date"), 
                               value=datetime.strptime(config.get("end_date", "2024-12-20"), "%Y-%m-%d"))
        
        # Strategy parameters
        ma_period = st.number_input(_("ma_period"), value=config.get("ma_period", 55), min_value=1)
        ma_protection = st.checkbox(_("ma_protection"), value=config.get("ma_protection", True))
        initial_positions = st.number_input(_("initial_positions"), value=config.get("initial_positions", 0), min_value=0)
        initial_cash = st.number_input(_("initial_cash"), value=config.get("initial_cash", 100000), min_value=0)
        min_buy_times = st.number_input(_("min_buy_times"), value=config.get("min_buy_times", 2), min_value=1)
        
        # Price range parameters
        price_range_min = st.number_input(
            _("min_value"),
            value=st.session_state.get("price_range_min", config.get("price_range_min", 3.9)),
            format="%.3f"
        )
        price_range_max = st.number_input(
            _("max_value"),
            value=st.session_state.get("price_range_max", config.get("price_range_max", 4.3)),
            format="%.3f"
        )
        n_trials = st.number_input(_("optimization_trials"), value=config.get("n_trials", 100), min_value=1)
        top_n = st.number_input(_("show_top_n_results"), value=config.get("top_n", 5), min_value=1)
        
        # Segment settings
        enable_segments = st.checkbox(_("segmented_backtest"), value=config.get("enable_segments", False))
        if enable_segments:
            profit_calc_method = st.selectbox(
                _("calculation_method"),
                options=["mean", "median"],
                index=0 if config.get("profit_calc_method", "mean") == "mean" else 1
            )
            connect_segments = st.checkbox(_("connect_segments"), value=config.get("connect_segments", False))
            
            # 显示每段天数
            segment_days = update_segment_days(min_buy_times)
            if segment_days:
                st.text(segment_days)
        else:
            profit_calc_method = "mean"
            connect_segments = False
            
        # Add start button at the bottom of parameters
        if st.button(_("start_optimization")):
            # Validate all inputs
            if not validate_all_inputs(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                ma_period=ma_period,
                initial_positions=initial_positions,
                initial_cash=initial_cash,
                min_buy_times=min_buy_times,
                price_range_min=price_range_min,
                price_range_max=price_range_max,
                n_trials=n_trials,
                top_n=top_n
            ):
                return
            
            # Save configuration
            save_config({
                "symbol": symbol,
                "symbol_name": symbol_name,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "ma_period": ma_period,
                "ma_protection": ma_protection,
                "initial_positions": initial_positions,
                "initial_cash": initial_cash,
                "min_buy_times": min_buy_times,
                "price_range_min": price_range_min,
                "price_range_max": price_range_max,
                "n_trials": n_trials,
                "top_n": top_n,
                "enable_segments": enable_segments,
                "profit_calc_method": profit_calc_method,
                "connect_segments": connect_segments
            })
            
            # 创建进度条和状态文本容器
            with results_col:
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            # Start optimization
            results = start_optimization(
                symbol=symbol,
                symbol_name=symbol_name,
                start_date=start_date,
                end_date=end_date,
                ma_period=ma_period,
                ma_protection=ma_protection,
                initial_positions=initial_positions,
                initial_cash=initial_cash,
                min_buy_times=min_buy_times,
                price_range_min=price_range_min,
                price_range_max=price_range_max,
                n_trials=n_trials,
                top_n=top_n,
                profit_calc_method=profit_calc_method,
                connect_segments=connect_segments,
                progress_bar=progress_bar,
                status_text=status_text
            )
            
            if results:
                # Display optimization results in the middle column
                with results_col:
                    display_optimization_results(results, top_n)
                
                # Display trade details in the right column
                with details_col:
                    if results["sorted_trials"]:
                        display_trade_details(results["sorted_trials"][0])

if __name__ == "__main__":
    main() 