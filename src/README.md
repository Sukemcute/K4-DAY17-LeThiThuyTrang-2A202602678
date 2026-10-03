# Triển khai hoàn chỉnh — Memory Systems for AI Agent

Thư mục `src/` đã được hoàn thiện. Chạy từ thư mục gốc bằng Python >= 3.11:

```powershell
python -X utf8 src/benchmark.py
python -m pytest src/test_agents.py -v
python -X utf8 src/demo.py
```

Offline chỉ dùng thư viện chuẩn; pytest dành cho kiểm thử, python-dotenv là tùy chọn để đọc `.env`.

## Các thành phần

| File | Trách nhiệm |
|---|---|
| `model_provider.py` | Chuẩn hóa và khởi tạo 6 provider; import SDK khi bật live |
| `config.py` | Đường dẫn, cấu hình memory, model chính và judge |
| `memory_store.py` | Rule extraction, confidence, provenance, correction, lưu nguyên tử, summary có giới hạn |
| `response_engine.py` | Responder offline chung, prompt và công thức token chung cho hai agent |
| `agent_baseline.py` | Lịch sử đầy đủ theo thread, không lưu hồ sơ |
| `agent_advanced.py` | User.md + summary + recent messages |
| `benchmark.py` | Hai dataset, ablation, thư mục tạm riêng, kết quả Markdown/JSON |
| `test_agents.py` | Tests hành vi memory, nhiễu, isolation, accounting và mock live |
| `demo.py` | Minh họa correction, nhớ qua thread và khởi tạo lại |

Advanced inject các giá trị đã chấp nhận đọc từ `User.md` vào prompt; metadata bằng chứng không kéo vào mỗi lượt. Summary chỉ sống trong thread, không lưu sang thread mới. Một `thread_id` thuộc một `user_id`; dùng lại thread cho user khác sẽ báo lỗi.

`reply()` trả dictionary gồm `response`, `agent_tokens`, `prompt_tokens`, `mode`, `token_method`. Counter đo output và input riêng. Cả offline và live đều báo ước lượng characters/4 để so sánh nhất quán; không phải usage trên hóa đơn.

Tên `_maybe_build_langchain_agent()` được giữ từ scaffold; bản này trả chat model LangChain. Memory pipeline được điều phối trực tiếp trong Python, không sử dụng LangGraph/checkpointer hay cấp tool ghi file cho model. Chế độ live dùng cùng memory pipeline với offline, nhưng thay responder bằng `model.invoke()`.

## Live tùy chọn

Cài `requirements-live.txt`, sao chép `.env.example` thành `.env`, đặt provider/model/key phù hợp. Benchmark chỉ gọi model thật khi dùng:

```powershell
python -X utf8 src/benchmark.py --live --output-dir results-live
```

Hướng dẫn sáu provider, chọn key/model theo provider, `--store` và log usage thực: xem `PROVIDERS.md` ở root. Mặc định chỉ so Baseline/Advanced; thêm `--ablation` khi muốn chạy hai biến thể đối chứng. Live chọn output directory mới cho mỗi lần chạy.

Mặc định chạy Baseline và Advanced trên cả hai dataset (268 lượt gọi model). `--no-ablation` được giữ để tương thích lệnh cũ; chỉ thêm `--ablation` khi cần gọi thêm hai biến thể đối chứng.

Với sử dụng agent trực tiếp, đặt `LAB_OFFLINE=false`. `force_offline=True` luôn vô hiệu hóa live. Lỗi SDK, cấu hình hoặc API được báo rõ, không giả kết quả offline thành live. `judge_model` được cấu hình sẵn nhưng benchmark hiện dùng quality heuristic; không gọi judge.

Đọc `REPORT.md` ở thư mục gốc để xem phương pháp đo, kết quả, bonus, giới hạn và đối chiếu rubric.
