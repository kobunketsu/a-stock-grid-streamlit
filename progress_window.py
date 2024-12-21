import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import sys
import io
from contextlib import redirect_stdout

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
        self.trade_details = None  # 用于存储交易详情的文本控件
        self.captured_output = []  # 用于存储捕获的输出
        
    def create_window(self):
        """在主线程中创建窗口"""
        self.root = tk.Tk()
        self.root.title("优化进度")
        self.root.geometry("600x500")  # 增加窗口大小以适应新控件
        
        # 设置窗口在屏幕中央
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 500) // 2
        self.root.geometry(f"600x500+{x}+{y}")
        
        # 创建左侧进度面板
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        
        # 进度相关控件放在左侧
        self.label = ttk.Label(progress_frame, text="正在优化参数...", font=('Arial', 10))
        self.label.pack(pady=10)
        
        self.progress = ttk.Progressbar(
            progress_frame, 
            orient="horizontal",
            length=200, 
            mode="determinate"
        )
        self.progress.pack(pady=10)
        
        self.percent_label = ttk.Label(progress_frame, text="0%", font=('Arial', 10))
        self.percent_label.pack(pady=5)
        
        self.time_label = ttk.Label(progress_frame, text="耗时: 0:00:00", font=('Arial', 10))
        self.time_label.pack(pady=5)
        
        self.eta_label = ttk.Label(progress_frame, text="预计剩余: --:--:--", font=('Arial', 10))
        self.eta_label.pack(pady=5)
        
        # 创建查看交易详情按钮
        self.view_trades_btn = ttk.Button(
            progress_frame, 
            text="查看交易详情",
            command=self.show_trade_details
        )
        self.view_trades_btn.pack(pady=10)
        self.view_trades_btn.state(['disabled'])  # 初始状态禁用
        
        # 创建右侧交易详情面板
        details_frame = ttk.Frame(self.root)
        details_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 创建搜索框和计数标签的容器
        search_frame = ttk.Frame(details_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 创建搜索输入框
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建搜索结果计数标签
        self.search_count_label = ttk.Label(search_frame, text="")
        self.search_count_label.pack(side=tk.LEFT, padx=5)
        
        # 绑定搜索框变化事件
        def on_search_change(*args):
            if self.trade_details:
                self.search_text()  # 每次输入变化时自动搜索
        
        self.search_var.trace_add('write', on_search_change)
        
        # 绑定 Command+F / Control+F 快捷键
        self.root.bind('<Command-f>', self.focus_search)  # macOS
        self.root.bind('<Control-f>', self.focus_search)  # Windows
        
        # 绑定回车键和shift+回车键到搜索功能
        self.search_entry.bind('<Return>', lambda e: self.search_text('down'))
        self.search_entry.bind('<Shift-Return>', lambda e: self.search_text('up'))
        
        # 创建交易详情文本框（设置为只读）
        self.trade_details = scrolledtext.ScrolledText(
            details_frame,
            wrap=tk.WORD,
            width=50,
            height=25,
            font=('Courier', 11)
        )
        self.trade_details.pack(fill=tk.BOTH, expand=True)
        
        # 设置文本框为只读
        self.trade_details.config(state='disabled')
        
        # 修改按键绑定，增加更多的加号键变体
        self.root.bind('<Command-plus>', self.increase_font_size)  # macOS
        self.root.bind('<Command-equal>', self.increase_font_size)  # macOS (等号键，不需要按Shift)
        self.root.bind('<Command-KP_Add>', self.increase_font_size)  # macOS 数字键盘
        self.root.bind('<Control-plus>', self.increase_font_size)  # Windows
        self.root.bind('<Control-equal>', self.increase_font_size)  # Windows (等号键，不需要按Shift)
        self.root.bind('<Control-KP_Add>', self.increase_font_size)  # Windows 数字键盘
        
        # 减号键绑定
        self.root.bind('<Command-minus>', self.decrease_font_size)  # macOS
        self.root.bind('<Command-KP_Subtract>', self.decrease_font_size)  # macOS 数字键盘
        self.root.bind('<Control-minus>', self.decrease_font_size)  # Windows
        self.root.bind('<Control-KP_Subtract>', self.decrease_font_size)  # Windows 数字键盘
        
        # 添加新的快捷键绑定
        self.root.bind('<Command-Down>', self.scroll_to_end)  # macOS
        self.root.bind('<Control-Down>', self.scroll_to_end)  # Windows
        self.root.bind('<Command-Up>', self.scroll_to_start)  # macOS
        self.root.bind('<Control-Up>', self.scroll_to_start)  # Windows
        
        # 设置窗口始终置顶
        self.root.attributes('-topmost', True)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 记录开始时间
        self.start_time = datetime.now()
    
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
        """处理窗口关闭事件"""
        self.is_closed = True
        self.root.destroy()
        sys.exit(0)  # 强制终止程序
        
    def update_progress(self, trial_number):
        """更新进度"""
        if self.root is None or self.is_closed:
            sys.exit(0)  # 如果窗口已关闭，终止程序
            
        try:
            self.current_trial = trial_number
            progress = (self.current_trial / self.total_trials) * 100
            self.progress["value"] = progress
            self.percent_label["text"] = f"{progress:.1f}%"
            
            # 更新耗时和预计完成时间
            if self.start_time and self.current_trial > 0:
                # 计算已用时间
                elapsed_time = datetime.now() - self.start_time
                hours = int(elapsed_time.total_seconds() // 3600)
                minutes = int((elapsed_time.total_seconds() % 3600) // 60)
                seconds = int(elapsed_time.total_seconds() % 60)
                self.time_label["text"] = f"耗时: {hours}:{minutes:02d}:{seconds:02d}"
                
                # 计算预计剩余时间
                if self.current_trial > 0:
                    time_per_trial = elapsed_time.total_seconds() / self.current_trial
                    remaining_trials = self.total_trials - self.current_trial
                    remaining_seconds = time_per_trial * remaining_trials
                    
                    eta_hours = int(remaining_seconds // 3600)
                    eta_minutes = int((remaining_seconds % 3600) // 60)
                    eta_seconds = int(remaining_seconds % 60)
                    self.eta_label["text"] = f"预计剩余: {eta_hours}:{eta_minutes:02d}:{eta_seconds:02d}"
            
            self.root.update()
        except tk.TclError:
            # 如果发生 TclError，说明窗口已被关闭
            sys.exit(0)
        
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