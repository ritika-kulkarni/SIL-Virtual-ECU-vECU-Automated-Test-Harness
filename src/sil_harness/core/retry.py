"""Retry helpers with exponential backoff."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from sil_harness.core.config import RetryConfig
from sil_harness.core.errors import SilHarnessError

T = TypeVar("T")


def build_retry(
    cfg: RetryConfig,
    *,
    retry_on: tuple[type[BaseException], ...] = (SilHarnessError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    return retry(
        reraise=True,
        stop=stop_after_attempt(cfg.max_attempts),
        wait=wait_exponential(
            multiplier=cfg.initial_delay_sec,
            max=cfg.max_delay_sec,
        ),
        retry=retry_if_exception_type(retry_on),
    )


def call_with_retry(
    fn: Callable[..., T],
    cfg: RetryConfig,
    *args: object,
    retry_on: tuple[type[BaseException], ...] = (SilHarnessError,),
    **kwargs: object,
) -> T:
    decorated = build_retry(cfg, retry_on=retry_on)(fn)
    try:
        return decorated(*args, **kwargs)
    except RetryError as exc:
        last = exc.last_attempt.exception() if exc.last_attempt else exc
        raise last from exc
