import streamlit as st
from datetime import datetime, timedelta
import json
import os
import logging
import pandas as pd
import sys

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from grid_strategy import GridStrategy
from trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol
import optuna
from locales.localization import _

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 获取项目根目录的路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT_DIR, "data", "grid_strategy_config.json")

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
                "start_date": "2023-10-10",
                "end_date": "2023-12-20",
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
            save_config(default_config)
            return default_config
    except Exception as e:
        st.error(_("config_load_error_format").format(str(e)))
        return {}

def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(_("config_save_error_format").format(str(e)))

def validate_symbol(symbol: str) -> bool:
    """验证证券代码"""
    if not symbol:
        st.error(_("please_enter_symbol_code"))
        return False
    
    try:
        if not is_valid_symbol(symbol):
            st.error(_("please_enter_valid_symbol_code"))
            return False
    except Exception as e:
        st.error(_("failed_to_validate_symbol_format").format(str(e)))
        return False
    
    return True

def validate_date(start_date: datetime, end_date: datetime) -> bool:
    """验证日期"""
    if end_date <= start_date:
        st.error(_("end_date_must_be_later_than_start_date"))
        return False
    
    return True

def validate_initial_cash(initial_cash: float) -> bool:
    """验证初始资金"""
    if initial_cash < 0:
        st.error(_("initial_cash_must_be_greater_than_or_equal_to_0"))
        return False
    
    return True

def validate_min_buy_times(min_buy_times: int) -> bool:
    """验证最小买入次数"""
    if min_buy_times <= 0:
        st.error(_("min_buy_times_must_be_greater_than_0"))
        return False
    
    return True

def validate_price_range(price_range_min: float, price_range_max: float) -> bool:
    """验证价格区间"""
    if price_range_min >= price_range_max:
        st.error(_("price_range_min_must_be_less_than_price_range_max"))
        return False
    
    return True

def validate_n_trials(n_trials: int) -> bool:
    """验证优化次数"""
    if n_trials <= 0:
        st.error(_("n_trials_must_be_greater_than_0"))
        return False
    
    return True

def validate_top_n(top_n: int) -> bool:
    """验证显示结果数量"""
    if top_n <= 0:
        st.error(_("top_n_must_be_greater_than_0"))
        return False
    
    return True

def optimize_strategy(optimizer, config):
    """
    使用optuna优化策略参数
    """
    try:
        # 创建优化器实例
        study = optuna.create_study(
            study_name="grid_strategy_optimization",
            direction="maximize"
        )
        
        def objective(trial):
            # 生成参数
            up_sell_rate = trial.suggest_float("up_sell_rate", 0.003, 0.03, step=0.001)
            up_callback_rate = trial.suggest_float("up_callback_rate", 0.001, up_sell_rate * 0.3, step=0.001)
            down_buy_rate = trial.suggest_float("down_buy_rate", 0.003, 0.03, step=0.001)
            down_rebound_rate = trial.suggest_float("down_rebound_rate", 0.001, down_buy_rate * 0.3, step=0.001)
            shares_per_trade = trial.suggest_int("shares_per_trade", 1000, 10000, step=1000)
            
            # 设置参数
            optimizer.up_sell_rate = up_sell_rate
            optimizer.up_callback_rate = up_callback_rate
            optimizer.down_buy_rate = down_buy_rate
            optimizer.down_rebound_rate = down_rebound_rate
            optimizer.shares_per_trade = shares_per_trade
            
            # 运行回测
            profit_rate = optimizer.backtest(
                start_date=config["start_date"],
                end_date=config["end_date"],
                verbose=False
            )
            
            # 记录交易统计
            trial.set_user_attr("trade_count", len(optimizer.trades))
            trial.set_user_attr("failed_trades", optimizer.failed_trades)
            
            return profit_rate
        
        # 运行优化
        study.optimize(objective, n_trials=config["n_trials"])
        
        # 获取最佳参数
        best_params = study.best_params
        best_value = study.best_value
        
        # 使用最佳参数运行一次详细回测
        optimizer.up_sell_rate = best_params["up_sell_rate"]
        optimizer.up_callback_rate = best_params["up_callback_rate"]
        optimizer.down_buy_rate = best_params["down_buy_rate"]
        optimizer.down_rebound_rate = best_params["down_rebound_rate"]
        optimizer.shares_per_trade = best_params["shares_per_trade"]
        
        final_profit_rate = optimizer.backtest(
            start_date=config["start_date"],
            end_date=config["end_date"],
            verbose=True
        )
        
        # 返回优化结果
        return {
            "best_params": best_params,
            "best_profit_rate": best_value,
            "study": study,
            "sorted_trials": sorted(study.trials, key=lambda t: t.value, reverse=True)
        }
        
    except Exception as e:
        logging.error(_("optimization_error_format").format(str(e)))
        raise e

def start_optimization(symbol, symbol_name, start_date, end_date, ma_period, ma_protection,
                     initial_positions, initial_cash, min_buy_times, price_range_min, price_range_max,
                     n_trials, top_n, progress_bar, status_text):
    """开始优化过程"""
    try:
        # 验证所有输入
        if not validate_symbol(symbol):
            return
        
        if not validate_date(start_date, end_date):
            return
        
        if not validate_initial_cash(initial_cash):
            return
        
        if not validate_min_buy_times(min_buy_times):
            return
        
        if not validate_price_range(price_range_min, price_range_max):
            return
        
        if not validate_n_trials(n_trials):
            return
        
        if not validate_top_n(top_n):
            return
        
        # 保存配置
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
            "top_n": top_n
        })
        
        # 创建策略实例
        logging.info(f"{_('creating_strategy_instance')}: {symbol} ({symbol_name})")
        optimizer = GridStrategy(symbol=symbol, symbol_name=symbol_name)
        
        # 设置基本参数
        optimizer.base_price = price_range_min
        optimizer.price_range = (price_range_min, price_range_max)
        optimizer.initial_positions = initial_positions
        optimizer.initial_cash = initial_cash
        optimizer.ma_period = ma_period
        optimizer.ma_protection = ma_protection
        
        # 设置证券类型
        optimizer.security_type = "ETF" if len(symbol) == 6 and symbol.startswith(("1", "5")) else "STOCK"
        logging.info(f"{_('setting_security_type')}: {optimizer.security_type}")
        
        # 更新状态
        status_text.text(_("waiting_to_start"))
        
        # 开始优化
        logging.info(_("starting_optimization"))
        try:
            results = optimize_strategy(optimizer, {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "n_trials": n_trials
            })
            
            # 显示优化结果
            st.header(_("optimization_results"))
            
            # 显示最佳参数
            st.subheader(_("best_parameter_combination"))
            best_params = results["best_params"]
            col5, col6 = st.columns(2)
            with col5:
                st.metric(_("best_profit_rate"), f"{results['best_profit_rate']:.2f}%")
                st.write(_("parameter_details"))
                st.write(f"- {_('up_sell')}: {best_params['up_sell_rate']*100:.2f}%")
                st.write(f"- {_('up_callback')}: {best_params['up_callback_rate']*100:.2f}%")
                st.write(f"- {_('down_buy')}: {best_params['down_buy_rate']*100:.2f}%")
                st.write(f"- {_('down_rebound')}: {best_params['down_rebound_rate']*100:.2f}%")
                st.write(f"- {_('shares_per_trade')}: {best_params['shares_per_trade']:,}")
            
            # 显示前N个结果
            st.subheader(_("top_n_results_format").format(top_n))
            for i, trial in enumerate(results["sorted_trials"][:top_n], 1):
                with st.expander(_("rank_profit_rate_format").format(i, trial.value)):
                    st.write(_("parameter_combination"))
                    for param, value in trial.params.items():
                        if param in ['up_sell_rate', 'up_callback_rate', 'down_buy_rate', 'down_rebound_rate']:
                            st.write(f"- {_(param)}: {value*100:.2f}%")
                        else:
                            st.write(f"- {_(param)}: {value:,}")
                    st.write(f"{_('trade_count')}: {trial.user_attrs['trade_count']}")
                    st.write(_("failed_trade_statistics"))
                    for reason, count in trial.user_attrs['failed_trades'].items():
                        if count > 0:
                            st.write(_("failed_trade_count_format").format(reason, count))
            
        except Exception as e:
            st.error(_("optimization_error_format").format(str(e)))
            logging.error(_("optimization_error_format").format(str(e)))
        
        finally:
            # 完成进度条
            progress_bar.progress(100)
            status_text.text(_("optimization_complete"))
            
    except Exception as e:
        st.error(_("app_error_format").format(str(e)))
        logging.error(_("app_error_format").format(str(e)))

def main():
    """主函数"""
    try:
        # 设置页面
        st.set_page_config(
            page_title=_("app_title"),
            page_icon="📈",
            layout="wide"
        )
        
        # 标题
        st.title(_("app_title"))
        
        # 侧边栏参数设置
        with st.sidebar:
            st.header(_("param_settings"))
            
            # 加载配置文件
            config = load_config()
            
            # 证券代码
            symbol = st.text_input(
                _("symbol_code"),
                value=config.get("symbol", "159300")
            )
            
            # 证券名称
            symbol_name = st.text_input(
                _("symbol_name"),
                value=config.get("symbol_name", "300ETF")
            )
            
            # 日期范围
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    _("start_date"),
                    value=datetime.strptime(config.get("start_date", "2024-10-10"), "%Y-%m-%d").date()
                )
            with col2:
                end_date = st.date_input(
                    _("end_date"),
                    value=datetime.strptime(config.get("end_date", "2024-12-20"), "%Y-%m-%d").date()
                )
            
            # 均线参数
            ma_period = st.number_input(
                _("ma_period"),
                value=int(config.get("ma_period", 55)),
                min_value=1
            )
            
            ma_protection = st.checkbox(
                _("ma_protection"),
                value=config.get("ma_protection", True)
            )
            
            # 资金和持仓
            initial_positions = st.number_input(
                _("initial_positions"),
                value=int(config.get("initial_positions", 0)),
                min_value=0
            )
            
            initial_cash = st.number_input(
                _("initial_cash"),
                value=int(config.get("initial_cash", 100000)),
                min_value=1
            )
            
            # 交易参数
            min_buy_times = st.number_input(
                _("min_buy_times"),
                value=int(config.get("min_buy_times", 2)),
                min_value=1
            )
            
            # 价格区间
            col3, col4 = st.columns(2)
            with col3:
                price_range_min = st.number_input(
                    _("min_value"),
                    value=float(config.get("price_range_min", 3.9)),
                    format="%.3f"
                )
            with col4:
                price_range_max = st.number_input(
                    _("max_value"),
                    value=float(config.get("price_range_max", 4.3)),
                    format="%.3f"
                )
            
            # 优化参数
            n_trials = st.number_input(
                _("optimization_trials"),
                value=int(config.get("n_trials", 100)),
                min_value=1
            )
            
            top_n = st.number_input(
                _("show_top_n_results"),
                value=int(config.get("top_n", 5)),
                min_value=1
            )
            
            # 显示进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 开始优化按钮
            if st.button(_("start_optimization")):
                start_optimization(
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
                    progress_bar=progress_bar,
                    status_text=status_text
                )
        
    except Exception as e:
        st.error(_("app_error_format").format(str(e)))
        logging.error(_("app_error_format").format(str(e)))

if __name__ == "__main__":
    main() 