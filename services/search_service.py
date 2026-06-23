from pathlib import Path
from services.google_sheet import lookup_formula_by_id, read_colorboard
from services.models import SearchResult


def cosine_similarity(query, target) -> float:
    query_values = list(query)
    target_values = list(target)
    query_norm = sum(value * value for value in query_values) ** 0.5
    target_norm = sum(value * value for value in target_values) ** 0.5
    if query_norm == 0 or target_norm == 0:
        return 0.0
    return float(sum(left * right for left, right in zip(query_values, target_values)) / (query_norm * target_norm))


def search_top_k(material: str, query_image_path: Path, top_k: int = 5) -> list[SearchResult]:
    from services.embedding_service import embed_image, load_vector_store

    query_embedding = embed_image(query_image_path)
    store = load_vector_store(material)
    board_rows = read_colorboard()
    results = []
    for item in store.get("items", []):
        score = cosine_similarity(query_embedding, item["embedding"])
        matched_boards = [row for row in board_rows if row["ID"] == item["id"]]
        board = matched_boards[0] if matched_boards else item
        formula_id = board.get("FormulaID", "")
        formula_rows = lookup_formula_by_id(formula_id) if formula_id and board.get("FormulaMode") == "EXISTING" else []
        results.append(SearchResult(id=item["id"], similarity=score, board=board, formula_rows=formula_rows))
    return sorted(results, key=lambda result: result.similarity, reverse=True)[:top_k]
