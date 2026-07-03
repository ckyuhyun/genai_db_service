import os
from dotenv import load_dotenv
from rag_service.weaviate_property_data import WeaviateProperty
from postgres_service.postgres import PostgresDB


class DBSync:
    def __init__(self, 
                 onlyPostgresdb: bool = True):
        load_dotenv()

        postgresdb_host = os.getenv("POSTGRES_HOST")
        postgresdb_port = int(os.getenv("POSTGRES_POST"))
        self.postgresDB = PostgresDB(host=postgresdb_host,
                                     dbname=os.getenv("POSTGRES_DB"),
                                port=postgresdb_port)
        self.onlyPostgresdb = onlyPostgresdb
        
    
    def push(self, 
             document_id: str, 
             content: str):
        
        if self.onlyPostgresdb:
            self._push_postgres_(document_id, content)
        else:
            self._push_postgres_with_weaviate_(document_id, content)

    def fetch(self):
        if self.onlyPostgresdb:
            return self._fetch_progress_()
        else:
            return self._sync_postgres_to_weaviate_()
        
        

    def _push_postgres_(self, 
                      document_id: str, 
                      content: str):
        _query = """
                INSERT INTO document_chunks (document_id, content, sync_status)
                VALUES (%s, %s, 'PENDING');
            """
        self.postgresDB.execute(query= _query, params=(document_id, content))

    def _fetch_progress_(self):
        fetched_data = self.postgresDB.fetch_all(query=
            """
                SELECT id, document_id, content, sync_status
                FROM document_chunks
                WHERE sync_status = 'PENDING';
            """
        )
        return fetched_data

    def _push_postgres_with_weaviate_(self, 
                                    document_id: str, 
                                    content: str):
        # self.postgresDB.update_many(query=
        #     """
        #         INSERT INTO document_chunks (document_id, content, sync_status)
        #         VALUES (%s, %s, 'SYNCED');
        #     """,
        #     data=[(document_id, content)]
        # )
        pass


        

    def _sync_postgres_to_weaviate_(self):
        fetched_data = self.postgresDB \
                           .fetch_all(query=
                                  """
                                    SELECT c.id, c.document_id, c.content, d.category 
                                                    FROM document_chunks c
                                                    JOIN enterprise_documents d ON c.document_id = d.id
                                                    WHERE c.sync_status = 'PENDING';
                                  """)
        
        if not fetched_data:
            return 
        
        wvc_property :list[WeaviateProperty] = []

        for d in fetched_data:
            chunk_id, doc_id , content, category  = d
            wvc_property.append(WeaviateProperty(
                postgres_chunk_id=str(chunk_id),
                document_id=str(doc_id),
                content = content,
                category=category
            ))


        
        # update data
        #weaviate.properties_config = wvc_property
        #weaviate.update_query(text_documents=fetched_data)


        

        
        
            


