import os
import base64
from typing import Optional
from aws_secrets import secrets_manager


class Config:
    """Application configuration from environment variables or AWS Secrets Manager.

    Resolution order for each credential:
    1. Environment variable (e.g., LANGFUSE_ORC_PUBLIC_KEY)
    2. AWS Secrets Manager (dev/* or prod/* based on ENVIRONMENT)
    3. Default value
    """

    @property
    def _environment(self) -> str:
        """Get environment (dev or prod)."""
        return "prod" if os.getenv("ENVIRONMENT") == "prod" else "dev"

    def _get(self, key: str, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Resolve credential: env var → AWS Secrets Manager → default."""
        # 1. Check environment variable
        if key in os.environ:
            return os.environ[key]

        # 2. Check AWS Secrets Manager
        secret = secrets_manager.get_secret(secret_name)
        if secret and key in secret:
            return secret[key]

        # 3. Return default
        return default

    # Langfuse
    @property
    def langfuse_public_key(self) -> Optional[str]:
        return self._get("LANGFUSE_ORC_PUBLIC_KEY", f"{self._environment}/langfuse-orc")

    @property
    def langfuse_secret_key(self) -> Optional[str]:
        return self._get("LANGFUSE_ORC_SECRET_KEY", f"{self._environment}/langfuse-orc")

    @property
    def langfuse_host(self) -> str:
        return self._get("LANGFUSE_ORC_BASE_URL", f"{self._environment}/langfuse-orc",
                        default="https://cloud.langfuse.com")

    # AI Insights
    @property
    def ai_insights_api_url(self) -> Optional[str]:
        return self._get("AI_INSIGHTS_API_URL", f"{self._environment}/ai-insights")

    @property
    def ai_insights_api_key(self) -> Optional[str]:
        return self._get("AI_INSIGHTS_API_KEY", f"{self._environment}/ai-insights")

    # Session storage (orchestrator conversation memory, persisted to Postgres)
    @property
    def session_db_url(self) -> Optional[str]:
        """libpq connection string for the session store (e.g. postgresql://user:pw@host/db)."""
        return self._get("SESSION_DATABASE_URL", f"{self._environment}/session-storage")

    def get_otel_headers(self) -> str:
        """Generate OTEL authentication header for Langfuse OTLP endpoint."""
        if not self.langfuse_public_key or not self.langfuse_secret_key:
            return ""
        creds = f"{self.langfuse_public_key}:{self.langfuse_secret_key}"
        encoded = base64.b64encode(creds.encode()).decode()
        return f"Authorization=Basic {encoded}"


config = Config()
