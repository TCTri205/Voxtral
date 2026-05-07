# Fix Evaluator & Observability — E1/E2/E3/E4

Bốn bug ưu tiên cao từ Deep Audit Plan cần được fix để đảm bảo tính chính xác của pipeline đánh giá và khả năng tái hiện kết quả.

## Proposed Changes

### E1: Fix evaluator — `hyp=="" AND gt==""` → `none/none`

**Vấn đề gốc rễ (B1 trong deep_audit_plan):**
- `silence_60s.wav` có cả `hyp_transcript` và `gt_plain` đều rỗng (`""`)
- Evaluator vẫn gửi prompt rỗng cho LLM → LLM trả `silence_text/high` vì thấy "60s audio mà không có text"
- Kết quả sai: file silence bị đếm vào hallucination rate → v1/v2: 10/11 thay vì 9/10

**Fix:**

#### [MODIFY] [report_exporter.py](file:///d:/VJ/Voxtral/llm_evaluator/report_exporter.py)

Thêm rule vào `apply_heuristics()` (line 17-25): kiểm tra nếu **cả** `hyp_transcript` và `gt` (plain hoặc timestamped) đều rỗng → override thành `none/none`. Cần truyền thêm `candidates` vào `apply_heuristics()` để so khớp `filename` → lấy `gt_plain`/`gt_timestamped`.

```python
def apply_heuristics(results, candidates=None):
    # Build GT lookup from candidates
    gt_lookup = {}
    if candidates:
        for c in candidates:
            gt_text = (c.gt_timestamped or c.gt_plain or "").strip()
            gt_lookup[c.filename] = gt_text

    for res in results:
        # Rule 1: Both HYP and GT are empty → not a hallucination
        gt_text = gt_lookup.get(res.filename, "")
        hyp_text = ""  # will be populated from evidence
        # Since we don't store raw hyp in result, check if the existing CER
        # hints at empty transcript: "0.00%" CER with none-able GT = empty match
        if not gt_text:
            cer = parse_cer(res.existing_cer)
            if cer is not None and cer == 0.0:
                res.has_hallucination = False
                res.primary_error = "none"
                res.severity = "none"
                res.reasoning = "HYP and GT both empty — correctly silent, no hallucination."
                res.review_status = "auto_accept"
                continue
        # ... existing heuristic
```

Nhưng cách này gián tiếp. **Cách trực tiếp hơn**: truyền `candidates` list vào, lookup `hyp_transcript` trực tiếp.

**Thay đổi thực tế:**

1. **`report_exporter.py` → `apply_heuristics()`**: Thêm param `candidates: List[EvaluationCandidate] = None`. Build `hyp_lookup` = `{c.filename: c.hyp_transcript for c in candidates}` và `gt_lookup` = `{c.filename: (c.gt_plain or c.gt_timestamped or "") for c in candidates}`. Nếu `hyp == ""` VÀ `gt.strip() == ""` → override `has_hallucination=False, primary_error="none", severity="none"`.

2. **`batch_runner.py` line 78**: Truyền `candidates` vào `apply_heuristics(results, candidates)`.

---

### E2: Fix merge overlap — `_merge_chunk_transcripts()` xử lý sub-chunk overlap

**Vấn đề gốc rễ (B4 trong deep_audit_plan):**
- `_create_vad_aware_chunks()` line 196-213: khi 1 VAD segment dài > `CHUNK_LIMIT_SEC` (15s), nó được sub-chunk với `overlap_samples` = `CHUNK_OVERLAP_SEC * sample_rate` = `1.0 * 16000` = 16000 samples (1 giây)
- `_merge_chunk_transcripts()` line 434-438: **chỉ nối chuỗi đơn giản** (`merged += chunk_text`), **bỏ qua overlap hoàn toàn**
- Comment line 423 nói "VAD chunks don't overlap" — **sai** với trường hợp sub-chunking
- Kết quả: `media_149733` (108.56s) bị lặp `という状態でしょうか` vì phần overlap 1s được transcribe 2 lần

**Fix:**

#### [MODIFY] [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py)

**Thay đổi 1 — `_create_vad_aware_chunks()`**: Thêm field `is_sub_chunk: bool` vào mỗi chunk dict để đánh dấu chunk nào đến từ sub-chunking (có overlap).

**Thay đổi 2 — `_merge_chunk_transcripts()`**: 
- Nhận thêm param `chunk_infos: list = None` chứa metadata (bao gồm `is_sub_chunk`)
- Khi merge 2 sub-chunk liên tiếp, **tìm và loại bỏ suffix trùng** bằng heuristic: tìm suffix dài nhất của chunk trước trùng prefix của chunk sau (character-level fuzzy matching cho Japanese text vì token boundaries có thể khác)
- Fallback: nếu không tìm thấy overlap → nối đơn giản (giữ hành vi cũ)

**Algorithm overlap removal:**
```python
def _find_overlap(prev_text: str, next_text: str, max_overlap_chars: int = 100) -> int:
    """Find the longest suffix of prev_text that matches a prefix of next_text."""
    if not prev_text or not next_text:
        return 0
    # Limit search window
    search_len = min(len(prev_text), len(next_text), max_overlap_chars)
    for length in range(search_len, 0, -1):
        if prev_text[-length:] == next_text[:length]:
            return length
    return 0
```

> [!IMPORTANT]
> Japanese text không có khoảng trắng giữa các từ, nên overlap detection phải dùng **exact character matching**. Fuzzy matching (Levenshtein) sẽ quá chậm và phức tạp. Exact match là đủ vì cùng 1 model với cùng input overlap → output overlap gần như giống hệt.

---

### E3: Thêm VAD config vào log/response

**Vấn đề gốc rễ (C2 trong deep_audit_plan):**
- `log_debug.txt` chỉ ghi: file name, RTF, "Done" → **không ghi bất kỳ tham số VAD nào**
- Server code có `_slog()` nhưng log chỉ ở **server console (Colab)**, client không nhận
- `run_asr.py` không có cơ chế nhận VAD config từ server
- Kết quả: khi v3 cho transcript rỗng ở `media_148393`, **không thể xác nhận** threshold VAD là bao nhiêu

**Fix — 2 phần:**

#### [MODIFY] [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py)

**Phần 3a — Server**: Thêm VAD config vào response `response.audio_transcript.done`:
```json
{
    "type": "response.audio_transcript.done",
    "transcript": "...",
    "vad_config": {
        "vad_threshold": 0.5,
        "vad_padding_ms": 500,
        "vad_min_speech_ms": 250,
        "vad_min_silence_ms": 100,
        "chunk_limit_sec": 15.0,
        "chunk_overlap_sec": 1.0,
        "server_version": "2026-04-24.1"
    },
    "vad_result": {
        "speech_detected": true,
        "num_segments": 5,
        "num_chunks": 3,
        "original_duration_sec": 108.56,
        "trimmed_duration_sec": 102.3
    }
}
```

Cụ thể: cần refactor `_run_inference_sync()` để return thêm metadata dict (hiện chỉ return `transcript: str`). Thay đổi return type thành `tuple[str, dict]` với dict chứa VAD config + result.

#### [MODIFY] [run_asr.py](file:///d:/VJ/Voxtral/run_asr.py)

**Phần 3b — Client**: 
- Parse `vad_config` và `vad_result` từ response
- Ghi vào `results.json` mỗi file entry
- Log vào `log_debug.txt`

---

### E4: Fix Avg CER comparison — ghi rõ mẫu số

**Vấn đề gốc rễ (A1 trong deep_audit_plan):**
- v3 `media_148393` trả transcript rỗng → `cer = "N/A (Empty)"` → `parse_cer()` return `None` → **file bị loại khỏi mẫu số**
- v3 Avg CER = `37.10%` tính trên **10 file**, trong khi v1/v2 tính trên **11 file**
- Báo cáo không nói rõ sự khác biệt → so sánh không công bằng

**Fix — 2 phần:**

#### [MODIFY] [report_exporter.py](file:///d:/VJ/Voxtral/llm_evaluator/report_exporter.py)

Trong `export_summary_json()`:
- Thêm `cer_file_count` (bao nhiêu file được tính CER) và `cer_excluded_files` (danh sách file bị loại + lý do) vào summary JSON
- Thêm metric mới: `deletion_count` (file có speech GT nhưng transcript rỗng) và `empty_on_speech_count`

#### [MODIFY] [evaluate_metrics.py](file:///d:/VJ/Voxtral/evaluate_metrics.py)

Trong `main()`:
- Thêm ghi chú vào report markdown: `"Average CER tính trên X/Y file (Z file bị loại: ...)"`
- Track danh sách file bị loại (CER = `"N/A (Empty)"`)

#### [MODIFY] [report_exporter.py](file:///d:/VJ/Voxtral/llm_evaluator/report_exporter.py) — Markdown report

Trong `export_markdown_report()`:
- Thêm dòng ghi chú `CER denominator` và `excluded files` vào summary section

---

## File Impact Summary

| File | E1 | E2 | E3 | E4 | Changes |
|------|----|----|----|----|---------|
| `llm_evaluator/report_exporter.py` | ✅ | | | ✅ | `apply_heuristics()` + `export_summary_json()` + `export_markdown_report()` |
| `llm_evaluator/batch_runner.py` | ✅ | | | | Truyền `candidates` vào `apply_heuristics()` |
| `voxtral_server_transformers.py` | | ✅ | ✅ | | `_merge_chunk_transcripts()` + `_run_inference_sync()` return type + response payload |
| `run_asr.py` | | | ✅ | | Parse `vad_config`/`vad_result` từ response |
| `evaluate_metrics.py` | | | | ✅ | Ghi chú mẫu số CER vào report |

---

## Verification Plan

### Automated Tests
1. **E1**: Tạo test case với `hyp=""` + `gt=""` → xác nhận `apply_heuristics()` trả `none/none`
2. **E2**: Tạo test case `_merge_chunk_transcripts()` với 2 transcript có overlap text → xác nhận overlap bị loại
3. **E4**: Tạo test case `export_summary_json()` với 1 file CER=`None` → xác nhận `cer_file_count < total_files` và `cer_excluded_files` có entry

### Manual Verification
1. **E3**: Chạy 1 file test qua server → kiểm tra response JSON có `vad_config` field
2. **Chạy lại LLM eval** trên v1/v2/v3 kết quả cũ → so sánh hallucination rate mới (sau fix E1) với rate cũ
3. Kiểm tra `silence_60s.wav` được đánh giá `none/none` ở cả 3 run

> [!WARNING]
> **E3 yêu cầu thay đổi server code** (`voxtral_server_transformers.py`). Server chạy trên Colab nên cần deploy lại. Fix E1/E2/E4 chỉ ảnh hưởng client-side, có thể test local ngay.
