import streamlit as st
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    演示通过修改一个输入框的内容来更新另一个输入框
    """
    st.title("文本输入框同步更新Demo")
    logger.debug("开始运行demo")
    
    # 方法1：使用on_change回调
    st.write("### 方法1: 使用on_change回调")
    
    # 初始化session state
    if "text_a" not in st.session_state:
        st.session_state.text_a = "Hello"
        logger.debug("[方法1] 初始化 text_a = %s", st.session_state.text_a)
    if "text_b" not in st.session_state:
        st.session_state.text_b = "World"
        logger.debug("[方法1] 初始化 text_b = %s", st.session_state.text_b)
    
    # 添加调试信息
    st.write("### 方法1的Session State:")
    method1_state = {k: v for k, v in st.session_state.items() if k in ['text_a', 'text_b']}
    st.write(method1_state)
    logger.debug("[方法1] 当前状态: %s", method1_state)
    
    def on_text_a_change():
        """当文本框A的内容改变时，更新文本框B"""
        logger.debug("[方法1] A变化回调触发: text_a = %s", st.session_state.text_a)
        st.session_state.text_b = f"来自A的消息: {st.session_state.text_a}"
        logger.debug("[方法1] A变化后: text_b = %s", st.session_state.text_b)
    
    def on_text_b_change():
        """当文本框B的内容改变时，更新文本框A"""
        logger.debug("[方法1] B变化回调触发: text_b = %s", st.session_state.text_b)
        st.session_state.text_a = f"来自B的回复: {st.session_state.text_b}"
        logger.debug("[方法1] B变化后: text_a = %s", st.session_state.text_a)
    
    col1, col2 = st.columns(2)
    
    with col1:
        text_a = st.text_input(
            "文本框 A",
            key="text_a",
            on_change=on_text_a_change
        )
        st.write(f"A的当前值: {text_a}")
        logger.debug("[方法1] 渲染A输入框: text_a = %s", text_a)
    
    with col2:
        text_b = st.text_input(
            "文本框 B",
            key="text_b",
            on_change=on_text_b_change
        )
        st.write(f"B的当前值: {text_b}")
        logger.debug("[方法1] 渲染B输入框: text_b = %s", text_b)
    
    # 方法2：使用不同的键和手动同步
    st.write("### 方法2: 使用不同的键和手动同步")
    
    # 初始化内部状态
    if "internal_x" not in st.session_state:
        st.session_state.internal_x = "你好"
        logger.debug("[方法2] 初始化 internal_x = %s", st.session_state.internal_x)
    if "internal_y" not in st.session_state:
        st.session_state.internal_y = "世界"
        logger.debug("[方法2] 初始化 internal_y = %s", st.session_state.internal_y)
    
    # 添加调试信息
    st.write("### 方法2的Session State:")
    method2_state = {k: v for k, v in st.session_state.items() if k in ['internal_x', 'internal_y', 'input_x', 'input_y']}
    st.write(method2_state)
    logger.debug("[方法2] 当前状态: %s", method2_state)
    
    def on_x_change():
        """当X的值改变时更新Y"""
        logger.debug("[方法2] X变化回调触发: input_x = %s", st.session_state.input_x)
        st.session_state.internal_y = f"X说: {st.session_state.input_x}"
        logger.debug("[方法2] X变化后: internal_y = %s", st.session_state.internal_y)
    
    def on_y_change():
        """当Y的值改变时更新X"""
        logger.debug("[方法2] Y变化回调触发: input_y = %s", st.session_state.input_y)
        st.session_state.internal_x = f"Y说: {st.session_state.input_y}"
        logger.debug("[方法2] Y变化后: internal_x = %s", st.session_state.internal_x)
    
    col3, col4 = st.columns(2)
    
    with col3:
        x = st.text_input(
            "文本框 X",
            value=st.session_state.internal_x,
            key="input_x",
            on_change=on_x_change
        )
        st.write(f"X的当前值: {x}")
        logger.debug("[方法2] 渲染X输入框: x = %s, internal_x = %s", x, st.session_state.internal_x)
    
    with col4:
        y = st.text_input(
            "文本框 Y",
            value=st.session_state.internal_y,
            key="input_y",
            on_change=on_y_change
        )
        st.write(f"Y的当前值: {y}")
        logger.debug("[方法2] 渲染Y输入框: y = %s, internal_y = %s", y, st.session_state.internal_y)
    
    logger.debug("Demo运行结束")

if __name__ == "__main__":
    main() 