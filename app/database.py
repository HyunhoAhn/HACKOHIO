import psycopg2
from psycopg2.extras import RealDictCursor, register_uuid
from contextlib import contextmanager
from app.config import get_settings

settings = get_settings()


class Database:
    def __init__(self):
        self.connection_string = settings.DATABASE_URL
        
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        conn = psycopg2.connect(self.connection_string)
        # UUID 타입 등록
        register_uuid()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()


# 싱글톤 인스턴스
db = Database()
