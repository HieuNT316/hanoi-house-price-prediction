@echo off
cd /d "D:\Python\realtime_estimate_tracker"
call venv_bds\Scripts\activate

:: Tạo thư mục log nếu chưa có
if not exist logs mkdir logs

:: Ghi timestamp bắt đầu
echo ========================================= >> logs\pipeline.log
echo [%date% %time%] BAT DAU PIPELINE >> logs\pipeline.log

:: === BƯỚC 1: CRAWL ===
echo [1/3] Dang cao du lieu...
python -m src.data_loader.spider >> logs\pipeline.log 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] LOI: Spider that bai. Dung pipeline. >> logs\pipeline.log
    goto :error
)

:: === BƯỚC 2: CLEAN ===
echo [2/3] Dang lam sach du lieu...
python -m src.preprocessing.cleaner >> logs\pipeline.log 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] LOI: Cleaner that bai. Dung pipeline. >> logs\pipeline.log
    goto :error
)

:: === BƯỚC 3: TRAIN ===
echo [3/3] Dang huan luyen AI...
python -m src.ai_engine.train_model >> logs\pipeline.log 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] LOI: Train model that bai. >> logs\pipeline.log
    goto :error
)

:: === BƯỚC 4: GIT PUSH ===
echo [4/4] Dang dong bo len GitHub...
git add data/*
git commit -m "Auto-update: %date% %time%" >> logs\pipeline.log 2>&1
git push origin main >> logs\pipeline.log 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] CANH BAO: Git push that bai. >> logs\pipeline.log
    :: Không goto error vì git push fail không ảnh hưởng data local
)

echo [%date% %time%] HOAN THANH PIPELINE >> logs\pipeline.log
goto :end

:error
echo [%date% %time%] PIPELINE DUNG DO LOI >> logs\pipeline.log
exit /b 1

:end
exit /b 0

:error
echo [%date% %time%] PIPELINE DUNG DO LOI >> logs\pipeline.log
:: Mở file log để xem lỗi (chỉ hoạt động khi chạy trực tiếp, không qua VBS)
start notepad logs\pipeline.log
exit /b 1