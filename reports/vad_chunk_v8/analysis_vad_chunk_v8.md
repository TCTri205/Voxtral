# Phân tích Benchmark VAD Chunk V8 — Run: 20-05-2026_v3

## 📊 1. Tổng quan kết quả

| Chỉ số | Giá trị | Nhận xét |
|---|---|---|
| **CER (Speech Only)** | **35.27%** | ❌ Rất cao — mục tiêu ≤ 6% |
| **CER (All Files)** | **28.86%** | ❌ Cao |
| **HRS (Hallucination on Silence)** | **0.000** | ✅ Hoàn hảo |
| **Avg RTF** | **1.14** | ⚠️ > 1.0, chưa đạt real-time |
| **Hallucination Rate (Speech)** | **100%** (9/9 files) | ❌ Nghiêm trọng |
| **Deletion errors** | **0** | ✅ Tốt — VAD Padding 300ms hiệu quả |

---

## 🔬 2. Phân tích từng file — Chi tiết lỗi

| File | CER | Lỗi cụ thể | Loại lỗi | Nguồn gốc |
|---|---|---|---|---|
| `media_149733` | **51.23%** | `Oh.` — hallucinated Anh ngữ | **Insertion** | Model hallucination |
| `media_148280` | **42.39%** | `ダンタク` ← thay cho `在宅` | **Substitution** | Acoustic model error |
| `media_148954` | **36.90%** | `アセプトジャパン` ← `アセットジャパン` | **Substitution** | Acoustic model error |
| `media_148394` | **35.18%** | `お疲れ様です。お疲れ様です。` — lặp | **Insertion** | Boundary artifact |
| `media_148393` | **35.11%** | `困りません` — từ không tồn tại trong GT | **Insertion** | Boundary artifact |
| `media_148414` | **34.95%** | `先生管理科` ← `中央清算管理課` | **Substitution** | Acoustic model error |
| `media_149291` | **30.61%** | `お理解しご連絡させて…` — lặp cụm từ | **Insertion** | Boundary artifact |
| `media_148284` | **28.46%** | `では` — insertion nhỏ ở biên chunk | **Insertion** | Boundary artifact |
| `media_148439` | **22.60%** | `年賀株式会社の坂本です生徒キャパン熊谷` | **Mixed** | Model + Boundary |

> **Lưu ý:** Không phải tất cả 9 file đều là Insertion thuần túy. 3 file (148280, 148954, 148414) là **Substitution** — mô hình nghe sai phoneme, không phải tự thêm từ. CER cao ở các file này đến từ chất lượng acoustic model, không thể fix bằng post-processing.

---

## 🩺 3. Chẩn đoán nguyên nhân gốc rễ

### 3.1. Phân loại lỗi: Insertion vs Substitution

Trong 9 file speech, cần phân biệt 2 loại lỗi khác nhau về bản chất:

**🔴 Insertion (6 files — fix được bằng post-processing)**: Mô hình tự *thêm* từ/cụm từ không có trong audio.
- Nguyên nhân chính: `_fuzzy_overlap_chars` threshold=15 + `VAD_CHUNK_PADDING` 300+300ms → boundary artifact khi merge chunk
- Biểu hiện: `では` (148284), `お疲れ様です。お疲れ様です。` (148394), `お理解しご連絡させて` (149291), `Oh.` (149733), `困りません` (148393), company name confusion (148439)

**🟡 Substitution (3 files — lỗi mô hình căn bản, không fix được bằng post-processing)**: Mô hình *nghe sai* phoneme, thay từ này bằng từ khác.
- Nguyên nhân: Acoustic model của Voxtral nhầm lẫn phoneme gần nhau trên telephony audio (8-16kHz, lossy MP3)
- Biểu hiện: `ダンタク`↔`在宅` (148280), `アセプトジャパン`↔`アセットジャパン` (148954), `先生管理科`↔`中央清算管理課` (148414)
- **Implication:** Ngay cả khi fix hết insertion, CER trên 3 file này vẫn ở mức 35-42% do substitution thuần túy

### 3.2. Chi tiết nguyên nhân Insertion

### 3.2. Chi tiết nguyên nhân Insertion

Có 2 nguồn gốc chính gây Insertion:

#### 🔴 A. Lỗi biên chunk (Overlap Boundary Artifact) — Nguồn chính
- **Biểu hiện:** `では` (media_148284), `お理解しご連絡させて` (media_149291)
- **Nguyên nhân:** `_fuzzy_overlap_chars` dùng `SequenceMatcher` với window 180 ký tự — nếu hai chunk kề nhau share một cụm từ ngắn ở biên thì vẫn có thể bị duplicate hoặc merged sai, tạo ra text chèn thêm.
- **Cụ thể:** Điều kiện matching hiện tại yêu cầu `first_block.b <= 15` và `last_block.a + last_block.size >= len(left_tail) - 15` — tức **threshold = 15 ký tự** (sai lệch so với báo cáo daily ghi "tolerance = 6"). Kèm theo `total_match_size >= 3` ký tự — quá lỏng, cho phép overlap ngắn bị false match dẫn đến duplication.
- **Tác nhân làm trầm trọng:** `VAD_CHUNK_PADDING_LEFT_MS=300` + `VAD_CHUNK_PADDING_RIGHT_MS=300` tạo **600ms overlap/chunk** — lượng audio trùng lặp quá lớn, kết hợp fuzzy threshold 15 khiến boundary matching dễ sai hàng loạt.

#### 🟡 B. Model Hallucination trên silence ngắn giữa các segment
- **Biểu hiện:** `Oh.` (media_149733)
- **Nguyên nhân:** Khoảng lặng ngắn giữa các VAD segment + model tự sinh filler text. Đã được giảm đáng kể nhờ HPF 80Hz (HRS=0 trên file silence thuần), nhưng vẫn xuất hiện trong speech có pause ngắn.

### 3.3. RTF > 1.0 — Không đạt real-time
- RTF range: 1.021 – 1.693, avg = 1.14
- File dài nhất (`media_148954`, RTF=1.693) mất ~69% thời gian audio chỉ để inference
- **Nguyên nhân:** FP16 trên T4 đã tốt hơn 4-bit nhưng chunking với padding + retry hallucination tốn thêm thời gian

### 3.4. CER cao dù không có Deletion
- **Sự nghịch lý:** Deletion = 0 (tốt) nhưng CER vẫn 35%+ — chứng tỏ CER không bị kéo lên bởi mất từ mà bởi **substitution + insertion**
- **Phân tách:** ~6 file bị insertion (fix được), ~3 file bị substitution (không fix được bằng post-processing). Nếu fix hết insertion, CER kỳ vọng giảm từ 35% → ~25-28%. Phần substitution còn lại đến từ chất lượng acoustic model của Voxtral trên telephony data.

---

## 📈 4. Lịch sử so sánh (từ per_file_results.json)

> *Lưu ý: per_file_results.json lưu trữ kết quả từ 19-04-2026_v1 đến v10, không map trực tiếp với các run mới. CER trong per_file_results.json có vẻ là CER baseline cố định theo file, chưa phản ánh các cải tiến VAD mới.*

| File | CER baseline (19-04 series) | CER hiện tại (20-05-v3) | Δ |
|---|---|---|---|
| `media_148280` | 65.49% | 42.39% | **-23.1%** ✅ |
| `media_148393` | 17.55% | 35.11% | **+17.6%** ❌ |
| `media_148414` | 100.00% | 34.95% | **-65.1%** ✅ |
| `media_148954` | 69.48% | 36.90% | **-32.6%** ✅ |
| `media_149291` | 97.80% | 30.61% | **-67.2%** ✅ |
| `media_149733` | 60.43% | 51.23% | **-9.2%** ✅ |

**Nhận xét:** Nhiều file đã cải thiện đáng kể so với baseline 19-04. Tuy nhiên `media_148393` bị thoái lùi — cần điều tra cụ thể.

---

## 💡 5. Đề xuất tối ưu — Phương án cải thiện CER

### Phương án 1: Tinh chỉnh `_fuzzy_overlap_chars` (Ưu tiên cao nhất)

**Vấn đề hiện tại (đã xác minh trong code `voxtral_server_transformers.py` dòng 1053-1078):**
```python
# ❌ Threshold = 15 ký tự — QUÁ RỘNG (không phải "6" như báo cáo daily)
# ❌ Minimum total match = 3 ký tự — QUÁ THẤP
# ❌ Kết hợp VAD_CHUNK_PADDING 300+300ms → 600ms overlap audio mỗi biên chunk
if first_block.b <= 15 and (last_block.a + last_block.size) >= len(left_tail) - 15:
    total_match_size = sum(b.size for b in blocks)
    if total_match_size >= 3:  # ← QUÁ THẤP — 3 ký tự (~1 từ ngắn) đã accepted
        return last_block.b + last_block.size
```
> ⚠️ **Sai lệch báo cáo:** Daily report ghi "tolerance đang ở mức 6" nhưng code thực tế dùng hằng số **15**. Mọi kế hoạch tinh chỉnh cần dựa trên giá trị thực tế này.

**Đề xuất sửa:**
```python
# Giảm threshold từ 15 → 6, tăng minimum match từ 3 → 10
MAX_BOUNDARY_DISTANCE = 6          # Giảm từ 15
MIN_FUZZY_MATCH = 10               # Tăng từ 3

if first_block.b <= MAX_BOUNDARY_DISTANCE and \
   (last_block.a + last_block.size) >= len(left_tail) - MAX_BOUNDARY_DISTANCE:
    total_match_size = sum(b.size for b in blocks)
    if total_match_size >= MIN_FUZZY_MATCH:
        return last_block.b + last_block.size
```
- `MAX_BOUNDARY_DISTANCE`: 15 → 6 — thu hẹp phạm vi tìm kiếm biên, giảm false match
- `MIN_FUZZY_MATCH`: 3 → 10 — yêu cầu overlap thực sự đủ dài (~5-7 từ tiếng Nhật) mới được chấp nhận, ngăn match ngẫu nhiên 2-3 ký tự

**Kỳ vọng:** Giảm insertion error do boundary artifact ~50-70%

---

### Phương án 1b: Đồng bộ `n_range` giữa `RepetitionStoppingCriteria` và `_truncate_repetitions` (Ưu tiên cao)

**Vấn đề hiện tại (đã xác minh trong code):**

| Thành phần | `n_range` hiện tại | Vị trí |
|---|---|---|
| `_truncate_repetitions` | `(3, 4, 5, 6, 7, 8, 10, 12)` | Dòng 1220 |
| `RepetitionStoppingCriteria` | `(3, 4, 5)` | Dòng 595 |

→ Stopping criteria **chỉ phát hiện loop ngắn** trong quá trình generation. Loop dài (10-gram, 12-gram) chỉ bị truncate *sau khi* generation hoàn tất → lãng phí compute, có thể sinh text dài vô ích rồi mới cắt.

**Đề xuất sửa (dòng 595):**
```python
# Trước:
stopping_criteria = StoppingCriteriaList([
    RepetitionStoppingCriteria(processor.tokenizer, threshold=5)
])

# Sau: Đồng bộ n_range
stopping_criteria = StoppingCriteriaList([
    RepetitionStoppingCriteria(
        processor.tokenizer, 
        threshold=5, 
        n_range=(3, 4, 5, 6, 7, 8, 10, 12)
    )
])
```

**Kỳ vọng:** Phát hiện và dừng loop dài sớm, giảm lãng phí token, giảm hallucination cuối chunk

---

### Phương án 2: Confidence-based Truncation (Ưu tiên trung bình — ⚠️ có rủi ro kỹ thuật)

> **Cảnh báo trước khi triển khai:**
> 1. `output_scores=True` + `return_dict_in_generate=True` trả về toàn bộ score tensor cho mỗi token sinh ra. Với vocab ~128k và max_new_tokens=512, riêng scores chiếm **~256MB VRAM** — nguy cơ OOM trên T4 16GB (đang dùng ~8GB cho model FP16).
> 2. Chưa xác minh `VoxtralRealtimeForConditionalGeneration` có hỗ trợ `output_scores` không. Một số model wrapper của HuggingFace không export scores.
> 3. Log-prob threshold -3.0 là arbitrary, cần tune nhiều lần trên tập test.

Sử dụng **log-probabilities** từ model output để tự động loại bỏ các token low-confidence:

```python
def _run_inference_with_confidence(audio_np, session_config, conn_id):
    """Generate với scores, lọc low-confidence tokens."""
    generation_kwargs = dict(
        **inputs,
        max_new_tokens=512,
        output_scores=True,
        return_dict_in_generate=True,
        # ...
    )
    output = model.generate(**generation_kwargs)
    
    # Tính log-prob cho mỗi token
    scores = output.scores  # list of tensors, one per generated token
    token_ids = output.sequences[0, -len(scores):]
    
    log_probs = []
    for i, score in enumerate(scores):
        token_id = token_ids[i]
        log_prob = torch.log_softmax(score, dim=-1)[0, token_id].item()
        log_probs.append(log_prob)
    
    # Truncate tại điểm log_prob < threshold
    CONFIDENCE_THRESHOLD = -3.0  # Tune empirically
    for i, lp in enumerate(log_probs):
        if lp < CONFIDENCE_THRESHOLD:
            # Truncate transcript tại đây
            break
    
    return transcript_up_to_i
```

**Kỳ vọng:** Loại bỏ hallucination cuối câu, giảm CER 5-10%. Nhưng cần verify memory footprint và model compatibility trước.

---

### Phương án 3: Cải thiện Hallucination Detection — Thêm Semantic Check (Ưu tiên thấp)

> **⚠️ Ưu tiên thấp vì:**
> 1. Latin ratio check dễ **false positive** trên business Japanese thực tế — tên công ty, thuật ngữ kỹ thuật, code-switching là bình thường trong hội thoại business Nhật
> 2. `SUSPICIOUS_INSERTIONS` trùng lặp với `english_hallucination_patterns` đã có sẵn trong code (dòng ~770)
> 3. Không giải quyết được nguyên nhân gốc rễ — chỉ thêm 1 tầng detection mà không sửa được lỗi

Hiện tại `_check_hallucination_guardrails` đã check:
- Short transcript
- English patterns (18 patterns)
- Looping n-grams

**Nếu vẫn muốn thêm, đề xuất gộp vào pattern hiện có thay vì tạo check riêng:**
```python
# Thêm vào english_hallucination_patterns hiện tại (dòng ~770), không tạo list riêng
# Các pattern cần bổ sung: "Oh.", "Yes.", "Okay."
```

---

## 🗺️ 6. Roadmap V9 — Kế hoạch ưu tiên

```
Tuần 1 (Ngắn hạn — Fix Insertion, kỳ vọng CER 35% → ~25-28%):
  [P0] Fix _fuzzy_overlap_chars: MAX_BOUNDARY_DISTANCE 15→6, MIN_FUZZY_MATCH 3→10
  [P0] Đồng bộ n_range của RepetitionStoppingCriteria với _truncate_repetitions: (3,4,5,6,7,8,10,12)
  [P2] Re-benchmark sau 2 fix trên để đo CER reduction

Tuần 2 (Trung hạn):
  [P2] Nghiên cứu Confidence-based Truncation: verify memory footprint + model compatibility trước khi implement
  [P1] Điều tra media_148393: tại sao CER tăng từ 17% → 35%?
  [P2] Cân nhắc giảm VAD_CHUNK_PADDING từ 300ms → 200ms (sau khi fuzzy overlap đã được fix)

Dài hạn:
  [P2] Xây dựng tập test lớn hơn (30+ files) với diverse telephony scenarios
  [P3] Đánh giá Latin ratio check nếu insertion vẫn cao sau các fix trên
```

> **Kỳ vọng thực tế:** Fix fuzzy overlap + repetition stopping criteria chỉ giải quyết được phần Insertion (~6/9 files). Phần Substitution (~3/9 files) đến từ chất lượng acoustic model, CER trên các file này sẽ không cải thiện. CER tổng kỳ vọng sau v9: **~25-28%** (không thể xuống dưới 20% nếu không đổi mô hình).

---

## ⚠️ 7. Điểm chú ý quan trọng

> **Sai lệch báo cáo → code:** Daily report ghi `tolerance = 6` trong `_fuzzy_overlap_chars`, nhưng code thực tế (`voxtral_server_transformers.py:1053-1078`) dùng hằng số **15** cho cả `first_block.b <= 15` và `last_block.a + last_block.size >= len(left_tail) - 15`. Đây là sai lệch nghiêm trọng ảnh hưởng đến kế hoạch v9 — mọi quyết định tinh chỉnh phải dựa trên giá trị thực tế **15**, không phải 6.

> **Không phải tất cả lỗi đều là Insertion:** 3/9 file (148280, 148954, 148414) bị **Substitution** — mô hình nghe sai phoneme, không phải tự thêm từ. Các fix post-processing không thể cải thiện CER trên các file này. CER floor với model hiện tại ước tính ~20-25%.

> **Phương án Confidence-based Truncation có rủi ro OOM:** `output_scores` + vocab 128k + max_tokens 512 = ~256MB VRAM riêng cho scores. Cần verify trên T4 16GB trước khi implement.

---

*Phân tích bởi: Antigravity | Dựa trên: daily_report_20052026.md, results/20-05-2026_v3/, voxtral_server_transformers.py*
*Ngày phân tích: 21/05/2026*
