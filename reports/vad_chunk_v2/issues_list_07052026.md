# Danh sách vấn đề tồn tại - Voxtral ASR (07/05/2026)

Dựa trên kết quả benchmark từ 3 lần chạy `v1`, `v2`, `v3` ngày 07/05/2026, các vấn đề kỹ thuật được phân loại như sau:

## 1. Lỗi Hallucination & Insertions (Nghiêm trọng)

Đây là nhóm lỗi phổ biến nhất (Hallucination Rate 81.82%), gây ảnh hưởng trực tiếp đến độ tin cậy của bản dịch.

### 1.1. Language Collapse (Chèn tiếng Anh)
Hệ thống tự ý chèn các câu tiếng Anh không có trong âm thanh gốc, thường xuất hiện ở đoạn đầu hoặc cuối chunk.
- **Ví dụ:** `media_148414` bị chèn `"Hi, Joseph. How are you? I'm sorry."` hoặc `"Hi, Joseph. I'm sorry."`
- **Ví dụ:** `media_149291` bị chèn `"Just the Asaga."`

### 1.2. Social/Phonetic Insertion (Chèn câu xã giao)
Các cụm từ tiếng Nhật mang tính chất khuôn mẫu (formulaic expressions) bị chèn vào dù không có trong Ground Truth (GT).
- **Cụm từ lặp lại:** `頑張りましょう` (Cùng cố gắng nào), `お疲れ様です` (Anh/chị đã vất vả rồi), `お茶になっております` (Đang uống trà - thực tế thường là nhầm của `お世話になっております`).
- **Tần suất:** Xuất hiện trong hầu hết các file speech (`media_148280`, `media_148393`, `media_148394`).

### 1.3. Contextual Hallucination (Nội dung giả tưởng)
Hệ thống tự suy diễn các thông tin chi tiết như tên người, chức danh hoặc ngày tháng không chính xác.
- **Ví dụ:** `media_148439` tự thêm `"こんにちは、ワイアンコープのシーケーションの坂本です。"`
- **Ví dụ:** `media_149733` chèn thêm thông tin ngày tháng sai lệch `"1月19日に..."`

## 2. Độ ổn định của hệ thống (System Stability)

### 2.1. Tính không nhất quán (Non-determinism)
Cùng một cấu hình VAD và file âm thanh nhưng kết quả trả về khác nhau đáng kể giữa các run.
- **Trường hợp điển hình:** `media_148284` có CER biến thiên từ **58.46%** (v1/v2) xuống còn **34.62%** (v3). Sự khác biệt nằm ở việc có hay không có đoạn insertion `"そうですね"`.

### 2.2. Biến thiên Severity
Mức độ nghiêm trọng của lỗi không ổn định:
- Run `v2` giảm được số ca "High Severity" xuống còn 2, nhưng `v1` và `v3` lại vọt lên 4 ca. Điều này cho thấy hệ thống có rủi ro tạo ra lỗi nặng một cách ngẫu nhiên.

## 3. Chất lượng nhận diện (Accuracy Issues)

### 3.1. Phonetic Substitution (Nhầm âm)
- Nhầm lẫn các tên riêng hoặc thuật ngữ kỹ thuật có âm gần giống nhau.
- **Ví dụ:** `アセットジャパン` (Asset Japan) bị nhận thành `アセプトジャパン` (Asept Japan) trong `media_148954`.
- **Ví dụ:** `トウノ` (Touno) bị nhận thành `トモノ` (Tomono) trong `media_149733`.

### 3.2. Lỗi lặp từ (Word Repetition) - Phân tích chuyên sâu
Dựa trên phân tích kỹ thuật các file `media_148280` và `media_148414` qua 3 phiên bản test (v1, v2, v3), chúng tôi xác định:

**Kết luận: Lỗi chủ yếu do Decoding/Model (Hallucination), không phải do logic ghép Chunk.**

*   **Trường hợp `media_148280`:** 
    *   **Hiện tượng:** Cụm từ `お世話になっております` (hoặc biến thể sai `お茶になっております`) xuất hiện nhiều lần.
    *   **Phân tích:** Ground Truth (GT) thực tế cũng có 3 lời chào xã giao liên tiếp. ASR nhận diện sai từ nhưng giữ đúng cấu trúc lặp lại của âm thanh gốc. Đây là lỗi **Substitution** (thế từ), không phải lỗi lặp từ do hệ thống.
*   **Trường hợp `media_148414` (v2):**
    *   **Hiện tượng:** `伊藤でございます。伊藤でございます` (Lặp lại 2 lần trong khi GT chỉ có 1).
    *   **Phân tích:** 
        *   Kết quả này **không nhất quán** (v1 và v3 chỉ xuất hiện 1 lần) mặc dù các đoạn cắt VAD hoàn toàn giống hệt nhau.
        *   Điều này chứng tỏ model bị hiện tượng **Looping Hallucination** trong quá trình decoding tại một số thời điểm không ổn định.
        *   Logic ghép chunk hiện tại (`_merge_chunk_transcripts`) sử dụng `_exact_overlap_chars` chỉ xử lý các đoạn khớp chính xác 100%. Nếu model produce văn bản hơi khác nhau ở phần overlap (ví dụ có thêm dấu chấm), logic này sẽ không cắt được và gây lặp. Tuy nhiên, với padding 200ms hiện tại, khả năng lặp cả cụm từ dài do chunking là rất thấp.

**Khuyến nghị:** 
1. Tập trung xử lý bằng **Post-processing filter** để loại bỏ các cụm từ xã giao lặp lại liên tiếp (Deduplication).
2. Không nên cố gắng tinh chỉnh VAD để sửa lỗi này vì gốc rễ nằm ở sự không ổn định của model weights/decoding.

## 4. Tổng kết rủi ro

| Vấn đề | Mức độ | Nguyên nhân dự kiến |
| :--- | :---: | :--- |
| Hallucination (English/Social) | **Cao** | Model bias hoặc VAD noise leakage |
| Non-determinism | **Trung bình** | Nhiễu trong quá trình Decoding của ASR |
| Phonetic Substitution | **Trung bình** | Hạn chế về từ vựng (Vocabulary) của model |
| Overhead/Performance | **Thấp** | Cơ chế chunking đã tối ưu (Overhead ~0.02 RTF) |

---
**Người tổng hợp:** Voxtral Audit Agent
**Tài liệu tham chiếu:** `results/07-05-2026_v*`
