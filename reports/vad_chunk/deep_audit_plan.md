# Deep Audit Plan — Voxtral VAD/Chunk Reports (05/05/2026)

> [!IMPORTANT]
> Mục tiêu: Đối chiếu **từng con số, từng nhận định** trong 3 file báo cáo với dữ liệu thực tế (results.json, llm_eval_*.*, log_debug.txt, ground_truth.json, source code). Tìm ra **nguyên nhân gốc rễ** của mỗi vấn đề.

---

## Phần A — Kiểm tra tính chính xác số liệu

### A1. Avg CER — Cách tính có đúng không?

| Run | Báo cáo ghi | Cần xác minh |
|-----|-------------|---------------|
| v1 | 39.63% | `llm_eval_summary.json` → `avg_cer: "39.63%"`. Tính bằng trung bình CER của **tất cả 11 file** (kể cả silence/noise CER=0%). Cần kiểm tra: file `media_148393` v3 có CER = `"N/A (Empty)"` → bị loại khỏi mẫu số? |
| v2 | 38.46% | ✅ Khớp `llm_eval_summary.json` |
| v3 | 37.10% | ✅ Khớp. Nhưng **v3 chỉ tính 10/11 file** vì `media_148393` = `N/A (Empty)` → mẫu số nhỏ hơn → CER trung bình bị méo xuống |

**Việc cần làm:**
- [ ] Tính tay CER trung bình v1/v2/v3 từ `results.json` để xác nhận
- [ ] Xác minh `report_exporter.py` line 61-64: `parse_cer()` trả `None` cho `"N/A (Empty)"` → file đó bị loại khỏi `cer_count` → **mẫu số v3 = 10, không phải 11**
- [ ] **Phát hiện**: Báo cáo không nói rõ v3 CER tính trên 10 file vs v1/v2 tính trên 11 file → **so sánh không công bằng**

### A2. Hallucination Rate

| Run | Báo cáo | Nguồn | Công thức |
|-----|---------|-------|-----------|
| v1 | 90.91% | `llm_eval_summary.json` → 0.9091 | 10/11 = 0.9091 ✅ |
| v2 | 90.91% | 0.9091 | 10/11 ✅ |
| v3 | 81.82% | 0.8182 | 9/11 = 0.8182 ✅ |

**Việc cần làm:**
- [ ] Xác nhận con số khớp → **OK**
- [ ] Nhưng cần ghi chú: `silence_60s.wav` bị đếm là hallucination (lỗi evaluator) → rate thực tế nên là v1: 9/10, v2: 9/10, v3: 8/10 (nếu loại silence khỏi tập đánh giá)

### A3. RTF

| Run | Báo cáo: Avg Inf RTF | Báo cáo: Avg Total RTF | benchmark JSON |
|-----|----------------------|------------------------|----------------|
| v1 | 1.920 | 1.945 | inf: 1.9204, total: 1.9445 ✅ |
| v2 | 1.887 | 1.908 | inf: 1.8873, total: 1.9075 ✅ |
| v3 | 1.895 | 1.920 | inf: 1.8948, total: 1.9196 ✅ |

**Việc cần làm:**
- [ ] Tính tay từ `results.json` mỗi run (trung bình 11 file) → xác nhận
- [ ] **Lưu ý**: RTF của silence/noise rất thấp (0.05-0.07) kéo trung bình xuống → RTF thực tế trên speech files cao hơn nhiều (~2.3-2.5x)

### A4. Severity Distribution

| Run | Báo cáo | llm_eval_summary.json | Khớp? |
|-----|---------|----------------------|-------|
| v1 | none:1, medium:5, high:5 | medium:5, high:5, none:1 | ✅ |
| v2 | none:1, medium:7, high:3 | medium:7, high:3, none:1 | ✅ |
| v3 | none:2, medium:5, high:4 | medium:5, none:2, high:4 | ✅ |

**Việc cần làm:**
- [ ] Đếm lại từ `llm_eval_details.csv` từng run → xác nhận

---

## Phần B — Phân tích từng lỗi theo file

### B1. `silence_60s.wav` — Evaluator đánh nhầm

**Hiện tượng:** Cả 3 run đều gán `silence_text/high` cho file này.

**Dữ liệu thực tế:**
- Transcript: `""` (rỗng) ở cả 3 run ✅
- CER: `0.00%` ở cả 3 run ✅
- ASR output hoàn toàn đúng (không sinh chữ)

**Nguyên nhân gốc rễ:**
- [ ] Xem `prompt_builder.py` line 34-42: `SYSTEM_PROMPT_NO_GT` → evaluator nhận silence_60s.wav **không có timestamped GT** (vì `timestamps/` không có file cho nó)
- [ ] Nhưng `ground_truth.json` **CÓ** entry `"silence_60s.wav": ""` → nên đi vào nhánh `SYSTEM_PROMPT_GT_PLAIN` (line 26-32)
- [ ] Prompt nhánh GT_PLAIN: "So sánh HYP với GT để tìm hallucination" → khi cả HYP lẫn GT đều rỗng, LLM vẫn xem "60s audio mà không có text" = suspicious
- [ ] **Bug thực sự**: `llm_caller.py` line 131 → prompt gửi `"Hypothesis (plain transcript):\n"` (chuỗi rỗng) + `"Ground Truth:\n"` (chuỗi rỗng) → LLM không có đủ ngữ cảnh để kết luận "none"
- [ ] **Fix**: Thêm rule hậu xử lý trong `report_exporter.py` `apply_heuristics()`: nếu `hyp == ""` VÀ `gt == ""` → override thành `none/none`

### B2. `media_148393` — Deletion risk ở v3

**Hiện tượng:**
- v1/v2: transcript có nội dung, CER 47.87%, insertion `頑張りましょう`
- v3: transcript **rỗng**, CER `N/A (Empty)`, evaluator gán `none`

**Dữ liệu thực tế:**
- GT có nội dung rõ ràng: `"お電話ありがとうございます.建設のエスタと申します..."` (25.64s audio)
- v1/v2 transcript gần giống nhau (cùng nội dung, cùng insertion `頑張りましょう`)
- v3 RTF vẫn bình thường (2.439) → server vẫn xử lý file, nhưng VAD trả empty

**Nguyên nhân gốc rễ cần kiểm tra:**
- [ ] Server code `_run_inference_sync()` line 521-524: nếu `speech_detected == False` → return `""` → **VAD không phát hiện speech**
- [ ] Hoặc line 531-533: `trimmed_duration < 0.1` → skip
- [ ] **Giả thuyết chính**: Silero VAD với `VAD_THRESHOLD=0.5` + audio chất lượng thấp (telephone, 25.64s ngắn) → non-deterministic → v3 bị miss
- [ ] **Không có log VAD** trong `log_debug.txt` → không thể xác nhận → đây là **lỗi thiếu observability**
- [ ] v1 và v2 transcript **giống hệt nhau** (cùng `頑張りましょう`) → model deterministic (temperature=0) → VAD output khác nhau giữa các run là nguyên nhân

**Bằng chứng:**
- `v1 connect_time=1.125, v2=0.956, v3=1.204` → khác nhau chút → có thể GPU state khác
- `v3 wait_after_commit=61.329` vs `v1=61.005, v2=61.002` → inference vẫn chạy bình thường
- **Nhưng transcript rỗng** → VAD đã chặn trước khi inference

### B3. `media_148414` — Language collapse ổn định

**Hiện tượng:** Cả 3 run đều chèn tiếng Anh.
- v1: `"Hi, Joseph. How are you? I'm sorry."` + tiếng Nhật
- v2: `"Hi, Joseph. How are you?"` (không có `I'm sorry`)
- v3: `"Hi, Joseph. How are you? I'm sorry."` (giống v1)

**GT thực tế:** `"はい、中央清算管理課でございます..."` → hoàn toàn tiếng Nhật

**Nguyên nhân gốc rễ:**
- [ ] Đây là **model hallucination**, không phải lỗi VAD/chunking
- [ ] Voxtral model có bias: khi audio đầu file có khoảng lặng hoặc tín hiệu không rõ → model "đoán" ngôn ngữ sai → sinh tiếng Anh
- [ ] Server code không có language enforcement: line 275 `language = session_config.get("language", "ja")` nhưng comment nói rõ "Voxtral model does NOT support language hints via text prefix"
- [ ] **Kết luận**: Không thể fix bằng VAD/chunking → cần post-processing hoặc model fine-tuning

### B4. `media_149733` — Repetition/Merge ở v3

**Hiện tượng:**
- v2 CER: 56.13%, severity: medium
- v3 CER: 60.43%, severity: high
- v3 chứa `"という状態でしょうか?という状態でしょうか"` (lặp cụm)

**GT:** `"お手元には届いていないという状態でしょうか？"` (chỉ 1 lần)

**Nguyên nhân gốc rễ cần kiểm tra:**
- [ ] File dài 108.56s → chắc chắn bị chunk (CHUNK_LIMIT_SEC=15.0)
- [ ] `_merge_chunk_transcripts()` line 434-438: chỉ nối chuỗi đơn giản (`merged += chunk_text`) → **không xử lý overlap**
- [ ] `_create_vad_aware_chunks()` line 196-213: sub-chunking có `overlap_samples` → phần overlap sẽ được transcribe 2 lần → **merge không loại bỏ phần trùng**
- [ ] **Bug**: Comment ở line 423 nói "VAD chunks don't overlap" nhưng sub-chunking (khi segment > 15s) CÓ overlap → contradiction
- [ ] Cần trace: file 108.56s bị chia thành bao nhiêu chunk? Có sub-chunk nào bị overlap không?

### B5. `media_148439` — Contextual hallucination

**Hiện tượng:** Cả 3 run đều thêm phần mở đầu không có trong GT:
- v1/v3: `"こんにちは、ワイアンコープのシーケーションの坂本です。生徒キャパーンの熊谷でございます。"`
- v2: `"こんにちは、ワイアンコープの司会者の坂本です。生徒キャパーン熊谷でございます。"`

**GT:** `"こんにちは、株式会社のサカモトです. Assetojapanのクマガイでございます."`

**Phân tích:**
- [ ] Model nghe đúng "Sakamoto" và "Kumagaya" nhưng sai công ty
- [ ] `ワイアンコープ` vs `株式会社` → phonetic substitution nghiêm trọng
- [ ] `シーケーション` / `司会者` → model đoán nghề nghiệp
- [ ] **Nguyên nhân**: Model bias + audio chất lượng thấp (telephone) → substitution ổn định qua 3 run

### B6. `media_148954` — Phonetic substitution tên thương hiệu

**Hiện tượng:**
- v1: `"アセスジャパン"` (sai)
- v2/v3: `"アセプトジャパン"` (sai)
- GT: `"アセットジャパン"` (đúng)

**Phân tích:**
- [ ] v1 sai khác so với v2/v3 → model non-deterministic dù temperature=0 (do chunking/VAD khác nhau mỗi run)
- [ ] **Nguyên nhân**: Tên thương hiệu không nằm trong vocabulary phổ biến → model dùng nearest phonetic match
- [ ] **Fix tiềm năng**: Post-processing glossary hoặc hotword boosting (nếu model hỗ trợ)

### B7. `media_149291` — Language collapse + CER cải thiện ở v3

**Hiện tượng:**
- v1: CER 64.88%, high severity, `"かJust the Asaga. Suing Atari, probably."`
- v2: CER 54.51%, medium severity, không còn `"Suing Atari"` nhưng vẫn có nội dung khác
- v3: CER 50.21%, medium severity, vẫn có `"Just the Asaga"` nhưng thêm đoạn đầu mới

**GT:** File dài 156.64s, nội dung tiếng Nhật hoàn toàn

**Phân tích:**
- [ ] v3 CER tốt hơn v1/v2 đáng kể (50.21% vs 64.88%) → chunking khác nhau có thể ảnh hưởng
- [ ] v3 transcript dài hơn đáng kể → nhiều nội dung đúng hơn nhưng vẫn còn insertion
- [ ] `"Just the Asaga"` xuất hiện ở v1 và v3 nhưng không ở v2 → non-deterministic

### B8. `media_148280` — Phonetic substitution ổn định

**Hiện tượng:** Cả 3 run đều có `"お茶になっております"` thay vì GT `"お世話になっております"`

**Phân tích:**
- [ ] `お世話` → `お茶` : phonetic gần (`oseWA` vs `oCHA`) → model bias ổn định
- [ ] Lỗi xuất hiện 100% qua 3 run → **deterministic model error**, không phải random

### B9. `media_148284` — Minor insertion

**Hiện tượng:**
- v1: `"手掛けておりますね"` vs GT `"出かけておりますね"` → substitution
- v2/v3: thêm `"そうですね"` không có trong GT

**Phân tích:**
- [ ] Substitution nhỏ, severity medium → đúng
- [ ] CER v1: 57.31%, v2: 58.85%, v3: 58.46% → gần nhau → lỗi ổn định

### B10. `media_148394` — Insertion `お疲れ様です`

**Hiện tượng:** Cả 3 run đều thêm `"お疲れ様です"` (GT có `"お世話になります"`)

**Phân tích:**
- [ ] CER ổn định 32.16% qua cả 3 run → model deterministic
- [ ] `"絶対ご用件でしょうか?"` vs GT `"どういったご用件でしょうか？"` → substitution

---

## Phần C — Phân tích nguyên nhân hệ thống

### C1. Tại sao kết quả khác nhau giữa các run?

**Phát hiện quan trọng từ source code:**
- Server dùng `temperature=0.0` (line 287-288) → model output **lẽ ra phải deterministic**
- Nhưng VAD (Silero) có thể trả kết quả khác nhau do:
  - GPU floating point non-determinism
  - Torch random seed không được fix
- Khi VAD trả speech timestamps khác nhau → chunk boundaries khác nhau → model nhận input khác nhau → output khác nhau

**Việc cần làm:**
- [ ] Kiểm tra server có set `torch.manual_seed()` không → **KHÔNG CÓ** trong code
- [ ] Đây là nguyên nhân gốc rễ của sự khác biệt giữa v1/v2/v3

### C2. Tại sao không có log VAD config?

**Phát hiện:**
- `log_debug.txt` chỉ ghi: file name, RTF, "Done" → **không ghi bất kỳ tham số VAD nào**
- Server code có print VAD info (`_slog`) nhưng log đó ở **server console (Colab)**, không được capture về client/benchmark_runner
- `benchmark_runner.py` chỉ parse `stdout` của `run_asr.py` → không có kênh nhận VAD config

**Việc cần làm:**
- [ ] Xác nhận `run_asr.py` không request/log VAD config từ server
- [ ] **Fix**: Server nên trả VAD config trong response JSON, hoặc `run_asr.py` query `/v1/config` endpoint

### C3. Evaluator dùng LLM không ổn định

**Phát hiện:**
- Dùng `llama-3.3-70b-versatile` qua Groq API
- `temperature=0.0` → gần deterministic nhưng không guaranteed
- Cùng file, cùng transcript → severity có thể khác nhau giữa lần eval v1 vs v2 (do LLM randomness)
- Ví dụ: `media_149291` severity v1=high, v2=medium → có thể do LLM, không phải ASR thay đổi

**Việc cần làm:**
- [ ] So sánh `reasoning` column trong CSV giữa v1/v2/v3 cho cùng file
- [ ] Xác định trường hợp nào severity thay đổi do **ASR output thay đổi** vs do **LLM evaluator không ổn định**

---

## Phần D — Kiểm tra tính nhất quán giữa 3 file báo cáo

### D1. report.md vs issues_list.md vs hallucination_analysis.md

| Nội dung | report.md | issues_list.md | hallucination_analysis.md | Nhất quán? |
|----------|-----------|----------------|--------------------------|------------|
| v1 Avg CER | 39.63% | — | — | ✅ |
| v3 Avg CER | 37.10% | — | 37.10% | ✅ nhưng cả 2 không nói rõ mẫu số khác |
| media_148393 v3 | deletion risk | deletion risk | deletion risk | ✅ |
| silence_60s | lỗi evaluator | lỗi evaluator | lỗi evaluator | ✅ |
| media_149733 v3 lặp cụm | CER 60.43% | CER 60.43% | CER 60.43% | ✅ |
| High severity speech v2 | 2/9 | — | 2/9 | ✅ |

**Việc cần làm:**
- [ ] Xác nhận không có mâu thuẫn số liệu giữa 3 file
- [ ] Kiểm tra có thông tin nào chỉ xuất hiện ở 1 file mà thiếu ở file khác

---

## Phần E — Checklist thực thi

### Ưu tiên cao (Bug thực sự cần fix)
- [ ] **E1**: Fix evaluator — thêm rule: `hyp=="" AND gt==""` → `none/none` (file: `report_exporter.py`)
- [ ] **E2**: Fix merge overlap — `_merge_chunk_transcripts()` không xử lý sub-chunk overlap
- [ ] **E3**: Thêm VAD config vào log/response — ghi `VAD_THRESHOLD`, `VAD_PADDING_MS`, etc.
- [ ] **E4**: Fix Avg CER comparison — ghi rõ mẫu số khi có file `N/A`

### Ưu tiên trung bình (Cải thiện)
- [ ] **E5**: Set `torch.manual_seed()` cho VAD để kết quả reproducible
- [ ] **E6**: Thêm metric `deletion_rate` — đếm file có speech nhưng transcript rỗng
- [ ] **E7**: Thêm `empty_on_speech` counter vào `llm_eval_summary.json`

### Ưu tiên thấp (Model-level, cần research)
- [ ] **E8**: Language collapse → cần model fine-tuning hoặc language constraint
- [ ] **E9**: Phonetic substitution → glossary/hotword boosting
- [ ] **E10**: Contextual insertion → decoding constraint hoặc domain LM

---

**Người lập:** Deep Audit Agent  
**Ngày:** 05/05/2026  
**Dữ liệu đã đọc:** 18 files (3 reports + 3×results.json + 3×llm_eval_summary.json + 3×llm_eval_details.csv + 3×log_debug.txt + ground_truth.json + benchmark_20260505.json + source code)
