from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_name: str
    db_user: str
    db_password: str
    db_host: str = "postgres"
    db_port: int = 5432

    kalshi_api_key: str = ""
    kalshi_api_secret: str = ""
    polymarket_api_key: str = ""

    environment: str = "development"

    @property
    def database_url(self) -> str:
        # TODO: return the asyncpg connection string
        # format: postgresql+asyncpg://user:password@host:port/dbname
        raise NotImplementedError

    class Config:
        env_file = ".env"


settings = Settings()
