import numpy as np
from services.embedding_service import embed_image
from services.vector_db import get_all_embeddings


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_top_k(material: str, image_path, top_k: int = 5):

    query_vec = embed_image(image_path)

    all_items = get_all_embeddings(material)

    results = []

    for item in all_items:

        score = cosine_similarity(query_vec, item["embedding"])

        results.append({
            "id": item["id"],
            "score": round(score, 4),
            "image_path": item["image_path"],
            "formula_id": item.get("formula_id", ""),
            "recipe_status": item.get("recipe_status", "UNKNOWN"),
            "material": item.get("material", ""),
        })

    # 排序
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return results[:top_k]
