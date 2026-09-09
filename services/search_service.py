import numpy as np
from services.embedding_service import embed_image, load_vector_store
from services.turso_db import get_all_color_match_boards


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def search_top_k(material: str | None, image_path, top_k: int = 5):
    # 1️⃣ query embedding
    query_vec = embed_image(image_path)
    # 2️⃣ metadata
    selected_material = (material or "").strip().upper()
    unrestricted = selected_material in ("", "ALL")
    all_items = get_all_color_match_boards()
    if not unrestricted:
        all_items = [
            item for item in all_items
            if str(item.get("Material", "")).strip().upper() == selected_material
        ]
    # 3️⃣ vector store
    materials = (
        sorted({str(item.get("Material", "")).strip().upper() for item in all_items})
        if unrestricted
        else [selected_material]
    )
    vector_items = {}
    for item_material in materials:
        if not item_material:
            continue
        vector_store = load_vector_store(item_material)
        vector_items.update({i["id"]: i["embedding"] for i in vector_store["items"]})

    results = []
    for item in all_items:
        item_id = item["ID"]
        if item_id not in vector_items:
            continue
        score = cosine_similarity(query_vec, vector_items[item_id])
        results.append({
            "id": item_id,
            "score": round(score, 4),
            "image_path": item["ImagePath"],
            "image_base64": item.get("ImageBase64", ""),  # 加這行
            "sample_image_1_base64": item.get("SampleImage1Base64", ""),
            "sample_image_2_base64": item.get("SampleImage2Base64", ""),
            "sample_description": item.get("SampleDescription", ""),
            "formula_id": item.get("FormulaID", ""),
            "recipe_status": item.get("RecipeStatus", "UNKNOWN"),
            "material": item.get("Material", ""),
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
