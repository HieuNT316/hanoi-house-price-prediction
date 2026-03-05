@echo off
:: Thay đổi bảng mã của cmd sang UTF-8
chcp 65001 >nul
:: Ép Python sử dụng UTF-8 khi in dữ liệu ra file log
set PYTHONIOENCODING=utf-8

cd /d "D:\Python\realtime_estimate_tracker"
call venv_bds\Scripts\activate

:: Tạo thư mục log nếu chưa có
if not exist logs mkdir logs

:: Ghi timestamp bắt đầu
echo ========================================= >> logs\deep_pipeline.log
echo [%date% %time%] BAT DAU LUONG DEEP & AI >> logs\deep_pipeline.log

:: === BƯỚC 1: DEEP CRAWL (CHI TIẾT) ===
echo [%date% %time%] [1/3] Dang cao chi tiet BĐS... >> logs\deep_pipeline.log
python -m src.data_loader.detail_spider >> logs\deep_pipeline.log 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] LOI: Detail Spider that bai. Dung pipeline. >> logs\deep_pipeline.log
    goto :error
)

:: === BƯỚC 2: TRAIN AI MODEL ===
echo [%date% %time%] [2/3] Dang huan luyen AI tren du lieu moi... >> logs\deep_pipeline.log
python -m src.ai_engine.train_xgb >> logs\deep_pipeline.log 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] LOI: Train model that bai. >> logs\deep_pipeline.log
    goto :error
)

:: === BƯỚC 3: GIT PUSH (ĐỒNG BỘ CLOUD VỚI GIT LFS) ===
echo [%date% %time%] [3/3] Dang dong bo AI Model (qua LFS) len GitHub... >> logs\deep_pipeline.log
git add .gitattributes models/* logs/*
git commit -m "Auto-update AI Model: %date% %time%" >> logs\deep_pipeline.log 2>&1
git push origin main >> logs\deep_pipeline.log 2>&1

echo [%date% %time%] HOAN THANH LUONG DEEP & AI >> logs\deep_pipeline.log
goto :eof

:error
echo [%date% %time%] LUONG DEEP & AI BI DUNG DO LOI >> logs\deep_pipeline.log
exit /b 1