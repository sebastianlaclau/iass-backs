# clients/iass-back-demo/config.py
from pydantic_settings import BaseSettings
from core.models.config import WABAConfig


class DemoClientSettings(BaseSettings):
    # Client-specific settings
    LABEL_DEMO: str = "Demo"

    PHONE_NUMBER_DEMO: str
    FB_WABA_DEMO: str
    FB_PERMANENT_TOKEN_DEMO: str
    PHONE_NUMBER_ID_DEMO: str
    OPENAI_ASSIST_ID_DEMO: str
    OPENAI_API_KEY_DEMO: str
    APP_ID_DEMO: str
    FB_VERIFY_TOKEN: str = "prasath"

    # Required base settings
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    class Config:
        env_file = "clients/iass_back_demo/.env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields

    def create_waba_config(self) -> WABAConfig:
        """Create initial WABA configuration from settings"""
        return WABAConfig(
            phone_number=self.PHONE_NUMBER_DEMO,
            waba_id=self.FB_WABA_DEMO,
            permanent_token=self.FB_PERMANENT_TOKEN_DEMO,
            phone_number_id=self.PHONE_NUMBER_ID_DEMO,
            verification_token=self.FB_VERIFY_TOKEN,
            openai_assist_id=self.OPENAI_ASSIST_ID_DEMO,
            openai_api_key=self.OPENAI_API_KEY_DEMO,
        )
