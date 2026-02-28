```markdown
# 🏡 Hệ Thống Phân Tích & Định Giá Bất Động Sản Hà Đông

Dự án là một hệ thống dữ liệu end-to-end (ETL Pipeline & Machine Learning) tự động cào dữ liệu, làm sạch, lưu trữ và huấn luyện mô hình AI để định giá bất động sản tại quận Hà Đông theo thời gian thực. Hệ thống sử dụng kiến trúc 2 luồng Pipeline bất đồng bộ để tối ưu tài nguyên và vượt qua các cơ chế Anti-bot, với PostgreSQL làm cơ sở dữ liệu trung tâm.

## 🏗️ Kiến trúc Hệ thống & Luồng Dữ liệu

Hệ thống được phân tách thành các module độc lập, hoạt động theo 2 luồng chính:

### A. Luồng 1: Fast Ingestion Pipeline (Quét bề mặt - 1 lần/ngày)
* **`spider.py`**: Bóc tách dữ liệu cơ bản (Giá, Diện tích, Phường, URL) từ trang danh sách. Gộp dữ liệu mới vào `raw_data.csv` bằng `pd.concat` để chống Schema Drift. File `raw_data.csv` được giữ nguyên trong mọi tình huống.
* **`cleaner.py`**: 
  * Áp dụng NLP và Regex để trích xuất số phòng từ văn bản.
  * Lọc Outlier (giá, diện tích, đơn giá) và điền khuyết bằng `KNNImputer`.
  * Băm ID (`listing_id`) bằng MD5 dựa trên các đặc trưng vật lý (bỏ title và published_date) để chống tin đăng lại.
  * Khởi tạo Schema bảng `bds_hadong` trong PostgreSQL (17 cột, gán giá trị NULL cho 6 cột feature nâng cao).
  * Upsert dữ liệu vào Database. Gán `is_enriched = True` cho các dữ liệu cũ thiếu URL để bảo vệ luồng 2.

### B. Luồng 2: Deep Enrich & Train Pipeline (Cào chi tiết & Học máy - Chạy ban đêm)
* **`detail_spider.py`**: 
  * Truy vấn PostgreSQL lấy các bản ghi có `is_enriched = False`.
  * Truy cập từng URL để cào 6 feature nâng cao: Mặt tiền, Đường vào, Số tầng, Hướng, Pháp lý, Nội thất.
  * Áp dụng kỹ thuật Respawn (tự động khởi tạo lại trình duyệt khi bị crash do Cloudflare/Headless) và Eager Loading + Timeout 30s (bỏ qua tải ảnh/iframe) để chống kẹt code.
  * Cập nhật dữ liệu trực tiếp vào PostgreSQL.
* **`train_model.py`**: 
  * Kéo toàn bộ dữ liệu từ PostgreSQL. Xử lý Missing Data bằng Median.
  * Áp dụng One-hot Encoding (sử dụng `drop_first=True` chống bẫy biến giả).
  * Huấn luyện bằng `RandomForestRegressor` kết hợp `GridSearchCV`.
  * **Cơ chế Champion-Challenger**: Chỉ lưu đè `house_price_model.pkl` nếu MAE (Sai số tuyệt đối trung bình) của mô hình mới thấp hơn mô hình hiện tại.

### C. Giao diện (Streamlit UI) & Dự đoán (`predictor.py`)
* Ứng dụng cung cấp giao diện nhập thông số.
* Sử dụng decorator `@st.cache_data(ttl=3600)` để lưu bộ nhớ đệm kết quả Query từ PostgreSQL trong 1 giờ.
* Mô hình ánh xạ chính xác các đặc trưng One-hot Encoding theo đúng cấu trúc lúc huấn luyện để suy luận giá.

## 🛠️ Tech Stack

* **Ngôn ngữ:** Python 3.10+
* **Cơ sở dữ liệu:** PostgreSQL (`PostgresManager` & `psycopg2`)
* **Thu thập dữ liệu:** Selenium (Undetected Chromedriver)
* **Xử lý dữ liệu:** Pandas (Ưu tiên Re-assignment, không dùng `inplace=True`), Numpy, Regex, Hashlib
* **Machine Learning:** Scikit-Learn (`RandomForestRegressor`, `GridSearchCV`)
* **Giao diện Web:** Streamlit, Streamlit-Float
* **Tích hợp AI:** Gemini API (Chatbot tư vấn)
* **Testing & CI/CD:** Pytest, Git LFS, Windows Task Scheduler

## 📂 Cấu trúc Thư mục

```text
├── .env                              # File biến môi trường (chứa GEMINI_API_KEY)
├── app.py                            # Khởi chạy giao diện Streamlit UI & cấu hình Cache
├── src/
│   ├── config/
│   │   ├── crawler.py                # Tham số cho Spider/Crawler
│   │   ├── database.py               # Cấu hình kết nối PostgreSQL
│   │   └── path.py                   # Quản lý đường dẫn file tập trung
│   ├── data_loader/
│   │   ├── browser.py                # Khởi tạo Selenium Driver
│   │   ├── spider.py                 # Crawler Luồng 1 (Quét bề mặt)
│   │   └── detail_spider.py          # Crawler Luồng 2 (Cào chi tiết)
│   ├── database/
│   │   └── postgres_manager.py       # Tương tác DB, xử lý Upsert/Update dữ liệu
│   ├── preprocessing/
│   │   └── cleaner.py                # Pipeline ETL, làm sạch dữ liệu & Regex
│   ├── ai_engine/
│   │   ├── train_model.py            # Huấn luyện mô hình, Champion-Challenger evaluation
│   │   ├── predictor.py              # Xử lý luồng dự đoán giá
│   │   └── chatbot.py                # Render Chatbot với Gemini API
│   └── ui/
│       ├── dashboard.py              # Giao diện biểu đồ thống kê
│       └── prediction.py             # Giao diện nhập liệu định giá
├── tests/                            # Chứa các file unit test (sử dụng pytest và unittest.mock)
├── data/                             # Chứa dữ liệu thô (.csv) 
├── models/                           # Chứa file house_price_model.pkl
├── logs/                             # Chứa log hệ thống
├── automation/                       # Các script tự động hóa (.bat, .vbs)
├── requirements.txt
└── README.md

```

## 🧠 Quy tắc Nghiệp vụ Bắt buộc (ETL & NLP)

* **Xử lý ngoại lệ "Đất nền":** Hệ thống tự động phân loại bất động sản. Nếu `property_type` là "Đất nền", thuật toán ép buộc gán số lượng phòng ngủ/phòng tắm bằng `0` để tránh gây nhiễu cho mô hình.
* **Trích xuất bằng ngôn ngữ tự nhiên:** Tự động đọc hiểu "ngôn ngữ môi giới" (vd: "3pn", "2wc") từ tiêu đề và mô tả trong trường hợp dữ liệu crawl bị thiếu hụt.

## 🚀 Hướng Dẫn Cài Đặt & Vận Hành

### Bước 1: Khởi tạo Môi trường

```bash
git clone [https://github.com/Alexus143/hanoi-house-price-prediction.git](https://github.com/Alexus143/hanoi-house-price-prediction.git)
cd hanoi-house-price-prediction
pip install -r requirements.txt

```

### Bước 2: Cấu hình Cơ sở dữ liệu & API Key

1. **Database:** Cập nhật thông số kết nối PostgreSQL (Host, Port, User, Password, DB Name) tại `src/config/database.py`.
2. **Gemini API:** Tạo file `.env` tại thư mục gốc của dự án và cấu hình key để kích hoạt AI Chatbot:

```env
# .env
GEMINI_API_KEY="your-google-gemini-api-key"

```

### Bước 3: Kiểm thử & Quản lý file lớn

* Chạy unit test để kiểm tra logic làm sạch, định dạng schema và pipeline:

```bash
pytest tests/

```

* Đảm bảo Git LFS đã được thiết lập để quản lý file `models/house_price_model.pkl` thông qua `.gitattributes`.

### Bước 4: Chạy Streamlit UI

```bash
streamlit run app.py

```

### Bước 5: Triển khai Tự Động Hóa (Windows Task Scheduler)

Hệ thống sử dụng các file VBScript chạy ngầm để thực thi các batch script quản lý luồng:

1. Thiết lập Trigger trên Windows Task Scheduler.
2. Cấu hình chạy các file tại thư mục `automation/`:
* **`run_fast_pipeline.bat`**: Chạy Luồng 1 (`spider.py` -> `cleaner.py`) và thực hiện `git push` dữ liệu thô.
* **`run_deep_ai_pipeline.bat`**: Chạy Luồng 2 (`detail_spider.py` -> `train_model.py`) và `git push` mô hình/dữ liệu mới.



```

```