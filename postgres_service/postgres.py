import os
from typing import Any, Dict, List, Optional, Sequence

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv




class PostgresDB:
    """
    Thin wrapper around psycopg2 for basic connection and CRUD operations.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dbname: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        load_dotenv()

        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", 5433))
        self.dbname = dbname or os.getenv("POSTGRES_DB", "agnetic_ai_db")
        self.user = user or os.getenv("POSTGRES_USER", "admin")
        self.password = password or os.getenv("POSTGRES_PASSWORD")

        self.connection = None

    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================

    def connect(self):
        """
        Open a connection to the Postgres database if not already connected.
        """
        if self.connection and not self.connection.closed:
            return self.connection

        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
            )
            self.connection.autocommit = True
            print(f"[Postgres connected] ({self.host}:{self.port}/{self.dbname})")
            return self.connection
        except Exception as e:
            print(f"[Postgres not connected] Postgres connection error: {e}")
            raise
        
    def _get_list_tables_(self) -> List[str]:
        """
        Return a list of table names in the connected database.
        """
        query = """
            SELECT tablename 
            FROM pg_catalog.pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
        """
        rows = self.fetch_all(query)
        return [row["tablename"] for row in rows]

    def close(self):
        """
        Close the connection if it is open.
        """
        if self.connection and not self.connection.closed:
            self.connection.close()
            print("[Postgres connection closed]")
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # =========================================================================
    # QUERY EXECUTION
    # =========================================================================

    def execute(self, 
                query: str, 
                params: Optional[Sequence[Any]] = None) -> None:
        """
        Execute a statement that does not return rows (INSERT/UPDATE/DELETE/DDL).
        """
        conn = self.connect()
        table_list = self._get_list_tables_()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
        except Exception as e:
            #cprint(f"Postgres execute error: {e}", C.RED)
            print(f"Postgres execute error: {e}")
            raise

    def fetch_one(self, 
                  query: str, 
                  params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute a query and return the first row as a dict, or None.
        """
        conn = self.connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            conn.rollback()
            #cprint(f"Postgres fetch_one error: {e}", C.RED)
            print(f"Postgres fetch_one error: {e}") 
            raise

    def fetch_all(self, 
                  query: str, 
                  params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and return all rows as a list of dicts.
        """
        conn = self.connect()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            conn.rollback()
            print(f"Postgres fetch_all error: {e}")
            raise

    def execute_many(self, 
                     query: str, 
                     params_list: Sequence[Sequence[Any]]) -> None:
        """
        Execute the same statement against a batch of parameter sets.
        """
        conn = self.connect()
        try:
            with conn.cursor() as cur:
                cur.executemany(query, params_list)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Postgres execute_many error: {e}")
            raise

    # =========================================================================
    # CRUD HELPERS
    # =========================================================================

    def insert(self, 
               table: str, 
               data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Insert a row into `table` and return the inserted row.
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(["%s"] * len(values))

        query = (
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({placeholders}) RETURNING *"
        )
        return self.fetch_one(query, values)

    def update(self,
               table: str,
               data: Dict[str, Any],
               where: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Update rows in `table` matching `where` with values from `data`.
        """
        set_clause = ", ".join([f"{col} = %s" for col in data.keys()])
        where_clause = " AND ".join([f"{col} = %s" for col in where.keys()])

        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause} RETURNING *"
        params = list(data.values()) + list(where.values())
        return self.fetch_all(query, params)

    def delete(self, 
               table: str, 
               where: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Delete rows from `table` matching `where`.
        """
        where_clause = " AND ".join([f"{col} = %s" for col in where.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause} RETURNING *"
        return self.fetch_all(query, list(where.values()))

    def table_exists(self, 
                     table: str) -> bool:
        """Check whether `table` exists in the connected database."""
        row = self.fetch_one(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s) AS exists",
            [table],
        )
        return bool(row and row["exists"])
