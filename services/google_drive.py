from pathlib import Path
import shutil
from config import SETTINGS


def save_image_to_drive(source_path: Path, image_path: str) -> str:
    destination = SETTINGS.local_drive_root / image_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination)
    return image_path


def write_uploaded_bytes(content: bytes, image_path: str) -> str:
    destination = SETTINGS.local_drive_root / image_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return image_path


def resolve_local_image_path(image_path: str) -> Path:
    return SETTINGS.local_drive_root / image_path
