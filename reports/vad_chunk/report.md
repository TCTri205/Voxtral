# Báo cáo Phân tích VAD & Chunking - Voxtral ASR (05/05/2026)

## 1. Tổng quan bộ benchmark

Báo cáo này tổng hợp kết quả từ 3 lần chạy benchmark trong cùng một bộ thử nghiệm ngày **05/05/2026**: `05-05-2026_v1`, `05-05-2026_v2`, `05-05-2026_v3`. Các thư mục `v1`, `v2`, `v3` là **các lần chạy**, không nên hiểu là 3 phiên bản model độc lập.

Nguồn đối chiếu:
- `results/05-05-2026_v*/results.json`
- `results/05-05-2026_v*/llm_eval_summary.json`
- `results/05-05-2026_v*/llm_eval_details.csv`
- `benchmarks/benchmark_20260505_100900.json`

| Run | Avg CER | Hallucination Rate | Avg Inference RTF | Avg Total RTF | Ghi chú |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `v1` | 39.63% | 90.91% | 1.920 | 1.945 | Baseline của bộ chạy ngày 05/05/2026 |
| `v2` | 38.46% | 90.91% | 1.887 | 1.908 | CER và high severity speech tốt hơn `v1` |
| `v3` | 37.10% | 81.82% | 1.895 | 1.920 | Hallucination rate tổng thấp nhất, nhưng có rủi ro deletion |

Kết luận tổng quan cần đọc thận trọng: `v3` có Avg CER và hallucination rate tổng tốt nhất, nhưng kết quả này đi kèm việc `media_148393` trả transcript rỗng (`N/A (Empty)`), nên không thể coi `v3` là tối ưu tuyệt đối về chất lượng nhận diện speech.

## 2. Phân tích VAD

### 2.1. Silence và noise

VAD/pipeline xử lý đúng 2 file không có speech hữu ích:

| File | v1 transcript | v2 transcript | v3 transcript | CER | Nhận xét |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `silence_60s.wav` | Rỗng | Rỗng | Rỗng | 0.00% | ASR đúng, nhưng LLM evaluator gán nhầm `silence_text/high` |
| `stochastic_noise_60s.wav` | Rỗng | Rỗng | Rỗng | 0.00% | Không bị hallucination trong cả 3 lần chạy |

Do đó lỗi hallucination trên `silence_60s.wav` là lỗi đánh giá tự động, không phải lỗi ASR. Các báo cáo LLM cần tách trường hợp file kỳ vọng không có speech và transcript rỗng thành `none`.

### 2.2. Hallucination và deletion

Phân bố severity từ `llm_eval_summary.json`:

| Run | none | medium | high | High trên 9 speech files |
| :--- | :---: | :---: | :---: | :---: |
| `v1` | 1 | 5 | 5 | 4/9 |
| `v2` | 1 | 7 | 3 | 2/9 |
| `v3` | 2 | 5 | 4 | 3/9 |

`v2` là run giảm high severity speech tốt nhất. `v3` là run duy nhất giảm tổng số file bị hallucination từ 10/11 xuống 9/11, chủ yếu vì `media_148393` chuyển từ transcript có insertion sang transcript rỗng.

Trường hợp cần chú ý:
- `media_148393`: `v1/v2` có CER `47.87%` và lỗi insertion `頑張りましょう`; `v3` trả transcript rỗng và CER `N/A (Empty)`. Đây là dấu hiệu deletion hoặc lọc speech quá mạnh, không phải cải thiện chất lượng nội dung.
- `media_149733`: CER tăng từ `56.13%` ở `v2` lên `60.43%` ở `v3`; `v3` có lặp cụm `という状態でしょうか` và vẫn có nhiều substitution/insertion.

Hiện không có log trong `results/05-05-2026_v*` xác nhận tham số VAD cụ thể của từng run. Vì vậy các nhận định như `v3` tăng `VAD_THRESHOLD` hoặc tăng `VAD_MIN_SPEECH_DURATION_MS` chỉ nên xem là giả thuyết từ output, không phải sự thật đã chứng minh.

## 3. Phân tích chunking và hiệu năng

Cơ chế chunking giữ overhead thấp trong cả 3 run:

| Run | Avg Total RTF | Avg Inference RTF | Overhead ước tính |
| :--- | :---: | :---: | :---: |
| `v1` | 1.945 | 1.920 | 0.025 |
| `v2` | 1.908 | 1.887 | 0.021 |
| `v3` | 1.920 | 1.895 | 0.025 |

Chênh lệch giữa total RTF và inference RTF chỉ khoảng `0.02-0.03`, cho thấy overhead của chia chunk, gửi dữ liệu và merge transcript thấp so với thời gian inference.

Các lỗi chính trong `llm_eval_details.csv` vẫn là insertion, substitution và language collapse. Chưa có bằng chứng rộng cho thấy lỗi chủ đạo nằm ở điểm nối chunk. Tuy nhiên `media_149733` ở `v3` có lặp cụm `という状態でしょうか`, nên merge/overlap vẫn cần được kiểm tra riêng trên các file dài.

## 4. Vấn đề tồn tại

### 4.1. Language collapse

Một số file vẫn bị chèn tiếng Anh không liên quan:
- `media_148414`: chèn `Hi, Joseph. How are you? I'm sorry.`
- `media_149291`: còn dấu hiệu chèn `Just the Asaga`

Vấn đề này xuất hiện qua nhiều run, nên nhiều khả năng không chỉ do VAD/chunking mà còn liên quan đến bias nội tại của model hoặc decoding.

### 4.2. Phonetic substitution và contextual insertion

Các lỗi nhầm âm/từ trong tiếng Nhật vẫn lặp lại:
- `お世話になっております` bị nhận thành biến thể sai nghĩa trong `media_148280`.
- `トウノ` bị nhận thành `トモノ`, `シカズ` thành `シャズ` hoặc `ショウズ` trong `media_149733`.
- Một số cụm hội thoại như `頑張りましょう`, `今日返しました`, `お疲れ様です` bị thêm khi không có trong GT.

### 4.3. Evaluator

LLM evaluator đang gán `silence_60s.wav` là `silence_text/high` dù transcript rỗng và CER `0.00%`. Cần sửa prompt hoặc rule hậu xử lý để file kỳ vọng không có speech và transcript rỗng được đánh giá là `none`.

## 5. Khuyến nghị

- Không chọn `v3` làm cấu hình production mặc định chỉ dựa trên Avg CER hoặc hallucination rate tổng; cần xử lý rủi ro deletion trên `media_148393`.
- Nếu ưu tiên giảm high severity trên speech, `v2` là điểm tham chiếu tốt hơn `v3` trong bộ chạy này.
- Nếu ưu tiên không sinh chữ trên noise/silence, cả 3 run đều đạt yêu cầu ở output ASR; lỗi còn lại nằm ở evaluator.
- Cần bổ sung log cấu hình runtime vào mỗi run, ít nhất gồm `VAD_THRESHOLD`, `VAD_PADDING_MS`, `CHUNK_OVERLAP_SEC`, các ngưỡng min/max speech/silence nếu có, để các báo cáo sau không phải suy luận nguyên nhân từ transcript.

---
**Người báo cáo:** Voxtral Audit Agent  
**Ngày:** 05/05/2026
