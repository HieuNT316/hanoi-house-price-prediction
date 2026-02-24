# src/config/crawler.py

BASE_URL = 'https://batdongsan.com.vn/nha-dat-ban-ha-dong'
# Cờ điều chỉnh hành vi crawler khi chạy tự động ngầm qua Task Scheduler
IS_TASK_SCHEDULER_ENV = True

# Có thể mở rộng thêm sau này:
# CAU_GIAY_URL = 'https://batdongsan.com.vn/nha-dat-ban-cau-giay'
# CRAWL_DELAY = 2.0  # Thời gian nghỉ giữa các request để tránh bị block