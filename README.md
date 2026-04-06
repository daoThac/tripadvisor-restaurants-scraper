# TripAdvisor Restaurant Scraper (Hue Province)

Dự án này chứa đoạn mã tự động (bot) chuyên dùng để trích xuất thông tin các điểm ăn uống (Nhà hàng, Quán Cafe, Trà, Tráng miệng, Quán Bar & Pub) và các bình luận trực tiếp từ TripAdvisor khu vực Thừa Thiên Huế.

## Yêu cầu cài đặt
Sử dụng Python 3.9+ và chạy lệnh sau để cài thư viện:
```bash
pip install -r requirements.txt
playwright install
```

## Cách sử dụng
Mở Terminal và khởi chạy công cụ crawler:
```bash
python restaurant_scraper.py
```
> **Lưu ý:** Tương tự như Hotel, bot sẽ tự động thực hiện 2 quy trình tuần tự:
> - **Bước 1:** Quét và lấy thông tin cơ bản của tất cả các nhà hàng tại Huế lưu vào `restaurants_hue_summary.csv`.
> - **Bước 2:** Vào từng nhà hàng, trích xuất tất cả các review có gắn nhãn thời gian từ sau tháng 1 năm 2025 và lưu dồn vào `restaurants_hue_reviews_jan2025.csv`.

Chương trình này đã được trang bị bộ trích xuất tương thích với giao diện DOM mới nhất của TripAdvisor (sử dụng `data-automation`) và hệ thống dịch định dạng ngày tháng đa ngôn ngữ (Tiếng Anh, Tiếng Việt). Công nghệ lưu dữ liệu tuyến tính giúp chương trình miễn nhiễm với các lỗi đứt quãng kết nối lưới mạng.
