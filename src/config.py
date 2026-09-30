"""Configuration, Secure Secret Management, and Strategic Model Routing."""

import os
from enum import Enum
from typing import Optional
from google.cloud import secretmanager


class TaskComplexity(str, Enum):
    FAST_RETRIEVAL = "fast_retrieval"
    STRUCTURED_DRAFTING = "structured_drafting"
    DEEP_REASONING = "deep_reasoning"


class SecretVault:
    """Retrieves secrets securely from Google Cloud Secret Manager without hardcoding keys."""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "siemens-kf-demo")
        self._client: Optional[secretmanager.SecretManagerServiceClient] = None

    @property
    def client(self) -> secretmanager.SecretManagerServiceClient:
        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()
        return self._client

    def get_secret(self, secret_id: str, version_id: str = "latest") -> str:
        """Fetches a secret from GCP Secret Manager with safe local demo fallback."""
        env_override = os.getenv(secret_id.upper())
        if env_override:
            return env_override

        if os.getenv("DEMO_OFFLINE_MODE", "true").lower() == "true":
            return f"demo-resolved-secret-for-{secret_id}"

        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")


class ModelRouter:
    """Routes agent workloads to the optimal Gemini model tier based on cognitive load."""

    FLASH_MODEL = "gemini-2.5-flash"
    PRO_MODEL = "gemini-2.5-pro"

    @classmethod
    def select_model(cls, complexity: TaskComplexity) -> str:
        """
        Routes high-speed search/breakdown tasks to Flash and complex architectural
        blast-radius or legacy C++/PLC refactoring tasks to Pro.
        """
        routing_table = {
            TaskComplexity.FAST_RETRIEVAL: cls.FLASH_MODEL,
            TaskComplexity.STRUCTURED_DRAFTING: cls.FLASH_MODEL,
            TaskComplexity.DEEP_REASONING: cls.PRO_MODEL,
        }
        return routing_table.get(complexity, cls.PRO_MODEL)
