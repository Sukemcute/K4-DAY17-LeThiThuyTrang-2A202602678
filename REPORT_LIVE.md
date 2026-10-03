# Báo cáo kiểm chứng bằng API thật

**Sinh viên:** Lê Thị Thùy Trang — **MSSV:** 2A202602678.

## 1. Mục đích và cách chạy

Sau khi kiểm tra logic memory bằng chế độ offline, em chạy thêm model thật để quan sát câu trả lời và token usage do provider báo. Phần này là bằng chứng bổ sung cho bài lab. Khi chạy live, bộ trả lời offline được thay bằng LangChain chat model; các quy tắc trích xuất và compact vẫn giữ nguyên.

Lần OpenAI được dùng trong báo cáo này chạy model `gpt-4o-mini`, temperature 0, cả hai suite và hai agent chính, tổng 268 lượt gọi. Mỗi agent/suite bắt đầu từ state trống và nhận cùng dữ liệu. Em không chạy ablation bằng API trong lần này. Bằng chứng nằm trong [benchmark.json](results-openai-audit/benchmark.json), [benchmark.md](results-openai-audit/benchmark.md) và [api-calls.jsonl](results-openai-audit/api-calls.jsonl).

## 2. Kết quả OpenAI

Bảng dưới dùng usage thực do API báo, khác với token ước lượng trong bảng chính của đề:

| Suite | Agent | Calls | Input tokens thực | Output tokens thực | Total tokens thực | Recall | Compactions |
|---|---|---:|---:|---:|---:|---:|---:|
| Standard | Baseline | 115 | 48,858 | 7,225 | 56,083 | 10.7% | 0 |
| Standard | Advanced | 115 | 78,463 | 14,179 | 92,642 | 100% | 8 |
| Stress | Baseline | 19 | 49,247 | 3,634 | 52,881 | 0% | 0 |
| Stress | Advanced | 19 | 20,279 | 3,777 | 24,056 | 100% | 15 |

Ở Standard, Advanced tăng input tokens 60.59% và tổng tokens 65.19%. Hồ sơ được đưa thêm vào prompt, đồng thời model tạo câu trả lời dài hơn nên lịch sử của các lượt sau cũng tăng. Dù đã có 8 lần compact, phần giảm lịch sử chưa bù hết lượng tokens tăng thêm. Kết quả này phù hợp với đánh đổi đã quan sát ở offline: nhớ tốt hơn không đồng nghĩa luôn tốn ít hơn.

Ở Stress, Advanced giảm input tokens 58.82% và tổng tokens 54.51%. Output tokens tăng nhẹ 3.94%. Em cho rằng lợi ích chính của compact trong workload này là giảm phần lịch sử gửi lặp lại, chứ không phải làm câu trả lời ngắn hơn. Advanced vẫn đạt đủ chuỗi kỳ vọng của các câu hỏi hồ sơ.

Tổng hai suite, Baseline dùng 108,964 tokens còn Advanced dùng 116,698. Nếu chỉ nhìn Stress thì dễ kết luận Advanced luôn tiết kiệm, nhưng tổng workload cho thấy các phiên ngắn có thể làm kết quả ngược lại. Em không quy đổi số tokens thành số tiền vì chưa đối chiếu hóa đơn, giá input/output và cách tính cached tokens. Đây là số lượng tokens xử lý, không phải kết luận về chi phí thanh toán.

Model live sinh câu trả lời dài hơn bộ trả lời offline, khiến compact kích hoạt nhiều hơn: Standard có 8 lần thay vì 0, Stress có 15 lần thay vì 3. Dù temperature bằng 0, lần chạy khác vẫn có thể có output khác. Vì vậy, em giữ riêng dữ liệu từng lần thay vì trộn các bảng.

## 3. Cách kiểm tra log và usage

Mỗi dòng JSONL lưu thời điểm, provider/model, agent, thread, messages, câu trả lời, response ID và usage. Tất cả 268 lượt OpenAI có completion ID và usage; tổng usage trong log khớp các dòng agent/suite trong benchmark JSON. API key và cấu hình SDK chứa key không được ghi vào log.

Lần chạy OpenAI bật `store=True`, kèm metadata `lab=day17-memory` và `purpose=benchmark`. Trên dashboard cần xem **Logs → Completions** của đúng project, thay vì chỉ xem tab Responses. Completion đầu tiên đã được đọc lại thành công bằng ID `chatcmpl-EUwmE3pIanh7CReqCm1ky6AlRXK3W`, nên có bằng chứng rằng request đã được lưu ở phía API.

Có thể chạy một lần mới bằng lệnh sau sau khi cài `requirements-live.txt` và cấu hình key:

```powershell
python -X utf8 src/benchmark.py --live --provider openai --model gpt-4o-mini --store --output-dir results-openai-new
python -X utf8 src/benchmark.py --live --provider openrouter --model openai/gpt-4o-mini --output-dir results-openrouter-new
```

Cần chọn output directory mới để không trộn log các lần chạy. Chương trình báo lỗi nếu thư mục đã có `api-calls.jsonl`. Chế độ live không tự chuyển thành offline khi API lỗi.

## 4. Giới hạn của điểm recall và quality

Baseline không có hồ sơ bền vững nhưng vẫn đạt 10.7% ở Standard. Điểm khác 0 không đủ chứng minh nhớ chéo phiên: model có thể nhắc từ đã có trong câu hỏi, dùng kiến thức sẵn có hoặc được tính điểm do khớp chuỗi nhầm. Ví dụ, sau khi chuyển chữ thường, chuỗi `AI` có thể khớp trong từ `hai`. Cần đọc câu trả lời thực để phân biệt trả lời đúng fact với chỉ chứa từ khóa.

Bộ chấm hiện dùng ba mức 0, 0.5 và 1 theo yêu cầu. Quality là proxy từ recall và độ gọn, không phải LLM judge độc lập. Advanced đạt 100% trên tập câu hỏi hồ sơ của đề; chưa có benchmark semantic recall đầy đủ cho các đoạn tin tức sau compact. Nếu đánh giá sâu hơn, em sẽ bổ sung kiểm tra nghĩa câu trả lời, phủ định và ranh giới từ.

Báo cáo này thay phần phân tích live ban đầu bằng lần chạy có log usage và phép chấm ba mức. Lần cũ dùng cách cho điểm khác và không có tổng actual usage; vì vậy, em không dùng số liệu cũ để so sánh trực tiếp hoặc làm bằng chứng chính của bài nộp.

## 5. Kiểm tra OpenRouter

Ban đầu SDK và HTTP trực tiếp đều trả 401 với thông báo `User not found`. Để xác định nguyên nhân, em kiểm tra loại key bằng endpoint `/api/v1/key`. Key lúc đó có `is_management_key=true` và `is_provisioning_key=true`. Theo [tài liệu OpenRouter](https://openrouter.ai/docs/guides/overview/auth/management-api-keys), management key dùng cho tác vụ quản trị và không được gọi completion. Điều này giải thích vì sao endpoint kiểm tra key trả 200 nhưng gọi chat lại lỗi.

Sau khi thay bằng key thông thường, endpoint kiểm tra key trả hai cờ trên là `false`. Gọi `openai/gpt-4o-mini` qua OpenRouter trả HTTP 200, câu trả lời `OK.`, với 11 input tokens, 2 output tokens, tổng 13. Kết quả an toàn, không chứa key, được lưu trong [openrouter-diagnostic.json](results/openrouter-diagnostic.json). Benchmark đầy đủ qua adapter OpenRouter đã hoàn thành; kết quả và đối chiếu usage được trình bày ở mục 6.

Gemini, Anthropic, Custom và Ollama đã được kiểm tra khởi tạo SDK, nhưng chưa có đủ key/server để gọi thật. Em phân biệt hỗ trợ cấu hình provider với đã kiểm chứng dịch vụ đó qua mạng để không ghi nhận kết quả chưa đo.

## 6. Kết quả benchmark đầy đủ qua OpenRouter

Em chạy cùng hai bộ dữ liệu và hai agent qua adapter OpenRouter, với model `openai/gpt-4o-mini` và temperature 0. Có 268 lượt gọi hoàn thành, tất cả có response ID và usage. Em cộng lại log theo thứ tự chạy từng agent/suite; các tổng input/output/total khớp từng dòng benchmark. Các số dưới đây là usage thực của lần OpenRouter, được giữ riêng với OpenAI.

| Suite | Agent | Calls | Input tokens thực | Output tokens thực | Total tokens thực | Recall | Compactions |
|---|---|---:|---:|---:|---:|---:|---:|
| Standard | Baseline | 115 | 57,892 | 9,008 | 66,900 | 10.7% | 0 |
| Standard | Advanced | 115 | 76,814 | 14,593 | 91,407 | 100.0% | 9 |
| Stress | Baseline | 19 | 48,203 | 3,497 | 51,700 | 0.0% | 0 |
| Stress | Advanced | 19 | 20,603 | 3,957 | 24,560 | 100.0% | 16 |

Ở Standard, Advanced dùng 91,407 tokens so với 66,900 của Baseline, tăng 36.63%. Ở Stress, Advanced giảm input tokens 57.26% và tổng tokens 52.50%, với recall 100%. Hai lần chạy OpenAI và OpenRouter đều cho thấy cùng xu hướng: hồ sơ cải thiện recall nhưng có overhead ở phiên ngắn; compact giúp giảm đầu vào khi lịch sử dài. Em không dùng chênh lệch giữa hai provider để kết luận dịch vụ nào tốt hơn vì output của từng lần chạy có thể khác.

Bằng chứng: [bảng benchmark](results-openrouter-audit/benchmark.md), [JSON chi tiết](results-openrouter-audit/benchmark.json), [log từng call](results-openrouter-audit/api-calls.jsonl) và [đối chiếu usage](results-openrouter-audit/usage-verification.json).
