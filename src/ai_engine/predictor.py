# src/ai_engine/predictor.py
import pandas as pd
import joblib
import os

class PricePredictor:
    def __init__(self, model_path):
        """Khởi tạo AI Engine và nạp Model"""
        self.model_data = self._load_model(model_path)
        if self.model_data:
            self.model = self.model_data['model']
            self.features = self.model_data['features']
            self.mae = self.model_data.get('mae', 0)
        else:
            self.model = None

    def _load_model(self, path):
        if os.path.exists(path):
            return joblib.load(path)
        return None

    def is_ready(self):
        return self.model is not None

    def predict_single(self, area, bedrooms, bathrooms, ward, property_type):
        """
        Nhận tham số thô từ UI, xử lý Feature Alignment và trả về giá dự đoán.
        """
        if not self.is_ready():
            raise ValueError("Model chưa sẵn sàng!")

        # 1. Tạo DataFrame đầu vào rỗng với cấu trúc cột chuẩn từ lúc Train
        input_df = pd.DataFrame(0, index=[0], columns=self.features)
        
        # 2. Điền các biến số lượng
        input_df['area'] = area
        input_df['bedrooms'] = bedrooms
        input_df['bathrooms'] = bathrooms
        
        # 3. Kỹ thuật Feature Alignment cho biến phân loại
        ward_col = f'ward_{ward}'
        type_col = f'property_type_{property_type}'
        
        if ward_col in input_df.columns:
            input_df[ward_col] = 1
        if type_col in input_df.columns:
            input_df[type_col] = 1

        # 4. Thực hiện dự đoán (LƯU Ý: Model giờ dự đoán ĐƠN GIÁ - Tỷ/m2)
        pred_unit_price = self.model.predict(input_df)[0]
        
        # 5. Quy đổi ra TỔNG GIÁ (Tỷ VNĐ)
        pred_total_price = pred_unit_price * area
        
        # Trả về Tổng giá, Đơn giá và MAE
        return pred_total_price, pred_unit_price, self.mae