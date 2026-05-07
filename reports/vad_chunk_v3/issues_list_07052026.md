# Danh sách vấn đề tồn tại - Voxtral ASR (07/05/2026)

Dựa trên kết quả benchmark từ 2 lần chạy `v4`, `v5` ngày 07/05/2026, các vấn đề kỹ thuật được phân loại như sau:

## 1. Lỗi Hallucination & Insertions (Nghiêm trọng)

Đây là nhóm lỗi phổ biến nhất (Hallucination Rate 81.82%), gây ảnh hưởng trực tiếp đến độ tin cậy của bản dịch.

### 1.1. Language Collapse (Chèn tiếng Anh)
Hệ thống tự ý chèn các câu tiếng Anh không có trong âm thanh gốc, thường xuất hiện ở đoạn đầu hoặc cuối chunk.
- **Ví dụ:** `media_148414` bị chèn `"Hi, Joseph. How are you? I'm sorry."` (CER 55.61%, High Severity)
  - Gây ra `hallucination_warning: true` trong VAD result
  - `lang_collapse_retries` status: **failed** - cơ chế phục hồi không hiệu quả

### 1.2. Context Collapse (Chèn ngữ cảnh)
Hệ thống tự suy diễn các thông tin chi tiết sai lệch:
- **Ví dụ:** `media_148439` tự thêm `"こんにちは、ワイアンコープのシーケーションの坂本です。"` (High Severity, CER 31.73%)
- **Ví dụ:** `media_149733` chèn thông tin ngày tháng sai `"1月19日に..."` (Medium Severity, CER 42.94%)

### 1.3. Social/Phonetic Insertion (Chèn câu xã giao)
Các cụm từ tiếng Nhật mang tính chất khuôn mẫu bị chèn vào dù không có trong Ground Truth:
- **Cụm từ lặp lại:** `お茶になっております` (được chèn trong `media_148280`), `お疲れ様です` (trong `media_148394`), `頑張りましょう` (trong `media_148393`)
- Tần suất: Xuất hiện trong gần đây các file speech

## 2. Vấn đề Language Collapse Recovery

### 2.1. Tỷ lệ thành công
- **Tổng số retry:** 11 lần
- **Thành công:** 8 lần (72.7%)
- **Thất bại:** 3 lần (27.3%)

### 2.2. Các trường hợp thất bại
| File | Group | Anchor | Status | Ghi chú |
| :--- | :---: | :---: | :---: | :--- |
| `media_148414` | 0 | 1 | failed | Kèm hallucination_warning |
| `media_149291` | 0 | 1 | failed | - |
| `media_149291` | 2 | 1 | failed | - |

**Nguyên nhân:** Các chunk bị Language Collapse nặng có thể không có anchor phù hợp để dùng làm context prefix.

## 3. Hiệu năng Server

### 3.1. Vấn đề với file dài
File `media_149291` (156.64s) gây ra **high keepalive warnings** (>112 keepalive count) tại cả v4 và v5:
```
[Warning] media_149291_1769069811005.mp3: High keepalive count (86-112). Server might be struggling.
```

This indicates:
- Server đang gặp pressure với các file dài
- Cần tối ưu chunk processing hoặc tăng timeout

### 3.2. RTF Comparison (v4 vs v5)
| Metric | v4 | v5 | Thay đổi |
| :--- | :---: | :---: | :---: |
| Avg Inference RTF | 2.674 | 2.597 | -3.0% |
| Max Inference RTF | 4.117 | 3.995 | -3.0% |

v5 có hiệu năng ổn định hơn nhẹ so với v4.

## 4. So sánh độ ổn định (v4 vs v5)

| Chỉ số | v4 | v5 | Nhận xét |
| :--- | :---: | :---: | :--- |
| Avg CER | 38.49% | 38.49% | **Giống nhau** tuyệt đối |
| CER Range | 30.86% - 55.61% | 30.86% - 55.61% | **Không thay đổi** |
| Hallucination Rate | 81.82% | 81.82% | **Ổn định** |
| Severity Dist | 2H/7M/2N | 2H/7M/2N | **Giống nhau** |

**Kết luận:** v4 và v5 cho kết quả gần như hoàn toàn giống nhau, cho thấy hệ thống đã đạt độ reproducible cao hơn so với v1-v3 (có sự biến thiên CER đáng kể).

## 5. Tổng kết rủi ro

| Vấn đề | Mức độ | Nguyên nhân dự kiến | Ảnh hưởng |
| :--- | :---: | :--- | :--- |
| Language Collapse Recovery Failed | **Cao** | Chunk không có anchor phù hợp | Hallucination Warning tại media_148414 |
| Hallucination (English/Context) | **Cao** | Model bias | 2 file High Severity |
| Server Performance (file dài) | **Trung bình** | Keepalive timeout | File >2min bị delay |
| System Stability | **Thấp** | - | v4/v5 rất ổn định |

---
**Người tổng hợp:** Voxtral Audit Agent
**Tài liệu tham chiếu:** `results/07-05-2026_v4`, `results/07-05-2026_v5`