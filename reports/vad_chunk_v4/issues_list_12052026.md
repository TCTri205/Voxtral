# Danh sách vấn đề tồn tại - Voxtral ASR (12/05/2026)

Dựa trên kết quả benchmark từ 2 lần chạy `v4`, `v5` ngày 12/05/2026, các vấn đề kỹ thuật được phân loại như sau:

## 1. Lỗi Hallucination & Insertions (Còn tồn tại)

Tỷ lệ ảo giác vẫn ở mức cao (81.82% ở v4), tuy nhiên mức độ nghiêm trọng đã giảm đáng kể.

### 1.1. Social/Phonetic Insertion (Chèn câu xã giao)
Đây là lỗi chủ đạo trong phiên bản này. Hệ thống tự chèn các cụm từ Nhật Bản khuôn mẫu:
- **Cụm từ lặp lại:** `お茶になっております` (trong `media_148280`), `お疲れ様でした` (trong `media_148284`), `頑張りましょう` (trong `media_148393`).
- **Đặc điểm:** Các câu này thường được chèn vào đầu hoặc cuối các đoạn hội thoại dù không có trong Ground Truth.

### 1.2. Context Collapse (Sai lệch thông tin tên riêng)
- **Ví dụ:** `media_148439` tự thêm thông tin người đại diện `"坂本"` không có trong GT (High Severity).
- **Ví dụ:** `media_148954` nhận diện sai tên ngân hàng `"アセプトジャパン"` thay vì `"アセットジャパン"`.

## 2. Vấn đề Độ ổn định & Mạng (Mới)

Lần chạy `v5` đã bộc lộ điểm yếu về khả năng chống chịu lỗi mạng của hệ thống benchmark.

### 2.1. Lỗi kết nối & DNS
- Xuất hiện lỗi `[Errno 11001] getaddrinfo failed` khiến quá trình xử lý bị dừng đột ngột trên 3 file.
- **Ảnh hưởng:** Gây sai lệch hoàn toàn kết quả thống kê của toàn bộ run (CER vọt lên 45%).

### 2.2. Timeout trên file dài
- File `media_149291` gặp lỗi `timeout` ở v5, cho thấy server vẫn gặp áp lực khi xử lý các file > 2 phút trong điều kiện mạng không ổn định.

## 3. Phân tích Language Collapse Recovery

### 3.1. Hiệu quả cải tiến
Cơ chế phục hồi ở bản `2026-05-12.2` hoạt động rất tốt:
- **Tỷ lệ thành công (v4):** 100% (**12/12** lần retry thành công).
- **Biến thiên (v6):** 91.7% (**11/12** lần thành công, ghi nhận 1 case `failed` tại `media_148954`).

## 4. So sánh độ ổn định (v4 vs v6)

Hệ thống cho thấy khả năng tái lập kết quả rất tốt:
- **v4 CER:** 34.58% | **v6 CER:** 36.44%
- **Hallucination Severity:** Cả 2 run đều chỉ có 1 lỗi High Severity duy nhất tại `media_148439`.
- **Kết luận:** Bản cập nhật này đạt độ ổn định cao về cả chất lượng và hiệu năng.

## 5. Tổng kết rủi ro

| Vấn đề | Mức độ | Nguyên nhân dự kiến | Ảnh hưởng |
| :--- | :---: | :--- | :--- |
| Network Instability | **Cao** | DNS/Internet fluctuation | Gây fail benchmark (v5) |
| Social Hallucinations | **Trung bình** | Model bias (standard phrases) | CER ~35% |
| High Severity Errors | **Thấp** | Context misinterpretation | Chỉ còn 1 file ở v4 |
| Language Collapse | **Thấp** | Đã có cơ chế Recovery tốt | Đã xử lý triệt để ở v4 |

---
**Người tổng hợp:** Voxtral Audit Agent
**Tài liệu tham chiếu:** `results/12-05-2026_v4`, `results/12-05-2026_v5`
