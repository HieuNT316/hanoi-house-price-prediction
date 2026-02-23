# src/config/crawler.py

BASE_URL = 'https://batdongsan.com.vn/nha-dat-ban-ha-dong'
IS_GITHUB_ACTIONS = False  # Cờ này có thể dùng để điều chỉnh hành vi crawler khi chạy trên GitHub Actions (nếu cần)

# Có thể mở rộng thêm sau này:
# CAU_GIAY_URL = 'https://batdongsan.com.vn/nha-dat-ban-cau-giay'
# CRAWL_DELAY = 2.0  # Thời gian nghỉ giữa các request để tránh bị block