import streamlit as st

def get_user_agent():
    """获取用户代理字符串"""
    try:
        # 使用新的API获取headers
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            headers = st.context.headers
            if headers and 'User-Agent' in headers:
                return headers['User-Agent']
            
        # 如果无法从headers获取，尝试从session state获取
        return st.session_state.get('_user_agent', '')
        
    except Exception as e:
        print(f"[ERROR] Failed to get user agent: {str(e)}")
        return '' 