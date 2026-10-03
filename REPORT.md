# Báo cáo bài lab Day 17 — Memory Systems for AI Agent

**Sinh viên:** Lê Thị Thùy Trang — **MSSV:** 2A202602678.

## 1. Mục tiêu của bài làm

Trong bài này, em xây dựng hai agent để tìm hiểu ảnh hưởng của bộ nhớ đến khả năng nhớ chéo phiên và lượng token cần xử lý. Baseline chỉ lưu hội thoại trong thread hiện tại. Advanced bổ sung hồ sơ người dùng bền vững và cơ chế nén lịch sử. Em muốn kiểm tra hai câu hỏi: lưu hồ sơ có giúp trả lời đúng ở phiên mới không, và compact có giảm lượng lịch sử phải gửi khi hội thoại dài không?

Trong báo cáo, thread là một luồng hội thoại; suite là một bộ kiểm tra gồm các phiên và câu hỏi recall. Recall chéo phiên là hỏi lại thông tin trong thread mới. Compact là rút gọn lịch sử cũ để giảm lượng nội dung phải xử lý.

Bài chạy offline để kiểm tra logic mà không cần API key. Chế độ live dùng model thật qua LangChain nhưng giữ cùng pipeline memory. Em triển khai ba phần bonus: confidence threshold, trích xuất thông tin có cấu trúc và xử lý mâu thuẫn. Phần trả lời trực tiếp bốn câu hỏi Bước 8 nằm trong [STEP8.md](STEP8.md).

## 2. Cách tổ chức và hoạt động của chương trình

Các thành phần chính nằm trong `src/`. `agent_baseline.py` quản lý lịch sử theo thread. `agent_advanced.py` phối hợp hồ sơ và lịch sử nén. `memory_store.py` phụ trách trích xuất, đọc/ghi/sửa hồ sơ và compact. `model_provider.py` chọn SDK tương ứng khi chạy live. `benchmark.py` chạy dữ liệu, chấm recall và ghi kết quả. Hai agent dùng chung bộ trả lời offline trong `response_engine.py` để giảm ảnh hưởng của việc sinh câu trả lời khi so sánh memory.

Baseline chỉ sử dụng user messages trong thread hiện tại để tìm thông tin. Advanced trích candidate từ phát biểu của người dùng, kiểm tra confidence, cập nhật hồ sơ, rồi xây prompt gồm hướng dẫn chung, giá trị hồ sơ, bản tóm tắt và các message gần nhất. Agent không đọc `expected_contains` để trả lời; phần này chỉ được benchmark sử dụng sau khi nhận câu trả lời để chấm điểm.

Hồ sơ có tám field: `name`, `location`, `profession`, `interests`, `favorite_drink`, `favorite_food`, `pet`, `response_style`. Mỗi field lưu giá trị, confidence, evidence và revision. Thông tin lặp lại không làm tăng file. Correction thay giá trị cũ; các yêu cầu về cách trả lời được ghép theo từng đặc điểm để bổ sung ví dụ không làm mất yêu cầu ngắn gọn đã lưu.

Em dùng ngưỡng confidence 0.85 và các mẫu trích xuất tiếng Việt. Chương trình bỏ qua những câu hỏi, giả định, câu đùa và một số thông tin tạm thời được nhận diện. Điểm confidence do quy tắc gán, chưa phải xác suất đúng của fact. Cách này dễ kiểm thử nhưng có thể bỏ sót những cách diễn đạt ngoài mẫu.

Khi lịch sử vượt 1,200 tokens ước lượng, Advanced tạo bản tóm tắt trích nội dung, giữ tối đa 1,600 ký tự cho summary và 4 message gần nhất theo cấu hình. Hồ sơ ổn định được lưu riêng nên không phụ thuộc hoàn toàn vào summary. Một message mới quá dài vẫn có thể làm prompt vượt ngưỡng. Bản này sử dụng pipeline Python trực tiếp và LangChain chat model; chưa triển khai graph/checkpointer hoặc các memory tool trong LangGraph.

## 3. Phương pháp thực nghiệm

Em giữ nguyên dữ liệu đề. Standard có 10 phiên, 101 user turns và 14 câu recall. Stress có 16 user turns và 3 câu recall. Mỗi agent trong mỗi suite có thư mục state tạm riêng. Các phiên được chạy theo thứ tự; câu recall được hỏi ngay sau phiên tương ứng để không sử dụng correction từ tương lai. Mỗi câu recall được hỏi trong một thread mới riêng, tránh câu trả lời trước cung cấp thông tin cho câu tiếp theo.

Bảng benchmark có sáu chỉ số. Agent tokens only đếm output ước lượng. Prompt tokens processed cộng độ dài prompt ở mọi lượt, kể cả recall. Recall là trung bình điểm 0/0.5/1 của từng câu sau chuẩn hóa Unicode và chữ hoa/thường. Response quality là proxy kết hợp recall và độ gọn, theo công thức `recall × (0.8 + 0.2 × min(1, 400 / độ dài answer))`; đây không phải đánh giá độc lập bằng LLM judge. Memory growth đo bytes UTF-8 của hồ sơ tăng từ đầu đến cuối suite. Compactions đếm số lần nén.

Token offline dùng `ceil(len(text.strip()) / 4)` và cộng 4 tokens cho mỗi message trong prompt. Em sử dụng cùng công thức cho hai agent để so sánh trong bài, nhưng không xem đây là số token thanh toán. Trong chế độ live, usage do provider trả được ghi riêng trong JSONL và bảng Actual API usage. Nếu provider không trả usage, log giữ trạng thái thiếu thay vì coi là 0.

## 4. Kết quả offline

### Standard

| Agent | Output tokens ước lượng | Prompt tokens ước lượng | Recall | Quality proxy | Memory bytes | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 1,349 | 24,185 | 0% | 0% | 0 | 0 |
| Advanced | 1,350 | 32,966 | 100% | 100% | 1,499 | 0 |

Advanced nhớ được hồ sơ ở thread mới nhưng tăng prompt load 36.31%. Hồ sơ được gửi thêm ở từng lượt, còn lịch sử chưa đủ dài để kích hoạt compact. Theo em, kết quả cho thấy cải thiện recall có chi phí đi kèm; không nên kết luận có memory thì luôn tiết kiệm token.

### Long-Context Stress

| Agent | Output tokens ước lượng | Prompt tokens ước lượng | Recall | Quality proxy | Memory bytes | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 305 | 24,248 | 0% | 0% | 0 | 0 |
| Advanced | 340 | 14,494 | 100% | 100% | 1,360 | 3 |

Advanced giảm prompt load 40.23% và giữ recall của các câu hỏi hồ sơ. Output tokens không giảm, nên lợi ích quan sát được chủ yếu là giảm lịch sử gửi vào model. Hồ sơ Stress nhỏ hơn Standard dù đoạn hội thoại dài hơn vì chỉ lưu fact phù hợp, không lưu nguyên văn mọi đoạn tin tức.

## 5. Kiểm tra đối chứng và bonus

Em chạy thêm hai biến thể bằng tùy chọn `--ablation`. Advanced tắt compact giữ nguyên các phần còn lại, chỉ nâng ngưỡng nén lên rất cao. Advanced ngưỡng confidence 1.0 giữ compact nhưng từ chối mọi candidate vì điểm quy tắc tối đa là 0.95.

| Biến thể | Prompt tokens Standard | Recall Standard | Prompt tokens Stress | Recall Stress | Compactions Stress |
|---|---:|---:|---:|---:|---:|
| Advanced | 32,966 | 100% | 14,494 | 100% | 3 |
| Advanced tắt compact | 32,966 | 100% | 25,495 | 100% | 0 |
| Advanced confidence 1.0 | 25,359 | 0% | 13,437 | 0% | 3 |

Ở Stress, bật compact giảm 43.15% prompt load so với cùng Advanced khi tắt compact. Đây là đối chứng trực tiếp cho tác động của nén. Ngưỡng confidence 1.0 giảm lượng thông tin phải đưa vào prompt nhưng làm mất recall, nên số tokens thấp hơn chưa đủ để nói biến thể tốt hơn.

Ba bonus phục vụ những vấn đề khác nhau. Confidence threshold hạn chế lưu địa điểm tạm thời thành nơi ở lâu dài. Hồ sơ có cấu trúc giúp cập nhật một field và tránh tăng file khi nhắc lại fact. Xử lý mâu thuẫn giúp ưu tiên nghề/nơi ở mới, đồng thời bỏ các câu đùa hoặc chuyến đi được nhận diện. Phân tích bằng chứng và rủi ro của từng phần được trình bày đầy đủ trong Bước 8. Em chưa triển khai memory decay.

## 6. Kiểm thử và khả năng chạy lại

Môi trường kiểm chứng là Windows, Python 3.12.2 và pytest 8.4.2. Bộ kiểm thử hiện có 49 tests pass. Ngoài bốn hành vi memory bắt buộc, các test kiểm tra correction, nhiễu, thông tin tạm thời, cập nhật lặp, cách trả lời 3 bullet, tách dữ liệu người dùng, tính token, Unicode, adapter provider và ghi usage. Các test provider gồm khởi tạo SDK thật không gọi mạng; điều này không thay cho bằng chứng gọi API thành công.

Có thể chạy phần bắt buộc từ root repo như sau:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 src/benchmark.py
.\.venv\Scripts\python.exe -m pytest src/test_agents.py -v
.\.venv\Scripts\python.exe -X utf8 src/benchmark.py --ablation --output-dir results-ablation
```

Benchmark offline còn được kiểm tra với `python -S`, không nạp site-packages. Script đóng gói chạy benchmark và tests trong bản sao sạch không có `.env` hay state, rồi tạo ZIP. Dữ liệu, câu trả lời và điểm từng câu được lưu trong `results/` và `results-ablation/` để kiểm tra lại.

## 7. Kiểm chứng API và các giới hạn

OpenAI đã chạy cả hai suite với `gpt-4o-mini`, temperature 0, tổng 268 lượt gọi. Log có completion IDs và usage thực. Kết quả cho thấy Standard Advanced tăng tổng tokens 65.19%, còn Stress giảm 54.51%. Vì vậy, kết luận tiết kiệm chỉ phù hợp với workload dài đã đo, không áp dụng cho mọi hội thoại. [REPORT_LIVE.md](REPORT_LIVE.md) trình bày số liệu và cách kiểm tra log.

Bài hỗ trợ OpenAI, Custom, Gemini, Anthropic, Ollama và OpenRouter qua cấu hình. OpenRouter ban đầu bị 401 vì dùng Management/Provisioning key. Sau khi thay key thông thường, kiểm tra kết nối trả HTTP 200 và usage 13 tokens; bằng chứng nằm trong `results/openrouter-diagnostic.json`. Benchmark OpenRouter đã hoàn thành 268 calls; usage khớp log và được phân tích riêng trong báo cáo live. Các provider còn lại cần key hoặc server tương ứng để kiểm chứng qua mạng.

Theo em, giới hạn lớn nhất là extractor theo mẫu và summary có thể mất chi tiết. Điểm recall chuỗi cũng có thể khớp nhầm, còn quality proxy không đo đầy đủ tính đúng, tự nhiên hay mâu thuẫn. Hồ sơ có evidence/revision nhưng chưa có undo đầy đủ hoặc khóa liên tiến trình; phủ định không có giá trị thay thế chưa xóa fact. Nếu phát triển tiếp, em sẽ bổ sung kiểm thử nhớ nội dung sau compact, xử lý xóa thông tin và đánh giá semantic recall, thay vì chỉ tăng số loại fact được lưu.
