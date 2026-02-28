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
│   │   ├── crawler.py                
│   │   ├── database.py               
│   │   └── path.py                   
│   ├── data_loader/
│   │   ├── browser.py                
│   │   ├── spider.py                 
│   │   └── detail_spider.py          
│   ├── database/
│   │   └── postgres_manager.py       
│   ├── preprocessing/
│   │   └── cleaner.py                
│   ├── ai_engine/
│   │   ├── train_model.py            
│   │   ├── predictor.py              
│   │   └── chatbot.py                
│   └── ui/
│       ├── dashboard.py              
│       └── prediction.py             
├── tests/                            
├── data/                             
├── models/                           
├── logs/                             
├── automation/                       
├── requirements.txt
└── README.md
🧠 Quy tắc Nghiệp vụ Bắt buộc (ETL & NLP)
Xử lý ngoại lệ "Đất nền": Hệ thống tự động phân loại bất động sản. Nếu property_type là "Đất nền", thuật toán ép buộc gán số lượng phòng ngủ/phòng tắm bằng 0 để tránh gây nhiễu cho mô hình.

Trích xuất bằng ngôn ngữ tự nhiên: Tự động đọc hiểu "ngôn ngữ môi giới" (vd: "3pn", "2wc") từ tiêu đề và mô tả trong trường hợp dữ liệu crawl bị thiếu hụt.

⚖️ Trade-offs & Limitations
Trong quá trình thiết kế hệ thống, các quyết định sau được thực thi dựa trên sự đánh đổi giữa tài nguyên, thời gian và ràng buộc hạ tầng:

1. Kiến trúc Thu thập Dữ liệu
Trade-off: Sử dụng Selenium (Undetected Chromedriver) thay vì HTTP Requests (Scrapy/BeautifulSoup). Việc này đánh đổi tốc độ thực thi và tài nguyên phần cứng (RAM/CPU cao) lấy khả năng vượt qua cơ chế Cloudflare Anti-bot.

Limitation: Độ ổn định phụ thuộc hoàn toàn vào cấu trúc DOM của trang web. Nếu nền tảng thay đổi giao diện, quá trình bóc tách sẽ thất bại. Mạng yếu có thể gây gián đoạn luồng cào dữ liệu chi tiết.

2. Định danh Dữ liệu (Deduplication)
Trade-off: Sử dụng MD5 Hash dựa trên đặc trưng vật lý (diện tích, giá, phân khúc) để tạo listing_id cho cơ chế Upsert. Tiêu đề và ngày đăng bị loại bỏ khỏi hàm băm nhằm ngăn chặn hành vi đăng lại bài cùng một bất động sản từ các môi giới khác nhau.

Limitation: Nếu thông số bị chỉnh sửa nhẹ (ví dụ diện tích từ 50m² thành 50.5m²) kèm thay đổi giá, hệ thống sẽ xác định đây là bản ghi mới, dẫn đến rò rỉ dữ liệu trùng lặp (Duplicate Data Leakage) trong PostgreSQL.

3. Mô hình Học máy
Trade-off: Lựa chọn RandomForestRegressor thay vì các thuật toán Boosting (XGBoost) hoặc Deep Learning. Quyết định này giữ cho mô hình nhẹ, dễ huấn luyện tại máy cục bộ và tính toán Feature Importance rõ ràng, nhưng hy sinh độ chính xác khi nội suy các mối quan hệ phi tuyến phức tạp.

Limitation: Thiếu dữ liệu tọa độ địa lý (Latitude/Longitude). Mô hình phân loại ranh giới thông qua "Phường" (Categorical variables), không đo lường được các yếu tố vị trí vi mô như khoảng cách ra trục đường chính, ngõ cụt hay tiện ích xung quanh.

4. Tiền xử lý & NLP
Trade-off: Xử lý văn bản tự do bằng Regex thay vì các mô hình LLM. Giải pháp này tiết kiệm tài nguyên tính toán và chi phí API, thực thi nhanh trên CPU.

Limitation: Bị giới hạn bởi các patterns định nghĩa trước. Nếu mô tả chứa lỗi chính tả, từ lóng hoặc sai quy chuẩn, Regex sẽ bỏ sót đặc trưng, dẫn đến việc phải dùng KNNImputer để nội suy, làm giảm phương sai tự nhiên của bộ dữ liệu.

5. Tự động hóa & CI/CD
Trade-off: Quản lý lịch trình qua Windows Task Scheduler bằng VBScript tại Local thay vì sử dụng Apache Airflow trên Cloud. Giúp tiết kiệm chi phí hạ tầng và đơn giản hóa quá trình vận hành ban đầu.

Limitation: Thiếu hệ thống giám sát và cảnh báo tự động (Alerting). Không hỗ trợ scale ngang nếu khối lượng dữ liệu phình to.

🚀 Hướng Dẫn Cài Đặt & Vận Hành
Bước 1: Khởi tạo Môi trường
Bash

git clone [https://github.com/Alexus143/hanoi-house-price-prediction.git](https://github.com/Alexus143/hanoi-house-price-prediction.git)
cd hanoi-house-price-prediction
pip install -r requirements.txt
Bước 2: Cấu hình Cơ sở dữ liệu & API Key
Database: Cập nhật thông số kết nối PostgreSQL tại src/config/database.py.

Gemini API: Tạo file .env tại thư mục gốc của dự án:

Code snippet

# .env
GEMINI_API_KEY="your-google-gemini-api-key"
Bước 3: Kiểm thử & Quản lý file lớn
Chạy test:

Bash

pytest tests/
Đảm bảo Git LFS đã được thiết lập để theo dõi file models/house_price_model.pkl.

Bước 4: Chạy Streamlit UI
Bash

streamlit run app.py
Bước 5: Triển khai Tự Động Hóa (Windows Task Scheduler)
Cấu hình chạy các file tại thư mục automation/:

run_fast_pipeline.bat: Chạy Luồng 1.

run_deep_ai_pipeline.bat: Chạy Luồng 2 và cập nhật Model.