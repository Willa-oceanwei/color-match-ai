import numpy as np
from services.embedding_service import embed_image
from services.google_sheet import get_all_colorboards  # 你已有 or 可之後補


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_top_k(material: str, image_path, top_k: int = 5):

    query_vec = embed_image(image_path)

    all_items = get_all_colorboards(material)

    results = []

    for item in all_items:

        # ⚠️ 先 debug：不要 skip
        if "embedding" not in item:
            continue

        score = cosine_similarity(query_vec, item["embedding"])

        results.append({
            "id": item["ID"],
            "score": round(score, 4),
            "image_path": item["ImagePath"],
            "formula_id": item.get("FormulaID", ""),
            "recipe_status": item.get("RecipeStatus", "UNKNOWN"),
            "material": item.get("Material", ""),
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_k]
