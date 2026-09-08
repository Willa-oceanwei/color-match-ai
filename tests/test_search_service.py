from services import search_service
from services.search_service import cosine_similarity


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1, 0], [1, 0]) == 1.0


def test_cosine_similarity_zero_vector():
    assert cosine_similarity([0, 0], [1, 0]) == 0.0


def test_search_without_material_loads_vectors_for_all_materials(monkeypatch):
    boards = [
        {"ID": "ABS_1", "Material": "ABS", "ImagePath": "a", "FormulaID": "1"},
        {"ID": "PP_2", "Material": "PP", "ImagePath": "b", "FormulaID": "2"},
    ]
    loaded_materials = []
    monkeypatch.setattr(search_service, "embed_image", lambda path: [1, 0])
    monkeypatch.setattr(search_service, "get_all_color_match_boards", lambda: boards)

    def load_vectors(material):
        loaded_materials.append(material)
        board_id = "ABS_1" if material == "ABS" else "PP_2"
        return {"items": [{"id": board_id, "embedding": [1, 0]}]}

    monkeypatch.setattr(search_service, "load_vector_store", load_vectors)

    results = search_service.search_top_k("ALL", "query.jpg")

    assert loaded_materials == ["ABS", "PP"]
    assert {result["id"] for result in results} == {"ABS_1", "PP_2"}
