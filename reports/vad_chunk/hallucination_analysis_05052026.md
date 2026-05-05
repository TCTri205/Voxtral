# Phân tích Hallucination - Voxtral ASR (05/05/2026)

## 1. Nguồn dữ liệu

Phân tích này chỉ dùng 3 lần chạy thuộc cùng bộ benchmark ngày **05/05/2026**:

- `results/05-05-2026_v1`
- `results/05-05-2026_v2`
- `results/05-05-2026_v3`

Mỗi run gồm 11 file: 9 file speech có GT timestamped và 2 file không có speech hữu ích (`silence_60s.wav`, `stochastic_noise_60s.wav`).

## 2. Tần suất hallucination

| Run | Total files | Hallucination rate | Error distribution | Severity distribution |
| :--- | :---: | :---: | :--- | :--- |
| `v1` | 11 | 90.91% | insertion: 9, silence_text: 1, none: 1 | medium: 5, high: 5, none: 1 |
| `v2` | 11 | 90.91% | insertion: 9, silence_text: 1, none: 1 | medium: 7, high: 3, none: 1 |
| `v3` | 11 | 81.82% | insertion: 8, silence_text: 1, none: 2 | medium: 5, high: 4, none: 2 |

`v3` giảm hallucination rate tổng từ `90.91%` xuống `81.82%`. Tuy nhiên phần giảm này đến từ `media_148393` trả transcript rỗng, nên cần phân biệt giữa “giảm hallucination” và “mất nội dung speech”.

## 3. High severity trên speech files

Nếu loại 2 file silence/noise và chỉ xét 9 speech files:

| Run | High severity speech files | Tỷ lệ |
| :--- | :---: | :---: |
| `v1` | 4/9 | 44.4% |
| `v2` | 2/9 | 22.2% |
| `v3` | 3/9 | 33.3% |

Theo tiêu chí high severity trên speech, `v2` tốt hơn `v3`. Theo tiêu chí hallucination rate tổng, `v3` tốt hơn. Hai kết luận này không mâu thuẫn vì chúng đo hai khía cạnh khác nhau.

## 4. File rủi ro cao

| File | v1 | v2 | v3 | Nhận xét |
| :--- | :--- | :--- | :--- | :--- |
| `media_148414` | high | high | high | Language collapse ổn định, chèn tiếng Anh |
| `media_148439` | high | high | high | Insertion/contextual hallucination |
| `media_149733` | high | medium | high | `v3` lặp `という状態でしょうか`, CER xấu hơn `v2` |
| `media_149291` | high | medium | medium | `v2/v3` giảm severity, nhưng vẫn còn insertion |
| `media_148393` | medium | medium | none | `v3` rỗng, cần xem là deletion risk |

## 5. Silence và noise

| File | v1 | v2 | v3 | Kết luận |
| :--- | :--- | :--- | :--- | :--- |
| `silence_60s.wav` | `silence_text/high` | `silence_text/high` | `silence_text/high` | Lỗi evaluator vì transcript rỗng là đúng |
| `stochastic_noise_60s.wav` | none | none | none | ASR/VAD xử lý đúng, không sinh chữ |

Output ASR cho cả 2 file đều rỗng và CER `0.00%`. Vì vậy không nên tính `silence_60s.wav` là hallucination thật khi đánh giá chất lượng ASR.

## 6. Nhận định chính

- `v3` có Avg CER thấp nhất (`37.10%`) và hallucination rate tổng thấp nhất (`81.82%`), nhưng có deletion risk rõ ràng ở `media_148393`.
- `v2` có high severity speech thấp nhất (`2/9`), nên là run cân bằng hơn nếu ưu tiên giảm lỗi nghiêm trọng trên speech.
- Language collapse và phonetic substitution vẫn tồn tại qua nhiều run, cho thấy VAD/chunking không đủ để xử lý toàn bộ lỗi hallucination.
- Không có bằng chứng log xác nhận `v3` dùng threshold VAD cao hơn. Mọi kết luận về tham số VAD cụ thể cần được ghi là giả thuyết, trừ khi có thêm snapshot config/runtime.

## 7. Khuyến nghị

- Sửa evaluator để file kỳ vọng không có speech và transcript rỗng được đánh giá là `none`.
- Không dùng hallucination rate tổng làm tiêu chí duy nhất; cần thêm metric deletion/empty-on-speech.
- Thêm log cấu hình runtime vào từng run để xác nhận nguyên nhân khi kết quả thay đổi.
- Kiểm tra riêng `media_149733` bằng trace chunk/overlap để xác định việc lặp cụm có đến từ merge hay từ decoding.

---
**Người báo cáo:** Voxtral Audit Agent  
**Ngày:** 05/05/2026
