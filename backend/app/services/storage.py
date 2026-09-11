import io
from typing import List, Dict, Any, Optional
from minio import Minio
from minio.error import S3Error
from app.core.config import settings

BUCKET_NAME = "invenza-documents"

class StorageService:
    _client: Optional[Minio] = None

    @classmethod
    def get_client(cls) -> Minio:
        if cls._client is None:
            # Strip http:// or https:// if present in endpoint
            endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
            cls._client = Minio(
                endpoint,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,
            )
            # Ensure bucket exists
            try:
                if not cls._client.bucket_exists(BUCKET_NAME):
                    cls._client.make_bucket(BUCKET_NAME)
            except Exception as e:
                print(f"[MinIO Storage] Notice on bucket check: {e}")
        return cls._client

    @classmethod
    def upload_file(
        cls,
        file_bytes: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        client = cls.get_client()
        # Ensure bucket
        try:
            if not client.bucket_exists(BUCKET_NAME):
                client.make_bucket(BUCKET_NAME)
        except Exception:
            pass

        data_stream = io.BytesIO(file_bytes)
        size = len(file_bytes)

        client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            data=data_stream,
            length=size,
            content_type=content_type,
            metadata=metadata or {},
        )

        return {
            "bucket": BUCKET_NAME,
            "object_name": object_name,
            "size": size,
            "content_type": content_type,
            "url": f"/api/v1/storage/files/{object_name}",
        }

    @classmethod
    def get_file(cls, object_name: str):
        client = cls.get_client()
        response = client.get_object(BUCKET_NAME, object_name)
        return response

    @classmethod
    def get_file_bytes(cls, object_name: str) -> Optional[bytes]:
        """Fetch raw bytes for an object from MinIO with safe error handling."""
        try:
            client = cls.get_client()
            response = client.get_object(BUCKET_NAME, object_name)
            try:
                data = response.read()
                return data
            finally:
                response.close()
                response.release_conn()
        except Exception as e:
            print(f"[MinIO Storage] Object {object_name} read error: {e}")
            return None

    @classmethod
    def file_exists(cls, object_name: str) -> bool:
        """Check if an object exists in MinIO bucket."""
        try:
            client = cls.get_client()
            client.stat_object(BUCKET_NAME, object_name)
            return True
        except Exception:
            return False

    @classmethod
    def delete_file(cls, object_name: str) -> bool:
        """Remove an object from MinIO bucket."""
        try:
            client = cls.get_client()
            client.remove_object(BUCKET_NAME, object_name)
            return True
        except Exception as e:
            print(f"[MinIO Storage] Error deleting {object_name}: {e}")
            return False

    @classmethod
    def list_files(cls) -> List[Dict[str, Any]]:
        client = cls.get_client()
        try:
            if not client.bucket_exists(BUCKET_NAME):
                return []
            objects = client.list_objects(BUCKET_NAME, recursive=True)
            return [
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "url": f"/api/v1/storage/files/{obj.object_name}",
                }
                for obj in objects
            ]
        except Exception as e:
            print(f"[MinIO list_files Error]: {e}")
            return []
