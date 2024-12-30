import os
import json
import gettext

def setup_localization():
    """设置本地化"""
    # 获取当前目录的上级目录中的 locales 文件夹
    locale_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locales')
    
    # 加载 JSON 翻译文件
    json_path = os.path.join(locale_dir, 'zh_CN.json')
    translations = {}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except Exception as e:
        print(f"Error loading translations: {e}")
    
    def translate(text):
        """翻译函数"""
        return translations.get(text, text)
    
    return translate

# 创建全局翻译函数
l = setup_localization() 