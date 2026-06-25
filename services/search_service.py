import numpy as np
from services.embedding_service import embed_image, load_vector_store
from services.google_sheet import get_all_colorboards


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_top_k(material: str, image_path, top_k: int = 5):
    # 1️⃣ query embedding
    query_vec = embed_image(image_path)
    # 2️⃣ metadata
    all_items = get_all_colorboards(material)
    # 3️⃣ vector store
    vector_store = load_vector_store(material)
    vector_items = {i["id"]: i["embedding"] for i in vector_store["items"]}

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
            "formula_id": item.get("FormulaID", ""),
            "recipe_status": item.get("RecipeStatus", "UNKNOWN"),
            "material": item.get("Material", ""),
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
