# Phụ lục đối chiếu yêu cầu và bằng chứng

**Sinh viên:** Lê Thị Thùy Trang — **MSSV:** 2A202602678.

## 1. Nội dung cần nộp

Em đối chiếu 11 ảnh hướng dẫn trong `.agent/` với README, Guide và Rubric. Bài nộp cá nhân bằng link repo GitHub trên VLearn, đặt tên theo mẫu `KX-DAY17-HoVaTen-MSSV`. Repo hiện tại là `K4-DAY17-LeThiThuyTrang-2A202602678`. Các phần chính cần có là `src/`, dữ liệu gốc trong `data/`, README hướng dẫn chạy và phân tích Bước 8. Em dùng `STEP8.md` cho phần phân tích này; checklist nằm trong `SUBMISSION.md`.

Phần offline phải chạy được khi không có API key. Benchmark mặc định in hai bảng, mỗi bảng chỉ hai dòng Baseline/Advanced với đủ sáu chỉ số. Các biến thể đối chứng chỉ xuất hiện khi thêm `--ablation`. Recall chấm theo ba mức 0/0.5/1. Test prompt load so trực tiếp Advanced với Baseline, đồng thời có đối chứng Advanced tắt compact.

## 2. Bằng chứng memory và bonus

Kết quả offline nằm trong `results/benchmark.json`, đối chứng trong `results-ablation/benchmark.json`. Dữ liệu gốc không được sửa để thay đổi expected hoặc làm đẹp kết quả. Benchmark tạo state tạm riêng cho mỗi agent/suite, còn các tests sử dụng thư mục tạm để tránh phụ thuộc hồ sơ cũ.

Bộ kiểm thử hiện có 49 tests pass. Có đủ bốn nhóm hành vi bắt buộc: đọc/ghi/sửa hồ sơ; compact khi vượt ngưỡng; recall chéo phiên; giảm prompt load của Advanced so với Baseline. Các test bổ sung kiểm tra correction, nhiễu, confidence, lặp fact, cách trả lời, user isolation, Unicode, cộng usage và lựa chọn provider. Bonus gồm confidence threshold, hồ sơ có cấu trúc và xử lý mâu thuẫn; giải thích vấn đề, bằng chứng và rủi ro nằm trong Bước 8.

## 3. Bằng chứng API và provider

OpenAI đã chạy đầy đủ hai suite, tổng 268 calls bằng `gpt-4o-mini`, temperature 0. Các file trong `results-openai-audit/` lưu câu trả lời, điểm, completion IDs và usage. Tất cả calls có usage; tổng JSONL khớp từng dòng trong báo cáo. Stored completion đầu tiên được đọc lại thành công. Usage thực được trình bày riêng với estimator, không dùng số ước lượng để đại diện hóa đơn.

OpenRouter ban đầu trả 401 do key là Management/Provisioning key. Sau khi thay key thông thường, kiểm tra HTTP trực tiếp trả 200 và usage 13 tokens. `results/openrouter-diagnostic.json` chỉ lưu trạng thái và kết quả an toàn, không lưu key. Benchmark OpenRouter đã hoàn thành 268 calls trong output directory riêng; tổng usage khớp log ở từng agent/suite, xem `results-openrouter-audit/usage-verification.json`.

Sáu adapter đều đã được kiểm tra khởi tạo SDK thật không gọi mạng. OpenAI có benchmark thật; OpenRouter cũng hoàn thành benchmark hai suite, tổng 268 calls có usage và response IDs. Gemini/Anthropic chưa có key tương ứng; Custom/Ollama chưa có server được cấu hình để kiểm chứng qua mạng. Khởi tạo SDK thành công không có nghĩa mọi dịch vụ đã gọi API thành công.

## 4. Kiểm tra gói nộp

`scripts/package_submission.py` chọn danh sách file được phép nộp và kiểm tra không chứa API key thật. Gói loại `.env`, `state/`, `.venv/`, Git metadata, `.agent/`, `.ai-log/` và cache. Script chạy benchmark bằng `python -S` và pytest trong bản sao sạch không có `.env` hay state trước khi tạo ZIP. Kết quả tái lập được ghi trong `dist/verification.json`.

Repo dự kiến nộp là https://github.com/Sukemcute/K4-DAY17-LeThiThuyTrang-2A202602678. Có file ZIP hoặc remote URL chưa có nghĩa các thay đổi mới đã được đưa lên GitHub. Bước chuẩn bị này chưa push code hoặc nộp link trên VLearn. Cần cập nhật repo với đúng nội dung bài làm rồi mới lấy link nộp.
