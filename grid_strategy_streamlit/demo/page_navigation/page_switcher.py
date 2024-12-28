from abc import ABC, abstractmethod
import streamlit as st
from typing import Any, Optional

class PageSwitcher(ABC):
    """页面切换器的抽象基类"""
    
    @abstractmethod
    def show_main_page(self) -> None:
        """显示主页面"""
        pass
        
    @abstractmethod
    def show_overlay_page(self) -> None:
        """显示覆盖页面"""
        pass
        
    @abstractmethod
    def switch_to_overlay(self) -> None:
        """切换到覆盖页面"""
        pass
        
    @abstractmethod
    def exit_overlay(self) -> None:
        """退出覆盖页面"""
        pass
        
    @abstractmethod
    def is_showing_overlay(self) -> bool:
        """判断是否正在显示覆盖页面"""
        pass

class SessionStateSwitcher(PageSwitcher):
    """使用Streamlit session state实现的页面切换器"""
    
    def __init__(self):
        """初始化session state"""
        if 'show_overlay' not in st.session_state:
            st.session_state.show_overlay = False
    
    def show_main_page(self) -> None:
        """显示主页面内容"""
        st.title("主页面")
        st.write("这是主页面的内容")
        st.write("点击下面的按钮打开新页面")
        if st.button("打开新页面"):
            self.switch_to_overlay()
    
    def show_overlay_page(self) -> None:
        """显示覆盖页面内容"""
        overlay = st.container()
        with overlay:
            st.title("新页面")
            st.write("这是覆盖在主页面上的新页面")
            st.write("这里可以放置新页面的内容")
            st.write("点击下面的按钮返回主页面")
            if st.button("退出"):
                self.exit_overlay()
    
    def switch_to_overlay(self) -> None:
        """切换到覆盖页面"""
        st.session_state.show_overlay = True
        st.experimental_rerun()
    
    def exit_overlay(self) -> None:
        """退出覆盖页面"""
        st.session_state.show_overlay = False
        st.experimental_rerun()
    
    def is_showing_overlay(self) -> bool:
        """判断是否正在显示覆盖页面"""
        return st.session_state.show_overlay