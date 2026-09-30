"""Observability: Structured JSON Logging, OpenTelemetry Tracing, PII Redaction, Intent/Outcome."""

import functools
import json
import logging
import os
import re
import sys
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from pythonjsonlogger import jsonlogger

try:
    from google.cloud import dlp_v2
    DLP_AVAILABLE = True
except ImportError:
    DLP_AVAILABLE = False


class PIIRedactor:
    """Scrubs sensitive PII/industrial credentials using Google Cloud DLP and regex fallback."""

    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    IP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    KEY_REGEX = re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]+['\"]?")

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "siemens-kf-demo")
        self.use_cloud_dlp = DLP_AVAILABLE and os.getenv("ENABLE_CLOUD_DLP", "false").lower() == "true"
        self._dlp_client = dlp_v2.DlpServiceClient() if self.use_cloud_dlp else None

    def redact_text(self, text: str) -> str:
        """Redacts emails, IPv4 addresses, and credentials before logging or memory persistence."""
        if not text:
            return text

        # Fast local regex pass
        scrubbed = self.EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
        scrubbed = self.IP_REGEX.sub("[REDACTED_IP]", scrubbed)
        scrubbed = self.KEY_REGEX.sub(r"\1=[REDACTED_SECRET]", scrubbed)

        # Optional Google Cloud DLP API pass for production environments
        if self.use_cloud_dlp and self._dlp_client:
            parent = f"projects/{self.project_id}/locations/global"
            inspect_config = {
                "info_types": [
                    {"name": "EMAIL_ADDRESS"},
                    {"name": "PHONE_NUMBER"},
                    {"name": "PERSON_NAME"},
                ]
            }
            deidentify_config = {
                "info_type_transformations": {
                    "transformations": [
                        {"primitive_transformation": {"replace_with_info_type_config": {}}}
                    ]
                }
            }
            response = self._dlp_client.deidentify_content(
                request={
                    "parent": parent,
                    "inspect_config": inspect_config,
                    "deidentify_config": deidentify_config,
                    "item": {"value": scrubbed},
                }
            )
            scrubbed = response.item.value

        return scrubbed


class RedactingJsonFormatter(jsonlogger.JsonFormatter):
    """Structured JSON log formatter that automatically scrubs PII across all fields."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.redactor = PIIRedactor()

    def process_log_record(self, log_record: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in list(log_record.items()):
            if isinstance(value, str):
                log_record[key] = self.redactor.redact_text(value)
            elif isinstance(value, dict):
                log_record[key] = json.loads(self.redactor.redact_text(json.dumps(value)))
        return super().process_log_record(log_record)


def setup_observability(service_name: str = "siemens-knowledge-fabric") -> tuple[logging.Logger, trace.Tracer]:
    """Configures structured JSON logging and OpenTelemetry distributed tracing."""
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = RedactingJsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(otelTraceID)s %(otelSpanID)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if os.getenv("ENABLE_OTEL_CONSOLE", "false").lower() == "true":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(service_name)
    return logger, tracer


logger, tracer = setup_observability()


def trace_intent_and_outcome(action_name: str) -> Callable:
    """
    Decorator that creates an OpenTelemetry span and explicitly logs both the
    agent's INTENDED action prior to execution and ACTUAL outcome afterward.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(action_name) as span:
                span_ctx = span.get_span_context()
                trace_id = format(span_ctx.trace_id, "032x") if span_ctx.is_valid else "no-trace"
                span_id = format(span_ctx.span_id, "016x") if span_ctx.is_valid else "no-span"

                logger.info(
                    "AGENT_INTENT_CAPTURED",
                    extra={
                        "event_type": "INTENT",
                        "intended_action": action_name,
                        "input_args": str(kwargs or args),
                        "otelTraceID": trace_id,
                        "otelSpanID": span_id,
                    },
                )
                try:
                    result = func(*args, **kwargs)
                    logger.info(
                        "AGENT_OUTCOME_CAPTURED",
                        extra={
                            "event_type": "OUTCOME",
                            "intended_action": action_name,
                            "actual_outcome": "SUCCESS",
                            "result_summary": str(result)[:300],
                            "otelTraceID": trace_id,
                            "otelSpanID": span_id,
                        },
                    )
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    logger.error(
                        "AGENT_OUTCOME_CAPTURED",
                        extra={
                            "event_type": "OUTCOME",
                            "intended_action": action_name,
                            "actual_outcome": "FAILURE",
                            "error_detail": str(exc),
                            "otelTraceID": trace_id,
                            "otelSpanID": span_id,
                        },
                    )
                    raise
        return wrapper
    return decorator
