"""
Telemetry compatibility shim for the assignment environment.

Upstream livekit-agents integrates with OpenTelemetry tracing/logging. In this
environment, the OpenTelemetry logging API surface differs from what this repo
expects, causing import-time crashes.

This module provides a no-op tracer + minimal trace_types constants so the rest
of the agents stack can run without telemetry.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any


def _setup_cloud_tracer(*args: Any, **kwargs: Any) -> None:
    return None


def _upload_session_report(*args: Any, **kwargs: Any) -> None:
    return None


def set_tracer_provider(*args: Any, **kwargs: Any) -> None:
    return None


class _NoopSpan:
    def set_attributes(self, *args, **kwargs) -> None:
        return None

    def is_recording(self) -> bool:
        return False

    def get_span_context(self):
        return None

    def set_attribute(self, *args: Any, **kwargs: Any) -> None:
        return None

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        return None

    def record_exception(self, *args: Any, **kwargs: Any) -> None:
        return None

    def add_event(self, *args: Any, **kwargs: Any) -> None:
        return None

    def end(self, *args: Any, **kwargs: Any) -> None:
        return None

    # Some OTEL spans are used as context managers
    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _NoopTracer:
    """
    Implements the tracer methods used across this repo:
    - start_as_current_span(name): used as decorator and as context manager
    - start_span(name): used to create a span object
    """

    def start_span(self, *args: Any, **kwargs: Any) -> _NoopSpan:
        return _NoopSpan()

    def start_as_current_span(self, *args: Any, **kwargs: Any):
        # Must support BOTH:
        # 1) decorator: @tracer.start_as_current_span("name")
        # 2) with: with tracer.start_as_current_span("name"):
        @contextmanager
        def _cm():
            yield _NoopSpan()

        def _decorator(fn):
            def _wrapped(*f_args: Any, **f_kwargs: Any):
                with _cm():
                    return fn(*f_args, **f_kwargs)
            return _wrapped

        class _Both:
            def __call__(self, fn):
                return _decorator(fn)

            def __enter__(self):
                self._it = _cm()
                return self._it.__enter__()

            def __exit__(self, exc_type, exc, tb):
                return self._it.__exit__(exc_type, exc, tb)

        return _Both()


class _TraceTypes:
    # Known attributes (keep these)
    ATTR_JOB_ID = "livekit.job.id"
    ATTR_WORKER_ID = "livekit.worker.id"
    ATTR_ROOM_NAME = "livekit.room.name"
    ATTR_PARTICIPANT_IDENTITY = "livekit.participant.identity"
    ATTR_PARTICIPANT_SID = "livekit.participant.sid"
    ATTR_AGENT_NAME = "livekit.agent.name"
    ATTR_AGENT_ID = "livekit.agent.id"
    ATTR_AGENT_LABEL = "livekit.agent.label"
    EVENT_GEN_AI_CHOICE = "livekit.event.gen_ai_choice"
    EVENT_GEN_AI_REQUEST = "livekit.event.gen_ai_request"
    EVENT_GEN_AI_RESPONSE = "livekit.event.gen_ai_response"


    # Catch-all: any missing ATTR_* will resolve to a stable string key
    def __getattr__(self, name: str) -> str:
        if name.startswith("ATTR_"):
            return "livekit." + name[5:].lower()
        if name.startswith("EVENT_"):
            return "livekit.event." + name[6:].lower()
        return name

tracer = _NoopTracer()
trace_types = _TraceTypes()
