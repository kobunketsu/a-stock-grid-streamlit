import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import sys
import io
from datetime import datetime

class ProgressWindow:
    def __init__(self, total_trials=100):
        """
        初始化进度窗口
        
        Args:
            total_trials (int): 总试验次数
        """
        self.root = tk.Tk()
        self.root.title("优化进度")
        self.root.geometry("600x400")
        
        # 设置窗口样式
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Custom.Horizontal.TProgressbar",
                       troughcolor='#E0E0E0',
                       background='#4CAF50',
                       thickness=20)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 进度条框架
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            style="Custom.Horizontal.TProgressbar",
            variable=self.progress_var,
            maximum=total_trials
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        # 进度标签
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.grid(row=0, column=1, padx=5)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="正在优化参数...")
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # 输出文本框
        self.output_text = scrolledtext.ScrolledText(main_frame, height=15)
        self.output_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 停止按钮
        self.stop_button = ttk.Button(
            button_frame,
            text="停止优化",
            command=self.stop_optimization
        )
        self.stop_button.grid(row=0, column=0, padx=5)
        
        # 查看交易详情按钮（初始禁用）
        self.trade_details_button = ttk.Button(
            button_frame,
            text="查看交易详情",
            command=self.show_trade_details,
            state='disabled'
        )
        self.trade_details_button.grid(row=0, column=1, padx=5)
        
        # 关闭按钮
        self.close_button = ttk.Button(
            button_frame,
            text="关闭窗口",
            command=self.close_window
        )
        self.close_button.grid(row=0, column=2, padx=5)
        
        # 初始化其他变量
        self.optimization_running = True
        self.captured_output = ""
        self.output_queue = queue.Queue()
        self.update_interval = 100  # 更新间隔（毫秒）
        
        # 配置网格权重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # 启动输出更新线程
        self.start_output_update()
        
    def update_progress(self, current_trial):
        """
        更新进度条
        
        Args:
            current_trial (int): 当前试验次数
        """
        try:
            self.progress_var.set(current_trial)
            progress_percentage = (current_trial / self.progress_bar['maximum']) * 100
            self.progress_label.config(text=f"{progress_percentage:.1f}%")
            
            if current_trial >= self.progress_bar['maximum']:
                self.status_label.config(text="优化完成")
                self.stop_button.config(state='disabled')
                
        except Exception as e:
            print(f"更新进度时发生错误: {e}")
            
    def stop_optimization(self):
        """停止优化过程"""
        self.optimization_running = False
        self.status_label.config(text="正在停止优化...")
        self.stop_button.config(state='disabled')
        
    def close_window(self):
        """关闭窗口"""
        self.optimization_running = False
        self.root.destroy()
        
    def show_trade_details(self):
        """显示交易详情"""
        if not self.captured_output:
            return
            
        # 创建新窗口
        details_window = tk.Toplevel(self.root)
        details_window.title("交易详情")
        details_window.geometry("800x600")
        
        # 创建文本框
        text_widget = scrolledtext.ScrolledText(details_window, wrap=tk.WORD)
        text_widget.pack(expand=True, fill='both', padx=10, pady=10)
        
        # 插入交易详情
        text_widget.insert(tk.END, self.captured_output)
        text_widget.config(state='disabled')  # 设为只读
        
        # 关闭按钮
        close_button = ttk.Button(
            details_window,
            text="关闭",
            command=details_window.destroy
        )
        close_button.pack(pady=10)
        
    def enable_trade_details_button(self):
        """启用查看交易详情按钮"""
        self.trade_details_button.config(state='normal')
        
    def capture_output(self, output):
        """
        捕获输出内容
        
        Args:
            output (str): 输出内容
        """
        self.captured_output = output
        
    def start_output_update(self):
        """启动输出更新线程"""
        def update_output():
            try:
                while True:
                    try:
                        # 非阻塞方式获取输出
                        output = self.output_queue.get_nowait()
                        self.output_text.insert(tk.END, output)
                        self.output_text.see(tk.END)  # 滚动到底部
                    except queue.Empty:
                        break
                    
            except Exception as e:
                print(f"更新输出时发生错误: {e}")
                
            finally:
                # 如果窗口仍然存在，继续更新
                if self.root.winfo_exists():
                    self.root.after(self.update_interval, update_output)
                    
        # 启动首次更新
        self.root.after(0, update_output)
        
    def write(self, text):
        """
        将文本写入输出队列
        
        Args:
            text (str): 要写入的文本
        """
        self.output_queue.put(text)
        
    def flush(self):
        """刷新输出"""
        pass

def create_progress_window(total_trials=100):
    """
    创建并返回进度窗口实例
    
    Args:
        total_trials (int): 总试验次数
        
    Returns:
        ProgressWindow: 进度窗口实例
    """
    window = ProgressWindow(total_trials)
    
    # 重定向标准输出到进度窗口
    sys.stdout = window
    
    return window 