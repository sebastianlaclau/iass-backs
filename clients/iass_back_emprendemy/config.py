# clients/iass_back_emprendemy/config.py
from pydantic_settings import BaseSettings
from core.models.config import WABAConfig


class EmprendemyClientSettings(BaseSettings):
    # Client-specific settings
    LABEL_EMPRENDEMY: str = "Emprendemy"

    # WABA settings - use the exact names from your environment variables
    PHONE_NUMBER_EMPRENDEMY: str
    FB_WABA_EMPRENDEMY: str
    FB_PERMANENT_TOKEN_EMPRENDEMY: str
    PHONE_NUMBER_ID_EMPRENDEMY: str
    OPENAI_ASSIST_ID_EMPRENDEMY: str
    OPENAI_API_KEY_EMPRENDEMY: str
    APP_ID_EMPRENDEMY: str
    FB_VERIFY_TOKEN: str = "prasath"

    # Required base settings
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    class Config:
        env_file = "clients/iass_back_emprendemy/.env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields

    def create_waba_config(self) -> WABAConfig:
        """Create initial WABA configuration from settings"""
        return WABAConfig(
            phone_number=self.PHONE_NUMBER_EMPRENDEMY,
            waba_id=self.FB_WABA_EMPRENDEMY,
            permanent_token=self.FB_PERMANENT_TOKEN_EMPRENDEMY,
            phone_number_id=self.PHONE_NUMBER_ID_EMPRENDEMY,
            verification_token=self.FB_VERIFY_TOKEN,
            openai_assist_id=self.OPENAI_ASSIST_ID_EMPRENDEMY,
            openai_api_key=self.OPENAI_API_KEY_EMPRENDEMY,
        )
