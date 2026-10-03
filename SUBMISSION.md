# Bài nộp Day 17 — đối chiếu hướng dẫn LMS

Đã đọc toàn bộ 11 ảnh trong `.agent/`, đặc biệt `image copy 9.png` (Bước 8/bonus) và `image copy 10.png` (Nộp bài).

## Cần nộp gì?

Bài cá nhân, **nộp link repo GitHub trên VLearn**. Repo đúng mẫu `KX-DAY17-HoVaTen-MSSV`. Repo hiện tại có tên `K4-DAY17-LeThiThuyTrang-2A202602678`, remote là https://github.com/Sukemcute/K4-DAY17-LeThiThuyTrang-2A202602678.

Cấu trúc chính theo ảnh hướng dẫn:

```text
K4-DAY17-LeThiThuyTrang-2A202602678/
├── src/          # Python đã hoàn thiện + tests
├── data/         # dataset gốc, không chỉnh sửa
├── STEP8.md      # trả lời bốn câu hỏi Bước 8 + bonus
└── README.md     # setup và lệnh chạy
```

Repo còn có requirements, báo cáo chi tiết, kết quả benchmark và script đóng gói để reviewer tái lập. Tên file phân tích không bị LMS quy định cứng trong đoạn Bước 8; chọn `STEP8.md` đúng tên được minh họa ở phần nộp bài.

Không nộp `.env`, API keys, `state/`, `.venv/`, `.ai-log/` hoặc cache. Không nộp nguyên thư mục làm việc bằng cách zip tất cả; dùng `python scripts/package_submission.py` để lấy đúng allowlist. `.env.example` chỉ chứa hướng dẫn/placeholder, không có key thật.

## Trước khi lấy link nộp

Chạy từ root repo:

```powershell
python src/benchmark.py
pytest src/test_agents.py -v
```

Lệnh thứ nhất phải in Standard và Long-Context Stress, mỗi bảng đúng hai dòng với đủ sáu metrics; lệnh thứ hai phải pass các tests, đặc biệt bốn test memory gốc. Chạy được từ trạng thái sạch, không phụ thuộc state còn sót hay API key. Bản này dùng state tạm trong benchmark và fixture tmp_path trong tests.

## Bonus mức 90–100

Đề chấp nhận confidence threshold, memory decay, structured entity extraction hoặc conflict handling. Cần ít nhất một hướng hữu ích và giải thích đủ: giải quyết gì; cải thiện recall/token cost thế nào; thêm rủi ro gì. Bài hiện có confidence threshold, structured entity extraction và conflict handling; `STEP8.md` ghi bằng chứng và đánh đổi của từng hướng. Memory decay không phải điều kiện bắt buộc nếu đã chọn bonus khác.

Live LangChain/LangGraph là phần mở rộng, không phải điều kiện để offline chạy. API logs/usage cũng là bằng chứng bổ sung, không thay code/tests/phân tích. Repo phải hỗ trợ cấu hình cả sáu provider; không có yêu cầu phải trả tiền gọi hết sáu provider khi không có key/server.

## Việc nộp trên hệ thống

Các thay đổi được chuẩn bị trong workspace và gói ZIP. Link remote hiện có không đồng nghĩa bản mới đã được push. Cần đưa code hiện tại lên repo trước, rồi dán link repo vào VLearn. Chưa thực hiện push hoặc nộp VLearn trong bước kiểm tra/đóng gói này.
