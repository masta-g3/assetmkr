from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


def get_embeddings(texts: list, model_name: str = "intfloat/e5-small-v2"):
    """Get embeddings for a list of texts."""
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings


def find_similar(
    query: str,
    passages: list,
    top_k: int = 5,
    threshold: float = 0.9,
    model_name: str = "intfloat/e5-small-v2",
):
    """ Get embeddings for a query and a set of passages and return most similar passages."""
    query_embedding = get_embeddings([query], model_name)[0]
    passage_embeddings = get_embeddings(passages, model_name)
    similarities = cosine_similarity([query_embedding], passage_embeddings)[0]
    similar_passages = [
        (passage, similarity)
        for passage, similarity in zip(passages, similarities)
        if similarity >= threshold
    ]
    similar_passages = sorted(similar_passages, key=lambda x: x[1], reverse=True)
    return similar_passages[:top_k]