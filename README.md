# 🏡 Hệ thống Phân tích & Định giá Bất động sản Hà Đông

Dự án là một hệ thống end-to-end (từ thu thập dữ liệu đến triển khai ứng dụng) nhằm mục đích crawl dữ liệu, phân tích và dự đoán giá bất động sản tại khu vực Hà Đông. Hệ thống được xây dựng với kiến trúc module hóa, tích hợp luồng ETL tự động và ứng dụng AI (Machine Learning) để định giá tự động thông qua giao diện web trực quan.

## 🏗️ Kiến trúc Hệ thống

Dự án được chia thành 4 luồng nghiệp vụ chính:

1. **Thu thập dữ liệu (Data Loading):** Tự động bóc tách dữ liệu từ các trang web bất động sản sử dụng Selenium (headless mode) và lưu trữ thành dạng raw.
2. **Cơ sở dữ liệu (Database):** Lưu trữ và quản lý dữ liệu bằng **PostgreSQL** để đảm bảo tính ổn định và khả năng mở rộng của hệ thống.
3. **Tiền xử lý & AI (Preprocessing & AI Engine):** Làm sạch dữ liệu, trích xuất đặc trưng bằng Regex và huấn luyện mô hình dự đoán. Đặc biệt, module *Cleaner* áp dụng các quy tắc nghiệp vụ chặt chẽ.
4. **Giao diện người dùng (UI):** Tương tác với người dùng qua Streamlit, tích hợp cơ chế cache để tối ưu hóa thời gian phản hồi.

## 🛠️ Tech Stack

* **Ngôn ngữ:** Python 3.x
* **Data Extraction (Crawl):** Selenium
* **Database:** PostgreSQL, psycopg2
* **Data Processing:** Pandas, Numpy, Regex
* **Machine Learning:** Scikit-Learn (RandomForestRegressor)
* **Web Framework:** Streamlit
* **Automation/ETL:** Windows Task Scheduler

## 📂 Cấu trúc Thư mục

```text
├── app.py                            # Khởi chạy giao diện Streamlit UI
├── src/
│   ├── config/
│   │   ├── crawler.py                # Cấu hình tham số cho Spider/Crawler
│   │   ├── database.py               # Cấu hình kết nối PostgreSQL
│   │   └── path.py                   # Quản lý đường dẫn file tập trung
│   ├── data_loader/
│   │   ├── browser.py                # Khởi tạo Selenium Driver
│   │   └── spider.py                 # Crawler bóc tách dữ liệu
│   ├── database/
│   │   └── postgres_manager.py       # Quản lý kết nối & thực thi Query DB
│   ├── preprocessing/
│   │   └── cleaner.py                # Xử lý logic, làm sạch dữ liệu & Regex
│   ├── ai_engine/
│   │   ├── train_model.py            # Huấn luyện & đánh giá mô hình ML
│   │   ├── predictor.py              # Xử lý luồng dự đoán giá
│   │   └── chatbot.py                # Tích hợp AI hỗ trợ người dùng
│   └── ui/
│       ├── dashboard.py              # Giao diện báo cáo phân tích
│       └── prediction.py             # Giao diện định giá BĐS
├── data/                             # Chứa dữ liệu raw, clean và file mô hình (.pkl)
├── requirements.txt
└── README.md

```

## 🧠 Tiền xử lý Dữ liệu (Module `cleaner.py`)

Module `src/preprocessing/cleaner.py` đóng vai trò cốt lõi trong việc đảm bảo chất lượng dữ liệu đầu vào cho AI Engine:

* **Trích xuất đặc trưng (Feature Extraction):** Sử dụng các biểu thức chính quy (Regex) phức tạp để bóc tách các thông tin ẩn trong mô tả văn bản (ví dụ: diện tích, mặt tiền, số tầng).
* **Quy tắc nghiệp vụ (Business Logic):** Xử lý chặt chẽ các trường hợp đặc thù, nổi bật là quy tắc: Nếu `property_type` là "Đất nền", hệ thống tự động ép buộc số phòng ngủ/số phòng tắm phải bằng `0` để tránh nhiễu dữ liệu.

## 🤖 AI Engine & Kết quả Mô hình

Hệ thống sử dụng thuật toán **RandomForestRegressor** để dự đoán giá nhà.

* **Cơ chế Champion-Challenger:** Mô hình được huấn luyện lại theo chu kỳ khi có dữ liệu mới. Hệ thống sẽ tự động so sánh sai số tuyệt đối trung bình (MAE - Mean Absolute Error) của mô hình mới (Challenger) và mô hình hiện tại (Champion).
* **Quy tắc cập nhật:** File `house_price_model.pkl` chỉ được lưu đè khi và chỉ khi mô hình mới thực sự mang lại độ chính xác cao hơn (MAE thấp hơn).
* **Kết quả hiện tại:** Mô hình đạt độ chính xác ổn định, bám sát với giá thị trường khu vực Hà Đông (Chi tiết mức MAE và Accuracy % được log tự động sau mỗi phiên run ETL).

## 🚀 Hướng dẫn Cài đặt & Vận hành

### 1. Cài đặt Môi trường

```bash
# Clone repository
git clone https://github.com/your-username/hanoi-house-price-prediction.git
cd hanoi-house-price-prediction

# Cài đặt thư viện
pip install -r requirements.txt

```

### 2. Cấu hình Cơ sở dữ liệu (PostgreSQL)

Mở file `src/config/database.py` và cập nhật thông tin kết nối tới server PostgreSQL của bạn:

```python
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "your_postgres_user"
DB_PASSWORD = "your_password"
DB_NAME = "real_estate_db"

```

*(Lưu ý: Luôn sử dụng `postgres_manager.py` cho các thao tác đọc/ghi vào DB, tuyệt đối không sử dụng SQLite).*

### 3. Khởi chạy Ứng dụng Streamlit

```bash
streamlit run app.py

```

### 4. Triển khai ETL Pipeline tự động bằng Task Scheduler

Hệ thống thu thập và cập nhật dữ liệu hàng ngày không sử dụng các dịch vụ cloud CI/CD mà được thiết kế để chạy trực tiếp qua **Windows Task Scheduler** nhằm tối ưu chi phí và tận dụng tài nguyên cục bộ:

1. Mở **Task Scheduler** trên Windows.
2. Chọn **Create Basic Task...**
3. Thiết lập **Trigger** (ví dụ: Chạy hàng ngày vào lúc 2:00 AM).
4. Ở tab **Action**, chọn *Start a program*.
5. Trỏ đường dẫn đến file `.bat` hoặc `.vbs` (`run_pipeline.bat` / `run_hidden.vbs`) đã được chuẩn bị sẵn trong thư mục gốc. Script này sẽ tự động kích hoạt quá trình: `spider.py` -> lưu DB -> `cleaner.py` -> `train_model.py` (cập nhật model nếu qua bài test MAE).