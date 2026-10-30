from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AICTE Integrated Institution Complaint Monitoring"
    environment: str = "development"
    database_url: str = "sqlite:///./aicte.db"
    secret_key: str = "dev-only-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    auto_link_threshold: float = 0.90
    review_threshold: float = 0.65
    sla_outer_days: int = 90
    sla_milestone_days: str = "30,60,75"
    no_action_reminder_days: int = 15
    at_risk_days: int = 75
    overlap_escalate_days: int = 3
    near_duplicate_threshold: float = 0.55
    scheduler_enabled: bool = True
    seed_demo: bool = True
    seed_random_seed: int = 20261025
    seed_use_llm: bool = False

    # Connectors / provenance
    source_mode_css: str = "simulator"
    source_mode_cpgrams: str = "simulator"
    css_base_url: str = "http://mock-css:8101"
    cpgrams_base_url: str = "http://mock-cpgrams:8102"
    css_admin_url: str = "http://mock-css:8101"
    cpgrams_admin_url: str = "http://mock-cpgrams:8102"
    css_file_path: str = "backend/sample_data/css_tickets.csv"
    cpgrams_file_path: str = "backend/sample_data/cpgrams_tickets.json"
    css_sync_interval: int = 20
    cpgrams_sync_interval: int = 20
    public_stats_interval: int = 900
    connector_timeout_seconds: int = 8
    source_cache_ttl_seconds: int = 300
    ogd_base_url: str = "https://api.data.gov.in/resource"
    ogd_resource_ids: str = ""
    ogd_api_key: str = ""
    cpgrams_public_stats_url: str = ""
    institution_master_url: str = ""
    enable_llm_query: bool = False
    enable_translation: bool = False
    translation_provider: str = "stub"
    complainant_hash_salt: str = "dev-demo-salt-change-me"
    cross_channel_window_days: int = 7
    emerging_min_count: int = 5
    emerging_z_threshold: float = 2.0
    institution_master_interval: int = 86400
    demo_scenario_enabled: bool = True

    # Transparent institution risk weights (points per unit, capped)
    risk_weight_active_cases: float = 8.0
    risk_weight_distinct_bureaus: float = 7.0
    risk_weight_overdue_cases: float = 10.0
    risk_weight_escalations: float = 8.0
    risk_weight_repeat_category: float = 5.0
    risk_weight_recency: float = 10.0
    risk_weight_unack_overlap: float = 12.0
    risk_cap: float = 100.0

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def milestone_days(self) -> List[int]:
        return sorted(int(v.strip()) for v in self.sla_milestone_days.split(",") if v.strip())

    @property
    def ogd_ids(self) -> List[str]:
        return [x.strip() for x in self.ogd_resource_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
