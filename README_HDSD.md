# 🚀 DỰ ÁN PHÂN TÍCH BẤT ĐỘNG SẢN NEW YORK (NYC)

Đây là thư mục Source Code chính thức của nhóm. 
Đã được dọn dẹp sạch sẽ, loại bỏ các file tạm, mật khẩu (.env) để đảm bảo an toàn tuyệt đối.

## 📂 Cấu trúc thư mục:
- pp.py: File chạy chính của trang web (Streamlit Dashboard).
- src/: Mã nguồn cốt lõi (Gồm file xử lý dữ liệu, vẽ biểu đồ, ETL).
- data/: Dữ liệu thô và dữ liệu đã qua tiền xử lý.
- output/: Kết quả của mô hình Machine Learning.
- 
equirements.txt: Danh sách các thư viện cần cài đặt.

## ⚙️ Hướng dẫn chạy thử trên máy của bạn (Local):
1. **Cài đặt môi trường:** Mở Terminal (CMD) và chạy lệnh sau để cài thư viện:
   `ash
   pip install -r requirements.txt
   `
2. **Khởi chạy Web App:** Chạy lệnh sau để mở Dashboard:
   `ash
   streamlit run app.py
   `

## 🔒 Ghi chú Bảo mật
- Không chia sẻ các tài khoản Database hay API Keys (đã được bóc tách).
- Nếu cần chạy kết nối tới cơ sở dữ liệu thật, hãy tự tạo file .env tại thư mục này nhé.

Chúc cả nhóm bảo vệ đồ án thành công rực rỡ! 🔥
