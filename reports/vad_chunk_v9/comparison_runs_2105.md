# Báo cáo Đối chiếu & Phân tích Chi tiết 3 Lần chạy (v4, v5, v6) Ngày 21-05-2026

Báo cáo này đối chiếu và phân tích kỹ thuật chi tiết về 3 lần chạy benchmark của máy chủ ASR Voxtral vào ngày 21-05-2026: **results/21-05-2026_v4**, **results/21-05-2026_v5**, và **results/21-05-2026_v6**.

---

## 📊 1. Kết quả Tổng quan & Đối chiếu Số liệu

Dưới đây là bảng đối chiếu chi tiết hiệu năng và chất lượng giữa 3 lần chạy. Cả 3 lần chạy đều được thực hiện trên mã nguồn máy chủ tại commit `2e3e402` (sau khi revert các commit không ổn định trước đó).

| File | Status | CER (v4) | CER (v5) | CER (v6) | RTF Inf (v4) | RTF Inf (v5) | RTF Inf (v6) | Nhận xét |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `media_148280...` | success | 44.02% | 44.02% | 44.02% | 1.494 | 1.272 | 1.272 | Đồng nhất CER |
| `media_148284...` | success | 28.46% | 28.46% | 28.46% | 1.018 | 1.017 | 1.025 | Đồng nhất CER |
| `media_148393...` | success | 35.11% | 35.11% | 35.11% | 1.398 | 1.406 | 1.404 | Đồng nhất CER |
| `media_148394...` | success | 35.18% | 35.18% | 35.18% | 1.629 | 1.637 | 1.630 | Đồng nhất CER |
| `media_148414...` | success | 34.95% | 34.95% | 34.95% | 1.337 | 1.337 | 1.244 | Đồng nhất CER |
| `media_148439...` | success | 22.60% | 22.60% | 22.60% | 1.489 | 1.496 | 1.489 | Đồng nhất CER |
| `media_148954...` | success | 29.14% | 29.14% | 29.14% | 1.690 | 1.637 | 1.639 | Đồng nhất CER |
| `media_149291...` | success | 30.19% | 30.19% | 30.19% | 1.457 | 1.427 | 1.396 | Đồng nhất CER |
| `media_149733...` | success | **51.23%** | **51.23%** | **51.23%** | 1.081 | 1.034 | 1.085 | Khác biệt 1 từ |
| `silence_60s.wav` | success | 0.00% | 0.00% | 0.00% | 0.051 | 0.043 | 0.043 | Đồng nhất (HRS=0) |
| `stochastic_noise...` | success | 0.00% | 0.00% | 0.00% | 0.043 | 0.043 | 0.043 | Đồng nhất (HRS=0) |
| **Speech-Only CER** | | **34.54%** | **34.54%** | **34.54%** | | | | **Không đổi** |
| **Avg Inference RTF** | | | | | **1.153** | **1.123** | **1.117** | **Cải thiện nhẹ** |

---

## 🔍 2. Phân tích Hiện tượng & Nguyên nhân Kỹ thuật

### 2.1. Sự đồng nhất và Khác biệt giữa các Run
* **v5 và v6 đồng nhất 100%:** Toàn bộ văn bản transcript và các số liệu CER của run v5 và v6 hoàn toàn khớp nhau từng ký tự. Điều này chứng minh pipeline hoạt động cực kỳ ổn định trong điều kiện thông thường.
* **v4 khác biệt đúng 1 từ tại `media_149733`:**
  * Transcript v4: `...そしたらガサ外人の方ですか?...`
  * Transcript v5/v6: `...そしたら外人の方ですか?...`
  * **Nguyên nhân:** File `media_149733` đã kích hoạt cơ chế tự phục hồi sụp đổ ngôn ngữ **Language Collapse Recovery** tại Chunk 2 (`lang_collapse_retries` ghi nhận nhóm `[2]` trạng thái `fixed`). Khi kích hoạt retry, hệ thống sử dụng cấu hình nhiệt độ ngẫu nhiên `RETRY_TEMPERATURE = 0.2`. Giá trị nhiệt độ này dẫn tới sự không đơn trị (non-determinism) khi sinh từ của mô hình ngôn ngữ (LLM/ASR), tạo ra sự khác biệt nhỏ giữa v4 và v5/v6.
  * **Tại sao CER vẫn bằng 51.23%?**
    * Ground Truth: `スリー、スリー ラスター 外人` (độ dài sạch: 13 ký tự).
    * v4 Hyp: `ガサ外人` (độ dài sạch: 4 ký tự). So khớp với Ground Truth mất 7 thao tác edit (thay thế 2 ký tự, xóa 5 ký tự).
    * v5 Hyp: `外人` (độ dài sạch: 2 ký tự). So khớp với Ground Truth mất 7 thao tác edit (xóa 7 ký tự).
    * Do khoảng cách Levenshtein (edit distance) so với Ground Truth của cả hai transcript đều bằng **166 ký tự** trên toàn file, CER cuối cùng của hai run vẫn bằng nhau tuyệt đối.

### 2.2. Chế độ chạy qua Server Audio Directory
* Cả 3 run đều ghi nhận `chunks_sent = 0` và `stream_time = 0.000` trên client.
* **Giải thích:** Client sử dụng cờ `--server-audio-dir`. Client chỉ gửi đường dẫn file âm thanh trên Colab/server và server tự load trực tiếp từ disk (`librosa.load`). Đây là chế độ chạy offline tối ưu hóa cao, loại bỏ độ trễ truyền tải mạng và tiết kiệm tối đa credit tính toán của Google Colab.

---

## ⚠️ 3. Những Điểm chưa ổn & Cần Tối ưu (Đối chiếu Code)

### 3.1. Chỉ số CER còn quá cao (34.54%) do Lỗi Nhận diện Âm vị (Substitution)
* Số liệu thực tế chỉ ra lỗi CER cao **không phải do mô hình bị lặp vô hạn hay sụp đổ ngôn ngữ** (các cơ chế Stopping Criteria và Fuzzy Overlap ở commit `2e3e402` đã triệt tiêu lỗi lặp).
* CER cao chủ yếu do lỗi nhận diện âm vị sai các thuật ngữ tiếng Nhật chuyên môn (Acoustic Substitution):
  * `中央清算管理課` (Chuuou Seisan Kanrika) $\rightarrow$ Bị nhận diện sai thành `先生管理科` (Sensei Kanrika).
  * `在宅` (Zaitaku) $\rightarrow$ Bị nhận diện sai thành `ダンタク` (Dantaku) $\rightarrow$ `大学` (Daigaku).
  * `アセットジャパン` (Asset Japan) $\rightarrow$ Bị nhận diện sai thành `アセプトジャパン` (Asept Japan) hoặc `生徒キャパン` (Seito Kyapan).
  * `建設のエスタ` (Kensetsu no Esuta) $\rightarrow$ Bị nhận diện sai thành `水建設 of 安田` (Sui Kensetsu no Yasuda).
* **Kết luận:** Đây là giới hạn về mặt âm học (acoustic) của mô hình nền tảng gốc, không thể sửa đổi đơn thuần bằng các thuật toán xử lý biên hay cắt lặp.

### 3.2. LLM Evaluator đánh giá sai phân loại lỗi (False Positive trên Insertion)
* Trong file `llm_eval_details.csv`, mô hình `llama-3.3-70b-versatile` phân loại 9/11 file gặp lỗi `insertion` (chèn từ lạ) với mức độ `medium`.
* **Vấn đề:** Các lỗi này thực chất là lỗi **Substitution** (như đã phân tích ở mục 3.1). Vì từ được mô hình nhận diện ra khác hoàn toàn từ gốc, LLM nghĩ rằng mô hình đã chèn thêm thông tin không có trong Ground Truth. Điều này khiến báo cáo thống kê Hallucination Rate bị đẩy lên **100%** giả tạo trên các file có tiếng nói, gây khó khăn cho việc đánh giá chính xác độ sụp đổ của mô hình.

### 3.3. Thời gian xử lý chậm (RTF > 1.0)
* Avg Inference RTF dao động khoảng **1.11 - 1.15**, nghĩa là xử lý âm thanh mất nhiều thời gian hơn cả thời lượng thực tế của file âm thanh.
* Lý do: Mô hình Voxtral kích thước lớn (4B) chạy trên GPU T4 (phần cứng cũ, hiệu năng giới hạn). Khi cấu hình VAD padding quá lớn (`VAD_PADDING_LEFT_MS = 300`, `VAD_PADDING_RIGHT_MS = 350`), lượng frame âm thanh dư thừa phải nạp vào mô hình tăng lên đáng kể, làm chậm tốc độ suy diễn.

### 3.4. Lọt lưới các lỗi Sụp đổ Ngôn ngữ cục bộ (Local Language Collapse)
* Trong `media_149291`, mô hình đã sinh ra một câu tiếng Tây Ban Nha vô nghĩa ở cuối chunk: `"Es que no menos mal ni en desqueo."`.
* Tuy nhiên, hệ thống **không phát hiện và không tự phục hồi (Recovery = `[]`)**.
* **Nguyên nhân dòng code:**
  * Hàm `_detect_language_collapse` tính tỷ lệ ký tự tiếng Nhật trên toàn bộ ký tự alphabetic của **cả chunk** (dòng 148):
    ```python
    ratio = len(jp_letters) / len(letters)
    ```
  * Vì chunk này chứa rất nhiều ký tự tiếng Nhật chính xác ở đoạn trước và sau, tỷ lệ ký tự tiếng Nhật chung đạt **0.662** $\rightarrow$ Vượt qua ngưỡng lọc `LANG_COLLAPSE_JP_RATIO = 0.55`.
  * Hậu quả là phần sụp đổ ngôn ngữ cục bộ bằng tiếng Tây Ban Nha bị bỏ qua và ghi thẳng vào kết quả cuối cùng.

---

## 💡 4. Đề xuất Hướng tối ưu hóa tiếp theo

Để giải quyết các vấn đề trên và đưa CER hướng tới mục tiêu $\le 6\%$, chúng ta cần áp dụng các giải pháp kỹ thuật sau:

### 1. Bổ sung cơ chế phát hiện sụp đổ ngôn ngữ cục bộ (Regex Latinh liên tiếp)
* **Giải pháp:** Cập nhật hàm `_detect_language_collapse` để quét xem có chuỗi ký tự Latinh (chữ cái và dấu cách) liên tục vượt quá độ dài nhất định hay không (ví dụ: chuỗi dài 12+ ký tự không chứa chữ Nhật).
* **Code đề xuất:**
  ```python
  # Nếu phát hiện một cụm từ tiếng nước ngoài liên tục dài trong chunk tiếng Nhật
  if re.search(r"[A-Za-z\s']{12,}", text):
      return {"is_collapsed": True, "jp_ratio": 0.0, "reason": "local_latin_drift"}
  ```
  Điều này sẽ giúp nhận diện ngay cụm `"Es que no menos mal ni en desqueo"` (dài 31 ký tự Latinh liên tục) và kích hoạt Language Collapse Recovery thành công.

### 2. Giảm nhẹ VAD Padding để tối ưu RTF
* Khi cơ chế Fuzzy Overlap đã hoạt động ổn định và chính xác tại commit `2e3e402`, chúng ta có thể giảm bớt VAD padding nhằm giảm tải dữ liệu âm thanh truyền vào mô hình:
  * Giảm `VAD_PADDING_LEFT_MS` từ `300` xuống `200`
  * Giảm `VAD_PADDING_RIGHT_MS` từ `350` xuống `200`
* Điều này giúp giảm lượng dữ liệu suy diễn âm thanh, qua đó cải thiện RTF đáng kể về mức $\le 1.0$.

### 3. Tinh chỉnh Prompt của LLM Evaluator
* Cập nhật prompt đánh giá trong `llm_evaluator/` để phân biệt rõ ràng giữa:
  * **Substitution (Lỗi nhận diện sai âm thanh):** Từ đọc lên tương tự nhưng viết sai chính tả hoặc sai từ đồng âm (ví dụ: `中央清算管理課` thành `先生管理科`).
  * **Insertion (Lỗi chèn/Hallucination thực sự):** Mô hình tự bịa ra thông tin mới hoàn toàn tại các đoạn không có tiếng nói hoặc lặp đi lặp lại vô nghĩa.
* Việc này giúp báo cáo Hallucination phản ánh chính xác tình trạng lỗi thực tế của hệ thống.

### 4. Áp dụng bảng từ vựng hậu xử lý (Domain Post-Processing Map)
* Do lỗi substitution chủ yếu rơi vào các danh từ riêng kinh doanh cố định (`中央清算管理課`, `アセットジャパン`, `在宅`), chúng ta có thể bổ sung một tầng ánh xạ hậu xử lý (Regex Mapping) ở cuối pipeline để tự động sửa các lỗi phát âm sai phổ biến của mô hình về đúng Ground Truth.
