# core/config/__init__.py

from core.config.manager import ConfigManager

# Create a singleton instance of ConfigManager
config_manager = ConfigManager()

# Export only config_manager
__all__ = ["config_manager"]
