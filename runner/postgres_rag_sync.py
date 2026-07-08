import os
from typing import List, Union
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
             event_id: str,
             content: str):
        
        if self.onlyPostgresdb:
            self._push_postgres_(document_id, event_id, content)
        else:
            self._push_postgres_with_weaviate_(document_id, content)

    # def fetch(self, 
    #           messages : Union[str, List[str]]):
    #     """
    #     Search for similar messages in the Weaviate database based on the provided messages.
    #     If onlyPostgresdb is True, it fetches the progress from Postgres instead.
    #     """
    #     if self.onlyPostgresdb:
    #         message = messages if isinstance(messages, str) else messages[0]
    #         return self._fetch_progress_(message)
    #     else:
    #         return self._sync_postgres_to_weaviate_()
    def fetch(self, 
              query:str, 
              params:tuple=()):
        """
        Search for similar messages in the Weaviate database based on the provided messages.
        If onlyPostgresdb is True, it fetches the progress from Postgres instead.
        """
        if self.onlyPostgresdb:
            return self._fetch_progress_(query, params)
        else:
            return self._sync_postgres_to_weaviate_()
        
        

    def _push_postgres_(self, 
                      document_id: str, 
                      event_id: str,
                      content: str
                      ):
        _query = """
                INSERT INTO document_chunks (document_id, event_id, content, sync_status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (document_id, event_id) 
                DO UPDATE SET 
                    content = EXCLUDED.content, 
                    sync_status = EXCLUDED.sync_status;
            """
                
        self.postgresDB.execute(query= _query, params=(document_id, event_id, content, 'PENDING'))

    # def _fetch_progress_(self, 
    #                      message: str):
    #     """
    #     Fetch the progress of a specific message from the Postgres database.
    #     """

    #     fetched_data = self.postgresDB.fetch_all(query=
    #         """
    #             SELECT id, document_id, content, sync_status
    #             FROM document_chunks
    #             WHERE sync_status = 'PENDING';
    #         """
    #     )
    #     return fetched_data
    def _fetch_progress_(self, 
                         query:str,
                         params:tuple=()):
        """
        Fetch the progress of a specific message from the Postgres database.
        """

        fetched_data = self.postgresDB.fetch_all(query=query, params=params)
        
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


        

        
        
            


