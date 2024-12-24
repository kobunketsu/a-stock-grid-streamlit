import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import sys
import io
from contextlib import redirect_stdout
import threading
import akshare as ak
import pandas as pd
import json
import os
from ma_utils import calculate_ma_price

class ProgressWindow:
    def __init__(self, total_trials):
        self.total_trials = total_trials
        self.current_trial = 0
        self.root = None
        self.progress = None
        self.percent_label = None
        self.label = None
        self.time_label = None
        self.eta_label = None
        self.start_time = None
        self.is_closed = False
        self.trade_details = None
        self.captured_output = []
        
        # 将变量声明为None，稍后在create_window中初始化
        self.symbol_var = None
        self.symbol_name_var = None
        self.start_date_var = None
        self.end_date_var = None
        self.ma_period_var = None
        self.ma_protection_var = None
        self.initial_positions_var = None
        self.initial_cash_var = None
        self.min_buy_times_var = None
        self.price_range_min_var = None
        self.price_range_max_var = None
        self.n_trials_var = None
        self.top_n_var = None
        
        # 添加分段回测相关变量的初始化
        self.enable_segments = None
        self.profit_calc_method_var = None
        self.connect_segments = None
        self.segment_label = None
        self.segment_mode_combo = None
        self.segment_days_label = None
        self.connect_checkbox = None
        
        self.sort_ascending = False
        self.current_results = []
        
        self.config_file = "grid_strategy_config.json"
        self.optimization_running = False
        self.start_button = None
        
    def create_window(self):
        self.root = tk.Tk()
        self.root.title("网格策略优化器")
        self.root.geometry("1200x800")
        
        # 初始化变量前先加载配置
        self.load_config()
        
        # 如果没有加载到配置，使用默认值初始化变量
        self.symbol_var = tk.StringVar(self.root, value=getattr(self, 'symbol', "159300"))
        self.symbol_name_var = tk.StringVar(self.root, value=getattr(self, 'symbol_name', ""))
        self.start_date_var = tk.StringVar(self.root, value=getattr(self, 'start_date', "2024-10-10"))
        self.end_date_var = tk.StringVar(self.root, value=getattr(self, 'end_date', "2024-12-20"))
        self.ma_period_var = tk.StringVar(self.root, value=getattr(self, 'ma_period', "55"))
        self.ma_protection_var = tk.BooleanVar(self.root, value=getattr(self, 'ma_protection', True))
        self.initial_positions_var = tk.StringVar(self.root, value=getattr(self, 'initial_positions', "0"))
        self.initial_cash_var = tk.StringVar(self.root, value=getattr(self, 'initial_cash', "100000"))
        self.min_buy_times_var = tk.StringVar(self.root, value=getattr(self, 'min_buy_times', "2"))
        self.price_range_min_var = tk.StringVar(value=getattr(self, 'price_range_min', "3.9"))
        self.price_range_max_var = tk.StringVar(value=getattr(self, 'price_range_max', "4.3"))
        self.n_trials_var = tk.StringVar(value=getattr(self, 'n_trials', "100"))
        self.top_n_var = tk.StringVar(value=getattr(self, 'top_n', "5"))
        self.profit_calc_method_var = tk.StringVar(self.root, value=getattr(self, 'profit_calc_method', "mean"))
        self.connect_segments_var = tk.BooleanVar(self.root, value=getattr(self, 'connect_segments', False))
        
        # 创建主布局框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧参数面板
        params_frame = ttk.LabelFrame(main_frame, text="参数设置", padding=10)
        params_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 参数输入控件
        self.create_parameter_inputs(params_frame)
        
        # 中间结果面板
        results_frame = ttk.LabelFrame(main_frame, text="优化结果", padding=10)
        results_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 添加排序按钮
        sort_frame = ttk.Frame(results_frame)
        sort_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.sort_ascending = False  # 排序方向标志
        self.sort_button = ttk.Button(
            sort_frame, 
            text="收益率 ↑", 
            command=self.toggle_sort
        )
        self.sort_button.pack(side=tk.LEFT)
        
        # 创建参数组合列表的画布和滚动条
        self.results_canvas = tk.Canvas(results_frame)
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_canvas.yview)
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建参数组合的容器
        self.params_container = ttk.Frame(self.results_canvas)
        self.results_canvas.create_window((0, 0), window=self.params_container, anchor=tk.NW)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 右侧交易详情面板
        details_frame = ttk.LabelFrame(main_frame, text="交易详情", padding=10)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建交易详情区域
        self.create_trade_details_area(details_frame)
        
        # 底部进度面板
        progress_frame = ttk.LabelFrame(self.root, text="优化进度", padding=10)
        progress_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
        # 创建进度相关控件
        self.create_progress_widgets(progress_frame)
        
        # 设置窗口始终置顶
        self.root.attributes('-topmost', True)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
        
    def create_parameter_inputs(self, parent):
        """创建参数输入控件"""
        # 设置左侧面板的宽度
        parent.configure(width=200)
        
        # 证券代码输入框
        ttk.Label(parent, text="证券代码:").grid(row=0, column=0, sticky=tk.W, pady=2)
        symbol_entry = ttk.Entry(parent, textvariable=self.symbol_var, width=12)
        symbol_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        symbol_entry.bind('<FocusOut>', lambda e: self.validate_symbol(symbol_entry))
        
        # 证券名称输入框
        ttk.Label(parent, text="证券名称:").grid(row=1, column=0, sticky=tk.W, pady=2)
        symbol_name_entry = ttk.Entry(parent, textvariable=self.symbol_name_var, width=12)
        symbol_name_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 绑定事件
        symbol_entry.bind('<FocusOut>', lambda e: self.update_symbol_info('code'))
        symbol_entry.bind('<Return>', lambda e: self.update_symbol_info('code'))
        symbol_name_entry.bind('<FocusOut>', lambda e: self.update_symbol_info('name'))
        symbol_name_entry.bind('<Return>', lambda e: self.update_symbol_info('name'))
        
        # 初始化证券信息
        self.update_symbol_info('code')
        
        # 其他参数输入框从第3行开始
        ttk.Label(parent, text="开始日期:").grid(row=2, column=0, sticky=tk.W, pady=2)
        start_date_entry = ttk.Entry(parent, textvariable=self.start_date_var, width=12)
        start_date_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        start_date_entry.bind('<FocusOut>', lambda e: self.validate_date(start_date_entry))
        
        ttk.Label(parent, text="结束日期:").grid(row=3, column=0, sticky=tk.W, pady=2)
        end_date_entry = ttk.Entry(parent, textvariable=self.end_date_var, width=12)
        end_date_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        end_date_entry.bind('<FocusOut>', lambda e: self.validate_date(end_date_entry))
        
        ttk.Label(parent, text="均线周期:").grid(row=4, column=0, sticky=tk.W, pady=2)
        ma_period_entry = ttk.Entry(parent, textvariable=self.ma_period_var, width=12)
        ma_period_entry.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(parent, text="启用均线保护", variable=self.ma_protection_var).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Label(parent, text="初始持仓:").grid(row=6, column=0, sticky=tk.W, pady=2)
        initial_pos_entry = ttk.Entry(parent, textvariable=self.initial_positions_var, width=12)
        initial_pos_entry.grid(row=6, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(parent, text="初始资金:").grid(row=7, column=0, sticky=tk.W, pady=2)
        initial_cash_entry = ttk.Entry(parent, textvariable=self.initial_cash_var, width=12)
        initial_cash_entry.grid(row=7, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(parent, text="最少买入次数:").grid(row=8, column=0, sticky=tk.W, pady=2)
        min_buy_entry = ttk.Entry(parent, textvariable=self.min_buy_times_var, width=12)
        min_buy_entry.grid(row=8, column=1, sticky=tk.W, pady=2)
        
        # 价格范围框架
        price_range_frame = ttk.LabelFrame(parent, text="价格范围", padding=5)
        price_range_frame.grid(row=9, column=0, columnspan=2, sticky=tk.EW, pady=5)
        
        ttk.Label(price_range_frame, text="最小值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.price_min_entry = ttk.Entry(price_range_frame, textvariable=self.price_range_min_var, width=6)
        self.price_min_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(price_range_frame, text="最大值:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(5,0))
        self.price_max_entry = ttk.Entry(price_range_frame, textvariable=self.price_range_max_var, width=6)
        self.price_max_entry.grid(row=0, column=3, sticky=tk.W, pady=2)
        
        
        # 优化设置
        ttk.Label(parent, text="优化次数:").grid(row=10, column=0, sticky=tk.W, pady=2)
        n_trials_entry = ttk.Entry(parent, textvariable=self.n_trials_var, width=12)
        n_trials_entry.grid(row=10, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(parent, text="显示前N个结果:").grid(row=11, column=0, sticky=tk.W, pady=2)
        top_n_entry = ttk.Entry(parent, textvariable=self.top_n_var, width=12)
        top_n_entry.grid(row=11, column=1, sticky=tk.W, pady=2)
        
        # 添加分隔线
        ttk.Separator(parent, orient='horizontal').grid(
            row=12, column=0, columnspan=2, sticky='ew', pady=10)

        # 分段回测设置框架
        segments_frame = ttk.LabelFrame(parent, text="分段回测设置", padding=5)
        segments_frame.grid(row=13, column=0, columnspan=2, sticky=tk.EW, pady=5)
        
        # 分段回测开关
        self.enable_segments = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            segments_frame,
            text="分段回测",
            variable=self.enable_segments,
            command=self.toggle_segment_options
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 分段收益计算模
        self.segment_label = ttk.Label(segments_frame, text="计算方式:")
        self.segment_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.segment_mode = tk.StringVar(value="平均值")
        self.segment_mode_combo = ttk.Combobox(
            segments_frame, 
            textvariable=self.segment_mode,
            values=["平均值", "中值"],
            state="readonly",
            width=12
        )
        self.segment_mode_combo.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # 添加天数显示标签
        self.segment_days_label = ttk.Label(segments_frame, text="")
        self.segment_days_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 资金持仓衔接选项
        self.connect_segments = tk.BooleanVar(value=False)
        self.connect_checkbox = ttk.Checkbutton(
            segments_frame,
            text="子区间资金和持仓衔接",
            variable=self.connect_segments
        )
        self.connect_checkbox.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 绑定最少买入次数变化事件
        self.min_buy_times_var.trace_add('write', self.update_segment_days)
        
        # 开始优化按钮
        self.start_button = ttk.Button(
            parent, 
            text="开始优化", 
            command=self.toggle_optimization
        )
        self.start_button.grid(row=14, column=0, columnspan=2, pady=10, sticky=tk.EW)
        # 绑定快捷键
        self.root.bind('<Command-Return>', lambda e: self.start_optimization() if not self.optimization_running else self.cancel_optimization())  # macOS
        self.root.bind('<Control-Return>', lambda e: self.start_optimization() if not self.optimization_running else self.cancel_optimization())  # Windows/Linux
        

        # 初始化控件状态
        self.toggle_segment_options()
        
        # 为所有输入框添加焦点事件处理
        all_entries = [
            symbol_entry, start_date_entry, end_date_entry, ma_period_entry,
            initial_pos_entry, initial_cash_entry, min_buy_entry,
            self.price_min_entry, self.price_max_entry, n_trials_entry, top_n_entry
        ]
        
        for entry in all_entries:
            # 绑定点击事件和Tab键事件到同一个处理函数
            entry.bind('<Button-1>', lambda e, widget=entry: self.handle_entry_focus(e, widget))
            entry.bind('<Tab>', lambda e, widget=entry: self.handle_entry_focus(e, widget))
            # 添加焦点进入事件处理
            entry.bind('<FocusIn>', lambda e, widget=entry: self.handle_focus_in(e, widget))
    
    def create_progress_widgets(self, parent):
        """创建进度相关控件"""
        self.label = ttk.Label(parent, text="等待开始...", font=('Arial', 10))
        self.label.pack(pady=5)
        
        self.progress = ttk.Progressbar(parent, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=5)
        
        self.percent_label = ttk.Label(parent, text="0%", font=('Arial', 10))
        self.percent_label.pack(pady=2)
        
        self.time_label = ttk.Label(parent, text="耗时: 0:00:00", font=('Arial', 10))
        self.time_label.pack(pady=2)
        
        self.eta_label = ttk.Label(parent, text="预计剩余: --:--:--", font=('Arial', 10))
        self.eta_label.pack(pady=2)
    
    def start_optimization(self, event=None):
        """开始优化按钮的回调函数"""
        try:
            # 如果已经在运行，直接返回
            if self.optimization_running:
                return
            
            # 获取并验证参数
            symbol = self.symbol_var.get().strip()
            if not symbol:
                messagebox.showerror("参数错误", "请输入证券代码")
                return
            
            # 自动判断证券类型
            security_type = "ETF" if len(symbol) == 6 and symbol.startswith(("1", "5")) else "STOCK"
            
            start_date = datetime.strptime(self.start_date_var.get().strip(), '%Y-%m-%d')
            end_date = datetime.strptime(self.end_date_var.get().strip(), '%Y-%m-%d')
            ma_period = int(self.ma_period_var.get())
            ma_protection = self.ma_protection_var.get()
            initial_positions = int(self.initial_positions_var.get())
            initial_cash = int(self.initial_cash_var.get())
            min_buy_times = int(self.min_buy_times_var.get())
            price_range = (
                float(self.price_range_min_var.get()),
                float(self.price_range_max_var.get())
            )
            n_trials = int(self.n_trials_var.get())
            
            # 更新UI状态
            self.optimization_running = True
            self.start_button.configure(text="取消优化")
            
            # 更新总试验次数
            self.total_trials = int(n_trials * 1.5)
            self.progress["maximum"] = self.total_trials
            
            # 重置进度
            self.current_trial = 0
            self.progress["value"] = 0
            self.percent_label["text"] = "0%"
            self.start_time = datetime.now()
            self.label["text"] = "正在优化参数..."
            
            # 清空之前的结果显示
            for widget in self.params_container.winfo_children():
                widget.destroy()
            
            # 清空交易详情
            self.trade_details.config(state='normal')
            self.trade_details.delete('1.0', tk.END)
            self.trade_details.config(state='disabled')
            
            # 创建优化器实例
            from stock_grid_optimizer import GridStrategyOptimizer  # 避免循环导入
            optimizer = GridStrategyOptimizer(
                symbol=symbol,
                security_type=security_type,  # 传递自动判断的证券类型
                start_date=start_date,
                end_date=end_date,
                ma_period=ma_period,
                ma_protection=ma_protection,
                initial_positions=initial_positions,
                initial_cash=initial_cash,
                min_buy_times=min_buy_times,
                price_range=price_range,
                profit_calc_method=self.profit_calc_method_var.get() if self.enable_segments.get() else None,
                connect_segments=self.connect_segments.get() if self.enable_segments.get() else False
            )
            
            # 进度窗口传递给优化器
            optimizer.progress_window = self
            
            def run_optimization():
                try:
                    # 运行优化
                    results = optimizer.optimize(n_trials=n_trials)
                    
                    if results and not self.is_closed and self.optimization_running:
                        # 在主线程中更新UI
                        def update_ui():
                            if not self.is_closed:
                                self.label["text"] = "优化完成"
                                self.start_button.configure(text="开始优化")
                                self.optimization_running = False
                                # 显示优化结果
                                self.display_optimization_results(results)
                        
                        self.root.after(0, update_ui)
                        
                except Exception as e:
                    if not self.is_closed:
                        self.root.after(0, lambda: messagebox.showerror("优化错误", str(e)))
                        self.label["text"] = "优化失败"
                        self.start_button.configure(text="开始优化")
                        self.optimization_running = False
                finally:
                    # 确保状态正确置
                    if not self.is_closed:
                        self.root.after(0, lambda: self.start_button.configure(text="开始优化"))
                        self.optimization_running = False
            
            # 在新线程中运行优化
            self.optimization_thread = threading.Thread(target=run_optimization)
            self.optimization_thread.daemon = True
            self.optimization_thread.start()
            
        except ValueError as e:
            messagebox.showerror("参数错误", str(e))
            self.start_button.configure(text="开始优化")
            self.optimization_running = False
        except Exception as e:
            messagebox.showerror("错误", f"启动优化失败: {str(e)}")
            self.start_button.configure(text="开始优化")
            self.optimization_running = False
    
    def capture_output(self, text):
        """捕获并存储输出文本"""
        self.captured_output.append(text)
    
    def show_trade_details(self, trial):
        """显示特定参数组合的策略详情"""
        # 清空现有内容
        self.trade_details.config(state='normal')
        self.trade_details.delete('1.0', tk.END)
        
        # 获取数和收益率
        params = trial.params
        profit_rate = -trial.value
        
        # 显示参数组合信息
        self.trade_details.insert(tk.END, "=== 参数组合详情 ===\n")
        self.trade_details.insert(tk.END, f"总收益率: {profit_rate:.2f}%\n\n")
        
        # 参数名称映射
        param_names = {
            'up_sell_rate': '上涨卖出',
            'up_callback_rate': '上涨回调',            
            'down_buy_rate': '下跌买入',
            'down_rebound_rate': '下跌反弹',
            'shares_per_trade': '单次交易股数'
        }
        
        # 显示参数详情
        self.trade_details.insert(tk.END, "参数详情:\n")
        for key, value in params.items():
            if key == 'shares_per_trade':
                self.trade_details.insert(tk.END, f"{param_names[key]}: {value:,}\n")
            else:
                self.trade_details.insert(tk.END, f"{param_names[key]}: {value*100:.2f}%\n")
        
        # 显示交易统计信息
        self.trade_details.insert(tk.END, f"\n交易次数: {trial.user_attrs.get('trade_count', 'N/A')}\n")
        
        # 显示分段回测结果（如果有）
        if 'segment_results' in trial.user_attrs:
            self.trade_details.insert(tk.END, "\n=== 分段回测详情 ===\n")
            for i, segment in enumerate(trial.user_attrs['segment_results'], 1):
                self.trade_details.insert(tk.END, f"\n第{i}段回测:\n")
                self.trade_details.insert(tk.END, f"时间段: {segment['start_date']} - {segment['end_date']}\n")
                self.trade_details.insert(tk.END, f"收益率: {segment['profit_rate']:.2f}%\n")
                self.trade_details.insert(tk.END, f"交易次数: {segment['trades']}\n")
                
                # 显示失败交易统计（如果有）
                if segment.get('failed_trades'):
                    self.trade_details.insert(tk.END, "\n失败交易统计:\n")
                    for reason, count in segment['failed_trades'].items():
                        if count > 0:
                            self.trade_details.insert(tk.END, f"  {reason}: {count}次\n")
        
        # 显示交易记录（如果有）
        if 'trade_records' in trial.user_attrs:
            self.trade_details.insert(tk.END, "\n=== 交易记录 ===\n")
            for record in trial.user_attrs['trade_records']:
                self.trade_details.insert(tk.END, f"{record}\n")
        
        # 恢复只读状态并滚动到顶部
        self.trade_details.config(state='disabled')
        self.trade_details.see('1.0')
    
    def enable_trade_details_button(self):
        """启用交易详情按钮"""
        if self.view_trades_btn:
            self.view_trades_btn.state(['!disabled'])
    
    def _on_closing(self):
        """窗口关闭时的处理"""
        try:
            self.save_config()  # 保存配置
        except Exception as e:
            print(f"保存配置时发生错误: {e}")
        finally:
            self.is_closed = True
            if self.root:
                self.root.destroy()
    
    def _check_thread_and_close(self):
        """检查优化线程是否束，如果结束则关闭窗口"""
        if not self.optimization_thread.is_alive():
            self.root.destroy()
        else:
            self.root.after(100, self._check_thread_and_close)
    
    def update_progress(self, current_trial):
        """更新进度条和相关标签"""
        if self.is_closed:
            return
        
        self.current_trial = current_trial
        progress = min(current_trial, self.total_trials)
        
        # 计算进度百分比
        percent = (progress / self.total_trials) * 100
        
        # 计算已用时间
        elapsed_time = datetime.now() - self.start_time
        
        # 计算预计剩余时间
        if percent > 0:
            total_estimated_time = elapsed_time * (100 / percent)
            remaining_time = total_estimated_time - elapsed_time
        else:
            remaining_time = datetime.now() - datetime.now()
        
        # 在主线程中更新UI
        def update_ui():
            if self.is_closed:
                return
            self.progress["value"] = progress
            self.percent_label["text"] = f"{percent:.1f}%"
            self.time_label["text"] = f"耗时: {str(elapsed_time).split('.')[0]}"
            self.eta_label["text"] = f"预计剩余: {str(remaining_time).split('.')[0]}"
        
        self.root.after(0, update_ui)
    
    def close(self):
        """关闭窗口"""
        if self.root is not None and not self.is_closed:
            self.is_closed = True
            self.root.destroy() 
        
    def update_label(self, text):
        """更新标签文本"""
        if self.root and not self.is_closed:
            try:
                self.label["text"] = text
                self.root.update()
            except tk.TclError:
                pass  # 忽略窗口已关闭的错误
    
    def increase_font_size(self, event=None):
        """增加字体大小"""
        if self.trade_details:
            try:
                # 获取当前字体配置
                current_font = self.trade_details['font']
                if isinstance(current_font, str):
                    # 如果是字符串格式，解析字体名称和大小
                    font_name = current_font.split()[0]
                    size = int(current_font.split()[-1])
                else:
                    # 如果是元组格式，直接获取字体名称和大小
                    font_name, size = current_font.split()[0], int(current_font.split()[1])
                
                # 增加字体大小（最大限制为30）
                new_size = min(size + 1, 30)
                self.trade_details.configure(font=(font_name, new_size))
            except Exception as e:
                print(f"调整字体大小时出错: {e}")
    
    def decrease_font_size(self, event=None):
        """减小字体大小"""
        if self.trade_details:
            try:
                # 获取当前字体配置
                current_font = self.trade_details['font']
                if isinstance(current_font, str):
                    # 如果是字符串格式，解析字体名称和大小
                    font_name = current_font.split()[0]
                    size = int(current_font.split()[-1])
                else:
                    # 如果是元组格式，直接获取字体名称和大小
                    font_name, size = current_font.split()[0], int(current_font.split()[1])
                
                # 减小字体大小（最小限制为6）
                new_size = max(size - 1, 6)
                self.trade_details.configure(font=(font_name, new_size))
            except Exception as e:
                print(f"调整字体大小时出错: {e}")
    
    def focus_search(self, event=None):
        """聚焦到搜索框"""
        self.search_entry.focus_set()
        return "break"
    
    def search_text(self, direction='down'):
        """搜索文本"""
        search_term = self.search_var.get()
        if not search_term:
            self.search_count_label.config(text="")
            return
        
        content = self.trade_details.get("1.0", tk.END)
        matches = content.lower().count(search_term.lower())
        self.search_count_label.config(text=f"找到 {matches} 个匹配")
        
        if matches > 0:
            # 获取当前光标位置
            current_pos = self.trade_details.index(tk.INSERT)
            
            # 根据搜索方向设置开始位置
            if direction == 'down':
                start_pos = current_pos
                search_direction = tk.SEL_FIRST
            else:
                start_pos = "1.0"
                search_direction = tk.SEL_LAST
            
            # 清除现有选择
            self.trade_details.tag_remove('sel', '1.0', tk.END)
            
            # 搜索文本
            pos = self.trade_details.search(
                search_term, 
                start_pos, 
                nocase=True, 
                stopindex=tk.END if direction == 'down' else current_pos
            )
            
            if pos:
                # 选中找到的文本
                line, char = pos.split('.')
                end_pos = f"{line}.{int(char) + len(search_term)}"
                self.trade_details.tag_add('sel', pos, end_pos)
                self.trade_details.mark_set(tk.INSERT, search_direction)
                self.trade_details.see(pos)
            else:
                # 如果没找到，从头/尾开始搜索
                start = "1.0" if direction == 'down' else tk.END
                pos = self.trade_details.search(search_term, start, nocase=True)
                if pos:
                    line, char = pos.split('.')
                    end_pos = f"{line}.{int(char) + len(search_term)}"
                    self.trade_details.tag_add('sel', pos, end_pos)
                    self.trade_details.mark_set(tk.INSERT, search_direction)
                    self.trade_details.see(pos)
    
    def scroll_to_end(self, event=None):
        """滚动到文本末尾"""
        if self.trade_details:
            self.trade_details.see(tk.END)
            # 将插入点移动到最后
            self.trade_details.mark_set(tk.INSERT, tk.END)
            return 'break'  # 阻止事件继续传播
    
    def scroll_to_start(self, event=None):
        """滚动到文本开始"""
        if self.trade_details:
            self.trade_details.see('1.0')
            # 将插入点移动到开始
            self.trade_details.mark_set(tk.INSERT, '1.0')
            return 'break'  # 阻止事件继续传播
    
    def show_strategy_details(self, strategy_params):
        """显示特定参数组合的策略详情"""
        # 清空现有内容
        self.trade_details.config(state='normal')
        self.trade_details.delete('1.0', tk.END)
        
        # 获取时间段
        start_date = datetime.strptime(self.start_date_var.get().strip(), '%Y-%m-%d')
        end_date = datetime.strptime(self.end_date_var.get().strip(), '%Y-%m-%d')
        
        # 获取是否启用多段回测
        enable_segments = self.enable_segments.get()
        
        if enable_segments:
            # 使用segment_utils中的方法构建时���段
            from segment_utils import build_segments
            segments = build_segments(
                start_date=start_date,
                end_date=end_date,
                min_buy_times=int(self.min_buy_times_var.get())
            )
        else:
            # 单段回测
            segments = [(start_date, end_date)]
        
        # 用于累计总收益的变量
        total_profit = 0
        total_trades = 0
        failed_trades_summary = {}
        
        # 遍历每个时间段
        for i, (seg_start, seg_end) in enumerate(segments, 1):
            # 创建策略实例
            from grid_strategy import GridStrategy
            strategy = GridStrategy(
                symbol=self.symbol_var.get().strip(),
                symbol_name=self.symbol_name_var.get().strip()
            )
            
            # 设置策略参数
            for param, value in strategy_params.items():
                setattr(strategy, param, value)
            
            # 设置初始资金和持仓
            strategy.initial_cash = float(self.initial_cash_var.get())
            strategy.cash = strategy.initial_cash
            strategy.initial_positions = int(self.initial_positions_var.get())
            strategy.positions = strategy.initial_positions
            # 设置基准价格和价格范围
            strategy.base_price = float(self.price_range_min_var.get())
            strategy.price_range = (
                float(self.price_range_min_var.get()),
                float(self.price_range_max_var.get())
            )
            # 捕获输出
            output = io.StringIO()
            with redirect_stdout(output):
                # 运行回测并获取收益率
                profit_rate = strategy.backtest(seg_start, seg_end, verbose=True)
                
            # 累计统计信息
            total_profit += profit_rate
            total_trades += len(strategy.trades)
            for reason, count in strategy.failed_trades.items():
                failed_trades_summary[reason] = failed_trades_summary.get(reason, 0) + count
            
            # 显示当前段的结果
            if enable_segments:
                self.trade_details.insert(tk.END, f"\n{'='*20} 第{i}段回测 {'='*20}\n")
                self.trade_details.insert(tk.END, 
                    f"时间段: {seg_start.strftime('%Y-%m-%d')} 至 {seg_end.strftime('%Y-%m-%d')}\n\n")
            
            self.trade_details.insert(tk.END, output.getvalue())
            self.trade_details.insert(tk.END, f"\n{'='*50}\n")
        
        # 显示汇总信息（仅在多段回测时显示）
        if enable_segments and len(segments) > 1:
            self.trade_details.insert(tk.END, "\n=== 多段回测汇总 ===\n")
            self.trade_details.insert(tk.END, f"总段数: {len(segments)}\n")
            
            # 根据收益计算方式显示
            if self.profit_calc_method_var.get() == "平均值":
                avg_profit = total_profit / len(segments)
                self.trade_details.insert(tk.END, f"平均收益率: {avg_profit:.2f}%\n")
            else:  # 中值
                self.trade_details.insert(tk.END, f"中值收益率: {total_profit:.2f}%\n")
            
            self.trade_details.insert(tk.END, f"总交易次数: {total_trades}\n")
            self.trade_details.insert(tk.END, "\n失败交易汇总:\n")
            for reason, count in failed_trades_summary.items():
                if count > 0:
                    self.trade_details.insert(tk.END, f"{reason}: {count}次\n")
        
        # 恢复只读状态并滚动到顶部
        self.trade_details.config(state='disabled')
        self.trade_details.see('1.0')
    
    def toggle_sort(self):
        """切换排序方向并重新显示结果"""
        self.sort_ascending = not self.sort_ascending
        self.sort_button.config(text=f"收益率 {'↑' if self.sort_ascending else '↓'}")
        if hasattr(self, 'current_results'):
            self.display_optimization_results(self.current_results)
    
    def display_optimization_results(self, results):
        """显示优化结果"""
        # 保存当前结果以供排序使用
        self.current_results = results
        
        # 清空现有结果
        for widget in self.params_container.winfo_children():
            widget.destroy()
        
        # 获取前N个结果
        top_n = int(self.top_n_var.get())
        
        # 过滤掉收益率<=0的结果并排序
        valid_trials = [trial for trial in results["sorted_trials"] if -trial.value > 0]
        
        # 按收益率排序（注意trial.value是负的收益率）
        # 默认降序排序（收益率从高到低）
        sorted_trials = sorted(valid_trials, key=lambda t: t.value, reverse=True)
        if not self.sort_ascending:  # 如果是降序，再次反转
            sorted_trials.reverse()
        
        # 限制显示数量
        display_trials = sorted_trials[:top_n]
        
        if not display_trials:
            # 如果没有有效结果，显示提示信息
            ttk.Label(
                self.params_container, 
                text="没有找到收益率大于0的参数组合",
                font=('Arial', 10)
            ).pack(pady=10)
            return
        
        # 参数名称映射
        param_names = {
            'up_sell_rate': '上涨卖出',
            'up_callback_rate': '上涨回调',            
            'down_buy_rate': '下跌买入',
            'down_rebound_rate': '下跌反弹',
            'shares_per_trade': '单次交易股数'
        }
        
        # 显示每个结果
        for i, trial in enumerate(display_trials, 1):
            profit_rate = -trial.value
            params = trial.params
            
            # 创建结果框架
            result_frame = ttk.LabelFrame(
                self.params_container,
                text=f"组合 {i} - 收益率: {profit_rate:.2f}%"
            )
            result_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # 添加参数信息
            param_text = ""
            # 按照param_names的顺序显示参数
            for key in param_names.keys():
                value = params[key]
                if key == 'shares_per_trade':
                    param_text += f"{param_names[key]}: {value:,}\n"
                else:
                    param_text += f"{param_names[key]}: {value*100:.2f}%\n"
            
            param_text += f"交易次数: {trial.user_attrs.get('trade_count', 'N/A')}"
            
            param_label = ttk.Label(result_frame, text=param_text, justify=tk.LEFT)
            param_label.pack(padx=5, pady=5)
            
            # 添加查看详情按钮
            # 添加查看按钮
            detailbutton = ttk.Button(result_frame, text="查看详情", 
                      command=lambda p=trial.params: self.show_strategy_details(p)).pack(
                          side=tk.RIGHT, padx=5)

        
        # 更新画布滚动区域
        self.params_container.update_idletasks()
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
    
    def create_trade_details_area(self, parent):
        """创建交易详情显示区域"""
        # 创建搜索框架
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.search_count_label = ttk.Label(search_frame, text="")
        self.search_count_label.pack(side=tk.LEFT, padx=5)
        
        # 创建文本框
        self.trade_details = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            width=50,
            height=25,
            font=('Courier', 11)
        )
        self.trade_details.pack(fill=tk.BOTH, expand=True)
        self.trade_details.config(state='disabled')
        
        # 绑定搜索相关事件
        self.search_var.trace_add('write', lambda *args: self.search_text())
        self.root.bind('<Command-f>', self.focus_search)
        self.root.bind('<Control-f>', self.focus_search)
        self.search_entry.bind('<Return>', lambda e: self.search_text('down'))
        self.search_entry.bind('<Shift-Return>', lambda e: self.search_text('up'))

    def update_symbol_info(self, source='code'):
        """
        更新证券信息
        @param source: 'code' 表示从代码更新名称，'name' 表示从名称更新代码
        """
        try:
            # 获取当前日期范围
            start_date = self.start_date_var.get().strip()
            end_date = self.end_date_var.get().strip()
            
            if source == 'code':
                symbol = self.symbol_var.get().strip()
                if not symbol:
                    self.symbol_name_var.set("")
                    return
                
                # 自动判断证券类型
                is_etf = len(symbol) == 6 and symbol.startswith(("1", "5"))
                
                # 检查是否是新的证券代码
                old_symbol = self.load_config_value('symbol')
                is_new_symbol = not os.path.exists(self.config_file) or symbol != old_symbol
                
                if is_etf:
                    # 获取ETF基金信息
                    df = ak.fund_etf_spot_em()
                    name = df[df['代码'] == symbol]['名称'].values[0]
                    if is_new_symbol:
                        # 获取历史数据
                        hist_df = ak.fund_etf_hist_em(
                            symbol=symbol,
                            start_date=start_date.replace('-', ''),
                            end_date=end_date.replace('-', ''),
                            adjust="qfq"
                        )
                else:
                    # 获取股票信息
                    df = ak.stock_zh_a_spot_em()
                    name = df[df['代码'] == symbol]['名称'].values[0]
                    if is_new_symbol:
                        # 获取历史数据
                        hist_df = ak.stock_zh_a_hist(
                            symbol=symbol,
                            start_date=start_date.replace('-', ''),
                            end_date=end_date.replace('-', ''),
                            adjust="qfq"
                        )
                
                self.symbol_name_var.set(name)
                
                # 如果是新证券，尝试从配置文件中获取价格范围
                if is_new_symbol:
                    # 先尝试从配置文件中���取该证券的价格范围
                    config_data = self.load_symbol_config(symbol)
                    if config_data:
                        self.price_range_min_var.set(config_data.get('price_range_min', ''))
                        self.price_range_max_var.set(config_data.get('price_range_max', ''))
                        print(f"已从配置加载价格范围: {config_data.get('price_range_min')} - {config_data.get('price_range_max')}")
                    elif not hist_df.empty:
                        # 如果配置文件中没有，则使用历史数据计算价格范围
                        price_min = hist_df['最低'].min()
                        price_max = hist_df['最高'].max()
                        # 设置价格范围（略微扩大范围）
                        self.price_range_min_var.set(f"{price_min:.3f}")
                        self.price_range_max_var.set(f"{price_max:.3f}")
                        print(f"已更新价格范围: {price_min:.3f} - {price_max:.3f}")
                
            else:  # source == 'name'
                name = self.symbol_name_var.get().strip()
                if not name:
                    self.symbol_var.set("")
                    return
                
                # 尝试在ETF中查找
                df_etf = ak.fund_etf_spot_em()
                etf_match = df_etf[df_etf['名称'].str.contains(name, na=False)]
                
                if not etf_match.empty:
                    new_symbol = etf_match.iloc[0]['代码']
                    self.symbol_var.set(new_symbol)
                    self.symbol_name_var.set(etf_match.iloc[0]['名称'])
                    
                    # 检查是否是新的证券代码
                    if not os.path.exists(self.config_file) or new_symbol != self.load_config_value('symbol'):
                        # 获取历史数据
                        hist_df = ak.fund_etf_hist_em(
                            symbol=new_symbol,
                            start_date=start_date.replace('-', ''),
                            end_date=end_date.replace('-', ''),
                            adjust="qfq"
                        )
                        if not hist_df.empty:
                            price_min = hist_df['最低'].min()
                            price_max = hist_df['最高'].max()
                            self.price_range_min_var.set(f"{price_min:.3f}")
                            self.price_range_max_var.set(f"{price_max:.3f}")
                            print(f"已更新价格范围: {price_min:.3f} - {price_max:.3f}")
                    return
                
                # 如果ETF中未找到，尝试在股票中查找
                df_stock = ak.stock_zh_a_spot_em()
                stock_match = df_stock[df_stock['名称'].str.contains(name, na=False)]
                
                if not stock_match.empty:
                    new_symbol = stock_match.iloc[0]['代码']
                    self.symbol_var.set(new_symbol)
                    self.symbol_name_var.set(stock_match.iloc[0]['名称'])
                    
                    # 检查是否是新的证券代码
                    if not os.path.exists(self.config_file) or new_symbol != self.load_config_value('symbol'):
                        # 获取历史数据
                        hist_df = ak.stock_zh_a_hist(
                            symbol=new_symbol,
                            start_date=start_date.replace('-', ''),
                            end_date=end_date.replace('-', ''),
                            adjust="qfq"
                        )
                        if not hist_df.empty:
                            price_min = hist_df['最低'].min()
                            price_max = hist_df['最高'].max()
                            self.price_range_min_var.set(f"{price_min:.3f}")
                            self.price_range_max_var.set(f"{price_max:.3f}")
                            print(f"已更新价格���围: {price_min:.3f} - {price_max:.3f}")
                else:
                    print(f"未找到包含 '{name}' 的证券")
                
        except Exception as e:
            print(f"更新证券信息失败: {e}")
            if source == 'code':
                self.symbol_name_var.set("未找到证券")
            else:
                self.symbol_var.set("")
    
    def handle_entry_focus(self, event, widget):
        """处理输入框的焦点事件"""
        def delayed_focus():
            if widget.winfo_exists():  # 确保widget仍然存在
                widget.focus_set()
                widget.selection_range(0, tk.END)  # 选中所有文本
                # 强制更新UI
                widget.update_idletasks()
        
        # 清除可能存在的待处理焦点事件
        if hasattr(self, '_focus_after_id'):
            self.root.after_cancel(self._focus_after_id)
        
        # 设置新的延迟焦点事件
        self._focus_after_id = self.root.after(10, delayed_focus)
        return "break"  # 阻止事件继续传播

    def handle_focus_in(self, event, widget):
        """处理输入框获得焦点时的事件"""
        widget.selection_range(0, tk.END)  # 选中所有文本
        # 强制更新UI
        widget.update_idletasks()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 将配置值设置为类属性，跳过None值
                for key, value in config.items():
                    if value is not None:
                        setattr(self, key, value)
                        
                # 加载多段回测设置
                # if 'profit_calc_method' in config and config['profit_calc_method'] is not None:
                #     self.profit_calc_method_var.set(config['profit_calc_method'])
                # if 'connect_segments' in config and config['connect_segments'] is not None:
                #     self.connect_segments_var.set(config['connect_segments'])
                    
                print("已加载配置文件")
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存配置到文件"""
        if not self.validate_all_inputs():
            print("保存错误", "输入参数有误，无法保存配置")
            return

        config = {
            "symbol": self.symbol_var.get(),
            "symbol_name": self.symbol_name_var.get(),
            "start_date": self.start_date_var.get(),
            "end_date": self.end_date_var.get(),
            "ma_period": self.ma_period_var.get(),
            "ma_protection": self.ma_protection_var.get(),
            "initial_positions": self.initial_positions_var.get(),
            "initial_cash": self.initial_cash_var.get(),
            "min_buy_times": self.min_buy_times_var.get(),
            "price_range_min": self.price_range_min_var.get(),
            "price_range_max": self.price_range_max_var.get(),
            "n_trials": self.n_trials_var.get(),
            "top_n": self.top_n_var.get(),
            "profit_calc_method": self.profit_calc_method_var.get(),
            "connect_segments": self.connect_segments_var.get()
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置时发生错误: {e}")
    
    def load_config_value(self, key):
        """获取配置文件中的特定值"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get(key)
        except Exception:
            pass
        return None
    
    def toggle_optimization(self):
        """切换优化状态（开始/取消）"""
        if not self.optimization_running:
            # 开始优化
            self.start_optimization()
            self.start_button.configure(text="取消优化")
            self.optimization_running = True
        else:
            # 取消优化
            self.cancel_optimization()
            self.start_button.configure(text="开始优化")
            self.optimization_running = False
    
    def cancel_optimization(self):
        """取消优化过程"""
        self.optimization_running = False
        self.label["text"] = "优化已取消"
        # 重置进度条
        self.progress["value"] = 0
        self.percent_label["text"] = "0%"
        self.time_label["text"] = "耗时: 0:00:00"
        self.eta_label["text"] = "预计剩余: --:--:--"

    def load_symbol_config(self, symbol):
        """
        从配置文件中加载特定证券的配置信息
        @param symbol: 证券代码
        @return: 配置信息字典或None
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('symbol') == symbol:
                        return {
                            'price_range_min': config.get('price_range_min'),
                            'price_range_max': config.get('price_range_max')
                        }
        except Exception as e:
            print(f"加载证券配置失败: {e}")
        return None

    def toggle_segment_options(self):
        """切换分段回测选项的启用状态"""
        enabled = self.enable_segments.get()
        
        # 更新控件状态
        self.segment_label.config(state='normal' if enabled else 'disabled')
        self.segment_mode_combo.config(state='readonly' if enabled else 'disabled')
        self.connect_checkbox.config(state='normal' if enabled else 'disabled')
        
        # 更新天数显示
        self.update_segment_days()

    def update_segment_days(self, *args):
        """更新分段天数显示"""
        if self.enable_segments.get():
            try:
                min_buy_times = int(self.min_buy_times_var.get())
                from segment_utils import get_segment_days
                days = get_segment_days(min_buy_times)
                self.segment_days_label.config(text=f"每段区间: {days}个交易日")
            except ValueError:
                self.segment_days_label.config(text="")
        else:
            self.segment_days_label.config(text="")

    def validate_symbol(self, entry):
        """验证证券代码"""
        symbol = self.symbol_var.get().strip()
        if not symbol or not self.is_valid_symbol(symbol):
            entry.config(foreground='red')
            messagebox.showerror("输入错误", "无效的证券代码")
        else:
            entry.config(foreground='black')

    def validate_date(self, entry):
        """验证日期格式"""
        date_str = entry.get().strip()
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            entry.config(foreground='black')
        except ValueError:
            entry.config(foreground='red')
            messagebox.showerror("输入错误", "无效的日期格式")

    def is_valid_symbol(self, symbol):
        """检查证券代码是否有效"""
        try:
            df = ak.fund_etf_spot_em()  # 或者使用其他适当的API
            return symbol in df['代码'].values
        except Exception:
            return False

    def validate_all_inputs(self):
        """验证所有输入框的内容"""
        # 验证证券代码
        if not self.is_valid_symbol(self.symbol_var.get()):
            return False
        # 验证日期
        try:
            datetime.strptime(self.start_date_var.get(), '%Y-%m-%d')
            datetime.strptime(self.end_date_var.get(), '%Y-%m-%d')
        except ValueError:
            return False
        # 验证其他参数（如有需要）
        # ... 其他验证逻辑 ...
        return True

# 不要在模块级别创建实例
def create_progress_window():
    window = ProgressWindow(0)
    window.create_window()
    return window

if __name__ == "__main__":
    progress_window = create_progress_window()
    progress_window.root.mainloop()