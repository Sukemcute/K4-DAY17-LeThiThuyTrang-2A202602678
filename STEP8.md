# Bước 8 — Phân tích kết quả và phần bonus

**Sinh viên:** Lê Thị Thùy Trang — **MSSV:** 2A202602678.

Trong bài lab này, em so sánh hai cách quản lý bộ nhớ. Baseline giữ lịch sử theo từng thread. Advanced giữ thêm hồ sơ người dùng trong `User.md` và nén lịch sử khi hội thoại dài. Em sử dụng nguyên hai bộ dữ liệu của đề, cho hai agent nhận cùng đầu vào và bắt đầu từ trạng thái trống. Phân tích chính dưới đây dựa trên [kết quả offline](results/benchmark.json). Kết quả API thật được trình bày riêng trong [REPORT_LIVE.md](REPORT_LIVE.md).

## 1. Vì sao Advanced nhớ chéo phiên tốt hơn Baseline?

Ở cả Standard và Long-Context Stress, Baseline đạt recall 0%, còn Advanced đạt 100%. Sự khác biệt nằm ở nơi lưu thông tin. Baseline giữ message theo `thread_id`. Khi câu hỏi recall được đặt trong thread mới, lịch sử cũ không được đưa vào nên agent không có thông tin về tên, nơi ở hoặc nghề nghiệp đã nói ở phiên trước. Baseline vẫn nhớ được trong cùng thread; điểm 0% ở đây phản ánh bài kiểm tra chéo phiên.

Advanced lấy thông tin phù hợp từ phát biểu của người dùng rồi ghi vào `User.md`. Khi mở thread mới, agent đọc lại hồ sơ và đưa các giá trị đã lưu vào prompt. Chẳng hạn, khi người dùng sửa nghề thành MLOps engineer, thông tin mới được dùng khi hỏi lại ở phiên sau. Hồ sơ nằm trên đĩa nên vẫn đọc được sau khi khởi tạo lại agent. Ngược lại, bản tóm tắt và lịch sử gần nhất chỉ nằm trong RAM của thread.

Em hiểu recall 100% là khớp đủ các chuỗi kỳ vọng trong tập câu hỏi của đề, chưa chứng minh agent nhớ mọi chi tiết của hội thoại. Mỗi câu được chấm 0 nếu không khớp, 0.5 nếu khớp một phần và 1 nếu khớp hết. Cách chấm chuỗi dễ kiểm tra nhưng có thể tính nhầm một từ nằm trong từ khác hoặc thông tin đã có ngay trong câu hỏi. Vì vậy, em lưu cả câu trả lời để có thể kiểm tra lại điểm.

## 2. Vì sao Advanced có thể tốn hơn ở hội thoại ngắn?

Trong Standard, Baseline xử lý 24,185 prompt tokens, còn Advanced xử lý 32,966. Advanced tăng 8,781 tokens, tương đương 36.31%. Output tokens gần bằng nhau, lần lượt là 1,349 và 1,350, vì hai agent dùng chung bộ trả lời offline.

Advanced đưa hồ sơ vào prompt ở mỗi lượt để cá nhân hóa câu trả lời, nên đầu vào dài hơn. Trong lần chạy offline này, lịch sử chưa vượt ngưỡng 1,200 tokens ước lượng và số lần compact bằng 0. Phần thông tin thêm chưa được bù bằng việc rút ngắn lịch sử. Theo em, đây là đánh đổi giữa khả năng nhớ chéo phiên và lượng thông tin phải gửi ở mỗi lượt, không phải lỗi của việc lưu memory.

Các số token offline được ước lượng bằng `ceil(len(text.strip()) / 4)`, cộng 4 tokens cho mỗi message trong prompt. Hai agent dùng cùng công thức, nhưng đây không phải usage hóa đơn. Việc trích xuất và ghi hồ sơ dùng quy tắc Python, không gọi model riêng nên không phát sinh token API cho thao tác ghi file.

## 3. Vì sao compact có lợi trong hội thoại dài?

Trong Stress, Baseline xử lý 24,248 prompt tokens, còn Advanced xử lý 14,494, giảm 40.23%. Advanced thực hiện 3 lần compact. Baseline gửi lại toàn bộ lịch sử ở mỗi lượt, nên cùng một message cũ được xử lý nhiều lần. Advanced thay lịch sử cũ bằng bản tóm tắt có giới hạn và giữ các message gần nhất để tiếp tục hội thoại.

Để kiểm tra tác động của compact, em chạy thêm Advanced tắt compact. Biến thể này giữ nguyên cách trích xuất, hồ sơ và bộ trả lời, chỉ đặt ngưỡng nén rất cao. Kết quả Stress là 25,495 prompt tokens và recall 100%. So với chính biến thể này, Advanced có compact giảm 11,001 tokens, tương đương 43.15%, trong khi điểm recall giữ nguyên. [Kết quả đối chứng](results-ablation/benchmark.json) giúp giải thích rằng việc giảm prompt load có liên quan trực tiếp đến nén lịch sử.

Lợi ích chủ yếu nằm ở đầu vào. Output tokens của Baseline và Advanced là 305 và 340, không giảm theo prompt. Bản tóm tắt hiện tại được tạo bằng Python để trích nội dung, không dùng một LLM khác. Nếu đổi sang LLM summarization, cần cộng token của những lần tóm tắt trước khi kết luận về tổng chi phí.

Việc nén cũng có thể làm mất chi tiết cũ khi bản tóm tắt đạt giới hạn. Các câu recall của đề chủ yếu hỏi hồ sơ ổn định, nên chưa đo khả năng nhớ đầy đủ những nội dung tin tức sau khi compact. Ngưỡng 1,200 là điều kiện kích hoạt nén, không phải cam kết mọi prompt luôn dưới 1,200 tokens; một message mới rất dài vẫn được giữ lại.

## 4. File memory tăng trưởng thế nào và có rủi ro gì?

Hồ sơ Advanced tăng 1,499 bytes ở Standard và 1,360 bytes ở Stress. Dù Stress có nhiều đoạn văn dài, hồ sơ không lớn hơn Standard vì em chỉ lưu các field được hỗ trợ, thay vì chép toàn bộ hội thoại vào file. Fact được nhắc lại không tạo thêm bản sao. Correction được chấp nhận sẽ thay giá trị cũ trong cùng field. Kiểm thử lặp cùng fact 100 lần cũng xác nhận file không tiếp tục tăng kích thước.

Theo em, rủi ro chính là lưu sai thông tin. Quy tắc có thể bỏ sót cách diễn đạt hoặc chấp nhận một phát biểu sai. Một correction sai có thể ghi đè giá trị đúng trước đó. Mỗi field có evidence và revision để kiểm tra cập nhật, nhưng chưa có lịch sử đầy đủ để khôi phục mọi phiên bản. File được ghi qua file tạm rồi thay thế để tránh ghi dở, nhưng chưa có khóa cho nhiều tiến trình cùng ghi. Nếu sử dụng thực tế, cần bổ sung quyền truy cập và chính sách xóa thông tin người dùng.

## 5. Ba hướng bonus em lựa chọn

### Confidence threshold

Em đặt ngưỡng chấp nhận thông tin là 0.85. Phát biểu rõ về tên, nơi ở hoặc nghề được quy tắc cho điểm 0.95; sở thích và cách trả lời có điểm 0.90. Địa điểm tạm thời, như làm việc ở quán cà phê hôm nay, có điểm 0.60 nên không thay nơi ở lâu dài. Mục đích là giảm việc lưu nhầm chi tiết trong phiên thành thông tin bền vững.

Khi tăng ngưỡng lên 1.0 trong đối chứng, mọi candidate đều bị loại, memory bằng 0 bytes và recall chéo phiên về 0%. Kết quả cho thấy ngưỡng quá cao có thể làm mất thông tin cần nhớ. Điểm confidence hiện là điểm theo quy tắc, chưa phải xác suất đã hiệu chuẩn. Em chưa có tập gán nhãn riêng để khẳng định 0.85 là ngưỡng tối ưu.

### Trích xuất thông tin có cấu trúc

Mỗi field có `value`, `confidence`, `evidence` và `revision`. Các field gồm tên, nơi ở, nghề, sở thích, món ăn, đồ uống, thú cưng và cách trả lời. Cách lưu này giúp cập nhật đúng một field và tránh đưa toàn bộ hội thoại vào prompt. Chỉ các giá trị đã chấp nhận được đưa vào prompt; evidence phục vụ kiểm tra hồ sơ. Kiểm thử cập nhật lặp và kích thước file trong benchmark là bằng chứng cho việc hạn chế tăng trưởng memory.

Đánh đổi là schema và mẫu trích xuất chỉ bao phủ một phần ngôn ngữ tự nhiên, chủ yếu bằng tiếng Việt. Fact ngoài schema hoặc diễn đạt khác mẫu có thể không được lưu. Vì vậy, cấu trúc rõ giúp quản lý hồ sơ nhưng chưa bảo đảm nhận ra mọi thông tin người dùng.

### Xử lý thông tin mâu thuẫn

Với cùng một field, phát biểu mới được chấp nhận thay giá trị cũ. Hồ sơ cuối Standard giữ Huế và MLOps engineer; Stress giữ Đà Nẵng và MLOps engineer. Hà Nội đi họp và product manager trong câu đùa không ghi đè các giá trị này. Kiểm thử còn dùng Cần Thơ, Hải Phòng và data engineer, là các giá trị ngoài dataset, để kiểm tra quy tắc không chỉ xử lý đáp án của đề.

Rủi ro là phát biểu mới sai nhưng vượt ngưỡng vẫn có thể thay giá trị đúng. Một câu chỉ phủ định fact cũ mà không cung cấp giá trị thay thế chưa xóa field. Đây là các trường hợp cần cải thiện nếu phát triển tiếp. Em chưa triển khai memory decay; ba hướng trên là các bonus em chọn.

## 6. Bằng chứng kiểm chứng

Bộ kiểm thử hiện có 49 tests pass, gồm bốn hành vi bắt buộc: đọc/ghi/sửa hồ sơ, kích hoạt compact, recall chéo phiên và giảm prompt load so với Baseline. Benchmark mặc định có hai bảng, mỗi bảng hai dòng Baseline/Advanced và đủ sáu chỉ số. Cách chạy và các giới hạn được giải thích thêm trong [REPORT.md](REPORT.md).

Bài hỗ trợ sáu adapter: OpenAI, Custom, Gemini, Anthropic, Ollama và OpenRouter. OpenAI đã chạy đầy đủ hai suite qua API thật. OpenRouter đã chạy thành công cả hai suite, tổng 268 calls, sau khi thay key quản trị bằng key thông thường. Việc khởi tạo SDK cho các provider khác đã được kiểm tra, nhưng chưa có đủ key/server để khẳng định tất cả đã chạy qua mạng.
