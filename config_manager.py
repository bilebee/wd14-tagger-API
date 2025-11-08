#!/usr/bin/env python3
"""
配置管理脚本，用于创建或修改WD14 Tagger API的配置文件
"""

import json
import os
import argparse
import sys

# 默认配置
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "model_dir": "./models",
    "debug": False,
    "reload": False
}

CONFIG_FILE = "config.json"

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取配置文件时出错: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"配置已保存到 {CONFIG_FILE}")
    except Exception as e:
        print(f"保存配置文件时出错: {e}")

def show_config():
    """显示当前配置"""
    config = load_config()
    print("当前配置:")
    print(json.dumps(config, indent=4, ensure_ascii=False))

def set_config_value(key, value):
    """设置配置项的值"""
    config = load_config()
    
    # 尝试转换值类型
    if value.lower() in ('true', 'false'):
        value = value.lower() == 'true'
    elif value.isdigit():
        value = int(value)
    elif value.replace('.', '').isdigit():
        value = float(value)
    
    config[key] = value
    save_config(config)
    print(f"配置项 {key} 已设置为 {value}")

def reset_config():
    """重置为默认配置"""
    save_config(DEFAULT_CONFIG)
    print("配置已重置为默认值")

def main():
    global CONFIG_FILE
    
    parser = argparse.ArgumentParser(description="WD14 Tagger API 配置管理工具")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    parser.add_argument("--set", nargs=2, metavar=('KEY', 'VALUE'), help="设置配置项的值")
    parser.add_argument("--reset", action="store_true", help="重置为默认配置")
    parser.add_argument("--config-file", default=CONFIG_FILE, help="指定配置文件路径")
    
    args = parser.parse_args()
    
    # 如果指定了配置文件路径，则更新全局变量
    CONFIG_FILE = args.config_file
    
    if args.show:
        show_config()
    elif args.set:
        key, value = args.set
        set_config_value(key, value)
    elif args.reset:
        reset_config()
    else:
        # 如果没有指定参数，显示帮助信息
        parser.print_help()

if __name__ == "__main__":
    main()