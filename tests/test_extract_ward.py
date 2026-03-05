import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.preprocessing.cleaner import extract_ward

@pytest.mark.parametrize("input_str, expected", [
    # Nhóm 1: Dữ liệu sạch
    ("Vạn Phúc", "Vạn Phúc"),
    ("Quang Trung, Hà Đông", "Quang Trung"),
    
    # Nhóm 2: Tiền tố P/Phường (Ảnh của bạn)
    ("P Dương Nội", "Dương Nội"),
    ("P. Dương Nội", "Dương Nội"),
    ("Phường Mỗ Lao", "Mỗ Lao"),
    ("P.Mỗ Lao", "Mỗ Lao"),
    
    # Nhóm 3: Thông tin sáp nhập trong ngoặc (Ảnh của bạn)
    ("P La Khê (P Dương Nội mới)", "La Khê"),
    ("P Phú La (P Kiến Hưng mới)", "Phú La"),
    ("P Vạn Phúc (P Hà Đông mới)", "Vạn Phúc"),
    
    # Nhóm 4: Ký tự nhiễu (Ảnh của bạn)
    (". Vạn Phúc", "Vạn Phúc"),
    ("  .  Quang Trung  ", "Quang Trung"),
    ("- Mỗ Lao", "Mỗ Lao"),
    
    # Nhóm 5: Kiểm tra "False Positives" (Không được xóa nhầm)
    ("Phúc La", "Phúc La"),      # P trong Phúc không được mất
    ("Phú Lương", "Phú Lương"),  # P trong Phú không được mất
    ("P. Phúc La", "Phúc La"),   # Chỉ mất P. tiền tố

    # --- NHÓM 6: KÝ TỰ LẠ VÀ ĐỊNH DẠNG SAI (Lỗi bạn vừa gặp) ---
    ("·\nMỗ Lao", "Mỗ Lao"),            # Dấu chấm giữa + xuống dòng
    ("\n  P. Mỗ Lao", "Mỗ Lao"),       # Xuống dòng + khoảng trắng + tiền tố
    ("...P Dương Nội", "Dương Nội"),    # Nhiều dấu chấm liên tiếp
    ("- Hà Cầu", "Hà Cầu"),             # Dấu gạch ngang đầu dòng
    (" * Quang Trung", "Quang Trung"),  # Dấu sao và khoảng trắng
    #dấu chấm giữa + xuống dòng + P. + tên
    ('·\nP. Dương Nội', 'Dương Nội'), 
    # Các biến thể "khó nhằn" khác
    ('·\n   Phường Mỗ Lao', 'Mỗ Lao'),
    ('\n\n P.La Khê', 'La Khê'),
    # Kiểm tra lại độ an toàn cho tên riêng
    ('Phú Lương', 'Phú Lương'),
    ('Phúc La', 'Phúc La'),
    # Kết hợp ngoặc đơn và ký tự lạ
    ('· P. Phú La (Kiến Hưng mới)', 'Phú La'),
    
    # Nhóm 7: Dữ liệu lỗi/Trống
    (None, "Khác"),
    ("", ""),
])
def test_extract_ward_cases(input_str, expected):
    assert extract_ward(input_str) == expected