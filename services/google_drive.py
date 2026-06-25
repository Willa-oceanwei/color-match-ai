from pathlib import Path
import io
import pickle
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from config import SETTINGS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def _get_folder_id(key: str) -> str:
    try:
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    import os
    return os.getenv(key, "")


def _get_drive_service():
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _find_file_id(service, file_name: str, folder_id: str) -> str | None:
    result = service.files().list(
        q=f"name='{file_name}' and '{folder_id}' in parents and trashed=false",
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = result.get("files", [])
    return files[0]["id"] if files else None


# =========================
# 圖片
# =========================
def write_uploaded_bytes(content: bytes, image_path: str) -> str:
    # 本地暫存
    destination = SETTINGS.local_drive_root / image_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    # 上傳到 Google Drive
    folder_id = _get_folder_id("GOOGLE_DRIVE_ROOT_FOLDER_ID")
    if not folder_id:
        raise ValueError("GOOGLE_DRIVE_ROOT_FOLDER_ID 未設定")

    service = _get_drive_service()
    file_name = Path(image_path).name
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="image/jpeg")

    existing_id = _find_file_id(service, file_name, folder_id)
    if existing_id:
        service.files().update(
            fileId=existing_id,
            media_body=media,
            supportsAllDrives=True
        ).execute()
    else:
        service.files().create(
            body={"name": file_name, "parents": [folder_id]},
            media_body=media,
            supportsAllDrives=True
        ).execute()

    return image_path


def resolve_local_image_path(image_path: str) -> Path:
    return SETTINGS.local_drive_root / image_path


def save_image_to_drive(source_path: Path, image_path: str) -> str:
    with open(source_path, "rb") as f:
        return write_uploaded_bytes(f.read(), image_path)


# =========================
# 向量
# =========================
def save_vector_to_drive(material: str, store: dict):
    folder_id = _get_folder_id("GOOGLE_DRIVE_VECTORS_FOLDER_ID")
    if not folder_id:
        raise ValueError("GOOGLE_DRIVE_VECTORS_FOLDER_ID 未設定")

    service = _get_drive_service()
    file_name = f"{material.upper()}_vectors.pkl"

    data = pickle.dumps(store)
    media = MediaIoBaseUpload(
        io.BytesIO(data),
        mimetype="application/octet-stream"
    )

    existing_id = _find_file_id(service, file_name, folder_id)
    if existing_id:
        service.files().update(
            fileId=existing_id,
            media_body=media,
            supportsAllDrives=True
        ).execute()
    else:
        service.files().create(
            body={"name": file_name, "parents": [folder_id]},
            media_body=media,
            supportsAllDrives=True
        ).execute()


def load_vector_from_drive(material: str) -> dict:
    folder_id = _get_folder_id("GOOGLE_DRIVE_VECTORS_FOLDER_ID")
    if not folder_id:
        return {
            "material": material.upper(),
            "model_name": SETTINGS.embedding_backend,
            "updated_at": "",
            "items": []
        }

    service = _get_drive_service()
    file_name = f"{material.upper()}_vectors.pkl"

    file_id = _find_file_id(service, file_name, folder_id)
    if not file_id:
        return {
            "material": material.upper(),
            "model_name": SETTINGS.embedding_backend,
            "updated_at": "",
            "items": []
        }

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(
        buffer,
        service.files().get_media(fileId=file_id)
    )
    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    return pickle.loads(buffer.read())
