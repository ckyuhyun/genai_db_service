
import os
import numpy as np
from dotenv import load_dotenv
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, Column, Integer, String, func, Uuid
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector


Base = declarative_base()

class  DocumentChunk(Base):
    __tablename__ = "document_chunks_embedding"

    id = Column(Uuid, primary_key=True)
    content = Column(String, nullable=False)
    embedding = Column(Vector(1024), nullable=False)


load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5433)
POSTGRES_DB = os.getenv("POSTGRES_DB", "agnetic_ai_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

db_url = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
engine = create_engine(db_url, pool_size=15, max_overflow=5)
SesssionLocal  = sessionmaker(bind=engine)


def get_similar_doc(taget_embedding : List[float],
                    similiarity_threshold: float) -> List[Dict[str, Any]]:
    
    """
    """
    embedding_arr = np.array(taget_embedding)

    with SesssionLocal() as session:
        similiarity_expr = (1.0 - DocumentChunk.embedding.cosine_distance(embedding_arr)).label("similarity_score")

        # Build the Inner Query (The CTE)
        score_cte = (
            select(DocumentChunk.content, similiarity_expr)
            .cte("score")
        )

        # Build the Outer Query matching your exact logic
        stmt = (
            select(score_cte.c.content, score_cte.c.similarity_score)
            .where(score_cte.c.similarity_score > similiarity_threshold)
            .order_by(score_cte.c.similarity_score.desc())
        )
        try:
            results = session.execute(stmt).fetchall()
        except Exception as e :
            raise e

        return [{"content": row.content, "score": float(row.similarity_score)} for row in results]





