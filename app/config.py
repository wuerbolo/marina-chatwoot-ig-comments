from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    meta_app_id: str
    meta_app_secret: str
    meta_verify_token: str
    ig_long_lived_access_token: str

    chatwoot_base_url: str
    chatwoot_account_id: str
    chatwoot_api_access_token: str
    chatwoot_inbox_id_comentarios: str
    chatwoot_inbox_webhook_secret: str

    database_url: str

    meta_graph_api_version: str = "v21.0"
    private_reply_window_days: int = 7


settings = Settings()
