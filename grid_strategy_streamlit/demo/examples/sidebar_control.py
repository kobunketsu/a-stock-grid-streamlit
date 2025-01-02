import streamlit as st

# 初始化session state变量来跟踪sidebar状态（'expanded'或'collapsed'）
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'expanded'

# 使用set_page_config的initial_sidebar_state参数来控制sidebar状态
st.set_page_config(
    page_title="Sidebar控制示例",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state
)

# Sidebar内容
with st.sidebar:
    st.title("Sidebar控制面板")
    st.write("这是一个简单的Sidebar控制示例")

# 主页面内容
st.title("Sidebar控制测试")
st.write("这个示例展示了如何通过程序控制Sidebar的显示和隐藏")

# 显示当前状态
st.write(f"当前Sidebar状态: {st.session_state.sidebar_state}")

# 切换按钮
if st.button('点击切换Sidebar状态'):
    # 在'expanded'和'collapsed'之间切换状态
    st.session_state.sidebar_state = 'collapsed' if st.session_state.sidebar_state == 'expanded' else 'expanded'
    # 切换状态后强制重新运行应用
    st.rerun()

# 显示一些帮助信息
st.markdown("""
### 使用说明
1. 点击"点击切换Sidebar状态"按钮来切换侧边栏的显示/隐藏状态
2. 观察当前状态的变化

### 注意事项
- 这个方法使用了Streamlit的session_state来保持状态
- 每次切换都会触发页面重新加载
- 这是官方推荐的控制sidebar状态的方法
""") 