import streamlit as st
from url_page_switcher import URLPageSwitcher

def main():
    # 设置页面配置
    st.set_page_config(
        page_title="演示应用",
        page_icon="📱",
        layout="wide"
    )

    # 创建URL参数页面切换器实例
    page_switcher = URLPageSwitcher()
    
    # 根据URL参数显示相应页面
    if not page_switcher.is_showing_overlay():
        page_switcher.show_main_page()
    else:
        page_switcher.show_overlay_page()

if __name__ == "__main__":
    main() 