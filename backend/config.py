from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # LLM
    groq_api_key: str
    mcp_server_url: str = "http://localhost:8001/sse"

    # Google Calendar
    google_credentials_path: str = "./services/google_credentials.json"
    google_token_path: str = "./services/google_token.json"

    # Resend
    resend_api_key: str
    from_email: str = "appointments@dobbeai.com"

    # Slack
    slack_bot_token: str
    slack_channel_id: str = "#doctor-notifications"

    class Config:
        env_file = ".env"
        extra = "ignore"


# Single instance used everywhere — import this, not the class
settings = Settings()
