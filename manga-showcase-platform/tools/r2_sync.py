"""
r2_sync.py - Cloudflare R2 Free Object Storage Uploader & Manager for Manga Showcases.
Provides:
  1. Zero-egress bandwidth hosting on Cloudflare R2 (10 GB free forever).
  2. Free public bucket streaming via r2.dev (no custom domain required!).
  3. Automatic CORS configuration for direct in-browser web app reading.
  4. Smart, resumable multipart uploads with progress tracking.
  5. Automatic synchronization with frontend/public/comics/index.json.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

CONFIG_FILE = Path(__file__).resolve().parent / "r2_config.json"
DEFAULT_COMICS_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public" / "comics"


def get_default_config() -> Dict[str, str]:
    return {
        "account_id": os.environ.get("R2_ACCOUNT_ID", ""),
        "access_key_id": os.environ.get("R2_ACCESS_KEY_ID", ""),
        "secret_access_key": os.environ.get("R2_SECRET_ACCESS_KEY", ""),
        "bucket_name": os.environ.get("R2_BUCKET_NAME", ""),
        "public_url": os.environ.get("R2_PUBLIC_URL", ""),
    }


def load_r2_config() -> Dict[str, str]:
    """Loads R2 credentials from r2_config.json or environment variables."""
    cfg = get_default_config()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if v and not cfg.get(k):
                        cfg[k] = v
                    elif v:
                        cfg[k] = v
        except Exception as e:
            print(f"Warning: Failed to read {CONFIG_FILE.name}: {e}")
    return cfg


def save_r2_config(
    account_id: str,
    access_key_id: str,
    secret_access_key: str,
    bucket_name: str,
    public_url: str = "",
) -> None:
    """Saves R2 credentials to r2_config.json."""
    data = {
        "account_id": account_id.strip(),
        "access_key_id": access_key_id.strip(),
        "secret_access_key": secret_access_key.strip(),
        "bucket_name": bucket_name.strip(),
        "public_url": public_url.strip().rstrip("/"),
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Cloudflare R2 configuration saved securely to {CONFIG_FILE.name}")


def get_r2_client(config: Optional[Dict[str, str]] = None):
    """Initializes and returns a boto3 S3 client configured for Cloudflare R2."""
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 is not installed. Run 'pip install boto3' to enable Cloudflare R2 upload.")

    cfg = config or load_r2_config()
    account_id = cfg.get("account_id")
    access_key = cfg.get("access_key_id")
    secret_key = cfg.get("secret_access_key")

    if not account_id or not access_key or not secret_key:
        raise ValueError("Missing Cloudflare R2 credentials (account_id, access_key_id, secret_access_key).")

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    return boto3.client(
        service_name="s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(
            s3={"addressing_style": "path"},
            signature_version="s3v4",
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


# Cloudflare R2 Free Tier: 10 GB-months of stored data per month included at $0.00
R2_FREE_TIER_LIMIT_BYTES = 10 * 1024 * 1024 * 1024  # 10.0 GiB (10,737,418,240 bytes)


class StorageLimitExceededError(Exception):
    """Raised when an R2 upload operation would exceed the free tier storage limit."""
    def __init__(self, message: str, storage_info: Dict[str, Any]):
        super().__init__(message)
        self.storage_info = storage_info


def check_r2_storage_limit(
    remote_inventory: Dict[str, int],
    files_to_upload: List[Tuple[Path, str]],
    limit_bytes: int = R2_FREE_TIER_LIMIT_BYTES,
) -> Dict[str, Any]:
    """
    Calculates current, incoming, and projected Cloudflare R2 storage usage.
    Returns metrics including bytes, gigabytes, percentage, and excess amounts.
    """
    current_bytes = sum(remote_inventory.values())
    projected_inventory = dict(remote_inventory)
    incoming_bytes = 0
    for local_fp, key in files_to_upload:
        sz = local_fp.stat().st_size
        incoming_bytes += sz
        projected_inventory[key] = sz

    projected_bytes = sum(projected_inventory.values())
    will_exceed = projected_bytes > limit_bytes
    excess_bytes = max(0, projected_bytes - limit_bytes)

    return {
        "current_bytes": current_bytes,
        "current_gb": current_bytes / (1024 ** 3),
        "incoming_bytes": incoming_bytes,
        "incoming_gb": incoming_bytes / (1024 ** 3),
        "projected_bytes": projected_bytes,
        "projected_gb": projected_bytes / (1024 ** 3),
        "limit_bytes": limit_bytes,
        "limit_gb": limit_bytes / (1024 ** 3),
        "usage_pct": (projected_bytes / limit_bytes) * 100 if limit_bytes else 0,
        "current_pct": (current_bytes / limit_bytes) * 100 if limit_bytes else 0,
        "will_exceed": will_exceed,
        "excess_bytes": excess_bytes,
        "excess_gb": excess_bytes / (1024 ** 3),
    }


def test_r2_connection(config: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """Tests connection to the Cloudflare R2 bucket and inspects free tier storage usage."""
    cfg = config or load_r2_config()
    bucket = cfg.get("bucket_name")
    if not bucket:
        return False, "Bucket name is empty. Please enter your R2 bucket name."

    try:
        s3 = get_r2_client(cfg)
        remote_objs = list_remote_r2_objects(cfg)
        total_bytes = sum(remote_objs.values())
        used_gb = total_bytes / (1024 ** 3)
        limit_gb = R2_FREE_TIER_LIMIT_BYTES / (1024 ** 3)
        pct = (total_bytes / R2_FREE_TIER_LIMIT_BYTES) * 100
        return True, f"✅ Connected to '{bucket}'! Free tier used: {used_gb:.2f} GB / {limit_gb:.0f} GB ({pct:.1f}%, {len(remote_objs)} files)"
    except Exception as e:
        return False, f"Cloudflare R2 connection failed: {e}"


def configure_r2_cors(config: Optional[Dict[str, str]] = None, log_callback: Callable[[str], None] = print) -> bool:
    """
    Configures standard CORS rules on the R2 bucket.
    This enables web browsers to fetch .cbz files directly from r2.dev without CORS blocking.
    """
    cfg = config or load_r2_config()
    bucket = cfg.get("bucket_name")
    try:
        s3 = get_r2_client(cfg)
        cors_configuration = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "HEAD"],
                    "AllowedOrigins": ["*"],
                    "ExposeHeaders": ["ETag", "Content-Length", "Content-Range", "Accept-Ranges"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }
        s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_configuration)
        log_callback(f"Successfully configured public CORS headers on R2 bucket '{bucket}'!")
        return True
    except Exception as e:
        log_callback(f"Notice: Failed to set bucket CORS automatically: {e}")
        return False


class ProgressPercentage:
    """Progress tracker callback for boto3 S3 transfers."""
    def __init__(self, filename: str, file_size: int, progress_callback: Optional[Callable[[float, str], None]] = None):
        self._filename = filename
        self._size = float(file_size)
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._progress_callback = progress_callback

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            if self._size > 0:
                pct = self._seen_so_far / self._size
                msg = f"{self._filename}: {int(self._seen_so_far / (1024*1024))}MB / {int(self._size / (1024*1024))}MB ({pct*100:.1f}%)"
            else:
                pct = 1.0
                msg = f"{self._filename}: done"
            if self._progress_callback:
                self._progress_callback(pct, msg)


def upload_file_to_r2(
    file_path: str | Path,
    remote_key: Optional[str] = None,
    config: Optional[Dict[str, str]] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Callable[[str], None] = print,
) -> str:
    """
    Uploads a single local file to Cloudflare R2 with multipart streaming and appropriate Content-Type.
    Returns the public download/stream URL for the uploaded object.
    """
    cfg = config or load_r2_config()
    bucket = cfg.get("bucket_name")
    public_base = cfg.get("public_url", "").rstrip("/")

    fp = Path(file_path).resolve()
    if not fp.exists() or not fp.is_file():
        raise FileNotFoundError(f"Local file not found: {fp}")

    key = remote_key or fp.name
    s3 = get_r2_client(cfg)
    file_size = fp.stat().st_size

    # Deduce MIME Content-Type
    ext = fp.suffix.lower()
    if ext == ".cbz":
        content_type = "application/vnd.comicbook+zip"
    elif ext == ".webp":
        content_type = "image/webp"
    elif ext in (".jpg", ".jpeg"):
        content_type = "image/jpeg"
    elif ext == ".json":
        content_type = "application/json"
    else:
        content_type, _ = mimetypes.guess_type(str(fp))
        content_type = content_type or "application/octet-stream"

    extra_args = {
        "ContentType": content_type,
        "CacheControl": "public, max-age=31536000, immutable",
    }

    log_callback(f"Uploading '{fp.name}' ({file_size // (1024*1024)} MB) to Cloudflare R2 [{bucket}/{key}]...")

    callback = ProgressPercentage(fp.name, file_size, progress_callback)
    s3.upload_file(
        Filename=str(fp),
        Bucket=bucket,
        Key=key,
        ExtraArgs=extra_args,
        Callback=callback,
    )

    log_callback(f"Successfully uploaded: {fp.name}")

    if public_base:
        encoded_key = quote(key, safe="/")
        return f"{public_base}/{encoded_key}"
    return key


def list_remote_r2_objects(config: Optional[Dict[str, str]] = None) -> Dict[str, int]:
    """Returns a dictionary of remote object keys and their sizes in bytes."""
    cfg = config or load_r2_config()
    bucket = cfg.get("bucket_name")
    s3 = get_r2_client(cfg)

    remote_objs: Dict[str, int] = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            remote_objs[obj["Key"]] = obj["Size"]

    return remote_objs


def get_r2_storage_usage(config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Queries Cloudflare R2 bucket for current total storage usage against the 10 GB free tier.
    """
    cfg = config or load_r2_config()
    remote_objs = list_remote_r2_objects(cfg)
    total_bytes = sum(remote_objs.values())
    total_gb = total_bytes / (1024 ** 3)
    free_limit_gb = R2_FREE_TIER_LIMIT_BYTES / (1024 ** 3)
    remaining_gb = max(0.0, free_limit_gb - total_gb)
    percentage = min(100.0, (total_bytes / R2_FREE_TIER_LIMIT_BYTES) * 100)
    return {
        "total_bytes": total_bytes,
        "total_gb": total_gb,
        "free_limit_gb": free_limit_gb,
        "remaining_gb": remaining_gb,
        "percentage": percentage,
        "object_count": len(remote_objs),
    }


def sync_comics_folder_to_r2(
    source_dir: Optional[str | Path] = None,
    comics_dir: Optional[str | Path] = None,
    config: Optional[Dict[str, str]] = None,
    sync_catalog_json: bool = True,
    only_volumes: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Callable[[str], None] = print,
    cancel_flag: Optional[Callable[[], bool]] = None,
    max_storage_bytes: int = R2_FREE_TIER_LIMIT_BYTES,
    allow_exceed_free_limit: bool = False,
) -> Dict[str, Any]:
    """
    Syncs local manga CBZ files and covers to Cloudflare R2.
    Skips any files already present on R2 with identical size.
    Checks if new uploads would exceed the 10 GB free tier limit to prevent unexpected charges.
    Updates frontend/public/comics/index.json with the public R2 streaming URLs.
    """
    actual_dir = source_dir if source_dir is not None else (comics_dir if comics_dir is not None else DEFAULT_COMICS_DIR)
    src_path = Path(actual_dir).resolve()
    cfg = config or load_r2_config()
    bucket = cfg.get("bucket_name")
    public_base = cfg.get("public_url", "").rstrip("/")

    if not src_path.exists():
        raise FileNotFoundError(f"Source folder does not exist: {src_path}")

    log_callback(f"=== Starting Cloudflare R2 Sync ===")
    log_callback(f"Connecting to bucket: {bucket} (Public URL: {public_base or '(Not configured)'})...")

    # 1. Test connection & Ensure CORS is configured
    try:
        configure_r2_cors(cfg, log_callback=lambda msg: log_callback(f"   {msg}"))
    except Exception:
        pass

    # 2. Fetch remote inventory to avoid redundant uploads
    log_callback("Querying existing files in R2 bucket...")
    remote_inventory = list_remote_r2_objects(cfg)
    log_callback(f"Found {len(remote_inventory)} existing objects in R2 bucket.")

    # 3. Collect local candidate files
    local_files: List[Tuple[Path, str]] = []

    # Volume CBZs
    for f in src_path.glob("Volume *.cbz"):
        local_files.append((f, f.name))

    if not only_volumes:
        # Chapter CBZs
        for f in src_path.glob("Chapter *.cbz"):
            local_files.append((f, f.name))

        # Covers subfolder
        covers_dir = src_path / "covers"
        if covers_dir.is_dir():
            for f in covers_dir.glob("cover-*.*"):
                if f.suffix.lower() in (".jpg", ".jpeg", ".webp", ".png"):
                    local_files.append((f, f"covers/{f.name}"))
            # Viz metadata JSON
            viz_meta_file = covers_dir / "viz_volumes_metadata.json"
            if viz_meta_file.is_file():
                local_files.append((viz_meta_file, "covers/viz_volumes_metadata.json"))

    to_upload: List[Tuple[Path, str]] = []
    skipped_count = 0

    for local_fp, key in local_files:
        local_size = local_fp.stat().st_size
        if key in remote_inventory and remote_inventory[key] == local_size:
            skipped_count += 1
        else:
            to_upload.append((local_fp, key))

    log_callback(f"Sync inventory: {len(to_upload)} file(s) to upload, {skipped_count} already up-to-date in R2.")

    # Storage Check: Guard against exceeding the 10 GB free tier limit
    storage_check = check_r2_storage_limit(remote_inventory, to_upload, limit_bytes=max_storage_bytes)
    log_callback(f"\n[Storage Check] Cloudflare R2 10 GB Free Tier:")
    log_callback(f"   • Current in R2: {storage_check['current_gb']:.2f} GB / 10.00 GB ({storage_check['current_pct']:.1f}%)")
    log_callback(f"   • To Upload:     {storage_check['incoming_gb']:.2f} GB ({len(to_upload)} files)")
    log_callback(f"   • Projected:     {storage_check['projected_gb']:.2f} GB / 10.00 GB ({storage_check['usage_pct']:.1f}%)\n")

    if storage_check["will_exceed"]:
        err_msg = (
            f"Sync halted! Uploading {len(to_upload)} files ({storage_check['incoming_gb']:.2f} GB) "
            f"would push R2 storage to {storage_check['projected_gb']:.2f} GB, exceeding the 10 GB free limit by {storage_check['excess_gb']:.2f} GB!\n"
            f"Upload stopped to protect against unexpected Cloudflare billing charges."
        )
        log_callback(f"\n⚠️  {err_msg}\n")
        if not allow_exceed_free_limit:
            raise StorageLimitExceededError(err_msg, storage_check)
        else:
            log_callback("⚠️  Proceeding anyway as 'allow_exceed_free_limit' is set to True.\n")

    uploaded_count = 0
    failed: List[Tuple[str, str]] = []

    for idx, (local_fp, key) in enumerate(to_upload, 1):
        if cancel_flag and cancel_flag():
            log_callback("\n[Cancelled] R2 sync was cancelled by user.")
            break

        status = f"[{idx}/{len(to_upload)}] Uploading {local_fp.name}..."
        log_callback(status)
        if progress_callback:
            progress_callback(idx / len(to_upload), status)

        try:
            upload_file_to_r2(
                file_path=local_fp,
                remote_key=key,
                config=cfg,
                log_callback=lambda msg: log_callback(f"   {msg}"),
            )
            uploaded_count += 1
            remote_inventory[key] = local_fp.stat().st_size
        except Exception as e:
            log_callback(f"   [Error] Failed to upload {local_fp.name}: {e}")
            failed.append((local_fp.name, str(e)))

    # 4. Update index.json with remote URLs
    if sync_catalog_json and public_base:
        index_file = src_path / "index.json"
        if index_file.exists():
            log_callback("\nUpdating index.json with Cloudflare R2 streaming URLs...")
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    catalog = json.load(f)

                updated_vols = 0
                for vol in catalog.get("volumes", []):
                    cbz_name = vol.get("cbzFile")
                    if cbz_name and cbz_name in remote_inventory:
                        remote_url = f"{public_base}/{quote(cbz_name, safe='/')}"
                        vol["cbzUrl"] = remote_url
                        updated_vols += 1

                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(catalog, f, indent=2, ensure_ascii=False)

                log_callback(f"Updated {updated_vols} volume(s) in index.json to stream from Cloudflare R2!")
            except Exception as e:
                log_callback(f"Notice: Failed to update index.json with R2 URLs: {e}")

    log_callback(f"\n=== Sync Complete ===")
    log_callback(f"Uploaded: {uploaded_count} | Skipped: {skipped_count} | Failed: {len(failed)}")

    return {
        "uploaded": uploaded_count,
        "skipped": skipped_count,
        "failed": failed,
    }


def interactive_setup():
    """Interactive command-line wizard for setting up Cloudflare R2."""
    print("\n" + "=" * 60)
    print(" Cloudflare R2 Free Storage Setup (Zero Egress Bandwidth)")
    print("=" * 60)
    print("Follow these 3 quick steps in your Cloudflare dashboard:")
    print("  1. Go to https://dash.cloudflare.com/ -> Click 'R2' in the sidebar.")
    print("  2. Create a bucket (e.g. 'one-piece-comics').")
    print("     - In bucket Settings -> 'R2.dev subdomain' -> click 'Allow Access'.")
    print("     - Copy the public URL (e.g. 'https://pub-xxxxxx.r2.dev').")
    print("  3. On R2 overview page, click 'Manage R2 API Tokens' -> 'Create API token'")
    print("     - Permissions: 'Object Read & Write'")
    print("     - Copy your Account ID, Access Key ID, and Secret Access Key.\n")

    current = load_r2_config()

    account_id = input(f"Enter Cloudflare Account ID [{current.get('account_id', '')}]: ").strip() or current.get("account_id", "")
    access_key = input(f"Enter Access Key ID [{current.get('access_key_id', '')}]: ").strip() or current.get("access_key_id", "")
    secret_key = input(f"Enter Secret Access Key [{current.get('secret_access_key', '')}]: ").strip() or current.get("secret_access_key", "")
    bucket = input(f"Enter Bucket Name [{current.get('bucket_name', '')}]: ").strip() or current.get("bucket_name", "")
    public_url = input(f"Enter Public R2.dev URL (e.g. https://pub-xxxx.r2.dev) [{current.get('public_url', '')}]: ").strip() or current.get("public_url", "")

    if not account_id or not access_key or not secret_key or not bucket:
        print("\n[Error] All credential fields are required.")
        return

    save_r2_config(account_id, access_key, secret_key, bucket, public_url)

    print("\nTesting connection to your Cloudflare R2 bucket...")
    ok, msg = test_r2_connection()
    if ok:
        print(f"SUCCESS: {msg}")
        configure_r2_cors()
    else:
        print(f"WARNING: {msg}")


def main():
    parser = argparse.ArgumentParser(description="Cloudflare R2 Free Manga Storage Uploader")
    parser.add_argument("--setup", action="store_true", help="Run interactive R2 credentials setup wizard")
    parser.add_argument("--test", action="store_true", help="Test connection to Cloudflare R2 bucket")
    parser.add_argument("--cors", action="store_true", help="Configure CORS headers on the R2 bucket")
    parser.add_argument("--sync-all", action="store_true", help="Sync all volumes, chapters, and covers to R2")
    parser.add_argument("--sync-volumes", action="store_true", help="Sync only volume CBZ files to R2")
    parser.add_argument("--upload-file", type=str, help="Upload a single file to R2")
    parser.add_argument("--dir", type=str, default=str(DEFAULT_COMICS_DIR), help="Source comics directory")
    args = parser.parse_args()

    if args.setup:
        interactive_setup()
        return

    if args.test:
        ok, msg = test_r2_connection()
        print(msg)
        return

    if args.cors:
        configure_r2_cors()
        return

    if args.upload_file:
        upload_file_to_r2(args.upload_file)
        return

    if args.sync_all or args.sync_volumes:
        sync_comics_folder_to_r2(
            source_dir=args.dir,
            only_volumes=args.sync_volumes,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
