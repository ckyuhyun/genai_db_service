import redis
import os
import json
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Union, List, Any, AsyncIterator

from config import redis_host, redis_port, redis_password, redis_default_key_name
from runner.redis_module import lifespan

from postgres_rag_sync import DBSync
from embedding_service import EmbeddingService
from postgres_service.postgres_wrapper import get_similar_doc



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


async def _stream_similar_messages(message_list: List[str], similiarity_threshold: float) -> AsyncIterator[str]:
    """Yields one NDJSON line per input message as soon as its similarity search completes,
    instead of blocking until the whole batch is done."""
    for m in message_list:
        try:
            emb = await asyncio.to_thread(embedding_service.embed_text, m)
            searched_content = None
            score = None
            if emb is not None:
                similar_results = await asyncio.to_thread(get_similar_doc, emb, similiarity_threshold)
                if similar_results:
                    searched_content = similar_results[0].get('content')
                    score = similar_results[0].get('score')
            yield json.dumps({"message": m, 
                              "searched_content": searched_content,
                              "score" : score}) + "\n"
        except Exception as e:
            print(f"[Error] Failed to process message '{m}': {e}")
            yield json.dumps({"message": m, "error": str(e)}) + "\n"


@app.get("/search")
async def search_similar_messages(body: dict):
    """
        Endpoint to trigger the subscriber for processing messages.
        Streams one NDJSON-encoded result per message as it's computed.
    """

    message_list = [m.get('message') for m in body.get('message')]
    similiarity_threshold = body.get('similiarity_threshold')

    return StreamingResponse(
        _stream_similar_messages(message_list, similiarity_threshold),
        media_type="application/x-ndjson")
    


if __name__ == "__main__":    
    uvicorn.run(app, 
                host="0.0.0.0", 
                port=5000)   