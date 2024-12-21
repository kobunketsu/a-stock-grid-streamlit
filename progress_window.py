import tkinter as tk
from tkinter import ttk
from datetime import datetime
import sys

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
        self.is_closed = False  # 添加标志来追踪窗口状态
        
    def create_window(self):
        """在主线程中创建窗口"""
        self.root = tk.Tk()
        self.root.title("优化进度")
        self.root.geometry("300x200")
        
        # 设置窗口在屏幕中央
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 300) // 2
        y = (screen_height - 200) // 2
        self.root.geometry(f"300x200+{x}+{y}")
        
        # 设置窗口始终置顶
        self.root.attributes('-topmost', True)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 进度标签
        self.label = ttk.Label(self.root, text="正在优化参数...", font=('Arial', 10))
        self.label.pack(pady=10)
        
        # 进度条
        self.progress = ttk.Progressbar(
            self.root, 
            orient="horizontal",
            length=200, 
            mode="determinate"
        )
        self.progress.pack(pady=10)
        
        # 百分比标签
        self.percent_label = ttk.Label(self.root, text="0%", font=('Arial', 10))
        self.percent_label.pack(pady=5)
        
        # 耗时标签
        self.time_label = ttk.Label(self.root, text="耗时: 0:00:00", font=('Arial', 10))
        self.time_label.pack(pady=5)
        
        # 预计完成时间标签
        self.eta_label = ttk.Label(self.root, text="预计剩余: --:--:--", font=('Arial', 10))
        self.eta_label.pack(pady=5)
        
        # 记录开始时间
        self.start_time = datetime.now()
        
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