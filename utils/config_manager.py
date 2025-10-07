"""
Configuration Manager
"""
import json
import os
from typing import Any, Dict

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = self.get_default_config()
        else:
            self.config = self.get_default_config()
            self.save()
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, indent=4, fp=f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'bot_token': '',
            'guild_id': '',
            'control_channel': 'g07-control',
            'refresh_interval': 5,
            'notifications': True,
            'autostart_bot': False,
            'sound_alerts': True,
            'offline_timeout': 90,  # seconds before marking client offline
            'ping_interval': 45,  # seconds between controller pings
            'theme': 'dark',  # dark or light
            'clients': [],
            'client_history': {}
        }
