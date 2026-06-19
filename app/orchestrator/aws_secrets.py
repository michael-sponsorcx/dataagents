import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SecretsManager:
    """Load secrets from AWS Secrets Manager with caching."""

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._aws_enabled = self._check_aws_available()

    def _check_aws_available(self) -> bool:
        """Check if AWS SDK is available and credentials are configured."""
        try:
            import boto3
            _ = boto3.Session()
            return True
        except Exception as e:
            logger.debug(f"AWS unavailable: {e}")
            return False

    def get_secret(self, secret_name: str) -> Optional[dict]:
        """Fetch secret from AWS Secrets Manager with caching."""
        if not self._aws_enabled:
            return None

        if secret_name in self._cache:
            return self._cache[secret_name]

        try:
            import boto3
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response["SecretString"])
            self._cache[secret_name] = secret
            logger.info(f"Loaded secret '{secret_name}' from AWS Secrets Manager")
            return secret
        except Exception as e:
            logger.warning(f"Failed to load secret '{secret_name}' from AWS: {e}")
            self._cache[secret_name] = {}
            return None


secrets_manager = SecretsManager()
