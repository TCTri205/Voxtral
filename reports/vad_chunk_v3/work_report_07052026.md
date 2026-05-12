# Báo Cáo Tổng Hợp Công Việc - Dự Án Voxtral ASR (07/05/2026)

## 1. Tổng Quan Công Việc
Ngày hôm nay (07/05/2026), đội ngũ đã tập trung vào việc ổn định hệ thống đánh giá (Evaluation Pipeline), triển khai cơ chế tự động phục hồi lỗi ngôn ngữ (Language Collapse) và tối ưu hóa quy trình xử lý audio theo phân đoạn (VAD-Aware Chunking).

---

## 2. Chi Tiết Các Thay Đổi (Dựa trên Git Commits)

### A. Cơ Chế Tự Phục Hồi Lỗi Ngôn Ngữ (Language Collapse Auto-Recovery)
- **Vấn đề:** Model thỉnh thoảng bị lỗi "Language Collapse" (hallucinate tiếng Anh khi audio là tiếng Nhật).
- **Giải pháp:** 
    - Triển khai hàm `_detect_language_collapse` dựa trên tỷ lệ ký tự ASCII (ngưỡng > 70%).
    - Thiết lập cơ chế **Context Prefix Retry**: Khi phát hiện lỗi, hệ thống sẽ lấy 5 giây audio từ phân đoạn "lành mạnh" (anchor chunk) liền kề để làm tiền đề (context) và thực hiện nhận dạng lại phân đoạn lỗi.
    - Cập nhật API response để bao gồm thông tin `lang_collapse_retries` giúp theo dõi hiệu quả phục hồi.

### B. Cải Tiến Hệ Thống Đánh Giá & Benchmark
- **Tính toán CER chính xác:** Cập nhật `benchmark_runner.py` để loại trừ các file tĩnh (silence, noise) khỏi tính toán CER trung bình. Điều này giúp phản ánh đúng độ chính xác trên dữ liệu giọng nói thực tế.
- **Xử lý Ground Truth trống:** Cải thiện logic đánh giá để không phạt CER khi cả Ground Truth và Transcript đều trống (trước đây tính là 100% lỗi).
- **Ghi nhật ký cấu hình VAD:** Tự động lưu trữ thông tin cấu hình VAD (Threshold, Padding, Chunk Limit) vào báo cáo đánh giá để đảm bảo tính tái lập (reproducibility).

### C. Tối Ưu Hóa Xử Lý Audio & VAD
- **VAD-Aware Chunking:** Cải thiện thuật toán chia chunk để tránh cắt ngang từ (mid-word). Hệ thống hiện tại ưu tiên chia nhỏ audio tại các khoảng lặng tự nhiên (silence gaps).
- **Xử lý chồng lấn (Merge Overlap):** Sửa lỗi chồng lấn văn bản khi ghép các phân đoạn (sub-chunks) bằng thuật toán phát hiện chuỗi ký tự trùng lặp chính xác ở biên.
- **Độ ổn định:** Cố định `temperature=0.0` để đảm bảo kết quả đầu ra mang tính định danh (deterministic), quan trọng cho việc đánh giá benchmark ổn định.

---

## 3. Kết Quả Benchmark Gần Nhất (v5)

| Chỉ số | Giá trị | Ghi chú |
| :--- | :--- | :--- |
| **Average CER** | **38.49%** | Đã loại trừ file silence/noise |
| **Hallucination Rate** | **81.82%** | Đánh giá bởi LLM (Llama-3.3-70B) |
| **Trạng thái xử lý** | **100% Success** | Không có lỗi crash server trên toàn bộ test set |
| **Tốc độ (Average RTF)** | **~3.2x** | Tốc độ suy luận trên GPU T4 |

---

## 4. Các Vấn Đề Tồn Đọng & Khó Khăn
- **Tỷ lệ Hallucination cao:** Mặc dù hệ thống đã ổn định hơn, nhưng model vẫn hay sinh ra các câu tiếng Anh mẫu (formulaic English) không có trong audio.
- **Hiệu quả phục hồi:** Cơ chế Auto-Recovery đã hoạt động nhưng vẫn có trường hợp retry thất bại (ví dụ: `media_148414`). Cần xem xét tăng độ dài context hoặc thay đổi chiến thuật anchor.

---

## 5. Kế Hoạch Tiếp Theo (Next Steps)
1. **Hậu xử lý (Post-processing Filter):** Xây dựng bộ lọc loại bỏ các pattern tiếng Anh phổ biến (hallucination patterns).
2. **Tinh chỉnh Auto-Recovery:** Tăng độ dài context từ 5s lên 8s và thử nghiệm cơ chế fallback nhiều tầng.
3. **Tối ưu hóa cho File dài:** Giảm kích thước chunk xuống 12s đối với audio có độ dài trên 2 phút để tránh lỗi timeout/keepalive.

---
**Người thực hiện báo cáo:** Antigravity AI
**Ngày cập nhật:** 07/05/2026 (16:55 UTC+7)