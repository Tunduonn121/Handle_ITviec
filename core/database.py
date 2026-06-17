import pyodbc
from core.config import SQL_SERVER_NAME, SQL_DATABASE_NAME

def get_db_connection():
    """
    Tạo ống nước kết nối đến SQL Server.
    Sử dụng Windows Authentication (Trusted_Connection=yes).
    """
    try:
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER_NAME};"
            f"DATABASE={SQL_DATABASE_NAME};"
            f"Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(connection_string)
        return conn
    except Exception as e:
        print(f"❌ Lỗi sập nguồn Database: Không thể kết nối tới SQL Server - {e}")
        return None