# Sáu provider và live logging

Bản bài nộp chạy offline không cần API key. Live sử dụng sáu adapter thật: ChatOpenAI (openai/custom), ChatGoogleGenerativeAI, ChatAnthropic, ChatOllama, ChatOpenRouter. Các SDK được import khi bật live. `.venv` được tạo mới và đã cài đủ các package; `requirements-live.lock.txt` ghi phiên bản môi trường kiểm chứng.

## Cấu hình

| Provider | Key/env | Model mặc định | Endpoint |
|---|---|---|---|
| openai | OPENAI_API_KEY | gpt-4o-mini | SDK mặc định, tùy chọn OPENAI_BASE_URL |
| custom | CUSTOM_API_KEY, CUSTOM_BASE_URL bắt buộc | local-model | OpenAI-compatible URL do người dùng đặt |
| gemini | GEMINI_API_KEY hoặc GOOGLE_API_KEY | gemini-2.5-flash | SDK Gemini, tùy chọn GEMINI_BASE_URL |
| anthropic | ANTHROPIC_API_KEY | claude-sonnet-4-5 | SDK Anthropic, tùy chọn ANTHROPIC_BASE_URL |
| ollama | Không cần key; OLLAMA_BASE_URL tùy chọn | llama3.2 | Ollama server local |
| openrouter | OPENROUTER_API_KEY | openai/gpt-4o-mini | OpenRouter SDK, tùy chọn OPENROUTER_BASE_URL |

Đặt `LLM_PROVIDER`, `LLM_MODEL` trong `.env` cho mặc định chung. Có thể đặt `<PROVIDER>_MODEL` riêng. `LLM_API_KEY`/`LLM_BASE_URL` là override cho provider mặc định; khi đổi provider bằng CLI, code lấy key/model tương ứng, không dùng nhầm key/model OpenAI cho OpenRouter. `JUDGE_PROVIDER`, `JUDGE_MODEL`, `JUDGE_API_KEY` được hỗ trợ nhưng hiện benchmark quality vẫn là heuristic.

CLI không cần sửa `.env` để đổi provider:

```powershell
python src/benchmark.py --live --provider openai --model gpt-4o-mini --store --output-dir results-openai-new
python src/benchmark.py --live --provider openrouter --model openai/gpt-4o-mini --output-dir results-openrouter-new
python src/benchmark.py --live --provider gemini --output-dir results-gemini-new
python src/benchmark.py --live --provider anthropic --output-dir results-anthropic-new
python src/benchmark.py --live --provider ollama --model llama3.2 --output-dir results-ollama-new
python src/benchmark.py --live --provider custom --model your-model --output-dir results-custom-new
```

Nếu SDK/provider chưa cài, dùng `python -m pip install -r requirements-live.txt`; hoặc dùng lockfile cho đúng phiên bản kiểm chứng. Với Ollama phải có server và model tương ứng. Custom cần URL và key theo server. Không gọi API thật cho provider thiếu credentials/server; không tự chuyển API lỗi thành offline.

## Log và usage

Live ghi `api-calls.jsonl` trong output dir: timestamp UTC, agent, provider, model, thread/user ID, messages, response, provider response ID nếu có, LangChain message ID, input/output/total usage thực. Metadata usage thiếu được đánh dấu `null` và đếm riêng, không giả làm 0. Log chỉ ghi payload benchmark và thông tin định danh call; không serialize key hay SDK config.

Bảng sáu cột của đề vẫn dùng cùng estimator input/output cho hai agent. Markdown/JSON có thêm bảng `Actual API usage` riêng lấy từ provider, tránh nhầm với usage ước lượng. Mỗi run chọn output directory mới; nếu đã có JSONL, CLI báo lỗi để tránh trộn evidence cũ vào run mới. Các suite hoàn thành được lưu ngay để giữ kết quả khi suite sau lỗi.

OpenAI `--store` gửi `store=True` và metadata `lab=day17-memory`, `purpose=benchmark`. Xem **Logs → Completions**, chọn đúng project/model; không tìm các call Chat Completions trong tab Responses. OpenRouter có dashboard activity của OpenRouter; `--store` chỉ áp dụng OpenAI, không truyền option không hỗ trợ sang các SDK còn lại.

## Bằng chứng kiểm tra

49 tests đã pass trong `.venv`, gồm constructor thật của sáu SDK không gọi mạng, provider-scoped credential selection, xử lý usage chuẩn LangChain/OpenAI/Ollama, stored-completions option và JSONL.

OpenAI đã chạy thành công cả hai suite qua API thật. OpenRouter ban đầu trả 401 vì endpoint `/api/v1/key` xác nhận key là Management/Provisioning key. Loại key này không gọi completion theo [tài liệu chính thức](https://openrouter.ai/docs/guides/overview/auth/management-api-keys). Cần tạo key thông thường tại [API Keys](https://openrouter.ai/settings/keys) và đặt vào `OPENROUTER_API_KEY`.

Sau khi thay key thông thường, kiểm tra chat trả HTTP 200 với 11 input tokens và 2 output tokens. Bằng chứng nằm trong `results/openrouter-diagnostic.json`. Benchmark qua SDK OpenRouter đã hoàn thành cả hai suite, tổng 268 calls, lưu riêng tại `results-openrouter-audit/`. Usage khớp log và tất cả calls có response ID; không dùng số liệu OpenAI thay cho OpenRouter.

Gemini/Anthropic/Custom/Ollama được khởi tạo SDK/test không gọi API; chưa có key/server để kiểm chứng end-to-end. Những adapter này vẫn dùng cùng pipeline memory và cùng normalized usage ledger.
