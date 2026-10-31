"""Output storage: a local directory for development, a GCS bucket in production."""

from __future__ import annotations

import logging
import mimetypes
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path

log = logging.getLogger(__name__)


class Store(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str | None = None) -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes | None: ...

    @abstractmethod
    def list_dirs(self, prefix: str) -> list[str]:
        """Names of the immediate child 'directories' under prefix (prefix ends with '/')."""

    @abstractmethod
    def url(self, key: str) -> str:
        """A link a person can open to fetch the object."""

    @abstractmethod
    def describe(self) -> str: ...

    def put_file(self, key: str, path: Path, content_type: str | None = None) -> None:
        self.put(key, path.read_bytes(), content_type or mimetypes.guess_type(str(path))[0])


class LocalStore(Store):
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents and p != self.root:
            raise ValueError(f"key escapes storage root: {key!r}")
        return p

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes | None:
        p = self._path(key)
        return p.read_bytes() if p.is_file() else None

    def list_dirs(self, prefix: str) -> list[str]:
        p = self._path(prefix.rstrip("/"))
        if not p.is_dir():
            return []
        return sorted(child.name for child in p.iterdir() if child.is_dir())

    def url(self, key: str) -> str:
        return self._path(key).as_uri()

    def describe(self) -> str:
        return f"local directory {self.root}"


class GCSStore(Store):
    def __init__(self, bucket: str, prefix: str = ""):
        from google.cloud import storage  # imported lazily so local dev needs no GCP libs loaded

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket)
        self.bucket_name = bucket
        self.prefix = prefix.strip("/")
        self._signing_warned = False

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        blob = self.bucket.blob(self._key(key))
        blob.upload_from_string(data, content_type=content_type or "application/octet-stream")

    def get(self, key: str) -> bytes | None:
        blob = self.bucket.blob(self._key(key))
        if not blob.exists():
            return None
        return blob.download_as_bytes()

    def list_dirs(self, prefix: str) -> list[str]:
        full = self._key(prefix.rstrip("/")) + "/"
        iterator = self.client.list_blobs(self.bucket_name, prefix=full, delimiter="/")
        list(iterator)  # populate prefixes
        names = [p[len(full):].rstrip("/") for p in iterator.prefixes]
        return sorted(n for n in names if n)

    def url(self, key: str) -> str:
        blob = self.bucket.blob(self._key(key))
        try:
            return blob.generate_signed_url(version="v4", expiration=timedelta(days=7))
        except Exception:
            pass
        try:
            import google.auth
            import google.auth.transport.requests

            creds, _ = google.auth.default()
            creds.refresh(google.auth.transport.requests.Request())
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(days=7),
                service_account_email=getattr(creds, "service_account_email", None),
                access_token=creds.token,
            )
        except Exception as exc:
            if not self._signing_warned:
                self._signing_warned = True
                log.warning(
                    "Could not create signed URLs (%s). Falling back to console links that need a Google "
                    "login. Grant the service account roles/iam.serviceAccountTokenCreator on itself to fix.",
                    exc,
                )
        return f"https://storage.cloud.google.com/{self.bucket_name}/{self._key(key)}"

    def describe(self) -> str:
        return f"gs://{self.bucket_name}/{self.prefix}".rstrip("/")


def open_store(spec: str) -> Store:
    """Parse POND_STORAGE: 'local:<dir>' or 'gs://<bucket>[/<prefix>]'."""
    if spec.startswith("gs://"):
        rest = spec[len("gs://"):]
        bucket, _, prefix = rest.partition("/")
        if not bucket:
            raise ValueError("gs:// storage needs a bucket name")
        return GCSStore(bucket, prefix)
    if spec.startswith("local:"):
        return LocalStore(Path(spec[len("local:"):]).expanduser())
    raise ValueError(f"Unknown storage spec {spec!r}; use local:<dir> or gs://<bucket>[/<prefix>]")
