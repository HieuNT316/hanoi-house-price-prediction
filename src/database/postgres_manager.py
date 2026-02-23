# src/database/postgres_manager.py
from sqlalchemy import create_engine
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.database import POSTGRES_URI

class PostgresManager:
    def __init__(self):
        """Khởi tạo kết nối tới PostgreSQL sử dụng SQLAlchemy Engine"""
        try:
            self.engine = create_engine(POSTGRES_URI)
            print("✅ Đã kết nối thành công tới PostgreSQL.")
        except Exception as e:
            print(f"❌ Lỗi kết nối Database: {e}")
            self.engine = None

    def save_dataframe(self, df: pd.DataFrame, table_name: str, if_exists: str = 'replace'):
        """
        Lưu Pandas DataFrame trực tiếp vào PostgreSQL.
        """
        if self.engine is None:
            print("Không có kết nối DB. Bỏ qua bước lưu.")
            return

        try:
            df.to_sql(table_name, con=self.engine, if_exists=if_exists, index=False)
            print(f"💾 Đã lưu {len(df)} bản ghi vào bảng '{table_name}' trong PostgreSQL.")
        except Exception as e:
            print(f"❌ Lỗi khi lưu dữ liệu vào PostgreSQL: {e}")

    def load_dataframe(self, query: str) -> pd.DataFrame:
        """Đọc dữ liệu từ PostgreSQL trả về Pandas DataFrame"""
        if self.engine is None:
            raise ConnectionError("Không có kết nối DB.")
        return pd.read_sql(query, con=self.engine)