import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# 默认配置
DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8080,
        "reload": False
    },
    "paths": {
        "deepdanbooru": None,
        "onnx": None,
        "hf_cache": None
    },
    "authentication": {
        "enabled": False,
        "username": "",
        "password": ""
    },
    "model": {
        "default": None
    },
    "tagging": {
        "max_tags_per_category": 1000,
        "min_tag_score": 0.05
    }
}

class ConfigManager:
    """Configuration manager for WD14 Tagger API"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.environ.get('WD14_TAGGER_CONFIG', 'config.yaml')
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file or use defaults"""
        config = DEFAULT_CONFIG.copy()
        
        # 如果配置文件存在，则加载它
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        # 合并配置，文件中的配置优先
                        self._merge_dict(config, file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_path}: {e}")
        
        return config
    
    def _merge_dict(self, base: Dict, update: Dict) -> None:
        """Recursively merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_dict(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'server.host')"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def save_default_config(self, path: str = "config.yaml") -> None:
        """Save default configuration to a file"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)