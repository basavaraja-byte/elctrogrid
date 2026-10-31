"""Application configuration settings powered by pydantic-settings."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Canonical application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="DISPATCHGRID", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # Database connection URL (defaults to PostgreSQL with psycopg v3 driver)
    database_url: str = Field(
        default="postgresql+psycopg://dispatchgrid:dispatchgrid_secret@localhost:5432/dispatchgrid",
        alias="DATABASE_URL",
    )
    test_database_url: str = Field(
        default="sqlite:///./test_dispatchgrid.db",
        alias="TEST_DATABASE_URL",
    )

    # CORS Origins
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,https://elctrogrid.vercel.app",
        alias="CORS_ORIGINS",
    )

    # Optional Supabase Integration Settings
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_secret: str | None = Field(default=None, alias="SUPABASE_JWT_SECRET")

    # Shift & Timezone Policies
    allow_overnight_shifts: bool = Field(
        default=False,
        alias="ALLOW_OVERNIGHT_SHIFTS",
    )
    local_timezone_offset_minutes: int = Field(
        default=330,  # IST (UTC+05:30)
        alias="LOCAL_TIMEZONE_OFFSET_MINUTES",
    )

    # Documented Multi-Criteria Heuristic Scoring Weights
    weight_travel_time: float = Field(default=0.25, alias="WEIGHT_TRAVEL_TIME")
    weight_sla_risk: float = Field(default=0.30, alias="WEIGHT_SLA_RISK")
    weight_job_priority: float = Field(default=0.15, alias="WEIGHT_JOB_PRIORITY")
    weight_workload_balance: float = Field(default=0.15, alias="WEIGHT_WORKLOAD_BALANCE")
    weight_schedule_stability: float = Field(default=0.15, alias="WEIGHT_SCHEDULE_STABILITY")

    # Razorpay Test Mode Settings
    razorpay_key_id: str | None = Field(default=None, alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: str | None = Field(default=None, alias="RAZORPAY_KEY_SECRET")
    payment_mode: str = Field(default="test", alias="PAYMENT_MODE")
    demo_payment_enabled: bool = Field(default=True, alias="DEMO_PAYMENT_ENABLED")

    @property
    def cors_origin_list(self) -> list[str]:
        """Return parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def scoring_weights_dict(self) -> dict[str, float]:
        """Return documented candidate ranking weights."""
        return {
            "travel_time": self.weight_travel_time,
            "sla_risk": self.weight_sla_risk,
            "job_priority": self.weight_job_priority,
            "workload_balance": self.weight_workload_balance,
            "schedule_stability": self.weight_schedule_stability,
        }


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


settings = get_settings()

