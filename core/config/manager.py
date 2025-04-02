from typing import Dict, Optional
from core.models.config import ProjectConfig, ClientConfig


class ConfigManager:
    """Manages loading and access to all configurations"""

    def __init__(self):
        self._project_config = ProjectConfig()
        self._clients: Dict[str, ClientConfig] = {}

    def register_client(self, client_id: str, config: ClientConfig):
        """Register a client configuration"""
        self._clients[client_id] = config

    def get_client_config(self, client_id: str) -> Optional[ClientConfig]:
        """Get configuration for a specific client"""
        return self._clients.get(client_id)

    def get_project_config(self) -> ProjectConfig:
        """Get base application configuration"""
        return self._project_config
