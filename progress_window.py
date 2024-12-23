import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import sys
import io
from contextlib import redirect_stdout
import threading
import akshare as ak
import pandas as pd

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
        self.symbol_name_var = None  # 新增证券名称变量
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
        
        self.sort_ascending = False  # 修改默认排序方向为降序
        self.current_results = []   # 存储当前的结果列表
        
    def create_window(self):
        self.root = tk.Tk()
        self.root.title("网格策略优化器")
        self.root.geometry("1200x800")
        
        # 在创建窗口后初始化变量
        self.symbol_var = tk.StringVar(self.root, value="159300")
        self.symbol_name_var = tk.StringVar(self.root)  # 新增证券名称变量
        self.start_date_var = tk.StringVar(self.root, value="2024-10-10")
        self.end_date_var = tk.StringVar(self.root, value="2024-12-20")
        self.ma_period_var = tk.StringVar(self.root, value="55")
        self.ma_protection_var = tk.BooleanVar(self.root, value=True)
        self.initial_positions_var = tk.StringVar(self.root, value="0")
        self.initial_cash_var = tk.StringVar(self.root, value="100000")
        self.min_buy_times_var = tk.StringVar(self.root, value="2")
        self.price_range_min_var = tk.StringVar(value="3.9")
        self.price_range_max_var = tk.StringVar(value="4.3")
        self.n_trials_var = tk.StringVar(value="100")
        self.top_n_var = tk.StringVar(value="5")
        
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
        
        ttk.Label(parent, text="结束日期:").grid(row=3, column=0, sticky=tk.W, pady=2)
        end_date_entry = ttk.Entry(parent, textvariable=self.end_date_var, width=12)
        end_date_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        
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
        price_min_entry = ttk.Entry(price_range_frame, textvariable=self.price_range_min_var, width=6)
        price_min_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(price_range_frame, text="最大值:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(5,0))
        price_max_entry = ttk.Entry(price_range_frame, textvariable=self.price_range_max_var, width=6)
        price_max_entry.grid(row=0, column=3, sticky=tk.W, pady=2)
        
        # 优化设置
        ttk.Label(parent, text="优化次数:").grid(row=10, column=0, sticky=tk.W, pady=2)
        n_trials_entry = ttk.Entry(parent, textvariable=self.n_trials_var, width=12)
        n_trials_entry.grid(row=10, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(parent, text="显示前N个结果:").grid(row=11, column=0, sticky=tk.W, pady=2)
        top_n_entry = ttk.Entry(parent, textvariable=self.top_n_var, width=12)
        top_n_entry.grid(row=11, column=1, sticky=tk.W, pady=2)
        
        # 添加开始优化按钮
        start_button = ttk.Button(parent, text="开始优化", command=self.start_optimization)
        start_button.grid(row=12, column=0, columnspan=2, pady=10)
        
        # 为所有输入框添加焦点事件处理
        all_entries = [
            symbol_entry, start_date_entry, end_date_entry, ma_period_entry,
            initial_pos_entry, initial_cash_entry, min_buy_entry,
            price_min_entry, price_max_entry, n_trials_entry, top_n_entry
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
    
    def start_optimization(self):
        """开始优化按钮的回调函数"""
        try:
            # 获取并验证参数
            symbol = self.symbol_var.get().strip()
            
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
            from stockdata import GridStrategyOptimizer  # 避免循环导入
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
                price_range=price_range
            )
            
            # 将进度窗口传递给优化器
            optimizer.progress_window = self
            
            def run_optimization():
                try:
                    # 运行优化
                    results = optimizer.optimize(n_trials=n_trials)
                    
                    if results and not self.is_closed:
                        # 在主线程中更新UI
                        def update_ui():
                            if not self.is_closed:
                                self.label["text"] = "优化完成"
                                # 显示优化结果
                                self.display_optimization_results(results)
                        
                        self.root.after(0, update_ui)
                        
                except Exception as e:
                    if not self.is_closed:
                        self.root.after(0, lambda: messagebox.showerror("优化错误", str(e)))
                        self.label["text"] = "优化失败"
            
            # 在新线程中运行优化
            self.optimization_thread = threading.Thread(target=run_optimization)
            self.optimization_thread.daemon = True  # 设置为守护线程
            self.optimization_thread.start()
            
        except ValueError as e:
            messagebox.showerror("参数错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", f"启动优化失败: {str(e)}")
    
    def capture_output(self, text):
        """捕获并存储输出文本"""
        self.captured_output.append(text)
    
    def show_trade_details(self):
        """显示交易详情"""
        if self.trade_details:
            # 临时启用文本框以更新内容
            self.trade_details.config(state='normal')
            self.trade_details.delete('1.0', tk.END)
            for text in self.captured_output:
                self.trade_details.insert(tk.END, text + '\n')
            self.trade_details.see(tk.END)  # 滚动到最后
            # 恢复只读状态
            self.trade_details.config(state='disabled')
    
    def enable_trade_details_button(self):
        """启用交易详情按钮"""
        if self.view_trades_btn:
            self.view_trades_btn.state(['!disabled'])
    
    def _on_closing(self):
        """窗口关闭时的处理"""
        self.is_closed = True
        if hasattr(self, 'optimization_thread') and self.optimization_thread.is_alive():
            # 等待优化线程结束
            self.label["text"] = "正在停止优化..."
            self.root.after(100, self._check_thread_and_close)
        else:
            self.root.destroy()
    
    def _check_thread_and_close(self):
        """检查优化线程是否结束，如果结束则关闭窗口"""
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
        
        # 创建并运行策略
        from grid_strategy import GridStrategy
        strategy = GridStrategy(
            symbol=self.symbol_var.get().strip(),
            symbol_name="ETF"  # 可以从接口获取实际名称
        )
        
        # 设置策略参数
        for param, value in strategy_params.items():
            setattr(strategy, param, value)
        
        # 运行回测
        start_date = datetime.strptime(self.start_date_var.get().strip(), '%Y-%m-%d')
        end_date = datetime.strptime(self.end_date_var.get().strip(), '%Y-%m-%d')
        
        # 捕获输出
        output = io.StringIO()
        with redirect_stdout(output):
            strategy.backtest(start_date, end_date, verbose=True)
        
        # 显示结果
        self.trade_details.insert(tk.END, output.getvalue())
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
        
        # 默认按收益率从高到低排序
        sorted_trials = sorted(valid_trials, key=lambda t: -t.value)  # 收益率从高到低
        if self.sort_ascending:  # 只有在明确要求升序时才改变顺序
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
        
        # 创建每个参数组合的显示块
        for i, trial in enumerate(display_trials, 1):
            frame = ttk.LabelFrame(
                self.params_container, 
                text=f"第 {i} 名", 
                padding=5
            )
            frame.pack(fill=tk.X, pady=5)
            
            # 创建参数信息
            info_frame = ttk.Frame(frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            profit_rate = -trial.value
            ttk.Label(info_frame, text=f"收益率: {profit_rate:.2f}%",
                     font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"交易次数: {trial.user_attrs['trade_count']}").pack(anchor=tk.W)
            
            # 显示参数
            params_text = "参数:\n"
            for param, value in trial.params.items():
                if param in ['up_sell_rate', 'down_buy_rate', 'up_callback_rate', 'down_rebound_rate']:
                    params_text += f"  {param}: {value*100:.2f}%\n"
                else:
                    params_text += f"  {param}: {value}\n"
            ttk.Label(info_frame, text=params_text).pack(anchor=tk.W)
            
            # 添加查看按钮
            ttk.Button(frame, text="查看详情", 
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
            if source == 'code':
                symbol = self.symbol_var.get().strip()
                if not symbol:
                    self.symbol_name_var.set("")
                    return
                
                # 自动判断证券类型
                is_etf = len(symbol) == 6 and symbol.startswith(("1", "5"))
                
                if is_etf:
                    # 获取ETF基金信息
                    df = ak.fund_etf_spot_em()
                    name = df[df['代码'] == symbol]['名称'].values[0]
                else:
                    # 获取股票信息
                    df = ak.stock_zh_a_spot_em()
                    name = df[df['代码'] == symbol]['名称'].values[0]
                
                self.symbol_name_var.set(name)
                
            else:  # source == 'name'
                name = self.symbol_name_var.get().strip()
                if not name:
                    self.symbol_var.set("")
                    return
                
                # 尝试在ETF中查找
                df_etf = ak.fund_etf_spot_em()
                etf_match = df_etf[df_etf['名称'].str.contains(name, na=False)]
                
                if not etf_match.empty:
                    self.symbol_var.set(etf_match.iloc[0]['代码'])
                    self.symbol_name_var.set(etf_match.iloc[0]['名称'])
                    return
                
                # 如果ETF中未找到，尝试在股票中查找
                df_stock = ak.stock_zh_a_spot_em()
                stock_match = df_stock[df_stock['名称'].str.contains(name, na=False)]
                
                if not stock_match.empty:
                    self.symbol_var.set(stock_match.iloc[0]['代码'])
                    self.symbol_name_var.set(stock_match.iloc[0]['名称'])
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

# 不要在模块级别创建实例
def create_progress_window():
    window = ProgressWindow(0)
    window.create_window()
    return window

if __name__ == "__main__":
    progress_window = create_progress_window()
    progress_window.root.mainloop()