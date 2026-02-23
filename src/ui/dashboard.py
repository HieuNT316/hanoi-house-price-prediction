# src/ui/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px

def render_dashboard(df):
    """Hàm hiển thị Tab Thống kê với biểu đồ tương tác Plotly"""
    st.subheader("📈 Phân tích Thị trường Bất Động Sản")
    
    # 1. TẠO BỘ LỌC (FILTERS)
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        location_counts = df['ward'].value_counts()
        options_ward = ["Tất cả"] + location_counts.index.tolist()
        chon_phuong = st.selectbox("📍 Chọn Phường/Xã:", options_ward, index=0, key="dash_phuong")

    with col_filter2:
        if 'property_type' in df.columns:
            type_counts = df['property_type'].dropna().value_counts()
            options_type = ["Tất cả"] + type_counts.index.tolist()
        else:
            options_type = ["Tất cả"]
        chon_loai = st.selectbox("🏢 Loại hình:", options_type, index=0, key="dash_loai")

    # Xử lý lọc cấp 1 (Theo Phường và Loại hình)
    df_display = df.copy()
    if chon_phuong != "Tất cả":
        df_display = df_display[df_display['ward'] == chon_phuong]
    if chon_loai != "Tất cả" and 'property_type' in df_display.columns:
        df_display = df_display[df_display['property_type'] == chon_loai]

    with col_filter3:
        # Bẫy lỗi: Xử lý an toàn khi df_display rỗng
        if df_display.empty or df_display['price_billion'].isna().all():
            st.warning("Không có dữ liệu cho khu vực/loại hình này.")
            return # Dừng render phần còn lại nếu không có dữ liệu
            
        max_price_db = float(df_display['price_billion'].max())
        # Tránh trường hợp max_price_db = 0 dẫn đến lỗi thanh trượt
        if max_price_db <= 0: max_price_db = 1.0 
        
        default_max = float(df_display['price_billion'].quantile(0.95))
        price_range = st.slider("💰 Khoảng giá (Tỷ VNĐ):", 0.0, max_price_db, (0.0, default_max), step=0.5, key="dash_price")

    # Xử lý lọc cấp 2 (Theo Khoảng giá)
    df_final = df_display[
        (df_display['price_billion'] >= price_range[0]) & 
        (df_display['price_billion'] <= price_range[1])
    ]

    st.markdown("---")

    # 2. HIỂN THỊ KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng số lượng tin", f"{len(df_final)} tin")
    
    if len(df_final) > 0:
        c2.metric("Giá trung bình", f"{df_final['price_billion'].mean():.2f} Tỷ VNĐ")
        avg_price_m2 = (df_final['price_billion'].sum() * 1000) / df_final['area'].sum()
        c3.metric("Đơn giá trung bình", f"{avg_price_m2:.1f} Triệu/m2")
        
        # 3. BIỂU ĐỒ TƯƠNG TÁC BẰNG PLOTLY
        st.markdown("<br>", unsafe_allow_html=True) # Tạo khoảng trắng nhỏ
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Biểu đồ Histogram: Phân bố giá
            fig_hist = px.histogram(
                df_final, 
                x="price_billion", 
                nbins=30, 
                title=f"Phân bố mức giá tại {chon_phuong}",
                labels={"price_billion": "Giá (Tỷ VNĐ)"},
                color_discrete_sequence=['#2E86C1']
            )
            fig_hist.update_layout(yaxis_title="Số lượng tin")
            st.plotly_chart(fig_hist, width='stretch')
            
        with chart_col2:
            # Biểu đồ Scatter: Tương quan Diện tích - Giá tiền
            fig_scatter = px.scatter(
                df_final, 
                x="area", 
                y="price_billion", 
                color="property_type" if 'property_type' in df_final.columns else None,
                title="Tương quan giữa Diện tích và Mức giá",
                labels={
                    "area": "Diện tích (m2)", 
                    "price_billion": "Giá (Tỷ VNĐ)", 
                    "property_type": "Loại hình"
                },
                opacity=0.7
            )
            st.plotly_chart(fig_scatter, width='stretch')
        
        # 4. BẢNG DỮ LIỆU CHI TIẾT
        st.subheader("📋 Dữ liệu chi tiết")
        
        # Sắp xếp các cột quan trọng lên đầu để dễ nhìn
        display_columns = ['title', 'price_billion', 'area', 'ward', 'property_type', 'bedrooms', 'bathrooms', 'published_date']
        # Chỉ lấy các cột thực sự tồn tại trong df
        display_columns = [c for c in display_columns if c in df_final.columns]
        
        st.dataframe(
            df_final[display_columns].sort_values('price_billion', ascending=False),
            width='stretch',
            hide_index=True
        )
    else:
        st.info("💡 Không tìm thấy tin bất động sản nào phù hợp với bộ lọc hiện tại.")