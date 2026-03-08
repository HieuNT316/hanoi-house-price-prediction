import os
import joblib

def save_model(model, mae, columns, path):
    model_data = {'model': model, 'mae': mae, 'features': list(columns)}
    joblib.dump(model_data, path)
    print(f"💾 Đã lưu tại: {path}")

def champion_challenger_evaluation(challenger_model, challenger_mae, feature_columns, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    if os.path.exists(path):
        try:
            saved_data = joblib.load(path)
            champion_mae = saved_data.get('mae', float('inf'))
            
            print(f"🥊 Đang so sánh... Champion MAE: {champion_mae:.4f} vs Challenger MAE: {challenger_mae:.4f}")
            
            if challenger_mae < champion_mae:
                print("🏆 Challenger chiến thắng! Cập nhật mô hình mới vào hệ thống.")
                save_model(challenger_model, challenger_mae, feature_columns, path)
            else:
                print("🛡️ Champion bảo vệ ngôi vương. Giữ nguyên mô hình cũ.")
        except Exception as e:
            print(f"⚠️ Lỗi đọc model cũ ({e}). Đang ghi đè model mới...")
            save_model(challenger_model, challenger_mae, feature_columns, path)
    else:
        print("🌟 Chưa có model trong hệ thống. Đang lưu Challenger làm Champion đầu tiên!")
        save_model(challenger_model, challenger_mae, feature_columns)
