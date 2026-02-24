# src/ui/prediction.py
import streamlit as st
import pandas as pd
import os
from src.ai_engine.predictor import PricePredictor
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.path import MODEL_PATH


# Khởi tạo đối tượng Predictor (Dùng cache để không load lại model mỗi lần click)
@st.cache_resource
def get_predictor():
    return PricePredictor(MODEL_PATH)

def render_prediction(df):
    predictor = get_predictor()

    if not predictor.is_ready():
        st.warning("Chưa có Model AI. Hãy chạy file `src/ai_engine/train_model.py` để huấn luyện!")
        return

    st.write("Nhập thông số căn nhà bạn muốn mua/bán, AI sẽ gợi ý mức giá hợp lý.")
    st.caption(f"💡 Hệ thống đang sử dụng mô hình Random Forest (Sai số chuẩn MAE: **{predictor.mae:.2f} Tỷ VNĐ**)")
    
    # Lấy danh sách thực tế từ Database
    valid_wards = sorted(df['ward'].dropna().unique().tolist())
    valid_types = sorted(df['property_type'].dropna().unique().tolist())

    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        in_type = st.selectbox("Loại hình BĐS:", valid_types, key="pred_type")
        in_ward = st.selectbox("Khu vực:", valid_wards, key="pred_ward")
        in_area = st.number_input("Diện tích (m2):", min_value=10.0, value=50.0, step=1.0, key="pred_area")
        
    with col_input2:
        if in_type == 'Đất nền':
            in_bedrooms = st.number_input("Số phòng ngủ:", value=0, disabled=True, key="pred_bed")
            in_bathrooms = st.number_input("Số phòng tắm/WC:", value=0, disabled=True, key="pred_bath")
        else:
            in_bedrooms = st.number_input("Số phòng ngủ:", min_value=1, value=2, step=1, key="pred_bed")
            in_bathrooms = st.number_input("Số phòng tắm/WC:", min_value=1, value=2, step=1, key="pred_bath")

    if st.button("🔮 Định giá ngay", type="primary"):
            try:
                # Hứng 3 giá trị trả về từ Predictor
                pred_price, pred_unit_price, mae = predictor.predict_single(
                    area=in_area, 
                    bedrooms=in_bedrooms, 
                    bathrooms=in_bathrooms, 
                    ward=in_ward, 
                    property_type=in_type
                )
                
                # Quy đổi Đơn giá từ (Tỷ/m2) sang (Triệu/m2) để hiển thị cho đẹp
                pred_m2_display = pred_unit_price * 1000
                
                st.success(f"💰 Mức giá khuyến nghị: **{pred_price:.2f} Tỷ**")
                st.caption(f"Tương đương: **{pred_m2_display:.1f} Triệu/m2**")
                
                avg_area_price = df[(df['ward'] == in_ward) & (df['property_type'] == in_type)]['price_billion'].mean()
                if pd.notna(avg_area_price):
                    diff = pred_price - avg_area_price
                    if diff > 0:
                        st.info(f"📈 Cao hơn mức trung bình của {in_type} tại {in_ward} khoảng {diff:.2f} Tỷ")
                    elif diff < 0:
                        st.info(f"📉 Thấp hơn mức trung bình của {in_type} tại {in_ward} khoảng {abs(diff):.2f} Tỷ")
                        
            except Exception as e:
                st.error(f"Lỗi khi dự đoán: {e}")