import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers

def get_user_agent():
    """获取用户代理字符串"""
    try:
        # 尝试从websocket headers获取
        headers = _get_websocket_headers()
        if headers and 'User-Agent' in headers:
            return headers['User-Agent']
            
        # 如果无法从headers获取，尝试从session state获取
        return st.session_state.get('_user_agent', '')
        
    except Exception as e:
        print(f"[ERROR] Failed to get user agent: {str(e)}")
        return '' 