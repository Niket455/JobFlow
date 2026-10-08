from typing import Any, Protocol

import boto3
from botocore.client import Config

from app.core.config import settings

DEFAULT_CONTENT_TYPE = "application/octet-stream"


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str = DEFAULT_CONTENT_TYPE) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class InMemoryStorage:
    """Test/dev storage backend that keeps objects in memory."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str = DEFAULT_CONTENT_TYPE) -> None:
        self._objects[key] = data

    def get(self, key: str) -> bytes:
        return self._objects[key]

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)


class S3Storage:
    """S3-compatible object storage (MinIO locally, S3 in the cloud)."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str,
    ) -> None:
        self._bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self._bucket_ensured = False

    def _ensure_bucket(self) -> None:
        if self._bucket_ensured:
            return
        names = {b["Name"] for b in self._client.list_buckets().get("Buckets", [])}
        if self._bucket not in names:
            self._client.create_bucket(Bucket=self._bucket)
        self._bucket_ensured = True

    def put(self, key: str, data: bytes, content_type: str = DEFAULT_CONTENT_TYPE) -> None:
        self._ensure_bucket()
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        data: bytes = obj["Body"].read()
        return data

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


def build_storage() -> ObjectStorage:
    return S3Storage(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
    )
