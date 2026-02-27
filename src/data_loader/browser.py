# src/data_loader/browser.py
import undetected_chromedriver as uc
import subprocess
import re
import platform
import sys

from src.config.crawler import IS_TASK_SCHEDULER_ENV 

# Ép Python xuất dữ liệu text ra terminal hoặc file log bằng chuẩn UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def get_chrome_version():
    """
    Hàm tự động dò tìm phiên bản Chrome trên cả Windows và Linux
    Trả về số phiên bản chính (Ví dụ: 139)
    """
    system_name = platform.system()
    version = None

    try:
        if system_name == "Windows":
            # Cách 1: Thử truy vấn Registry (Nhanh và chuẩn nhất trên Windows)
            try:
                # Lệnh cmd để đọc Registry key nơi Chrome lưu version
                process = subprocess.Popen(
                    ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                )
                output, _ = process.communicate()
                output = output.decode()
                # Parse kết quả: ... version REG_SZ 139.0.xxxx ...
                match = re.search(r'version\s+REG_SZ\s+(\d+)', output)
                if match:
                    version = int(match.group(1))
            except Exception:
                pass

        elif system_name == "Linux":
            # Cách 2: Chạy lệnh terminal trên Linux
            try:
                cmd_list = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium']
                for cmd in cmd_list:
                    try:
                        result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                        if result.returncode == 0:
                            output = result.stdout.strip()
                            # Output dạng: "Google Chrome 144.0.7559.0"
                            match = re.search(r'(\d+)\.\d+\.\d+\.\d+', output)
                            if match:
                                version = int(match.group(1))
                                break
                    except FileNotFoundError:
                        continue
            except Exception:
                pass
                
    except Exception as e:
        print(f"[Browser] Không dò được version Chrome: {e}")

    if version:
        print(f"[Browser] Phát hiện Chrome ({system_name}): Version {version}")
    else:
        print(f"[Browser] Không tìm thấy Chrome trên {system_name}. Sẽ để thư viện tự quyết định.")
        
    return version

# Cập nhật tham số mặc định thành cờ Task Scheduler
def init_driver(headless=IS_TASK_SCHEDULER_ENV):
    """Khởi tạo Chrome Driver với cấu hình Anti-Detect"""
    print("[Browser] Đang khởi tạo trình duyệt...")
    options = uc.ChromeOptions()
    # Ép trình duyệt không chờ tải ảnh/iframe, có HTML là chiến luôn
    options.page_load_strategy = 'eager'
    args = [
        "--disable-popup-blocking", 
        "--disable-notifications",
        "--no-sandbox", 
        "--disable-dev-shm-usage", 
        "--disable-gpu",
        "--window-size=1920,1080", # Rất quan trọng cho headless
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    ]
    for arg in args:
        options.add_argument(arg)

    try:
        driver = uc.Chrome(
            options=options,
            headless=headless,
            use_subprocess=True,
            version_main=get_chrome_version() # Gọi hàm dò version
        )
        # Patch để ẩn dấu hiệu selenium
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"[Browser] Lỗi khởi tạo driver: {e}")
        raise e