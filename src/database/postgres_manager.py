# src/database/postgres_manager.py
from sqlalchemy import create_engine, text
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
    
    def upsert_dataframe(self, df: pd.DataFrame, table_name: str, unique_key: str):
        """
        Thực hiện logic Upsert (Update if exists, Insert if not) cho DataFrame.
        """
        if df.empty:
            print("⚠️ DataFrame trống, bỏ qua Upsert.")
            return

        temp_table = f"temp_{table_name}"
        
        # Mở một transaction an toàn
        with self.engine.begin() as conn:
            # 1. Đẩy dữ liệu mới vào Bảng Tạm (Tự động tạo bảng tạm thời)
            df.to_sql(temp_table, con=conn, index=False, if_exists='replace')
            
            # 2. Xây dựng câu lệnh SQL chuẩn PostgreSQL
            columns = [f'"{col}"' for col in df.columns]
            columns_str = ", ".join(columns)
            
            # Xây dựng vế UPDATE: col1 = EXCLUDED.col1, ... (Bỏ qua unique_key)
            update_cols = [f'"{col}" = EXCLUDED."{col}"' for col in df.columns if col != unique_key]
            update_str = ", ".join(update_cols)
            
            # Câu lệnh lõi: INSERT ... ON CONFLICT DO UPDATE
            upsert_query = f"""
                INSERT INTO "{table_name}" ({columns_str})
                SELECT {columns_str} FROM "{temp_table}"
                ON CONFLICT ("{unique_key}") 
                DO UPDATE SET {update_str};
            """
            
            # 3. Thực thi Upsert
            conn.execute(text(upsert_query))
            
            # 4. Xóa bảng tạm để giải phóng tài nguyên
            conn.execute(text(f'DROP TABLE "{temp_table}";'))