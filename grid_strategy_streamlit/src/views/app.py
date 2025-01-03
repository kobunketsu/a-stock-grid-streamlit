import streamlit as st
from datetime import datetime, timedelta
import json
import os
import logging
import pandas as pd
import sys
from typing import Dict, Optional, Tuple, Any

# 获取项目根目录的路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 配置文件路径
CONFIG_FILE = os.path.join(ROOT_DIR, "resources", "data", "grid_strategy_config.json")

# 导入本地化函数并初始化
from src.utils.localization import l, load_translations
from src.utils.browser_utils import get_user_agent
load_translations()  # 确保在使用前初始化翻译

# 其他导入
from src.services.business.grid_strategy import GridStrategy
from src.services.business.trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol, get_symbol_by_name
import optuna
from src.services.business.stock_grid_optimizer import GridStrategyOptimizer
from src.views.parameter_panel import (
    create_parameter_inputs, handle_symbol_name_update, validate_date,
    validate_all_inputs, validate_symbol, validate_initial_cash,
    validate_min_buy_times, validate_price_range, validate_n_trials,
    validate_top_n
)

# 给 st 添加获取用户代理的方法
st.get_user_agent = get_user_agent

# 初始化页面配置（必须是第一个st命令）
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'expanded'  # 初始时展开

st.set_page_config(
    page_title=l("app_title"),
    page_icon="📈",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state
)

#region 初始化和配置
#初始化和配置相关函数，包括：
#- 页面配置初始化
#- 设备检测 
#- 状态管理
#- 配置文件处理
def init_page_config():
    """初始化页面配置"""
    print("[DEBUG] Initializing page config")
    
    # 加载外部CSS文件
    css_path = os.path.join(ROOT_DIR, "static", "css", "main.css")
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # 初始化遮罩层状态
    if 'show_mask' not in st.session_state:
        st.session_state['show_mask'] = False

def init_device_detection():
    """初始化设备检测"""
    print("[DEBUG] Initializing device detection")
    if 'is_mobile' not in st.session_state:
        st.session_state['is_mobile'] = detect_mobile()
        print(f"[DEBUG] Initial device detection: {st.session_state['is_mobile']}")
    
    # 每次运行时重新检测设备类型（因为用户可能在运行时切换设备模式）
    current_is_mobile = detect_mobile()
    if current_is_mobile != st.session_state['is_mobile']:
        print(f"[DEBUG] Device type changed: {st.session_state['is_mobile']} -> {current_is_mobile}")
        st.session_state['is_mobile'] = current_is_mobile
        st.rerun()  # 重新运行以应用新的布局

def init_optimization_state():
    """初始化优化状态"""
    if 'optimization_running' not in st.session_state:
        st.session_state.optimization_running = False
    if 'show_mask' not in st.session_state:
        st.session_state.show_mask = False

def detect_mobile():
    """检测是否为移动设备"""
    try:
        # 获取用户代理字符串
        user_agent = st.get_user_agent()
        print(f"[DEBUG] User Agent: {user_agent}")
        
        # 检查是否为移动设备
        is_mobile = any(device in user_agent.lower() for device in [
            'iphone', 'ipod', 'ipad', 'android', 'mobile', 'blackberry', 
            'webos', 'incognito', 'webmate', 'bada', 'nokia', 'midp', 
            'phone', 'opera mobi', 'opera mini'
        ])
        
        print(f"[DEBUG] Device detection - is_mobile: {is_mobile}")
        return is_mobile
        
    except Exception as e:
        print(f"[ERROR] Error detecting mobile device: {str(e)}")
        return False

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
        st.error(l("config_load_error_format").format(str(e)))
        return {}

def save_config(config):
    """保存配置文件"""
    try:
        # 确保配置文件目录存在
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(l("config_save_error_format").format(str(e)))

#endregion

#region 页面布局
# 页面布局相关函数，包括：
# - 布局列创建
# - 参数输入区域
# - 优化按钮
# - 证券名称更新处理
def create_layout_columns():
    """创建布局列"""
    print("[DEBUG] Creating layout columns")
    params_col, results_col, details_col = st.columns([2, 2, 2])
    st.session_state['params_col'] = params_col
    st.session_state['results_col'] = results_col
    st.session_state['details_col'] = details_col
    return params_col, results_col, details_col

def create_mask_layer():
    """创建遮罩层，在优化过程中阻止参数输入交互"""
    if st.session_state.get('optimization_running', False):
        # 添加遮罩层样式
        st.markdown(
            """
            <style>
            .mask-layer {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.5);
                z-index: 999990;
                pointer-events: all;
            }

            /* 不修改sidebar的z-index 999991，让它保持默认行为 */

            /* 为sidebar内的控件添加额外的遮罩 */
            section[data-testid="stSidebar"] .element-container {
                pointer-events: none !important;
            }

            /* 保持必要控件可交互 */
            div[data-testid="stButton"],
            div[data-testid="stProgressBar"] {
                position: relative;
                z-index: 1000000;
                pointer-events: all !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # 添加遮罩层元素
        st.markdown(
            '<div class="mask-layer"></div>',
            unsafe_allow_html=True
        )

def create_optimization_button():
    """创建优化按钮"""
    # 添加按钮的自定义样式
    st.markdown("""
        <style>
            div[data-testid="stButton"] {
                left: 0;
                right: 0;
                bottom: 0;
                position: fixed !important;
                margin: 0 !important;
                padding: 0 !important;
                background: gray !important;
                width: 100% !important;
            }
            div[data-testid="stButton"] button {
                width: 100% !important;
                padding: 0.5rem !important;
                border-radius: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    button_disabled = st.session_state.get('date_validation_failed', False)
    print(f"[DEBUG] Button disabled state: {button_disabled}")
    
    return st.button(
        l("cancel_optimization") if st.session_state.optimization_running else l("start_optimization"),
        use_container_width=True,
        disabled=button_disabled
    )

#endregion

#region 优化控制
#优化控制相关函数，包括：
#- 优化状态切换
#- 优化过程处理  
#- 策略优化执行
def toggle_optimization():
    """切换优化状态（开始/取消）"""
    if not st.session_state.get('optimization_running', False):
        # 开始优化
        st.session_state['optimization_running'] = True
    else:
        # 取消优化
        cancel_optimization()

def cancel_optimization():
    """取消优化"""
    st.session_state['optimization_running'] = False
    if 'optimizer' in st.session_state:
        optimizer = st.session_state['optimizer']
        optimizer.optimization_running = False
        del st.session_state['optimizer']
    st.rerun()

def handle_optimization(config, params):
    """处理优化过程"""
    (start_date, end_date, ma_period, ma_protection, initial_positions, 
     initial_cash, min_buy_times, price_range_min, price_range_max, 
     n_trials, top_n, enable_segments, profit_calc_method, connect_segments) = params
    
    progress_container = st.container()
    with progress_container:
        progress_text = l("optimization_progress_format").format("0", str(n_trials))
        progress_bar = st.progress(0, progress_text)
    
    # 从session state获取symbol
    symbol = st.session_state.get("internal_symbol", "")
    if not symbol:
        st.error(l("please_input_valid_symbol"))
        return
    
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
    
    print("[DEBUG] Saving configuration")
    # Save configuration
    save_config({
        "symbol": symbol,
        "symbol_name": st.session_state.get("symbol_name_input", ""),
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
    
    print("[DEBUG] Starting optimization")
    # Start optimization
    results = start_optimization(
        symbol=symbol,
        symbol_name=st.session_state.get("symbol_name_input", ""),
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
        progress_bar=progress_bar
    )
    
    if results:
        print("[DEBUG] Optimization completed successfully")
        # Display optimization results
        st.session_state['new_results'] = True
        st.session_state['optimization_results'] = results
        st.session_state.optimization_running = False
        # 优化完成后设置sidebar状态为collapsed（收起）
        st.session_state.sidebar_state = 'collapsed'
        st.rerun()
    else:
        print("[DEBUG] Optimization failed or was cancelled")
        if st.session_state.optimization_running:
            cancel_optimization()
        else:
            st.rerun()

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
    """执行优化过程"""
    try:
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
        
        # 设置进度条和状态文本
        optimizer.progress_bar = progress_bar
        optimizer.status_text = None  # 不再使用单独的状态文本
        
        # 存储优化器实例到session state
        st.session_state.optimizer = optimizer
        
        # 运行优化
        results = optimizer.optimize(n_trials=n_trials)
        
        # 检查是否被取消
        if not optimizer.optimization_running:
            return None
            
        return results
        
    except Exception as e:
        st.error(l("optimization_error_format").format(str(e)))
        logging.error(f"优化过程发生错误: {str(e)}")
        return None

def optimize_strategy(optimizer, config):
    """使用optuna优化策略参数"""
    try:
        # 运行优化
        results = optimizer.optimize(n_trials=config["n_trials"])
        
        if results is None:
            st.error(l("optimization_cancelled"))
            return None
            
        # 返回优化结果
        return results
        
    except Exception as e:
        st.error(l("optimization_error_format").format(str(e)))
        logging.error(f"优化过程发生错误: {str(e)}")
        return None

#endregion

#region 结果显示
#结果显示相关函数，包括：
#- 优化结果展示
#- 交易详情显示  
#- 策略详情展示
def display_results(top_n):
    """显示优化结果"""
    print("[DEBUG] Checking for existing results")
    if 'optimization_results' in st.session_state:
        try:
            if st.session_state.get('new_results', False):
                print("[DEBUG] Displaying new optimization results")
                display_optimization_results(st.session_state['optimization_results'], top_n)
                st.session_state['new_results'] = False
            else:
                print("[DEBUG] Displaying existing optimization results")
                display_optimization_results(None, top_n)
        except Exception as e:
            print(f"[ERROR] Error displaying optimization results: {str(e)}")
            import traceback
            print(f"[ERROR] Stack trace: {traceback.format_exc()}")
            st.error(f"显示优化结果时发生错误: {str(e)}")

def display_optimization_results(results: Dict[str, Any], top_n: int) -> None:
    """显示优化结果详情"""
    print("[DEBUG] Entering display_optimization_results")
    
    # 获取全局列对象
    results_col = st.session_state.get('results_col')
    details_col = st.session_state.get('details_col')
    
    if results_col is None or details_col is None:
        print("[DEBUG] Layout columns not found in session state")
        return
    
    # 如果是新的优化结果，则更新session state
    if results is not None:
        print("[DEBUG] Storing new optimization results in session state")
        st.session_state['optimization_results'] = results
        st.session_state['sorted_trials'] = sorted(results["sorted_trials"], key=lambda t: t.value)
        # 只在第一次显示结果时初始化状态
        if 'display_details' not in st.session_state:
            st.session_state['display_details'] = False
            st.session_state['current_trial'] = None
            st.session_state['current_trial_index'] = None
            
        # 保存当前的配置信息
        st.session_state['saved_config'] = {
            'symbol': st.session_state.get('symbol_input', ''),
            'symbol_name': st.session_state.get('symbol_name', ''),
            'start_date': st.session_state.get('start_date', datetime.strptime('2024-10-10', '%Y-%m-%d')),
            'end_date': st.session_state.get('end_date', datetime.strptime('2024-12-20', '%Y-%m-%d')),
            'initial_cash': st.session_state.get('initial_cash', 100000),
            'initial_positions': st.session_state.get('initial_positions', 0),
            'price_range_min': st.session_state.get('price_range_min', 3.9),
            'price_range_max': st.session_state.get('price_range_max', 4.3),
            'enable_segments': st.session_state.get('enable_segments', False),
            'min_buy_times': st.session_state.get('min_buy_times', 2),
            'profit_calc_method': st.session_state.get('profit_calc_method', 'mean')
        }
        print(f"[DEBUG] Saved config: {st.session_state['saved_config']}")
        
        # 确保sidebar收起
        if not isinstance(st.session_state, dict):
            st.session_state.sidebar_state = 'collapsed'
        else:
            st.session_state['sidebar_state'] = 'collapsed'
        
    elif 'optimization_results' not in st.session_state:
        print("[DEBUG] No results to display")
        return
        
    # 在结果列中显示优化结果
    with results_col:
        # 如果是移动端且需要滚动到顶部
        if st.session_state.get('is_mobile', False) and st.session_state.get('scroll_to_top', False):
            print("[DEBUG] Adding scroll to top script")
            st.write("[DEBUG] 准备执行sidebar收起操作")
            results_col.markdown("""
                <script>
                    // 发送开始消息
                    fetch('/_stcore/upload', {
                        method: 'POST',
                        body: JSON.stringify({type: 'debug', message: '开始尝试收起sidebar'})
                    });
                    
                    window.scrollTo(0, 0);
                    // 收起sidebar
                    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
                    if (sidebar) {
                        const button = sidebar.querySelector('button[aria-label="Close sidebar"]');
                        if (!button) {
                            // 如果找不到关闭按钮，尝试查找展开按钮的父元素并点击
                            const expanderDiv = sidebar.querySelector('div[data-testid="collapsedControl"]');
                            if (expanderDiv) {
                                expanderDiv.click();
                                // 发送成功消息
                                fetch('/_stcore/upload', {
                                    method: 'POST',
                                    body: JSON.stringify({type: 'debug', message: '成功点击展开按钮父元素'})
                                });
                            }
                        } else {
                            button.click();
                            // 发送成功消息
                            fetch('/_stcore/upload', {
                                method: 'POST',
                                body: JSON.stringify({type: 'debug', message: '成功点击关闭按钮'})
                            });
                        }
                    }
                </script>
                """, unsafe_allow_html=True)
            st.write("[DEBUG] sidebar收起操作执行完成")
            st.session_state['scroll_to_top'] = False
            print("[DEBUG] Reset scroll_to_top flag")
        
        st.markdown(f"### {l('optimization_results')}")
        print("[DEBUG] Filtering valid trials")
        # 获取前N个结果并过滤掉收益率<=0的结果
        valid_trials = [trial for trial in st.session_state['sorted_trials'] if -trial.value > 0]
        sorted_trials = valid_trials[:top_n]
        
        print(f"[DEBUG] Found {len(valid_trials)} valid trials")
        print(f"[DEBUG] Displaying top {len(sorted_trials)} trials")
        
        if not sorted_trials:
            print("[DEBUG] No valid trials found")
            st.write(l("no_parameter_combinations_with_profit_greater_than_0_found"))
            return
        
        # 参数名称映射，与tk版保持一致
        param_names = {
            'up_sell_rate': l('up_sell'),
            'up_callback_rate': l('up_callback'),            
            'down_buy_rate': l('down_buy'),
            'down_rebound_rate': l('down_rebound'),
            'shares_per_trade': l('shares_per_trade')
        }
        
        # 显示所有参数组合
        for i, trial in enumerate(sorted_trials, 1):
            profit_rate = -trial.value
            print(f"[DEBUG] Displaying trial {i} with profit rate {profit_rate}")
            
            # 使用 expander 来组织每个组合的显示
            with st.expander(l("parameter_combination_format").format(i, profit_rate), expanded=True):
                # 按照param_names的顺序显示参数
                for key in param_names.keys():
                    value = trial.params[key]
                    if key == 'shares_per_trade':
                        st.write(f"- {param_names[key]}: {value:,}")
                    else:
                        st.write(f"- {param_names[key]}: {value*100:.2f}%")
                
                st.write(f"{l('trade_count')}: {trial.user_attrs['trade_count']}")
                
                # 显示失败交易统计
                failed_trades = eval(trial.user_attrs["failed_trades"])
                if any(count > 0 for count in failed_trades.values()):
                    st.write(l("failed_trade_statistics"))
                    for reason, count in failed_trades.items():
                        if count > 0:
                            st.write(f"- {l(reason)}: {count} {l('times')}")
                
                # 显示分段结果（如果有）
                if "segment_results" in trial.user_attrs:
                    st.write(l("segment_results"))
                    segment_results = eval(trial.user_attrs["segment_results"])
                    for j, result in enumerate(segment_results, 1):
                        st.write(f"\n{l('segment')} {j}:")
                        st.write(f"- {l('period')}: {result['start_date']} {l('to')} {result['end_date']}")
                        st.write(f"- {l('profit_rate')}: {result['profit_rate']:.2f}%")
                        st.write(f"- {l('trade_count')}: {result['trades']}")
                        if result['failed_trades']:
                            st.write(l("failed_trade_statistics"))
                            for reason, count in result['failed_trades'].items():
                                if count > 0:
                                    st.write(f"  - {l(reason)}: {count} {l('times')}")
                
                # 添加查看详细交易记录的按钮
                button_key = f"details_{i}_{id(trial)}"  # 使用trial对象的id确保key的唯一
                print(f"[DEBUG] Creating view details button with key: {button_key}")
                if st.button(l("view_details"), key=button_key):
                    print(f"[DEBUG] View details button {i} clicked")
                    st.session_state['display_details'] = True
                    st.session_state['current_trial'] = trial
                    st.session_state['current_trial_index'] = i - 1
                    
                    # 恢复保存的配置信息
                    if 'saved_config' in st.session_state:
                        print(f"[DEBUG] Restoring saved config: {st.session_state['saved_config']}")
                        for key, value in st.session_state['saved_config'].items():
                            st.session_state[key] = value
                            print(f"[DEBUG] Restored {key} = {value}")
                            
                    st.rerun()
    
    # 在详情列中显示交易详情
    with details_col:
        print("[DEBUG] Checking conditions for displaying details")
        print(f"[DEBUG] display_details={st.session_state.get('display_details')}")
        print(f"[DEBUG] current_trial exists={st.session_state.get('current_trial') is not None}")
        
        if st.session_state.get('display_details', False) and st.session_state.get('current_trial') is not None:
            close_button_key = "close_details_" + str(id(st.session_state['current_trial']))  # 使用唯一的key
            if st.button(l("close_details"), key=close_button_key):
                st.session_state['display_details'] = False
                st.session_state['current_trial'] = None
                st.session_state['current_trial_index'] = None
                st.rerun()
            else:
                print(f"[DEBUG] Displaying details for trial")
                display_strategy_details(st.session_state['current_trial'].params)
        else:
            print("[DEBUG] No trial selected for details")
            st.write(l("click_view_details_to_see_trade_details"))

def display_trade_details(trial: Any) -> None:
    """显示交易详情"""
    print("[DEBUG] Entering display_trade_details")
    print(f"[DEBUG] Trial object exists: {trial is not None}")
    
    if not trial:
        print("[DEBUG] No trial object provided")
        return
        
    st.subheader(l("trade_details"))
    
    # 创建策略实例
    strategy = GridStrategy(
        symbol=st.session_state.get('symbol', ''),
        symbol_name=st.session_state.get('symbol_name', '')
    )
    
    # 使用format_trial_details方法获取显示内容
    output_lines = strategy.format_trial_details(trial)
    
    # 显示内容
    for line in output_lines:
        st.write(line)

def update_symbol_info(symbol: str) -> Tuple[str, Tuple[float, float]]:
    """更新证券信息返回证券名称和价格区间"""
    try:
        print(f"[DEBUG] Updating symbol info for: {symbol}")
        # 获证券信息
        name, security_type = get_symbol_info(symbol)
        print(f"[DEBUG] Got symbol info - name: {name}, type: {security_type}")
        if name is None:
            print("[DEBUG] Symbol not found")
            st.error(l("symbol_not_found"))
            return None, None
        
        # 获价格区间
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        print(f"[DEBUG] Calculating price range from {start_date} to {end_date}")
        price_min, price_max = calculate_price_range(
            symbol,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            security_type
        )
        print(f"[DEBUG] Got price range - min: {price_min}, max: {price_max}")
        if price_min is None or price_max is None:
            print("[DEBUG] Failed to get price range")
            st.error(l("failed_to_get_price_range"))
            return name, None
        
        print(f"[DEBUG] Successfully updated symbol info - name: {name}, price range: ({price_min}, {price_max})")
        return name, (price_min, price_max)
        
    except Exception as e:
        print(f"[ERROR] Error updating symbol info: {str(e)}")
        st.error(l("failed_to_update_symbol_info_format").format(str(e)))
        return None, None

def update_segment_days(min_buy_times: int) -> str:
    """更新分段天数示"""
    try:
        from segment_utils import get_segment_days
        days = get_segment_days(min_buy_times)
        return f"{l('days_per_segment')}: {days} {l('trading_days')}"
    except Exception as e:
        logging.error(f"计算分段天数失败: {str(e)}")
        return ""

def display_strategy_details(strategy_params):
    """显示特定参数组合的策略详情"""
    print("[DEBUG] Entering display_strategy_details")
    print(f"[DEBUG] Strategy params: {strategy_params}")
    
    st.subheader(l("trade_details"))
    
    # 获取时间段
    try:
        # 从session_state获取日期对象
        start_date = st.session_state.get('start_date')
        end_date = st.session_state.get('end_date')
        
        print(f"[DEBUG] Initial dates from session state - start_date: {start_date}, end_date: {end_date}")
        
        # 如果是字符串，转换为datetime对象
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
        # 如果没有获取到日期，使用默认值
        if not start_date:
            start_date = datetime.strptime('2024-10-10', '%Y-%m-%d')
        if not end_date:
            end_date = datetime.strptime('2024-12-20', '%Y-%m-%d')
            
        print(f"[DEBUG] Final dates - start_date: {start_date}, end_date: {end_date}")
    except Exception as e:
        st.error(f"日期格式错误: {str(e)}")
        print(f"[DEBUG] Date parsing error: {str(e)}")
        return
    
    # 获取是否启用多段回测
    enable_segments = st.session_state.get('enable_segments', False)
    segments = None
    
    print(f"[DEBUG] Enable segments: {enable_segments}")
    
    if enable_segments:
        # 使用segment_utils中的方法构建时段
        from segment_utils import build_segments
        segments = build_segments(
            start_date=start_date,
            end_date=end_date,
            min_buy_times=int(st.session_state.get('min_buy_times', 2))
        )
        print(f"[DEBUG] Built segments: {segments}")
    
    # 创建策略实例
    symbol = st.session_state.get('symbol', '')
    symbol_name = st.session_state.get('symbol_name', '')
    print(f"[DEBUG] Creating strategy with symbol: {symbol}, symbol_name: {symbol_name}")
    
    strategy = GridStrategy(
        symbol=symbol,
        symbol_name=symbol_name
    )
    
    # 设置初始资金和持仓
    initial_cash = float(st.session_state.get('initial_cash', 100000))
    initial_positions = int(st.session_state.get('initial_positions', 0))
    print(f"[DEBUG] Setting initial cash: {initial_cash}, initial positions: {initial_positions}")
    
    strategy.initial_cash = initial_cash
    strategy.initial_positions = initial_positions
    
    # 设置基准价格和价格范围
    price_range_min = float(st.session_state.get('price_range_min', 3.9))
    price_range_max = float(st.session_state.get('price_range_max', 4.3))
    print(f"[DEBUG] Setting price range: min={price_range_min}, max={price_range_max}")
    
    strategy.base_price = price_range_min
    strategy.price_range = (price_range_min, price_range_max)
    
    try:
        # 运行策略详情分析
        print("[DEBUG] Running strategy details analysis")
        results = strategy.run_strategy_details(
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            segments=segments
        )
        
        if results is None:
            print("[DEBUG] Strategy details analysis returned None")
            st.error(l("strategy_analysis_no_results"))
            return
            
        print(f"[DEBUG] Strategy details analysis results: {results}")
        
        # 使用format_trade_details方法获取显示内容
        print("[DEBUG] Formatting trade details")
        output_lines = strategy.format_trade_details(
            results=results,
            enable_segments=enable_segments,
            segments=segments,
            profit_calc_method=st.session_state.get('profit_calc_method', 'mean')
        )
        
        print(f"[DEBUG] Formatted output lines: {output_lines}")
        
        # 显示内容
        for line in output_lines:
            st.write(line)
        
    except Exception as e:
        print(f"[DEBUG] Error running strategy details: {str(e)}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
        st.error(f"{l('run_strategy_details_error_format').format(error=str(e))}")
        return

#endregion



def display_strategy_details(strategy_params):
    """显示特定参数组合的策略详情"""
    print("[DEBUG] Entering display_strategy_details")
    print(f"[DEBUG] Strategy params: {strategy_params}")
    
    st.subheader(l("trade_details"))
    
    # 获取时间段
    try:
        # 从session_state获取日期对象
        start_date = st.session_state.get('start_date')
        end_date = st.session_state.get('end_date')
        
        print(f"[DEBUG] Initial dates from session state - start_date: {start_date}, end_date: {end_date}")
        
        # 如果是字符串，转换为datetime对象
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
        # 如果没有获取到日期，使用默认值
        if not start_date:
            start_date = datetime.strptime('2024-10-10', '%Y-%m-%d')
        if not end_date:
            end_date = datetime.strptime('2024-12-20', '%Y-%m-%d')
            
        print(f"[DEBUG] Final dates - start_date: {start_date}, end_date: {end_date}")
    except Exception as e:
        st.error(f"日期格式错误: {str(e)}")
        print(f"[DEBUG] Date parsing error: {str(e)}")
        return
    
    # 获取是否启用多段回测
    enable_segments = st.session_state.get('enable_segments', False)
    segments = None
    
    print(f"[DEBUG] Enable segments: {enable_segments}")
    
    if enable_segments:
        # 使用segment_utils中的方法构建时段
        from segment_utils import build_segments
        segments = build_segments(
            start_date=start_date,
            end_date=end_date,
            min_buy_times=int(st.session_state.get('min_buy_times', 2))
        )
        print(f"[DEBUG] Built segments: {segments}")
    
    # 创建策略实例
    symbol = st.session_state.get('symbol', '')
    symbol_name = st.session_state.get('symbol_name', '')
    print(f"[DEBUG] Creating strategy with symbol: {symbol}, symbol_name: {symbol_name}")
    
    strategy = GridStrategy(
        symbol=symbol,
        symbol_name=symbol_name
    )
    
    # 设置初始资金和持仓
    initial_cash = float(st.session_state.get('initial_cash', 100000))
    initial_positions = int(st.session_state.get('initial_positions', 0))
    print(f"[DEBUG] Setting initial cash: {initial_cash}, initial positions: {initial_positions}")
    
    strategy.initial_cash = initial_cash
    strategy.initial_positions = initial_positions
    
    # 设置基准价格和价格范围
    price_range_min = float(st.session_state.get('price_range_min', 3.9))
    price_range_max = float(st.session_state.get('price_range_max', 4.3))
    print(f"[DEBUG] Setting price range: min={price_range_min}, max={price_range_max}")
    
    strategy.base_price = price_range_min
    strategy.price_range = (price_range_min, price_range_max)
    
    try:
        # 运行策略详情分析
        print("[DEBUG] Running strategy details analysis")
        results = strategy.run_strategy_details(
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            segments=segments
        )
        
        if results is None:
            print("[DEBUG] Strategy details analysis returned None")
            st.error(l("strategy_analysis_no_results"))
            return
            
        print(f"[DEBUG] Strategy details analysis results: {results}")
        
        # 使用format_trade_details方法获取显示内容
        print("[DEBUG] Formatting trade details")
        output_lines = strategy.format_trade_details(
            results=results,
            enable_segments=enable_segments,
            segments=segments,
            profit_calc_method=st.session_state.get('profit_calc_method', 'mean')
        )
        
        print(f"[DEBUG] Formatted output lines: {output_lines}")
        
        # 显示内容
        for line in output_lines:
            st.write(line)
        
    except Exception as e:
        print(f"[DEBUG] Error running strategy details: {str(e)}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        print(f"[DEBUG] Stack trace: {traceback.format_exc()}")
        st.error(f"{l('run_strategy_details_error_format').format(error=str(e))}")
        return


#region 主函数
#主程序入口
def main():
    """主函数"""
    try:
        print("[DEBUG] Starting main function")
        
        # 初始化页面配置
        init_page_config()
        
        # 创建遮罩层（如果正在优化）
        create_mask_layer()
        
        # 初始化设备检测
        init_device_detection()
        
        # 初始化优化状态
        init_optimization_state()
        
        # 加载配置
        print("[DEBUG] Loading configuration")
        config = load_config()
        print(f"[DEBUG] Loaded config: {config}")
        
        # 创建布局列
        params_col, results_col, details_col = create_layout_columns()
        
        print("[DEBUG] Starting parameter input section")
        
        # 创建参数输入区域
        with st.sidebar:
            try:
                print("[DEBUG] Creating parameter input section")
                # 添加footer容器
                footer_container = st.container()
                
                # Left column - Parameters
                with params_col:
                    handle_symbol_name_update()
                
                # 创建参数输入
                params = create_parameter_inputs(config)
                
                # 创建优化按钮
                if create_optimization_button():
                    print("[DEBUG] Optimization button clicked")
                    toggle_optimization()
                    st.rerun()
                
                # 如果正在优化中，处理优化过程
                if st.session_state.optimization_running:
                    handle_optimization(config, params)
                
            except Exception as e:
                print(f"[ERROR] Error in parameter input section: {str(e)}")
                import traceback
                print(f"[ERROR] Stack trace: {traceback.format_exc()}")
                st.error(f"发生错误: {str(e)}")
        
        # 显示结果
        display_results(params[9])  # params[9] is top_n
                
    except Exception as e:
        print(f"[ERROR] Critical error in main function: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")
        st.error(f"程序发生严重错误: {str(e)}")



if __name__ == "__main__":
    try:
        print("[DEBUG] Starting application")
        main()
        print("[DEBUG] Application completed normally")
    except Exception as e:
        print(f"[ERROR] Application crashed: {str(e)}")
        import traceback
        print(f"[ERROR] Stack trace: {traceback.format_exc()}")
        st.error(f"程序崩溃: {str(e)}") 