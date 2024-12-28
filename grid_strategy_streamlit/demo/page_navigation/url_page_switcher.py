import streamlit as st
from page_switcher import PageSwitcher
from urllib.parse import urlencode
import webbrowser
from typing import Optional

class URLPageSwitcher(PageSwitcher):
    """使用URL参数实现的页面切换器"""
    
    def __init__(self):
        """初始化URL参数检查"""
        # 获取URL参数
        query_params = st.experimental_get_query_params()
        # 检查页面参数
        self.current_page = query_params.get("page", ["main"])[0]
    
    def show_main_page(self) -> None:
        """显示主页面内容"""
        st.title("主页面")
        st.write("这是主页面的内容")
        st.write("点击下面的按钮打开新页面")
        
        # 使用URL参数打开新页面
        if st.button("打开新页面"):
            self.switch_to_overlay()
    
    def show_overlay_page(self) -> None:
        """显示覆盖页面内容"""
        st.title("新页面")
        st.write("这是新页面的内容")
        st.write("这里可以放置新页面的内容")
        st.write("点击下面的按钮返回主页面")
        
        # 使用URL参数返回主页面
        if st.button("退出"):
            self.exit_overlay()
    
    def switch_to_overlay(self) -> None:
        """切换到覆盖页面"""
        # 设置URL参数为overlay页面
        st.experimental_set_query_params(page="overlay")
        st.experimental_rerun()
    
    def exit_overlay(self) -> None:
        """退出覆盖页面"""
        # 清除URL参数，返回主页面
        st.experimental_set_query_params()
        st.experimental_rerun()
    
    def is_showing_overlay(self) -> bool:
        """判断是否正在显示覆盖页面"""
        return self.current_page == "overlay"