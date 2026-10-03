# Phase 2, Track 3, Day 17: Memory Systems for AI Agent

## Bài làm và cách chạy

**Sinh viên:** Lê Thị Thùy Trang — **MSSV:** 2A202602678.

[STEP8.md](STEP8.md) trả lời bốn câu hỏi Bước 8 và phân tích ba bonus. [REPORT.md](REPORT.md) trình bày thiết kế, thực nghiệm offline, đối chứng và kết quả API thật qua OpenAI/OpenRouter. Bảng offline nằm trong [results/benchmark.md](results/benchmark.md), kèm JSON chi tiết và hồ sơ mẫu.

Chạy từ thư mục gốc trên Windows, Python >= 3.11:

```powershell
python -m pip install -r requirements.txt
python -X utf8 src/benchmark.py
python -m pytest src/test_agents.py -v
python -X utf8 src/demo.py
```

Offline không cần API key hay SDK provider. Benchmark mặc định in hai bảng, mỗi bảng hai dòng Baseline/Advanced với sáu chỉ số. Thêm `--ablation` để chạy đối chứng. Token offline là ước lượng, quality là heuristic; usage thực được báo riêng khi chạy live. [src/README.md](src/README.md) mô tả các module và giao diện agent.

## Cấu hình sáu provider và chạy live

Cài `requirements-live.txt`, sao chép `.env.example` thành `.env` và đặt key/model phù hợp. SDK chỉ được import khi bật live. `requirements-live.lock.txt` ghi phiên bản môi trường đã kiểm chứng.

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

## Chuẩn bị bài nộp

Bài cá nhân, nộp **link repo GitHub trên VLearn**, đặt tên theo mẫu `KX-DAY17-HoVaTen-MSSV`. Repo này là [K4-DAY17-LeThiThuyTrang-2A202602678](https://github.com/Sukemcute/K4-DAY17-LeThiThuyTrang-2A202602678). Nội dung chính gồm `src/`, dữ liệu gốc trong `data/`, `README.md` và `STEP8.md`. `REPORT.md` cùng các thư mục kết quả bổ sung giải thích và bằng chứng.

Bonus được chọn gồm confidence threshold, trích xuất có cấu trúc và xử lý mâu thuẫn. Bước 8 giải thích vấn đề, cải thiện và rủi ro của từng hướng. Live là phần mở rộng; phần offline vẫn chạy khi không có key. OpenAI và OpenRouter đã chạy thật; Gemini, Anthropic, Custom và Ollama mới được kiểm tra khởi tạo SDK, cần key/server tương ứng để gọi qua mạng.

Chạy `python scripts/package_submission.py` để tạo ZIP sạch trong `dist/`. Script chọn các file cần nộp, kiểm tra không có key thật, rồi chạy benchmark và 49 tests trong bản sao không có `.env` hay state. Kết quả kiểm tra nằm trong `dist/verification.json`. Không nộp `.env`, API keys, `state/`, `.venv/`, `.agent/`, `.ai-log/` hoặc cache.

Sau khi đưa phiên bản bài làm hiện tại lên GitHub mới lấy link nộp VLearn. Việc chuẩn bị ZIP chưa thực hiện push hoặc nộp trên hệ thống.

## Đề bài gốc

Phần bên dưới giữ nội dung đề bài gốc; các mô tả scaffold/TODO là trạng thái lúc giao bài.

Trong Day 17 này, các bạn sẽ tập trung vào một câu hỏi rất thực tế: làm sao để AI agent **không chỉ trả lời tốt trong một lượt chat**, mà còn **nhớ đúng thông tin quan trọng qua nhiều phiên làm việc** mà vẫn kiểm soát được chi phí token.

Trong bài lab này, các bạn sẽ xây dựng và so sánh hai agent:

- `Baseline Agent`: chỉ có short-term memory trong cùng một thread
- `Advanced Agent`: có short-term memory, `User.md` bền vững, và compact memory để nén hội thoại dài

Mục tiêu cuối cùng không phải chỉ là “agent nhớ nhiều hơn”, mà là hiểu rõ trade-off giữa:

- độ nhớ dài hạn
- chất lượng phản hồi
- chi phí token
- độ phức tạp của hệ thống memory

## Các bạn sẽ làm gì trong track này?

Sau khi hoàn thành, các bạn cần có khả năng:

- phân biệt `short-term memory`, `persistent memory`, và `compact memory`
- xây dựng agent baseline và advanced trên cùng một benchmark
- lưu hồ sơ người dùng bằng `User.md`
- kích hoạt compact memory khi hội thoại dài vượt ngưỡng
- benchmark hai agent bằng cùng một bộ dữ liệu tiếng Việt
- đọc kết quả benchmark theo các chỉ số recall, token, memory growth, chất lượng phản hồi

## Cấu trúc codebase

```
.
├── README.md        # giới thiệu track (file này)
├── Guide.md         # hướng dẫn từng bước
├── Rubric.md        # tiêu chí chấm điểm
├── data/            # dữ liệu benchmark dùng chung
│   ├── conversations.json
│   └── advanced_long_context.json
└── src/             # bản scaffold dành cho sinh viên (pseudocode + TODO)
    ├── model_provider.py
    ├── config.py
    ├── memory_store.py
    ├── agent_baseline.py
    ├── agent_advanced.py
    ├── benchmark.py
    └── test_agents.py
```

Khi chạy, agent sẽ ghi trạng thái (ví dụ `state/profiles/<user>/User.md`) vào thư mục `state/`. Thư mục này đã nằm trong `.gitignore`.

### Vai trò từng file trong `src/`

Các file được liệt kê theo thứ tự nên triển khai:

| File | Vai trò | Thành phần chính |
|---|---|---|
| `model_provider.py` | Khởi tạo chat model cho từng provider | `ProviderConfig`, `normalize_provider()`, `build_chat_model()` |
| `config.py` | Cấu hình chung của lab | `LabConfig` (đường dẫn, ngưỡng compact, model chính + judge), `load_config()` |
| `memory_store.py` | Lõi memory layer | `estimate_tokens()`, `UserProfileStore` (read/write/edit `User.md`), `extract_profile_updates()`, `summarize_messages()`, `CompactMemoryManager` |
| `agent_baseline.py` | Agent A: chỉ nhớ trong cùng thread | `BaselineAgent.reply()`, `token_usage()`, `prompt_token_usage()` |
| `agent_advanced.py` | Agent B: short-term + `User.md` + compact | `AdvancedAgent.reply()`, `_reply_offline()`, `_estimate_prompt_context_tokens()`, `_offline_response()` |
| `benchmark.py` | So sánh hai agent trên hai bộ dữ liệu | `run_agent_benchmark()`, `recall_points()`, `heuristic_quality()`, `format_rows()` |
| `test_agents.py` | Kiểm chứng hành vi memory | test `User.md`, compact trigger, cross-session recall, giảm prompt load |

### Luồng xử lý một lượt của Advanced Agent

```
message người dùng
  → extract_profile_updates()      # trích fact ổn định: tên, nơi ở, nghề, style...
  → ghi vào User.md                # persistent memory
  → CompactMemoryManager.append()  # short-term memory, tự compact khi vượt ngưỡng
  → prompt = User.md + summary + recent messages
  → sinh câu trả lời → cập nhật bộ đếm token
```

Baseline Agent chỉ giữ danh sách message theo `thread_id`. Sang thread mới, nó **phải quên** toàn bộ fact cũ.

Cả hai agent nên có **chế độ offline** cho ra kết quả lặp lại được, để benchmark và test chạy được mà không cần API key. Chế độ live (LangChain/LangGraph) là phần mở rộng.

## Dữ liệu benchmark

| File | Nội dung | Mục tiêu |
|---|---|---|
| `data/conversations.json` | 10 hội thoại khoảng 10 lượt, user `dungct`, kèm `recall_questions` | Standard benchmark: đo recall qua nhiều phiên bình thường |
| `data/advanced_long_context.json` | 1 hội thoại 16 lượt rất dài, user `dungct_stress` | Long-context stress benchmark: ép compact xảy ra nhiều lần |

Mỗi hội thoại có dạng:

```json
{
  "id": "conv-01",
  "user_id": "dungct",
  "turns": ["...", "..."],
  "recall_questions": [
    { "question": "...", "expected_contains": ["DũngCT", "cà phê sữa đá"] }
  ]
}
```

`recall_questions` được hỏi ở **thread mới**. Điểm recall dựa trên số chuỗi trong `expected_contains` xuất hiện trong câu trả lời.

Dữ liệu cố tình chứa các tình huống khó:

- **correction**: nơi ở đổi giữa Đà Nẵng và Huế, agent phải giữ fact mới nhất
- **nhiễu**: "Hà Nội" chỉ là nơi đi họp, "product manager" chỉ là câu đùa
- **ngữ cảnh dài**: nhiều đoạn tin tức dài trong stress test để làm lộ chi phí prompt của baseline

## Provider hỗ trợ

Trong bản solved lab, runtime hỗ trợ các provider sau:

- `openai`
- `custom` (OpenAI-compatible base URL)
- `gemini`
- `anthropic`
- `ollama`
- `openrouter`

Điều này quan trọng vì memory system không nên bị khóa vào một provider duy nhất.

## Chỉ số benchmark cần hiểu

Khi hoàn thiện bài, benchmark nên cho các cột sau:

- `Agent tokens only`: token sinh ra trực tiếp trong hội thoại của agent
- `Prompt tokens processed`: lượng ngữ cảnh agent phải kéo theo qua các lượt
- `Cross-session recall`: khả năng nhớ facts qua thread hoặc session mới
- `Response quality`: chất lượng phản hồi
- `Memory growth (bytes)`: tốc độ phình của file memory
- `Compactions`: số lần compact memory đã nén lịch sử cũ

Điểm quan trọng nhất của track này là:

- ở hội thoại ngắn, `Advanced` có thể tốn hơn `Baseline` về token usage
- ở hội thoại rất dài, compact memory nên giúp `Advanced` xử lý ngữ cảnh hiệu quả hơn đáng kể + tiết kiệm usage.

## Setup môi trường

Các bạn cần chuẩn bị môi trường Python `>= 3.11` và cài các package cần thiết cho LangChain, LangGraph, provider SDK, `python-dotenv`, `tabulate`, và `pytest`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install langchain langgraph langchain-openai langchain-google-genai langchain-anthropic langchain-ollama langchain-openrouter python-dotenv tabulate pytest
```

Nếu muốn chạy chế độ live với LLM thật, hãy tạo file `.env` ở root repo (đã nằm trong `.gitignore`). Tên biến môi trường do các bạn quyết định khi viết `load_config()`. Ví dụ:

```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
```

## Chạy benchmark và test

Sau khi hoàn thiện `src/`, chạy từ root repo:

```bash
python src/benchmark.py
```

```bash
pytest src/test_agents.py -v
```

Benchmark cần in ra hai bảng: **Standard Benchmark** và **Long-Context Stress Benchmark**. Mỗi bảng so sánh Baseline với Advanced theo đủ 6 cột trong phần "Chỉ số benchmark cần hiểu".

## Cách dùng repo này

Nếu các bạn là sinh viên:

- làm bài trong `src/`
- dùng `data/` làm benchmark input

Nếu các bạn là giảng viên hoặc reviewer:

- dùng `src/` để đánh giá scaffold giao cho sinh viên và kết quả hoàn thiện cuối cùng

## Tài liệu nên đọc tiếp

- `Guide.md`: hướng dẫn từng bước để hoàn thành lab
- `Rubric.md`: tiêu chí chấm điểm và bonus

Track này được thiết kế để các bạn không chỉ “dùng agent”, mà còn bắt đầu nghĩ như một người thiết kế **memory system** cho agent production.
