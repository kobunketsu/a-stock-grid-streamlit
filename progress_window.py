import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import sys
import io
from contextlib import redirect_stdout
import threading

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
        
    def create_window(self):
        self.root = tk.Tk()
        self.root.title("网格策略优化器")
        self.root.geometry("900x600")
        
        # 在创建窗口后初始化变量
        self.symbol_var = tk.StringVar(self.root, value="159300")
        self.start_date_var = tk.StringVar(self.root, value="2024-10-10")
        self.end_date_var = tk.StringVar(self.root, value="2024-12-20")
        self.ma_period_var = tk.StringVar(self.root, value="55")
        self.ma_protection_var = tk.BooleanVar(self.root, value=True)
        self.initial_positions_var = tk.StringVar(self.root, value="0")
        self.initial_cash_var = tk.StringVar(self.root, value="100000")
        self.min_buy_times_var = tk.StringVar(self.root, value="2")
        self.price_range_min_var = tk.StringVar(self.root, value="3.9")
        self.price_range_max_var = tk.StringVar(self.root, value="4.3")
        self.n_trials_var = tk.StringVar(self.root, value="100")
        
        # 设置窗口在屏幕中央
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 900) // 2
        y = (screen_height - 600) // 2
        self.root.geometry(f"900x600+{x}+{y}")
        
        # 创建左侧参数面板
        params_frame = ttk.LabelFrame(self.root, text="参数设置", padding=10)
        params_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        
        # 创建参数输入控件
        # ETF代码
        ttk.Label(params_frame, text="ETF代码:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.symbol_var, width=20).grid(row=0, column=1, pady=2)
        
        # 日期范围
        ttk.Label(params_frame, text="开始日期:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.start_date_var, width=20).grid(row=1, column=1, pady=2)
        
        ttk.Label(params_frame, text="结束日期:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.end_date_var, width=20).grid(row=2, column=1, pady=2)
        
        # 均线设置
        ttk.Label(params_frame, text="均线周期:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.ma_period_var, width=20).grid(row=3, column=1, pady=2)
        
        ttk.Checkbutton(params_frame, text="启用均线保护", variable=self.ma_protection_var).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # 资金设置
        ttk.Label(params_frame, text="初始持仓:").grid(row=5, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.initial_positions_var, width=20).grid(row=5, column=1, pady=2)
        
        ttk.Label(params_frame, text="初始资金:").grid(row=6, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.initial_cash_var, width=20).grid(row=6, column=1, pady=2)
        
        ttk.Label(params_frame, text="最少买入次数:").grid(row=7, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.min_buy_times_var, width=20).grid(row=7, column=1, pady=2)
        
        # 价格范围
        price_range_frame = ttk.LabelFrame(params_frame, text="价格范围", padding=5)
        price_range_frame.grid(row=8, column=0, columnspan=2, sticky=tk.EW, pady=5)
        
        ttk.Label(price_range_frame, text="最小值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(price_range_frame, textvariable=self.price_range_min_var, width=8).grid(row=0, column=1, pady=2)
        
        ttk.Label(price_range_frame, text="最大值:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(10,0))
        ttk.Entry(price_range_frame, textvariable=self.price_range_max_var, width=8).grid(row=0, column=3, pady=2)
        
        # 优化次数
        ttk.Label(params_frame, text="优化次数:").grid(row=9, column=0, sticky=tk.W, pady=2)
        ttk.Entry(params_frame, textvariable=self.n_trials_var, width=20).grid(row=9, column=1, pady=2)
        
        # 添加开始优化按钮
        ttk.Button(params_frame, text="开始优化", command=self.start_optimization).grid(
            row=10, column=0, columnspan=2, pady=10)
        
        # 创建右侧进度和结果面板
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 进度相关控件
        progress_frame = ttk.LabelFrame(right_frame, text="优化进度", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.label = ttk.Label(progress_frame, text="等待开始...", font=('Arial', 10))
        self.label.pack(pady=5)
        
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=5)
        
        self.percent_label = ttk.Label(progress_frame, text="0%", font=('Arial', 10))
        self.percent_label.pack(pady=2)
        
        self.time_label = ttk.Label(progress_frame, text="耗时: 0:00:00", font=('Arial', 10))
        self.time_label.pack(pady=2)
        
        self.eta_label = ttk.Label(progress_frame, text="预计剩余: --:--:--", font=('Arial', 10))
        self.eta_label.pack(pady=2)
        
        # 创建查看交易详情按钮
        self.view_trades_btn = ttk.Button(progress_frame, text="查看交易详情", command=self.show_trade_details)
        self.view_trades_btn.pack(pady=5)
        self.view_trades_btn.state(['disabled'])
        
        # 创建结果文本框
        self.create_results_text_area(right_frame)
        
        # 设置窗口始终置顶
        self.root.attributes('-topmost', True)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def create_results_text_area(self, parent):
        """创建结果显示区域"""
        # 创建搜索框和文本框
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.search_count_label = ttk.Label(search_frame, text="")
        self.search_count_label.pack(side=tk.LEFT, padx=5)
        
        # 绑定搜索相关事件
        self.search_var.trace_add('write', lambda *args: self.search_text())
        self.root.bind('<Command-f>', self.focus_search)
        self.root.bind('<Control-f>', self.focus_search)
        self.search_entry.bind('<Return>', lambda e: self.search_text('down'))
        self.search_entry.bind('<Shift-Return>', lambda e: self.search_text('up'))
        
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
        
    def start_optimization(self):
        """开始优化按钮的回调函数"""
        try:
            # 获取并验证参数
            symbol = self.symbol_var.get().strip()
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
            
            # 创建优化器实例
            from stockdata import GridStrategyOptimizer  # 避免循环导入
            optimizer = GridStrategyOptimizer(
                symbol=symbol,
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
                    results = optimizer.optimize(n_trials=n_trials)
                    if results and not self.is_closed:
                        # 在主线程中更新UI
                        self.root.after(0, lambda: optimizer.print_results(results))
                except Exception as e:
                    if not self.is_closed:
                        self.root.after(0, lambda: messagebox.showerror("优化错误", str(e)))
            
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
        if self.search_entry:
            self.search_entry.focus_set()
            self.search_entry.select_range(0, tk.END)  # 选中所有文本
            return 'break'  # 阻止事件继续传播
    
    def search_text(self, direction='down'):
        """
        搜索文本内容
        @param direction: 搜索方向，'up' 向上搜索，'down' 向下搜索
        """
        # 获取搜索关键词
        search_key = self.search_var.get()
        if not search_key:
            self.search_count_label.config(text="")  # 清空计数标签
            return
        
        # 启用文本框以进行搜索
        self.trade_details.config(state='normal')
        
        # 移除之前的搜索标记
        self.trade_details.tag_remove('search', '1.0', tk.END)
        
        # 获取文本内容
        content = self.trade_details.get('1.0', tk.END)
        
        # 获取当前光标位置
        current_pos = self.trade_details.index(tk.INSERT)
        
        # 将搜索关键词转换为小写以进行不区分大小写的搜索
        content_lower = content.lower()
        search_key_lower = search_key.lower()
        
        # 找出所有匹配位置
        matches = []
        start = 0
        while True:
            pos = content_lower.find(search_key_lower, start)
            if pos == -1:
                break
            matches.append(pos)
            start = pos + 1

        if not matches:
            self.search_count_label.config(text="未找到")
            self.trade_details.config(state='disabled')
            return
        
        # 获取当前光标位置对应的内容偏移量
        current_offset = len(self.trade_details.get('1.0', current_pos)) - 1
        
        # 根据搜索方向找到下一个匹配位置
        if direction == 'down':
            next_pos = None
            current_index = 0
            for i, pos in enumerate(matches):
                if pos > current_offset:
                    next_pos = pos
                    current_index = i
                    break
            # 如果没有找到更大的位置，则回到第一个匹配位置
            if next_pos is None:
                next_pos = matches[0]
                current_index = 0
        else:  # 向上搜索
            next_pos = None
            current_index = len(matches) - 1
            for i, pos in reversed(list(enumerate(matches))):
                if pos < current_offset:
                    next_pos = pos
                    current_index = i
                    break
            # 如果没有找到更小的位置，则跳到最后一个匹配位置
            if next_pos is None:
                next_pos = matches[-1]
                current_index = len(matches) - 1
        
        # 更新搜索结果计数标签
        self.search_count_label.config(text=f"{current_index + 1}/{len(matches)}")
        
        # 计算匹配位置的行号和列号
        text_before = content[:next_pos]
        line_count = text_before.count('\n') + 1
        last_newline = text_before.rfind('\n')
        col = next_pos - last_newline - 1 if last_newline != -1 else next_pos
        
        # 设置高亮和光标位置
        start_pos = f"{line_count}.{col}"
        end_pos = f"{line_count}.{col + len(search_key)}"
        
        self.trade_details.tag_add('search', start_pos, end_pos)
        self.trade_details.tag_config('search', background='yellow', foreground='black')
        self.trade_details.see(start_pos)
        self.trade_details.mark_set(tk.INSERT, end_pos)
        
        # 恢复只读状态
        self.trade_details.config(state='disabled')
    
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

# 不要在模块级别创建实例
def create_progress_window():
    window = ProgressWindow(0)
    window.create_window()
    return window

if __name__ == "__main__":
    progress_window = create_progress_window()
    progress_window.root.mainloop()