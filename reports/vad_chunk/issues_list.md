# Danh sách vấn đề tồn tại - Voxtral ASR (05/05/2026)

Tài liệu này liệt kê các lỗi kỹ thuật được xác nhận sau khi đối chiếu 3 lần chạy trong cùng bộ benchmark `05-05-2026_v1`, `05-05-2026_v2`, `05-05-2026_v3`. Đây là danh sách vấn đề của bộ chạy ngày 05/05/2026, không phải so sánh giữa 3 phiên bản model độc lập.

## 1. Evaluator đánh nhầm file silence

`silence_60s.wav` có transcript rỗng trong cả 3 lần chạy và CER `0.00%`, nhưng LLM evaluator vẫn gán:

| Run | has_hallucination | primary_error | severity |
| :--- | :---: | :--- | :--- |
| `v1` | True | `silence_text` | high |
| `v2` | True | `silence_text` | high |
| `v3` | True | `silence_text` | high |

Đây là lỗi evaluator. Với file silence, trường hợp kỳ vọng không có speech và transcript rỗng phải là `none`, không phải hallucination.

## 2. Deletion hoặc lọc speech quá mạnh

`media_148393_1767860211615 (1).mp3` là case rủi ro cao nhất của `v3`:

| Run | Transcript | CER | LLM severity |
| :--- | :--- | :---: | :---: |
| `v1` | Có nội dung, nhưng thêm `頑張りましょう` | 47.87% | medium |
| `v2` | Có nội dung, nhưng thêm `頑張りましょう` | 47.87% | medium |
| `v3` | Rỗng | N/A (Empty) | none |

Evaluator xem `v3` là `none`, nhưng theo góc nhìn ASR đây là deletion hoặc failure nếu file có speech hợp lệ. Không nên xem case này là cải thiện hallucination sạch hoàn toàn nếu chưa xác minh audio/GT.

Nguyên nhân cụ thể chưa được xác nhận vì log của các run không ghi tham số VAD runtime. Có thể liên quan đến cấu hình lọc speech aggressive hơn, nhưng đây chỉ là giả thuyết.

## 3. Language collapse

Mô hình vẫn chèn tiếng Anh không liên quan vào transcript tiếng Nhật:

| File | Run bị ảnh hưởng | Dẫn chứng |
| :--- | :--- | :--- |
| `media_148414` | `v1`, `v2`, `v3` | `Hi, Joseph. How are you? I'm sorry.` |
| `media_149291` | `v1`, `v3` | `Just the Asaga` và các cụm tiếng Anh không thuộc GT |

Vì lỗi xuất hiện qua nhiều run, VAD/chunking nhiều khả năng không phải nguyên nhân duy nhất. Cần xem xét model bias, decoding hoặc post-processing theo ngôn ngữ.

## 4. Phonetic substitution

Mô hình nhầm các cụm tiếng Nhật có âm gần nhau, đặc biệt là tên riêng và cụm business:

| GT | Hyp | File | Ghi chú |
| :--- | :--- | :--- | :--- |
| `お世話になっております` | biến thể sai nghĩa như `お茶になっております` | `media_148280` | Lỗi business phrase ổn định |
| `アセットジャパン` | `アセプトジャパン` | `media_148954` | Sai tên thương hiệu |
| `トウノ` | `トモノ` | `media_149733` | Sai tên riêng |
| `シカズ` | `シャズ` / `ショウズ` | `media_149733` | Sai tên riêng |

Nhóm lỗi này cần xử lý bằng post-processing, glossary, domain LM hoặc ràng buộc decoding; VAD/chunking khó giải quyết triệt để.

## 5. Contextual insertion

Mô hình thêm cụm hội thoại phổ biến dù không có trong GT:

- `頑張りましょう` trong `media_148393` ở `v1/v2`.
- `今日返しました` trong `media_149733`.
- Một số cụm chào hỏi hoặc xác nhận ngữ cảnh bị thêm vào transcript dài.

Đây là dạng over-predict theo ngữ cảnh hội thoại, làm tăng CER và gây rủi ro sai nghĩa.

## 6. Merging/Repetition trên file dài

`media_149733` ở `v3` có dấu hiệu lặp cụm:

- Hypothesis chứa `という状態でしょうか?という状態でしょうか`.
- CER của file này tăng từ `56.13%` ở `v2` lên `60.43%` ở `v3`.
- Severity tăng từ `medium` ở `v2` lên `high` ở `v3`.

Đây là bằng chứng cần kiểm tra thêm phần overlap/merge hoặc điểm cắt chunk trên file dài. Tuy nhiên chưa đủ bằng chứng để kết luận merge là nguyên nhân chính của toàn bộ lỗi.

## 7. Hiệu năng và latency

RTF trung bình vẫn cao hơn real-time:

| Run | Avg Inference RTF | Avg Total RTF |
| :--- | :---: | :---: |
| `v1` | 1.920 | 1.945 |
| `v2` | 1.887 | 1.908 |
| `v3` | 1.895 | 1.920 |

Overhead ngoài inference thấp, nhưng tốc độ inference vẫn khoảng `1.9x` thời lượng audio. Nếu mục tiêu là streaming real-time, cần tối ưu model/runtime riêng.

## 8. Thiếu log cấu hình runtime

Các file `log_debug.txt` chỉ ghi danh sách file, RTF và trạng thái hoàn tất. Chúng không ghi các tham số như:

- `VAD_THRESHOLD`
- `VAD_PADDING_MS`
- `CHUNK_OVERLAP_SEC`
- min/max speech duration nếu pipeline có dùng
- min silence duration hoặc silence split threshold

Thiếu dữ liệu này làm báo cáo chỉ có thể suy luận nguyên nhân VAD từ output. Các benchmark tiếp theo nên ghi snapshot cấu hình vào `results.json` hoặc `log_debug.txt`.

---
**Người tổng hợp:** Voxtral Audit Agent  
**Ngày lập:** 05/05/2026
