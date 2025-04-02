# core/utils/supabase_client.py
from supabase import create_client
from core.config import config_manager

# Get project-wide configuration
project_config = config_manager.get_project_config()

supabase = create_client(
    project_config.SUPABASE_URL, project_config.SUPABASE_SERVICE_ROLE_KEY
)
