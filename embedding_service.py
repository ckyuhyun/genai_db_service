import requests
from typing import List, Union

from config import tei_embedding_url, tei_embedding_model


class EmbeddingService:
    """
    Generates embeddings via the TEI container's OpenAI-compatible API.

    Must stay on tei_embedding_model (whatever TEI is actually serving) since
    that's the model pgai's vectorizer-worker used to populate
    document_chunks_embedding. A different model/dimension here would make
    query vectors incomparable to the stored document vectors.
    """

    def __init__(self, 
                 base_url: str = tei_embedding_url, 
                 timeout: float = 10.0):
        """
        Initializes the EmbeddingService with the base URL of the embedding service and a timeout for requests.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def embed_text(self, 
                   text: str) -> Union[List[float],None]:
        embedded_texts = self.embed_texts([text])
        
        return embedded_texts if embedded_texts else None

    def embed_texts(self, 
                    texts: List[str]) -> List[float]:
        response = requests.post(
            url=f"{self.base_url}/v1/embeddings",
            json={"input": texts, "model": tei_embedding_model},
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}") 
            print(f"Status Code: {http_err.response.status_code}")

        if response.status_code != 200:
            raise ''
        data = response.json()["data"]
        return [item["embedding"] for item in data][0]
