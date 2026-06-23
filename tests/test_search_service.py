from services.search_service import cosine_similarity


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1, 0], [1, 0]) == 1.0


def test_cosine_similarity_zero_vector():
    assert cosine_similarity([0, 0], [1, 0]) == 0.0
