import streamlit as st
from datetime import datetime, timedelta
import json
import os
import logging
import pandas as pd
from grid_strategy import GridStrategy
from trading_utils import get_symbol_info, calculate_price_range, is_valid_symbol
import optuna

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
        st.error(f"加载配置文件失败: {str(e)}")
        return {}

def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"保存配置文件失败: {str(e)}")

def validate_symbol(symbol: str) -> bool:
    """验证证券代码"""
    if not symbol:
        st.error("请输入证券代码")
        return False
    
    try:
        if not is_valid_symbol(symbol):
            st.error("请输入有效的证券代码")
            return False
    except Exception as e:
        st.error(f"验证证券代码失败: {str(e)}")
        return False
    
    return True

def validate_date(start_date: datetime, end_date: datetime) -> bool:
    """验证日期"""
    if end_date <= start_date:
        st.error("结束日期必须晚于开始日期")
        return False
    
    return True

def validate_initial_cash(initial_cash: float) -> bool:
    """验证初始资金"""
    if initial_cash < 0:
        st.error("initial_cash must be greater than or equal to 0")
        return False
    
    return True

def validate_min_buy_times(min_buy_times: int) -> bool:
    """验证最小买入���数"""
    if min_buy_times <= 0:
        st.error("min_buy_times must be greater than 0")
        return False
    
    return True

def validate_price_range(price_range_min: float, price_range_max: float) -> bool:
    """验证价格区间"""
    if price_range_min >= price_range_max:
        st.error("price_range_min must be less than price_range_max")
        return False
    
    return True

def validate_n_trials(n_trials: int) -> bool:
    """验证优化次数"""
    if n_trials <= 0:
        st.error("n_trials must be greater than 0")
        return False
    
    return True

def validate_top_n(top_n: int) -> bool:
    """验证显示结果数量"""
    if top_n <= 0:
        st.error("top_n must be greater than 0")
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
            up_callback_rate = trial.suggest_float("up_callback_rate", 0.001, min(up_sell_rate * 0.3, 0.01), step=0.001)
            down_buy_rate = trial.suggest_float("down_buy_rate", 0.003, 0.03, step=0.001)
            down_rebound_rate = trial.suggest_float("down_rebound_rate", 0.001, min(down_buy_rate * 0.3, 0.01), step=0.001)
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
        logging.error(f"优化过程出错: {str(e)}")
        raise e

def main():
    """主函数"""
    try:
        # 设置页面
        st.set_page_config(
            page_title="网格交易策略优化",
            page_icon="📈",
            layout="wide"
        )
        
        # 标题
        st.title("网格交易策略优化")
        
        # 侧边栏参数设置
        with st.sidebar:
            st.header("参数设置")
            
            # 加载配置文件
            config = load_config()
            
            # 证券代码
            symbol = st.text_input(
                "证券代码",
                value=config.get("symbol", "159300")
            )
            
            # 证券名称
            symbol_name = st.text_input(
                "证券名称",
                value=config.get("symbol_name", "300ETF")
            )
            
            # 日期范围
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "开始日期",
                    value=datetime.strptime(config.get("start_date", "2024-10-10"), "%Y-%m-%d").date()
                )
            with col2:
                end_date = st.date_input(
                    "结束日期",
                    value=datetime.strptime(config.get("end_date", "2024-12-20"), "%Y-%m-%d").date()
                )
            
            # 均线参数
            ma_period = st.number_input(
                "均线周期",
                value=int(config.get("ma_period", 55)),
                min_value=1
            )
            
            ma_protection = st.checkbox(
                "启用均线保护",
                value=config.get("ma_protection", True)
            )
            
            # 资金和持仓
            initial_positions = st.number_input(
                "初始持仓",
                value=int(config.get("initial_positions", 0)),
                min_value=0
            )
            
            initial_cash = st.number_input(
                "初始资金",
                value=int(config.get("initial_cash", 100000)),
                min_value=1
            )
            
            # 交易参数
            min_buy_times = st.number_input(
                "最少买入次数",
                value=int(config.get("min_buy_times", 2)),
                min_value=1
            )
            
            # 价格区间
            col3, col4 = st.columns(2)
            with col3:
                price_range_min = st.number_input(
                    "最低价格",
                    value=float(config.get("price_range_min", 3.9)),
                    format="%.3f"
                )
            with col4:
                price_range_max = st.number_input(
                    "最高价格",
                    value=float(config.get("price_range_max", 4.3)),
                    format="%.3f"
                )
            
            # 优化参数
            n_trials = st.number_input(
                "优化次数",
                value=int(config.get("n_trials", 100)),
                min_value=1
            )
            
            top_n = st.number_input(
                "显示前N个结果",
                value=int(config.get("top_n", 5)),
                min_value=1
            )
            
            # 开始优化按钮
            if st.button("开始优化"):
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
                logging.info(f"创建策略实例: {symbol} ({symbol_name})")
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
                logging.info(f"设置证券类型: {optimizer.security_type}")
                
                # 显示进度条
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 开始优化
                logging.info("开始执行优化...")
                try:
                    results = optimize_strategy(optimizer, {
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "n_trials": n_trials
                    })
                    
                    # 显示优化结果
                    st.header("优化结果")
                    
                    # 显示最佳参数
                    st.subheader("最佳参数组合")
                    best_params = results["best_params"]
                    col5, col6 = st.columns(2)
                    with col5:
                        st.metric("最佳收益率", f"{results['best_profit_rate']:.2f}%")
                        st.write("参数详情:")
                        st.write(f"- 上涨卖出比率: {best_params['up_sell_rate']*100:.2f}%")
                        st.write(f"- 上涨回调比率: {best_params['up_callback_rate']*100:.2f}%")
                        st.write(f"- 下跌买入比率: {best_params['down_buy_rate']*100:.2f}%")
                        st.write(f"- 下跌反弹比率: {best_params['down_rebound_rate']*100:.2f}%")
                        st.write(f"- 单次交易股数: {best_params['shares_per_trade']:,}")
                    
                    # 显示前N个结果
                    st.subheader(f"前{top_n}个最佳结果")
                    for i, trial in enumerate(results["sorted_trials"][:top_n], 1):
                        with st.expander(f"第{i}名 - 收益率: {trial.value:.2f}%"):
                            st.write("参数组合:")
                            for param, value in trial.params.items():
                                if param in ['up_sell_rate', 'up_callback_rate', 'down_buy_rate', 'down_rebound_rate']:
                                    st.write(f"- {param}: {value*100:.2f}%")
                                else:
                                    st.write(f"- {param}: {value:,}")
                            st.write(f"交易次数: {trial.user_attrs['trade_count']}")
                            st.write("失败交易统计:")
                            for reason, count in trial.user_attrs['failed_trades'].items():
                                if count > 0:
                                    st.write(f"- {reason}: {count}次")
                    
                except Exception as e:
                    st.error(f"优化过程中出错: {str(e)}")
                    logging.error(f"优化过程出错: {str(e)}")
                
                finally:
                    # 完成进度条
                    progress_bar.progress(100)
                    status_text.text("优化完成")
        
    except Exception as e:
        st.error(f"应用程序出错: {str(e)}")
        logging.error(f"应用程序出错: {str(e)}")

if __name__ == "__main__":
    main() 