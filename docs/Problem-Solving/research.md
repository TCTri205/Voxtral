# Báo cáo Đánh giá Chuyên sâu: Tính Khả thi và Chiến lược Triển khai Mô hình Voxtral-Mini-4B-Realtime-2602 trong Môi trường Tự Lưu trữ

Tài liệu này cung cấp một phân tích kỹ thuật và kiến trúc toàn diện nhằm đánh giá tính khả thi của các giải pháp tối ưu hóa hiệu suất Nhận dạng Giọng nói Tự động (ASR) đã được đề xuất trước đó, áp dụng cụ thể cho mô hình `mistralai/Voxtral-Mini-4B-Realtime-2602` khi triển khai trên hạ tầng tự lưu trữ (self-hosted). Thông qua việc đối chiếu các phương án đề xuất ban đầu với đặc tả kỹ thuật, cấu trúc mã nguồn, và tài liệu nghiên cứu mới nhất về kiến trúc streaming nội tại của mô hình, báo cáo sẽ chỉ ra những rào cản kỹ thuật cốt lõi. Từ đó, tài liệu đề xuất một cấu trúc triển khai thay thế ở cấp độ hệ thống nhằm giải quyết triệt để hiện tượng sụp đổ ngôn ngữ (**Language Collapse**), ngắt lời sớm (**Early Truncation**), và ảo giác chèn (**Insertion Hallucination**) mà không phá vỡ nguyên lý hoạt động của mô hình.

---

## 1. Nền tảng Kiến trúc của Voxtral-Mini-4B-Realtime-2602

Việc cố gắng áp dụng các kỹ thuật tiền xử lý và hậu xử lý của mô hình ASR ngoại tuyến (offline) truyền thống—như kiến trúc encoder-decoder của OpenAI Whisper—lên mô hình Voxtral-Mini-4B-Realtime-2602 thường dẫn đến những thất bại mang tính hệ thống. Để hiểu nguyên nhân gốc rễ của sự bất tương thích này, cần phải phân tích sâu vào kiến trúc thiết kế đột phá của hệ thống Voxtral Realtime.

### 1.1. Khung Mô hình hóa Luồng Trì hoãn (Delayed Streams Modeling)

Mô hình Voxtral-Mini-4B-Realtime-2602 không sử dụng cơ chế thu nhận toàn bộ tệp âm thanh rồi mới tiến hành dịch (batch processing) và cũng không sử dụng cơ chế chú ý chéo (cross-attention) truyền thống giữa bộ mã hóa và bộ giải mã.[^1] Thay vào đó, khối lượng tham số khoảng 4 tỷ được chia thành hai cấu phần chính hoạt động đồng bộ: một **Bộ mã hóa âm thanh (Audio Encoder)** với xấp xỉ 970 triệu tham số và một **Bộ giải mã ngôn ngữ (LLM Decoder)** dựa trên kiến trúc Ministral-3B với khoảng 3,4 tỷ tham số.[^3]

Điểm khác biệt cốt lõi nằm ở phương pháp **Mô hình hóa Luồng Trì hoãn (Delayed Streams Modeling - DSM)**. Trong kiến trúc này, bộ mã hóa âm thanh được huấn luyện lại từ đầu với cơ chế **chú ý nhân quả (causal attention)**, có nghĩa là tại bất kỳ thời điểm nào, mô hình chỉ được phép nhìn vào dữ liệu âm thanh trong quá khứ mà không được chờ đợi hoặc lấy bối cảnh từ dữ liệu tương lai.[^4] Điều này trái ngược hoàn toàn với Whisper, vốn là một mô hình hai chiều (bi-directional) cần bối cảnh của toàn bộ cửa sổ 30 giây để đưa ra dự đoán chính xác.[^6]

### 1.2. Cơ chế Đồng bộ Thời gian 80ms và Token Đệm

Luồng âm thanh đầu vào ở tần số lấy mẫu 16 kHz được hệ thống chuyển đổi thành phổ Mel (Mel Spectrogram) với 128 dải tần, sử dụng kích thước cửa sổ 25 mili-giây (ms) và bước nhảy 10 ms.[^7] Sau đó, một khối tích chập 1D (Convolutional Stem) sẽ giảm tốc độ lấy mẫu xuống 4 lần, tạo ra một luồng dữ liệu với tần số khung hình là 12,5 Hz. Đặc tính vật lý này thiết lập một hằng số bất biến trong toàn bộ kiến trúc: **đúng một token văn bản sẽ được ánh xạ với 80 ms âm thanh**.[^7]

Bộ giải mã LLM hoạt động đồng bộ chặt chẽ với luồng âm thanh này. Để duy trì tính liên tục của hệ thống streaming khi tín hiệu âm thanh chưa chứa thông tin ngữ nghĩa hoàn chỉnh (ví dụ: đang ở giữa một âm tiết kéo dài hoặc trong một khoảng lặng), hệ thống phát ra token đệm đặc biệt **`[P]` (Padding)**. Khi một từ kết thúc và thỏa mãn độ trễ mục tiêu, hệ thống phát ra token ranh giới từ ` ` (Word boundary), theo sau là các token subword tương ứng với từ đó.[^1] Mọi sự can thiệp từ bên ngoài làm phá vỡ nhịp điệu ánh xạ thời gian thực 80 ms này—chẳng hạn như việc tự ý cắt ghép âm thanh (chunking) hoặc thay đổi chiến lược lấy mẫu (sampling strategy)—đều sẽ làm hỏng bộ nhớ đệm nội tại (KV Cache) và gây ra sự sụp đổ của chuỗi tự hồi quy.

### 1.3. Quản lý Độ trễ Thông qua Adaptive RMS Norm

Một trong những cải tiến kỹ thuật quan trọng nhất của Voxtral Realtime là việc kiểm soát độ trễ thông qua cơ chế chuẩn hóa **Adaptive RMS Norm (Ada RMS-Norm)**.[^7] Thay vì cố định một mức độ trễ trong quá trình huấn luyện, kiến trúc cho phép người dùng điều chỉnh độ trễ phiên mã (transcription delay) một cách linh hoạt từ 80 ms lên đến 2,4 giây.[^2]

Về mặt toán học, mức độ trễ này được mã hóa dưới dạng một embedding thời gian (sử dụng hàm sin/cos dựa trên tần số nghịch đảo) và được chiếu qua một mạng nơ-ron đa lớp (MLP) nhỏ. Đầu ra của mạng này được sử dụng để điều biến (modulate) luồng dư (residual stream) bên trong bộ giải mã LLM ngay sau lớp chuẩn hóa FFN.[^6] Mức thiết lập lý tưởng được Mistral AI khuyến nghị mạnh mẽ là **480 ms**, tương đương với 6 token trễ. Tại độ trễ này, mô hình đạt được điểm cân bằng tối ưu giữa tốc độ phản hồi thời gian thực và độ chính xác, ghi nhận Tỷ lệ Lỗi Từ (WER) trung bình là 8.72% trên tập dữ liệu đa ngôn ngữ FLEURS (với tiếng Anh đạt 4.90% và tiếng Nhật đạt hiệu suất cạnh tranh với các hệ thống ngoại tuyến hàng đầu).[^2]

---

## 2. Thẩm định Tính Khả thi của Các Phương án Đề xuất Ban đầu

Dựa trên hiểu biết về kiến trúc Mô hình hóa Luồng Trì hoãn, các phương án tối ưu hóa hiệu suất được đề xuất trong tài liệu trước đây cần được thẩm định lại một cách nghiêm ngặt. Việc tự lưu trữ (self-hosting) mô hình tải về từ Hugging Face mang lại quyền kiểm soát toàn diện đối với luồng dữ liệu, nhưng đồng thời cũng phơi bày những giới hạn của các API bậc cao.

### 2.1. Đánh giá Phương án 1 & 2: Ép Ngôn ngữ (Language Hinting) và Sụp đổ Ngôn ngữ

Hiện tượng **sụp đổ ngôn ngữ (Language Collapse)**, khi mô hình tự động chuyển sang giải mã thành tiếng Anh do chất lượng âm thanh đầu vào kém (ví dụ file media_148414 đạt CER 100%), là một rủi ro hiện hữu. Phương án đề xuất trước đó là can thiệp vào tham số `language="ja"` trong `TranscriptionRequest` thông qua việc sửa đổi hàm `_run_inference_sync()` và sử dụng API của thư viện `mistral_common`.

> [!CAUTION]
> **Kết luận Thẩm định: Không khả thi ở cấp độ mô hình Streaming.**

Mặc dù mã nguồn của thư viện `mistral_common` cung cấp cấu trúc dữ liệu `TranscriptionRequest` cho phép truyền tham số `language` [^11], và bộ thực thi mô hình (model executor) của vLLM trong tệp `voxtral.py` cũng bao gồm logic nhận tham số này [^12], bề mặt API này thực chất được thiết kế để tương thích ngược với các mô hình ngoại tuyến như Voxtral Mini Transcribe V2.

Các kỹ sư cốt lõi tại Mistral AI đã xác nhận minh thị rằng kiến trúc Voxtral Realtime hiện tại **không hỗ trợ** chức năng gợi ý ngôn ngữ (language hint) thông qua chuỗi request.[^13] Nguyên nhân bắt nguồn từ thiết kế của Tokenizer và cơ chế streaming nhân quả. Tokenizer Tekken của mô hình realtime (với bộ từ vựng 131.072 token) không sử dụng các token bắt buộc để định hướng không gian ngữ nghĩa (như `<|ja|>` trong Whisper) ở đầu chuỗi nhằm tối ưu hóa độ trễ tính toán ngay lập tức.[^7] Do đó, việc truyền biến `language="ja"` qua `TranscriptionRequest` sẽ bị hệ thống bỏ qua ở lớp tensor.

### 2.2. Đánh giá Phương án 4: Chiến lược Phân mảnh Âm thanh (Chunking & Overlapping)

Để giải quyết vấn đề Ngắt lời sớm (Early Truncation) trên các tệp âm thanh dài (ví dụ file media_149291 kéo dài 156 giây), phương án đề xuất trước đó là cắt tệp thành các đoạn nhỏ (chunks) dựa trên VAD, có độ chồng lấp (overlap) 1-2 giây, xử lý độc lập và hợp nhất văn bản.

> [!WARNING]
> **Kết luận Thẩm định: Là một Anti-Pattern phá vỡ kiến trúc, hoàn toàn không khả thi.**

Việc áp dụng chiến lược cắt tệp rồi thực hiện suy luận độc lập sẽ phá vỡ hoàn toàn lợi thế kiến trúc của Voxtral Realtime. Sự giới hạn của kiến trúc mã hóa nhân quả (causal encoder) là mô hình cần thời gian để tích lũy ngữ cảnh âm học từ trạng thái khởi tạo. Cụ thể, bộ mã hóa âm thanh sử dụng Chú ý Cửa sổ Trượt (Sliding Window Attention) với kích thước cửa sổ lên đến 750 khung, trong khi bộ giải mã ngôn ngữ duy trì cửa sổ trượt 8192 token.[^7]

Mỗi khi một chunk mới được gửi đi dưới dạng một yêu cầu suy luận độc lập mới, hệ thống phải thực hiện lại toàn bộ quá trình điền trước (prefill) và tái tính toán trạng thái biên của khối tích chập 1D.[^7] Việc này mang lại hai hệ quả tai hại:

1. **Lãng phí chu kỳ GPU**: Chi phí khởi động (startup cost) cho mỗi lần gọi encoder độc lập là khoảng 50 ms. Việc chia nhỏ một tệp 60 giây thành hàng chục chunk sẽ làm tăng thời gian xử lý lên gấp 5 lần so với việc duy trì một luồng duy nhất.[^15]
2. **Mất mát Ngữ cảnh m học**: Ranh giới của các từ nằm ở điểm cắt bị mất đi, sự liên kết ngữ nghĩa giữa các câu bị phá vỡ, tạo ra ảo giác (hallucination) nghiêm trọng tại các điểm nối.

Cấu trúc của Voxtral Realtime về mặt lý thuyết cho phép mô hình xử lý một luồng âm thanh vô hạn (infinite streaming) mà không bao giờ gặp giới hạn chiều dài tuyệt đối.[^10] Tham số cấu hình `--max-model-len` mặc định trong vLLM được đặt ở mức 131.072 token, tương đương với khả năng duy trì một luồng hội thoại liên tục lên đến gần 3 giờ đồng hồ mà không cần bất kỳ sự can thiệp chunking nào.[^10]

### 2.3. Đánh giá Phương án 5: Tối ưu Lấy mẫu (Fallback Sampling qua Temperature)

Nhằm hạn chế ảo giác khi gặp nhiễu, một đề xuất phổ biến là áp dụng cơ chế Fallback (tái thử) bằng cách nâng chỉ số temperature từ `0.0` lên `0.2` khi văn bản trả về chứa ký tự lặp lại.

> [!IMPORTANT]
> **Kết luận Thẩm định: Gây hại nghiêm trọng đến sự đồng bộ luồng.**

Tài liệu chính thức và các khuyến nghị triển khai của Mistral AI cho kiến trúc Voxtral Realtime liên tục nhấn mạnh một quy tắc bất di bất dịch: **Luôn luôn thiết lập Temperature ở mức 0.0**.[^10]

Mô hình hóa Luồng Trì hoãn đòi hỏi mức độ chính xác tuyệt đối trong việc gắn kết giữa âm thanh vật lý và token văn bản theo chu kỳ 80 ms.[^1] Cơ chế tham lam (Greedy Decoding ở Temperature = 0.0) đảm bảo rằng tại bất kỳ thời điểm nào, xác suất lớn nhất luôn chi phối sự tồn tại của token đệm `[P]` hoặc ký tự có nghĩa. Việc kích hoạt tính năng lấy mẫu có điều kiện (`do_sample = True`, `temperature = 0.2`) sẽ mở ra sự ngẫu nhiên trong việc phân phối token.

---

## 3. Kiến trúc Triển khai Thay thế Tối ưu cho Môi trường Tự Lưu trữ

Từ những phân tích trên, rõ ràng việc sử dụng thư viện `transformers` với cơ chế sinh văn bản tuần tự (`model.generate`) và các kịch bản can thiệp biến môi trường cục bộ là không đủ để khai thác năng lực của Voxtral Realtime. Lộ trình tối ưu để thiết lập hạ tầng ASR tại chỗ (on-premise) đòi hỏi sự chuyển đổi từ mô hình xử lý chuỗi cắt đoạn (chunked batch) sang mô hình **kiến trúc hướng sự kiện thời gian thực (event-driven real-time architecture)**.

### 3.1. Máy chủ Suy luận vLLM: Trái tim của Hệ thống Streaming

Khung phục vụ (serving framework) `vLLM` là giải pháp duy nhất được Mistral AI hợp tác phát triển để cung cấp hỗ trợ cấp độ sản xuất (production-grade) cho mô hình Voxtral Realtime.[^10] vLLM giải quyết được thách thức lớn nhất của ASR thời gian thực: tiếp nhận dữ liệu đầu vào liên tục mà không cần tính toán lại toàn bộ ngữ cảnh.

Để làm được điều này, vLLM áp dụng kiến trúc **PagedAttention** với Bộ đệm KV không đồng nhất (Temporally Heterogeneous KV Caches). Hệ thống duy trì đồng thời hai bộ đệm KV độc lập—một cho bộ mã hóa âm thanh và một cho bộ giải mã ngôn ngữ—với tốc độ khung hình khác nhau.[^1]

#### Cấu hình Triển khai Máy chủ vLLM Tự Lưu trữ

Việc triển khai cần một GPU có dung lượng VRAM tối thiểu 16GB (ví dụ: NVIDIA T4, L4, hoặc A100) do mô hình sử dụng định dạng trọng số BF16 nguyên bản.[^10] Cấu hình khởi chạy tối ưu nhất:

```bash
VLLM_DISABLE_COMPILE_CACHE=1 vllm serve mistralai/Voxtral-Mini-4B-Realtime-2602 \
    --tokenizer-mode mistral \
    --config-format mistral \
    --load-format mistral \
    --trust-remote-code \
    --compilation-config '{"cudagraph_mode":"PIECEWISE"}' \
    --tensor-parallel-size 1 \
    --max-model-len 45000 \
    --max-num-batched-tokens 8192 \
    --max-num-seqs 16 \
    --gpu-memory-utilization 0.90 \
    --host 0.0.0.0 --port 8000
```

**Phân tích các Tham số Kỹ thuật Quan trọng:**

* `VLLM_DISABLE_COMPILE_CACHE=1`: Cực kỳ quan trọng để ngăn chặn quá trình biên dịch bộ đệm thừa gây lỗi khởi động.[^10]
* `cudagraph_mode: PIECEWISE`: Bắt buộc đối với mô hình Voxtral Realtime để duy trì tốc độ phát token >12.5 tok/s.[^10]
* `--max-model-len 45000`: Giảm giới hạn này xuống 45.000 (tương đương 1 giờ âm thanh) giúp giải phóng VRAM, cải thiện thông lượng (throughput).[^10]

---

## 4. Tích hợp Voice Activity Detection (VAD) và Quản lý Ảo giác

Hiện tượng **Ảo giác Chèn (Insertion Hallucination)** với tỷ lệ cao, khi mô hình nỗ lực chuyển đổi tiếng ồn của quạt gió hay các khoảng lặng dài thành các câu hội thoại không có thực, là một hệ quả tất yếu của mô hình có tính đồng bộ thời gian chặt chẽ (time-synchronous) không có ngưỡng cắt nhiễu nội tại.

### Kiến trúc Tích hợp Silero VAD tại Gateway

Đề xuất đưa Silero VAD làm bộ lọc tiền xử lý (pre-processing filter) là một giải pháp đúng đắn. Tuy nhiên, thay vì tích hợp VAD thành một quy trình cắt-dán cứng trong máy chủ giống như cơ chế xử lý ngoại tuyến, VAD cần được triển khai như một Máy trạng thái (State Machine) điều phối luồng tại lớp Ingress Gateway.

Silero VAD là một mô hình mạng nơ-ron cực nhẹ (~2MB), hoạt động ở mức hiệu suất cực cao, có thể đánh giá xác suất giọng nói trên các khối âm thanh 32 ms trong thời gian dưới 1 ms trên một luồng CPU duy nhất.[^19] Việc đặt Silero VAD ở biên (edge) của Gateway mang lại sự linh hoạt tuyệt đối: nó cho phép chặn đứng âm thanh rác trước khi băng thông bị lãng phí và trước khi các tài nguyên GPU đắt đỏ bị huy động.[^21]

### Thiết kế Máy Trạng thái (State Machine) VAD cho WebSocket

Gateway sẽ duy trì một vòng lặp liên tục, đọc dữ liệu âm thanh PCM 16kHz từ luồng đầu vào, chuyển qua Silero VAD để lấy giá trị `speech_prob`, và ra quyết định tương tác với vLLM WebSocket dựa trên các trạng thái sau:

| Trạng thái VAD | Điều kiện Kích hoạt | Hành động của Ingress Gateway đối với vLLM WebSocket API |
| :--- | :--- | :--- |
| **STATE_SILENCE** | `speech_prob < 0.5` | Bỏ qua dữ liệu âm thanh. Không gửi bất kỳ byte nào qua kết nối WebSocket. |
| **STATE_SPEECH_START** | `speech_prob >= 0.5` liên tục trong 250 ms | Mở một kết nối WebSocket mới. Gửi lệnh `session.update`. Thực hiện "Mồi Âm thanh Định hướng Ngôn ngữ". |
| **STATE_SPEECH_ACTIVE** | `speech_prob >= 0.5` | Băm dữ liệu PCM 16kHz thành base64 và gửi qua lệnh `input_audio_buffer.append`. |
| **STATE_SHORT_PAUSE** | `speech_prob < 0.5` (< 800 ms) | Tiếp tục nạp các khung âm thanh chứa khoảng lặng ngắn. Mô hình sẽ xuất token đệm `[P]`. |
| **STATE_SPEECH_END** | `speech_prob < 0.5` (> 800 ms) | Ngừng gửi âm thanh. Phát lệnh `input_audio_buffer.commit`. Kết thúc phiên làm việc. |

---

## 5. Chiến lược Giải quyết Sập Ngôn ngữ (Language Collapse)

Dựa trên nguyên lý của **Causal Audio Encoder**, tại trạng thái `STATE_SPEECH_START` của Ingress Gateway, trước khi bất kỳ byte âm thanh nào của người dùng được đẩy vào, Gateway sẽ chủ động chèn một **"tệp mồi" (warm-up audio file)**.

Như đã chứng minh ở phần trước, API TranscriptionRequest không hỗ trợ tham số language đối với mô hình realtime.[^13] Các cơ chế Bias Ngữ cảnh (Context Biasing) thông qua văn bản (ví dụ: cung cấp danh sách 100 từ vựng cho các thuật ngữ chuyên ngành) chỉ được hỗ trợ chính thức trên các mô hình ngoại tuyến như Voxtral Mini Transcribe V2, và việc thử nghiệm trên mô hình realtime thường không mang lại hiệu ứng khóa ngôn ngữ mạnh mẽ.[^22]

### Cơ chế Mồi Âm thanh (Audio Prompting)

1. **Chuẩn bị Tệp Mồi**: Tạo một tệp âm thanh PCM 16kHz, độ dài khoảng 1.0 - 1.5 giây, chứa một câu nói tiếng Nhật rõ ràng (ví dụ: *"はい、お電話ありがとうございます"*).
2. **Quy trình Bơm (Injection)**: Khi thiết lập kết nối, Gateway gửi tệp mồi này qua lệnh `input_audio_buffer.append` đầu tiên.
3. **Che giấu Đầu ra (Output Masking)**: Bỏ qua đoạn văn bản phản hồi đầu tiên tương ứng với tệp mồi.
4. **Hiệu ứng**: Mô hình sẽ coi tệp mồi và giọng nói người dùng là một luồng hội thoại liên tục. Do đã được "khởi động" bằng tiếng Nhật rõ ràng, mô hình sẽ ép buộc việc giải mã bám sát theo tiếng Nhật thay vì sụp đổ về tiếng Anh.

---

## 6. Tổng kết Lộ trình Triển khai và Kỳ vọng Hiệu suất

| Vấn đề Gốc rễ (Root Cause) | Giải pháp Triển khai Tối ưu cho Tự Lưu trữ | Hiệu quả Kỳ vọng |
| :--- | :--- | :--- |
| **Sụp đổ Ngôn ngữ** (nhiễu) | Áp dụng kỹ thuật **Mồi Âm thanh Khởi tạo** (Audio Prompting) tại lớp Gateway. | Chấm dứt CER 100%. Mô hình bị khóa vào không gian tiếng Nhật. |
| **Ảo giác Chèn** (không có ngưỡng cắt) | Triển khai **Silero VAD** như một Máy trạng thái tại lớp Gateway. | Triệt tiêu 100% ảo giác trên các đoạn tĩnh lặng. Tiết kiệm GPU. |
| **Ngắt lời Sớm** và Lỗi Phân mảnh | Sử dụng API **WebSocket /v1/realtime** của vLLM với Resumable Requests. | Dịch luồng vô hạn mà không mất ngữ cảnh. Xóa bỏ hiện tượng cắt đột ngột. |
| **Lặp Vòng** (do Fallback) | Duy trì **temperature=0.0** để bảo vệ đồng bộ thời gian 80ms của DSM. | Cùng với VAD, mô hình sẽ không bao giờ rơi vào vòng lặp vô tận. |

---

## Nguồn trích dẫn

[^1]: [Voxtral Realtime - arXiv](https://arxiv.org/html/2602.11298v3)
[^2]: [From Sound to Text in Real-Time: Understanding Voxtral Realtime](https://kshreyas.dev/post/voxtral-realtime/)
[^3]: [mlx-community/Voxtral-Mini-4B-Realtime-2602-4bit - Hugging Face](https://huggingface.co/mlx-community/Voxtral-Mini-4B-Realtime-2602-4bit)
[^4]: [From Whisper to Voxtral... - Medium](https://medium.com/@albertogontras/from-whisper-to-voxtral-the-new-architecture-of-real-time-voice-ai-e140c01ddab3)
[^6]: [Voxtral Realtime - arXiv (v1)](https://arxiv.org/html/2602.11298v1)
[^7]: [mistralai/Voxtral-Mini-4B-Realtime-2602 Discussions - Hugging Face](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602/discussions/17)
[^10]: [mistralai/Voxtral-Mini-4B-Realtime-2602 - Hugging Face Model Card](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602)
[^11]: [Speech-to-Text Support - vLLM Docs](https://docs.vllm.ai/en/latest/contributing/model/transcription/)
[^12]: [voxtral - vLLM API Docs](https://docs.vllm.ai/en/latest/api/vllm/model_executor/models/voxtral/)
[^13]: [Hints for language Discussion - Hugging Face](https://huggingface.co/mistralai/Voxtral-Mini-4B-Realtime-2602/discussions/19)
[^15]: [Pure C inference of Mistral Voxtral Realtime - GitHub](https://github.com/antirez/voxtral.c)
