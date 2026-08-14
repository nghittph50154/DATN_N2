====================================================
  NYC Smart Property Guide — Hướng dẫn Cài đặt
====================================================

📁 CÁC FILE TRONG THƯ MỤC NÀY:
  nyc_platform.py          → App chính (chạy cái này)
  nyc_ml_analysis.py       → Trang kiểm chứng AI (tùy chọn)
  Dulieu_Cleaned_v2.csv    → Dữ liệu 42,000+ giao dịch BĐS NYC
  nyc_combined_data.json   → Dữ liệu 45 chỉ số kinh tế-xã hội
  requirements.txt         → Danh sách thư viện cần cài

====================================================
  CÀI ĐẶT & CHẠY (3 bước)
====================================================

BƯỚC 1 — Cài Python (nếu chưa có):
  Tải tại: https://www.python.org/downloads/
  ✅ Tích vào "Add Python to PATH" khi cài

BƯỚC 2 — Cài thư viện:
  Mở terminal/cmd trong thư mục này, gõ:
  
  pip install -r requirements.txt

BƯỚC 3 — Chạy app:

  streamlit run nyc_platform.py --server.port 8502

  Rồi mở trình duyệt vào: http://localhost:8502

----------------------------------------------------
  (Tùy chọn) Chạy trang AI phụ:
  streamlit run nyc_ml_analysis.py --server.port 8503
  → Mở: http://localhost:8503
====================================================

⚠️  LƯU Ý QUAN TRỌNG:
  - Để TẤT CẢ file trong CÙNG 1 thư mục
  - Không đổi tên file CSV hoặc JSON
  - Lần đầu chạy sẽ mất 1-2 phút để train AI model

====================================================
