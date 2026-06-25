from pathlib import Path
import numpy as np
from PIL import Image
from config import SETTINGS


def _color_stats_embedding(image_path: Path) -> np.ndarray:
    image = Image.open(str(image_path)).convert("RGB").resize((64, 64))
    arr = np.asarray(image, dtype=np.float32) / 255.0
    means = arr.mean(axis=(0, 1))
    stds = arr.std(axis=(0, 1))
    mins = arr.min(axis=(0, 1))
    maxs = arr.max(axis=(0, 1))
    hist_parts = []
    for channel in range(3):
        hist, _ = np.histogram(
            arr[:, :, channel], bins=8, range=(0, 1), density=True
        )
        hist_parts.append(hist.astype(np.float32))
    vector = np.concatenate([means, stds, mins, maxs, *hist_parts]).astype(np.float32)
    norm = np.linalg.norm(vector)
    return vector if norm == 0 else vector / norm


def _openclip_embedding(image_path: Path) -> np.ndarray:
    import torch
    import open_clip
    model, _, preprocess = open_clip.create_model_and_transforms(
        SETTINGS.openclip_model_name,
        pretrained=SETTINGS.openclip_pretrained,
    )
    model.eval()
    image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        features = model.encode_image(image)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.squeeze(0).cpu().numpy().astype(np.float32)


def embed_image(image_path: Path) -> np.ndarray:
    if SETTINGS.embedding_backend == "openclip":
        return _openclip_embedding(image_path)
    return _color_stats_embedding(image_path)


def load_vector_store(material: str) -> dict:
    from services.google_sheet import load_vectors_from_sheet
    items = load_vectors_from_sheet(material)
    return {
        "material": material.upper(),
        "model_name": SETTINGS.embedding_backend,
        "updated_at": "",
        "items": items
    }


def save_vector_store(material: str, store: dict):
    # 向量改存 Google Sheet，這裡不需要做事
    pass


def upsert_embedding(material: str, item: dict, embedding: np.ndarray, updated_at: str) -> None:
    from services.google_sheet import save_vector_to_sheet
    save_vector_to_sheet(
        board_id=item["id"],
        material=material,
        embedding=embedding,
        updated_at=updated_at
    )
