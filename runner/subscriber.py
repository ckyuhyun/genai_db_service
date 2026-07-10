import redis
import os
import json
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import redis_host, redis_port, redis_password, redis_default_key_name
from runner.redis_module import lifespan

from postgres_rag_sync import DBSync
from embedding_service import EmbeddingService

class Message(BaseModel):
    message : str
    similiarity_threshold : float = 0.7


postgres_rag_sync = DBSync()
embedding_service = EmbeddingService()

app = FastAPI(title="RAG Ingestion Subscriber Service", 
              version="1.0.0", 
              lifespan=lifespan)




def redis_conn():
    try:
        redis_client = redis.Redis(host=redis_host,
                            port=redis_port,
                            password=redis_password,
                            db=0,
                            decode_responses=True)
    except Exception as e:
        print(f"[Error] Failed to connect to Redis: {e}")
        raise e
    
    return redis_client


@app.get("/search")
async def search_similar_messages(message : Message):
    """
        Endpoint to trigger the subscriber for processing messages.
    """
    
    
    emb = str(embedding_service.embed_text(message.message))
    result = postgres_rag_sync.fetch(
        query=
            """
            with score as (
                select
                    content,
                    (1 - (embedding <=> %s:: vector)) as similarity_score
                    from document_chunks_embedding
                )
                select content, similarity_score
                from score
                where similarity_score > %s
                ORDER BY similarity_score DESC
            """,
        params=(emb, message.similiarity_threshold))   

    return StreamingResponse(
        content     = iter([json.dumps(result)]),
        media_type  = "application/json", 
        headers     = {"Content-Disposition": "attachment; filename=result.json"})
    


if __name__ == "__main__":    
    uvicorn.run(app, 
                host="0.0.0.0", 
                port=5000)   