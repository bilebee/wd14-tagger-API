import json
import os
from typing import Dict, Any

# 默认配置
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "model_dir": "./models",
    "debug": False,
    "reload": False
}

CONFIG_FILE = "config.json"

def load_config() -> Dict[str, Any]:
    """
    加载配置文件，如果不存在则创建默认配置文件
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 确保所有必需的键都存在
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception as e:
            print(f"读取配置文件时出错: {e}，使用默认配置")
            return DEFAULT_CONFIG
    else:
        # 创建默认配置文件
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]) -> None:
    """
    保存配置到文件
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置文件时出错: {e}")

def get_config_file_path() -> str:
    """
    获取配置文件路径
    """
    return os.path.abspath(CONFIG_FILE)