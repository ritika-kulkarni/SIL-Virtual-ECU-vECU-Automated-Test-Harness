"""Artifactory publishers (HTTP + local mock)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin

import httpx

from sil_harness.core.config import ArtifactoryConfig, RetryConfig
from sil_harness.core.errors import PublishError
from sil_harness.core.logging import get_logger
from sil_harness.core.retry import call_with_retry

log = get_logger(__name__)


class ArtifactoryClient(Protocol):
    def upload(self, local_path: Path, remote_path: str) -> str: ...


class LocalMockArtifactory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def upload(self, local_path: Path, remote_path: str) -> str:
        if not local_path.exists():
            raise PublishError(f"Artifact missing: {local_path}")
        dest = self.root / remote_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if local_path.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(local_path, dest)
        else:
            shutil.copy2(local_path, dest)
        uri = f"file://{dest.resolve()}"
        log.info("Mock Artifactory upload %s -> %s", local_path, uri)
        return uri


class HttpArtifactory:
    def __init__(self, cfg: ArtifactoryConfig, retry: RetryConfig) -> None:
        self.cfg = cfg
        self.retry = retry
        user = os.environ.get(cfg.username_env, "")
        password = os.environ.get(cfg.password_env, "")
        self._auth = (user, password) if user or password else None

    def upload(self, local_path: Path, remote_path: str) -> str:
        if not local_path.is_file():
            raise PublishError(f"HTTP publisher expects a file: {local_path}")

        url = urljoin(
            self.cfg.base_url.rstrip("/") + "/",
            f"{self.cfg.repository}/{remote_path}",
        )

        def _put() -> str:
            try:
                with local_path.open("rb") as fh:
                    response = httpx.put(url, content=fh, auth=self._auth, timeout=60.0)
                if response.status_code >= 400:
                    raise PublishError(
                        f"Artifactory upload failed ({response.status_code}): {response.text[:200]}"
                    )
                log.info("Uploaded %s -> %s", local_path, url)
                return url
            except httpx.HTTPError as exc:
                raise PublishError(f"Artifactory HTTP error: {exc}") from exc

        return call_with_retry(_put, self.retry, retry_on=(PublishError,))


def create_artifactory_client(cfg: ArtifactoryConfig, retry: RetryConfig) -> ArtifactoryClient:
    if cfg.mode == "http":
        return HttpArtifactory(cfg, retry)
    return LocalMockArtifactory(Path(cfg.local_root))
