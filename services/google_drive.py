from pathlib import Path
import io
import base64
from PIL import Image
import streamlit as st
from config import SETTINGS


def _image_to_base64(content: bytes) -> str:
    img = Image.open(io.BytesIO(content)).convert("RGB")
    img.thumbnail((300, 300))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def write_uploaded_bytes(content: bytes, image_path: str) -> str:
    # 本地暫存（Streamlit Cloud 重啟會消失，但上傳當下 embed_image 還用得到）
    destination = SETTINGS.local_drive_root / image_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return image_path


def write_uploaded_bytes_get_base64(content: bytes, image_path: str) -> tuple[str, str]:
    write_uploaded_bytes(content, image_path)
    b64 = _image_to_base64(content)
    return image_path, b64


def resolve_local_image_path(image_path: str) -> Path:
    return SETTINGS.local_drive_root / image_path


def save_image_to_drive(source_path: Path, image_path: str) -> str:
    with open(source_path, "rb") as f:
        return write_uploaded_bytes(f.read(), image_path)
