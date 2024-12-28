import os
import json
from typing import Dict

# 默认语言
DEFAULT_LANGUAGE = 'zh_CN'

# 翻译字典
_translations: Dict[str, Dict[str, str]] = {}

def load_translations(lang: str = DEFAULT_LANGUAGE) -> None:
    """加载指定语言的翻译"""
    global _translations
    try:
        locale_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources',
            'localization',
            f'{lang}.json'
        )
        if os.path.exists(locale_path):
            with open(locale_path, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
        else:
            _translations[lang] = {}
    except Exception as e:
        print(f"加载翻译文件失败: {e}")
        _translations[lang] = {}

def _(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """获取翻译文本"""
    if lang not in _translations:
        load_translations(lang)
    return _translations.get(lang, {}).get(key, key)

# 初始化默认语言的翻译
load_translations() 