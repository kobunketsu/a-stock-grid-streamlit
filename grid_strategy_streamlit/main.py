import streamlit as st
import akshare as ak
from datetime import datetime, timedelta
import json
import os
from stock_grid_optimizer import GridStrategyOptimizer

def load_config():
    """加载配置文件"""
    config_path = "grid_strategy_config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_config(config):
    """保存配置到文件"""
    config_path = "grid_strategy_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def update_symbol_info():
    """更新股票信息"""
    try:
        symbol = st.session_state.symbol
        if len(symbol) == 6:
            if symbol.startswith(("1", "5")):  # ETF
                df = ak.fund_etf_spot_em()
                symbol_info = df[df["代码"] == symbol].iloc[0]
                st.session_state.symbol_name = symbol_info["名称"]
                st.session_state.price_min = float(symbol_info["最低"])
                st.session_state.price_max = float(symbol_info["最高"])
            else:  # 股票
                df = ak.stock_zh_a_spot_em()
                symbol_info = df[df["代码"] == symbol].iloc[0]
                st.session_state.symbol_name = symbol_info["名称"]
                st.session_state.price_min = float(symbol_info["最低"])
                st.session_state.price_max = float(symbol_info["最高"])
    except Exception as e:
        st.error(f"获取股票信息失败: {str(e)}")

def main():
    st.set_page_config(
        page_title="网格交易策略优化器",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("网格交易策略优化器")
    
    # 加载配置
    config = load_config()
    
    # 创建两列布局
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("参数设置")
        
        # 股票代码输入
        symbol = st.text_input(
            "股票代码",
            value=config.get("symbol", "") if config else "",
            help="输入6位股票代码或ETF代码"
        )
        
        if symbol and len(symbol) == 6:
            if "symbol" not in st.session_state or st.session_state.symbol != symbol:
                st.session_state.symbol = symbol
                update_symbol_info()
            
            symbol_name = st.session_state.get("symbol_name", "")
            if symbol_name:
                st.write(f"股票名称: {symbol_name}")
        
        # 日期选择
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.strptime(config.get("start_date", "2023-01-01"), "%Y-%m-%d").date() if config else datetime(2023, 1, 1).date()
            )
        
        with col_date2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.strptime(config.get("end_date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d").date() if config else datetime.now().date()
            )
        
        # MA参数设置
        col_ma1, col_ma2 = st.columns(2)
        with col_ma1:
            ma_period = st.number_input(
                "MA周期",
                value=int(config.get("ma_period", 20)) if config else 20,
                min_value=1
            )
        
        with col_ma2:
            ma_protection = st.checkbox(
                "启用MA保护",
                value=config.get("ma_protection", True) if config else True
            )
        
        # 资金和持仓设置
        col_pos1, col_pos2 = st.columns(2)
        with col_pos1:
            initial_positions = st.number_input(
                "初始持仓",
                value=int(config.get("initial_positions", 0)) if config else 0,
                min_value=0
            )
        
        with col_pos2:
            initial_cash = st.number_input(
                "初始资金",
                value=float(config.get("initial_cash", 100000)) if config else 100000,
                min_value=0.0
            )
        
        # 最小买入次数
        min_buy_times = st.number_input(
            "最小买入次数",
            value=int(config.get("min_buy_times", 3)) if config else 3,
            min_value=1
        )
        
        # 价格区间设置
        st.subheader("价格区间")
        price_range_min = st.number_input(
            "最小值",
            value=float(config.get("price_range_min", getattr(st.session_state, 'price_min', 0.91))) if config else getattr(st.session_state, 'price_min', 0.91),
            format="%.3f"
        )
        
        price_range_max = st.number_input(
            "最大值",
            value=float(config.get("price_range_max", getattr(st.session_state, 'price_max', 1.01))) if config else getattr(st.session_state, 'price_max', 1.01),
            format="%.3f"
        )
        
        # 优化设置
        st.subheader("优化设置")
        n_trials = st.number_input(
            "优化次数",
            value=int(config.get("n_trials", 100)) if config else 100,
            min_value=1
        )
        
        top_n = st.number_input(
            "显示前N个结果",
            value=int(config.get("top_n", 5)) if config else 5,
            min_value=1
        )
        
        # 分段回测设置
        st.subheader("分段回测设置")
        enable_segments = st.checkbox("启用分段回测", value=True)
        
        if enable_segments:
            profit_calc_method = st.selectbox(
                "收益计算方式",
                options=["mean", "median"],
                index=0 if config.get("profit_calc_method", "mean") == "mean" else 1
            )
            
            connect_segments = st.checkbox(
                "子区间资金和持仓衔接",
                value=config.get("connect_segments", False) if config else False
            )
        
        # 保存配置按钮
        if st.button("保存配置"):
            new_config = {
                "symbol": symbol,
                "symbol_name": symbol_name,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "ma_period": str(ma_period),
                "ma_protection": ma_protection,
                "initial_positions": str(initial_positions),
                "initial_cash": str(initial_cash),
                "min_buy_times": str(min_buy_times),
                "price_range_min": f"{price_range_min:.3f}",
                "price_range_max": f"{price_range_max:.3f}",
                "n_trials": str(n_trials),
                "top_n": str(top_n),
                "profit_calc_method": profit_calc_method if enable_segments else "mean",
                "connect_segments": connect_segments if enable_segments else False
            }
            save_config(new_config)
            st.success("配置已保存")
    
    with col2:
        st.subheader("优化结果")
        
        # 开始优化按钮
        if st.button("开始优化", type="primary"):
            with st.spinner("正在优化参数..."):
                # 创建优化器实例
                optimizer = GridStrategyOptimizer(
                    symbol=symbol,
                    security_type="ETF" if len(symbol) == 6 and symbol.startswith(("1", "5")) else "STOCK",
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    ma_period=ma_period,
                    ma_protection=ma_protection,
                    initial_positions=initial_positions,
                    initial_cash=initial_cash,
                    min_buy_times=min_buy_times,
                    price_range=(price_range_min, price_range_max),
                    profit_calc_method=profit_calc_method if enable_segments else "mean",
                    connect_segments=connect_segments if enable_segments else False
                )
                
                # 创建进度条
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                # 优化进度回调函数
                def progress_callback(study, trial):
                    progress = (trial.number + 1) / n_trials
                    progress_bar.progress(progress)
                    progress_text.text(f"优化进度: {progress*100:.1f}%")
                
                # 运行优化
                results = optimizer.optimize(n_trials=n_trials)
                
                if results:
                    # 显示优化结果
                    st.success("优化完成！")
                    
                    # 显示最佳参数
                    st.subheader("最佳参数组合")
                    best_trial = results["sorted_trials"][0]
                    best_params = best_trial.params
                    best_profit = -best_trial.value
                    
                    st.write(f"收益率: {best_profit:.2f}%")
                    st.write("参数详情:")
                    for param, value in best_params.items():
                        if param in ['up_sell_rate', 'down_buy_rate', 'up_callback_rate', 'down_rebound_rate']:
                            st.write(f"- {param}: {value*100:.2f}%")
                        else:
                            st.write(f"- {param}: {value}")
                    
                    # 显示前N个结果
                    st.subheader(f"前 {top_n} 个最佳组合")
                    for i, trial in enumerate(results["sorted_trials"][:top_n], 1):
                        with st.expander(f"组合 {i} - 收益率: {-trial.value:.2f}%"):
                            for param, value in trial.params.items():
                                if param in ['up_sell_rate', 'down_buy_rate', 'up_callback_rate', 'down_rebound_rate']:
                                    st.write(f"- {param}: {value*100:.2f}%")
                                else:
                                    st.write(f"- {param}: {value}")
                            st.write(f"交��次数: {trial.user_attrs.get('trade_count', 'N/A')}")
                            
                            # 显示失败交易统计
                            failed_trades = eval(trial.user_attrs.get("failed_trades", "{}"))
                            if failed_trades:
                                st.write("失败交易统计:")
                                for reason, count in failed_trades.items():
                                    if count > 0:
                                        st.write(f"- {reason}: {count}次")
                else:
                    st.error("优化过程中发生错误")

# 直接调用main函数
if __name__ == "__main__":
    main()
