# Phân tích Benchmark & Đối chiếu Code VAD Chunk V9

**Trạng thái:** Đã revert mã nguồn máy chủ về commit `2e3e402` (mã nguồn hoạt động ổn định nhất hôm nay).

---

## 📊 1. Kết quả đối chiếu CER giữa các Run (21-05-2026)

| File | v1 (Commit `2e3e402`) | v2 (Commit `5a1789c`) | v3 (Commit `8095b10`) | Delta (v1 → v3) | Đánh giá |
|---|---|---|---|---|---|
| `media_148280_1767762915627.mp3` | 44.02% | 44.02% | 44.02% | +0.00% | Ổn định (Lỗi Substitution thuần) |
| `media_148284_1767766514646 (1).mp3` | **28.46%** | 28.46% | 31.54% | **+3.08%** ❌ | Thoái lùi (Xóa nhầm text thật) |
| `media_148393_1767860211615 (1).mp3` | 35.11% | 35.11% | 35.11% | +0.00% | Ổn định |
| `media_148394_1767860189485 (1).mp3` | **35.18%** | 35.18% | 36.18% | **+1.00%** ❌ | Thoái lùi nhẹ |
| `media_148414_1767922241264 (1).mp3` | 34.95% | 34.95% | 34.95% | +0.00% | Ổn định |
| `media_148439_1767926711644 (1).mp3` | **22.60%** | 22.60% | 26.44% | **+3.84%** ❌ | Thoái lùi |
| `media_148954_1768789819598 (1).mp3` | **29.31%** | 44.66% | 28.97% | -0.34% | v2 bị spike nghiêm trọng do recovery |
| `media_149291_1769069811005.mp3` | **30.19%** | 36.79% | 35.32% | **+5.13%** ❌ | Thoái lùi |
| `media_149733_1769589919400.mp3` | **50.00%** | 41.41% | 51.23% | **+1.23%** ❌ | Biến động |
| `silence_60s.wav` | 0.00% | 0.00% | 0.00% | +0.00% | Hoàn hảo (HRS = 0.0) |
| `stochastic_noise_60s.wav` | 0.00% | 0.00% | 0.00% | +0.00% | Hoàn hảo (HRS = 0.0) |
| **Speech-only Average CER** | **34.42%** | **35.91%** | **35.97%** | **+1.55%** ❌ | **Thoái lùi từ v1 đến v3** |

---

## 🔍 2. Phân tích nguyên nhân thoái lùi từ code diff

Quyết định revert hai commit gần nhất (`8095b10` và `5a1789c`) dựa trên ba phát hiện kỹ thuật sau:

### Lỗi 1: `_deduplicate_adjacent_phrases` xóa nhầm từ tiếng Nhật hợp lệ
Commit `8095b10` giới thiệu hàm khử trùng lặp cụm từ kề nhau (`min_phrase_len=4`, `max_phrase=16`).
* **Vấn đề thực tế:** Trong hội thoại kinh doanh tiếng Nhật, các từ xác nhận ngắn như `はい、はい` (vâng, vâng) hoặc các cụm từ đệm lặp lại tự nhiên bị hàm này quét sạch, làm mất từ gốc trong Ground Truth và tăng CER.
* **Giới hạn độ dài cụm lặp:** Do giới hạn cứng `max_phrase = 16`, các lỗi trùng lặp dài do lặp chunk (như cụm 38 ký tự trong `media_149291`: `"教授がもしかしたら難しいかもしれないんですけれども明日以降でも大丈夫そうですか"`) hoàn toàn không bị lọc bỏ, trong khi các từ ngắn hợp lệ lại bị xóa sai.

### Lỗi 2: Thuật toán Sub-chunk Fallback thiếu ổn định
Commit `5a1789c` bổ sung tính năng fallback chia nhỏ chunk khi phát hiện Language Collapse nhưng kết quả anchor recovery bị rỗng.
* **Hậu quả:** Số lượng kích hoạt `lang_collapse_retries` tăng vọt từ 1 (ở v1) lên 2-3 lần (ở v2/v3).
* Việc kích hoạt sub-chunk một cách không kiểm soát dẫn đến chất lượng sinh text của model suy giảm đáng kể trên các phân đoạn biên, minh chứng qua việc `media_148954` bị tăng vọt CER từ **29.31% lên 44.66%** ở run v2.

### Lỗi 3: Sai số ngẫu nhiên (nondeterminism) trong Lang Collapse Recovery
Việc thay đổi cấu trúc dữ liệu trả về và cơ chế fallback làm thay đổi nhiệt độ generation (retry ở T=0.2) tạo ra sự mất ổn định giữa các lần chạy kế tiếp, khiến hệ thống rất khó hội tụ về một CER tối ưu chung.

---

## 🛠️ 3. Điểm sáng từ Commit `2e3e402` (Hiện tại)
Commit `2e3e402` mang lại kết quả tốt nhất nhờ:
1. **Fuzzy Overlap Siết Chặt:** Rút ngắn khoảng cách biên từ 15 ký tự xuống còn **6 ký tự** và yêu cầu khớp tối thiểu **10 ký tự** mới tiến hành merge. Điều này triệt tiêu phần lớn các "boundary artifact" nhỏ lẻ (`では`, `お疲れ様です` bị chèn dư thừa ở biên).
2. **Đồng bộ `n_range` Repetition:** Khớp chính xác phạm vi tìm kiếm lặp `(3, 4, 5, 6, 7, 8, 10, 12)` giữa quá trình generate (Stopping Criteria) và hậu xử lý, giảm tối đa việc lãng phí tài nguyên sinh chuỗi lặp dài.

---

## 📈 4. Kế hoạch tối ưu tiếp theo cho V9
Sau khi đưa hệ thống về điểm neo ổn định `2e3e402`, các bước tiếp theo cần thực hiện:
1. **Verify v4:** Tiến hành chạy lại benchmark v4 để xác nhận CER quay về mức nền 34.42% (hoặc tốt hơn nhờ fuzzy overlap được siết chặt).
2. **Tinh chỉnh Heuristic Phân biệt lỗi của LLM Eval:** Cải thiện prompt đánh giá để tránh việc LLM gắn nhãn nhầm các lỗi Substitution (mô hình nghe sai phoneme như `大学` thay vì `在宅`) thành lỗi Insertion.
3. **Cải tiến Tốc độ (RTF):** Tập trung vào việc giảm nhẹ VAD padding khi fuzzy overlap đã hoạt động chính xác hơn.
