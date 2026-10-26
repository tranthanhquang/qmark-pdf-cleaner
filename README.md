# QMark PDF Cleaner

Ứng dụng desktop QMark xử lý PDF cục bộ, cho xem trước và xóa dấu scan theo từng trang. Phiên bản hiện tại nhận diện wordmark `CamScanner` làm dấu mẫu; logo không có chữ sẽ chưa được hỗ trợ.

## Yêu cầu

- Python 3.12
- Tkinter
- Tesseract OCR được cài cục bộ để xử lý các trang PDF dạng ảnh/scan

Trên macOS dùng Homebrew, cài các thành phần cần thiết bằng lệnh:

```bash
brew install python-tk@3.12 tesseract
```

## Chạy ứng dụng

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src
```

## Chạy kiểm tra tự động

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Nhận diện chữ và OCR đều chạy trên thiết bị; ứng dụng không gửi nội dung PDF đến dịch vụ bên ngoài. Tệp nguồn không bị ghi đè: hãy chọn đường dẫn riêng để lưu kết quả. Vùng dấu bị xóa sẽ được thay bằng nền trắng; nội dung bị dấu che không được khôi phục.

## Giấy phép

Dự án này được cấp phép theo GNU Affero General Public License phiên bản 3 (`AGPL-3.0-only`); xem nội dung đầy đủ trong `LICENSE`. Dự án chọn nhánh AGPL của PyMuPDF. Nếu muốn phân phối ứng dụng theo giấy phép khác hoặc đóng mã nguồn, cần thay PyMuPDF bằng thư viện phù hợp hoặc xin giấy phép thương mại từ Artifex trước khi phân phối. Xem [điều khoản PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).

## Trạng thái kiểm chứng

Cả 10 kiểm tra tự động đều đạt. Các kiểm tra bao gồm nhận diện chữ nhúng trong PDF với các cách viết xung quanh khác nhau, xóa toàn bộ block marker có khung, lựa chọn giữ/xóa theo trang, bảo toàn tệp nguồn và trang, quy đổi tọa độ OCR bằng dữ liệu OCR mô phỏng, xử lý tệp không hợp lệ và thông báo khi thiếu Tesseract. Trong quá trình triển khai chưa có Tesseract và PDF CamScanner mẫu, nên chưa xác minh OCR trên bản scan thực tế hoặc mục tiêu nhận diện 95%.

Mã nguồn ứng dụng không có HTTP client hoặc lời gọi dịch vụ bên ngoài. Việc xử lý PDF và OCR chỉ sử dụng tệp cục bộ và chương trình chạy trên thiết bị.
