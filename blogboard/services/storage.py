import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import boto3
from botocore.exceptions import ClientError

from blogboard.config.settings import app_settings

class LocalStorageService:
    """Simple local file storage for articles and metadata."""

    def __init__(self):
        root = app_settings.storage.LOCAL_ROOT.strip(' "\'')
        self.storage_root = Path(root)
        if not self.storage_root.is_absolute():
            self.storage_root = (Path(__file__).resolve().parents[2] / self.storage_root).resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, key: str) -> Path:
        return self.storage_root / key

    def get_uri(self, key: str) -> str:
        return str(self._resolve_key(key))

    def get_object(self, key: str) -> Optional[str]:
        path = self._resolve_key(key)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] Local storage error fetching {key}: {e}")
            return None

    def put_object(self, key: str, data: str, content_type: str = "text/plain") -> bool:
        path = self._resolve_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(data, encoding="utf-8")
            print(f"  ✅ Saved locally: {path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save {key} locally: {e}")
            return False

    def get_json(self, key: str) -> Optional[List[Dict[str, Any]]]:
        data = self.get_object(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                print(f"[WARN] Failed to decode JSON from {key}. Starting fresh.")
                return []
        return []

    def get_articles_json(self, domain: str) -> List[Dict[str, Any]]:
        return self.get_json(f"blogs/{domain}/articles.json") or []

    def save_articles_json(self, domain: str, articles: List[Dict[str, Any]]) -> bool:
        json_str = json.dumps(articles, indent=2, ensure_ascii=False)
        return self.put_object(f"blogs/{domain}/articles.json", json_str, content_type="application/json")

    def get_recent_history(self, domain: str, limit: int = 3) -> List[Dict[str, Any]]:
        articles = self.get_articles_json(domain)
        sorted_articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)
        recent = sorted_articles[:limit]
        return [{
            "title": a.get("title"),
            "topic": a.get("topic"),
            "subtopics": a.get("subtopics", "")
        } for a in recent]

    def get_all_domains_last_updated(self) -> Dict[str, str]:
        latest_dates = {}
        for domain_slug in app_settings.tags.model_dump().keys():
            articles = self.get_articles_json(domain_slug)
            if not articles:
                latest_dates[domain_slug] = "Never"
            else:
                sorted_articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)
                latest_dates[domain_slug] = sorted_articles[0].get("date", "Unknown")
        return latest_dates

class R2StorageService:
    """Cloudflare R2 storage backend."""

    def __init__(self):
        if app_settings.storage.TYPE.lower() != "r2":
            raise RuntimeError("R2StorageService requires STORAGE_TYPE=r2.")
        if app_settings.r2 is None:
            raise RuntimeError("Missing R2 configuration. Set r2 settings or use local storage.")

        self.bucket_name = app_settings.r2.BUCKET_NAME.strip(' "\'')
        self.client = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{app_settings.r2.ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=app_settings.r2.ACCESS_KEY_ID,
            aws_secret_access_key=app_settings.r2.SECRET_ACCESS_KEY,
            region_name="auto"
        )

    def get_uri(self, key: str) -> str:
        return f"r2://{key}"

    def get_object(self, key: str) -> Optional[str]:
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read().decode("utf-8")
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            print(f"[ERROR] R2 error in get_object ({key}): {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error fetching {key}: {e}")
            return None

    def put_object(self, key: str, data: str, content_type: str = "text/plain") -> bool:
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data.encode("utf-8"),
                ContentType=content_type
            )
            print(f"  ✅ Uploaded to R2: {self.bucket_name}/{key}")
            return True
        except ClientError as e:
            print(f"[ERROR] Failed to upload {key} to R2: {e}")
            return False

    def get_json(self, key: str) -> Optional[List[Dict[str, Any]]]:
        data = self.get_object(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                print(f"[WARN] Failed to decode JSON from {key}. Starting fresh.")
                return []
        return []

    def get_articles_json(self, domain: str) -> List[Dict[str, Any]]:
        return self.get_json(f"blogs/{domain}/articles.json") or []

    def save_articles_json(self, domain: str, articles: List[Dict[str, Any]]) -> bool:
        json_str = json.dumps(articles, indent=2, ensure_ascii=False)
        return self.put_object(f"blogs/{domain}/articles.json", json_str, content_type="application/json")

    def get_recent_history(self, domain: str, limit: int = 3) -> List[Dict[str, Any]]:
        articles = self.get_articles_json(domain)
        sorted_articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)
        recent = sorted_articles[:limit]
        return [{
            "title": a.get("title"),
            "topic": a.get("topic"),
            "subtopics": a.get("subtopics", "")
        } for a in recent]

    def get_all_domains_last_updated(self) -> Dict[str, str]:
        latest_dates = {}
        for domain_slug in app_settings.tags.model_dump().keys():
            articles = self.get_articles_json(domain_slug)
            if not articles:
                latest_dates[domain_slug] = "Never"
            else:
                sorted_articles = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)
                latest_dates[domain_slug] = sorted_articles[0].get("date", "Unknown")
        return latest_dates


def get_storage_service():
    if app_settings.storage.TYPE.lower() == "r2":
        return R2StorageService()
    return LocalStorageService()
