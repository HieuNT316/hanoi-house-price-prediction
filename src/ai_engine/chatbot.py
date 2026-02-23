# src/ai_engine/chatbot.py
import streamlit as st
from google import genai
from streamlit_float import *

def render_chatbot(df, api_key):
    """
    Hàm hiển thị Chatbot AI Floating có bộ nhớ ngữ cảnh.
    """
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Lỗi khởi tạo AI Client: {e}")
        return

    # --- 1. CSS & STYLE ---
    button_css = "position: fixed; bottom: 30px; right: 30px; z-index: 10000;"
    chat_box_css = """
        position: fixed; 
        bottom: 100px; 
        right: 30px; 
        width: 400px; 
        background-color: white; 
        border-radius: 10px; 
        border: 1px solid #ddd; 
        box-shadow: 0px 5px 20px rgba(0,0,0,0.2); 
        z-index: 9999;
        overflow: hidden;
    """

    st.markdown(
        f"""
        <style>
        div.stButton > button[kind="secondary"] {{
            {button_css}
            border-radius: 50%;
            width: 60px;
            height: 60px;
            background-color: #0084FF;
            color: white;
            font-size: 24px;
            border: none;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }}
        div.stButton > button[kind="secondary"]:hover {{
            transform: scale(1.1);
            background-color: #0073e6;
        }}
        </style>
        """, 
        unsafe_allow_html=True
    )

    # --- 2. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
    
    if "messages" not in st.session_state:
        # Câu chào mặc định để hướng dẫn người dùng
        st.session_state.messages = [
            {"role": "assistant", "content": "Chào bạn! Tôi là trợ lý AI Bất động sản Hà Đông. Bạn muốn tìm hiểu giá nhà ở khu vực nào?"}
        ]

    # --- 3. NÚT BẤM MỞ CHAT ---
    with st.container():
        if st.button("💬", key="toggle_chat"):
            st.session_state.show_chat = not st.session_state.show_chat

    # --- 4. HỘP CHAT CHÍNH ---
    if st.session_state.show_chat:
        chat_container = st.container()
        
        with chat_container:
            st.markdown("""
            <div style="background-color: #0084FF; color: white; padding: 10px; border-radius: 10px 10px 0 0; font-weight: bold; text-align: center;">
                🤖 Trợ lý AI Bất Động Sản
            </div>
            """, unsafe_allow_html=True)
            
            messages_container = st.container(height=350)
            with messages_container:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

            if prompt := st.chat_input("Nhập câu hỏi... (VD: Giá nhà Văn Quán)"):
                # Hiển thị ngay câu hỏi của user
                st.session_state.messages.append({"role": "user", "content": prompt})
                with messages_container:
                    with st.chat_message("user"):
                        st.markdown(prompt)

                # --- LỚP RAG TIỀN XỬ LÝ ---
                stats_text = f"Tổng quan: {len(df)} tin, giá trung bình {df['price_billion'].mean():.2f} tỷ."
                
                # Tìm kiếm thông tin khu vực (Bỏ qua phân biệt hoa thường)
                prompt_lower = prompt.lower()
                ds_phuong = df['ward'].dropna().unique()
                for phuong in ds_phuong:
                    if phuong.lower() in prompt_lower:
                        df_loc = df[df['ward'] == phuong]
                        if not df_loc.empty:
                            stats_text += f"\n- Khu vực {phuong}: {len(df_loc)} tin, giá trung bình {df_loc['price_billion'].mean():.2f} tỷ. Diện tích trung bình {df_loc['area'].mean():.1f} m2."
                        break # Tìm thấy 1 phường là dừng để tối ưu tốc độ

                # --- XÂY DỰNG NGỮ CẢNH (MEMORY) ---
                # Chỉ lấy 5 tin nhắn gần nhất để tránh vượt quá giới hạn token và tiết kiệm chi phí
                recent_history = ""
                for msg in st.session_state.messages[-6:-1]: 
                    role_name = "Khách hàng" if msg["role"] == "user" else "AI"
                    recent_history += f"{role_name}: {msg['content']}\n"

                # --- GỌI GEMINI VỚI PROMPT CHUẨN KỸ SƯ AI ---
                system_instruction = f"""
                Bạn là AI tư vấn Bất động sản chuyên nghiệp tại Hà Đông. Dữ liệu thực tế hệ thống cung cấp:
                {stats_text}
                
                Lịch sử trò chuyện gần đây:
                {recent_history}
                
                Khách hàng hỏi: "{prompt}"
                
                Quy tắc:
                1. Dựa CHÍNH XÁC vào dữ liệu thực tế được cung cấp. Nếu không có số liệu, hãy nói rõ là hệ thống chưa có dữ liệu.
                2. Trả lời ngắn gọn, súc tích (dưới 4 câu), thân thiện.
                3. Gợi mở câu hỏi tiếp theo cho khách hàng (VD: Bạn có muốn biết giá chung cư ở đây không?).
                """
                
                try:
                    # Sử dụng model flash để phản hồi nhanh nhất trên giao diện web
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=system_instruction
                    )
                    ai_reply = response.text
                    
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                    st.rerun() 
                    
                except Exception as e:
                    st.error(f"Lỗi kết nối AI: {e}")

        chat_container.float(chat_box_css)