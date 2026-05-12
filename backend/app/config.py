from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://wm:changeme@localhost:5432/wm_predictor"
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    ODDS_API_KEY: str | None = None
    ODDS_API_BASE: str = "https://api.the-odds-api.com/v4"

    CORS_ORIGINS: str = "http://localhost:5173"

    ENSEMBLE_WEIGHT_ODDS: float = 0.60
    ENSEMBLE_WEIGHT_ELO: float = 0.25
    ENSEMBLE_WEIGHT_FORM: float = 0.10
    ENSEMBLE_WEIGHT_H2H: float = 0.03
    ENSEMBLE_WEIGHT_HOME: float = 0.02

    ELO_K_WORLDCUP: float = 60
    ELO_K_CONTINENTAL: float = 50
    ELO_K_QUALIFIER: float = 40
    ELO_K_NATIONS: float = 35
    ELO_K_FRIENDLY: float = 20

    MC_DEFAULT_RUNS: int = 10000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
