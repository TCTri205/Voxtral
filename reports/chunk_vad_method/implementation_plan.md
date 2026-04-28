# Kế hoạch Phân tích Hallucination Tiếng Anh — media_148954 & media_149291

## Bối cảnh

Trong batch `28-04-2026_v1`, 2 file dài nhất bị hallucination tiếng Anh:

| File | Duration | Hallucination | Vị trí trong transcript |
|------|----------|---------------|------------------------|
| `media_148954` | 95.96s | *"Now, how does someone communicate their own number? How many times have you called someone? Yes. In Japan,"* | Giữa phần đọc SĐT và giờ làm việc |
| `media_149291` | 156.64s | *"So this call. Just to ask that."* | Sau đoạn hỏi về callback schedule |

---

## Phân tích Kiến trúc Server (đã xác nhận từ source code)

Pipeline xử lý trong [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py):

```
Audio → VAD Trim (đầu/cuối only) → Chunked Inference (15s/chunk, 1s overlap) → Simple Merge → Guardrails
```

### Vấn đề đã xác nhận trong code:

| # | Vấn đề | File/Line | Chi tiết |
|---|--------|-----------|----------|
| 1 | **VAD chỉ trim đầu/cuối** | [L70-128](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L70-L128) | [_trim_silence_with_vad()](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#70-129) lấy `first_start` → `last_end`, **không loại bỏ silence giữa file** |
| 2 | **Chunk cắt cơ học** | [L376-384](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L376-L384) | Fixed 15s sliding window, **không align theo speech boundaries** |
| 3 | **Merge thô** | [L252-258](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L252-L258) | `TODO: Implement smarter overlap detection` — đang chỉ concatenate |
| 4 | **Guardrails vô hiệu** | [L203-232](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L203-L232) | Chỉ check "transcript ngắn", **không detect tiếng Anh trong audio JP** |
| 5 | **`VOXTRAL_RETRY_HALLUCINATION` = false** | [L34](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L34) | Retry mechanism tắt, và dù bật cũng không giúp vì guardrails sai |

---

## Phân tích Chunk Boundaries vs Hallucination

### media_148954 (95.96s → ~7 chunks)

```
Chunk 1: [0.0s - 15.0s]   ← Greeting + Introduction
Chunk 2: [14.0s - 29.0s]  ← Hỏi truyền lời nhắn
Chunk 3: [28.0s - 43.0s]  ← Nhắc lại tên, kể về SĐT
Chunk 4: [42.0s - 57.0s]  ← 🔴 ĐỌC GIỜ LÀM VIỆC → HALLUCINATION
Chunk 5: [56.0s - 71.0s]  ← 🔴 HALLUCINATION TIẾP TỤC + KẾT THÚC
Chunk 6: [70.0s - 85.0s]  ← Xác nhận, cảm ơn
Chunk 7: [84.0s - 96.0s]  ← Chào tạm biệt
```

**Hallucination xảy ra tại Chunk 4-5 (~42-71s).** RTTM xác nhận khu vực này có **nhiều micro-segments** (0.2-0.4s speech, ví dụ: "21時、はい" tại 44-47s, "17時、はい" tại 48-49s) xen kẽ im lặng. Model nhận chunk 15s với tín hiệu "rời rạc" → mất context → hallucinate.

**Ground truth tương ứng (~42-67s):**
> 営業。。。あの、受付の時間が、平日朝9時から21時まで → 21時、はい → 土日祝日が朝9時から17時まで → 17時、はい → 私以外の者でも案内できるんしておりますので、お電話いただきたいの伝言、お願いしてもよろしいでしょうか？

**ASR output (chunk 4-5 merged):**
> ...実は中原さんの携帯電話を聞いていただきました。**Now, how does someone communicate their own number? How many times have you called someone? Yes. In Japan,** 平日朝9時から21時まで...

→ Hallucination thay thế đoạn "留守番電話に銀行名と電話番号などは吹き込みさせていただいているので、番号自体はご存じでいらっしゃいます" — đây là **nội dung về "truyền đạt số điện thoại"**. Model đã dịch ý nghĩa sang tiếng Anh thay vì transcribe.

### media_149291 (156.64s → ~12 chunks)

```
Chunk 1: [0.0s - 15.0s]   ← Introduction, callback request
Chunk 2: [14.0s - 29.0s]  ← Availability discussion
Chunk 3: [28.0s - 43.0s]  ← 🔴 KHOẢNG LẶNG DÀI + HALLUCINATION
Chunk 4: [42.0s - 57.0s]  ← Property identification
...
Chunk 12: [~140s-157s]     ← Goodbye
```

**Hallucination tại Chunk 3 (~28-43s).** RTTM cho thấy khu vực 29-48s có:
- SPEAKER_2: 29.650-47.891 (18.2s liên tục) — nhưng GT cho thấy chỉ nói "わかりました。えっと、どうしようかな。うーん、まあ、わかりました。大丈夫です。"
- SPEAKER_1 xen kẽ tại 35.197-35.590 (0.4s)

Khu vực ~35-47s có **nhiều pause dài + do dự** ("えっと、どうしようかな。うーん、まあ"). Chunk 3 nhận toàn bộ khu vực rời rạc này → hallucinate *"So this call. Just to ask that."*

---

## Giả thuyết Nguyên nhân (Updated)

### H1: Silence/Low-energy cho từng chunk (CHÍNH — Ưu tiên cao nhất)
- VAD chỉ trim đầu/cuối → silence/pause **giữa file** vẫn tồn tại trong từng chunk
- Chunk 15s chứa nhiều micro-segments xen kẽ im lặng → model hallucinate
- **Bằng chứng mạnh:** Cả 2 hallucination đều xảy ra tại khu vực micro-segment + pause dài

### H2: Loss of context tại chunk boundaries (PHỤ — Góp phần)
- Mỗi chunk xử lý **độc lập** (không có context từ chunk trước)
- Prompt chỉ là "日本語で書き起こしてください。" — không đủ mạnh để giữ ngôn ngữ target
- Overlap 1s chỉ tạo overlap audio, không giúp model maintain context

### H3: Semantic hallucination (MỚI — Cần kiểm chứng)
- `media_148954`: Hallucination *"how does someone communicate their own number"* khớp về **ngữ nghĩa** với nội dung thực (đang nói về truyền đạt số điện thoại)
- Đây có thể là model **"hiểu" nội dung nhưng output sai ngôn ngữ** — dấu hiệu của cross-lingual confusion trong multilingual model

### H3-old: Server overload (LOẠI BỎ - Không liên quan)
- `media_148954` chỉ có 49 keepalive (bình thường cho 96s audio)
- Keepalive chỉ là heartbeat (mỗi 5s), không phải indicator overload
- Cả 2 file đều có inference RTF ~2.63-2.64, giống các file khác

---

## Kế hoạch Phân tích — 3 Pha

### Pha 1: Static Analysis (không cần server)

#### 1.1 — Tính chunk boundaries chính xác
Tạo script mô phỏng **chính xác** thuật toán chunking của server để map:
- Chunk nào chứa hallucination
- Audio content thực tế trong chunk đó (dựa trên RTTM)
- Tỷ lệ speech vs silence trong từng chunk

#### 1.2 — Waveform + Energy Analysis
Dùng `librosa` phân tích từng chunk nghi ngờ:
- RMS energy profile → xác định khoảng im lặng nội bộ
- Spectrogram → phát hiện nhiễu hoặc tín hiệu lạ
- So sánh với chunk "sạch" (không hallucination)

#### 1.3 — Text alignment analysis
So sánh transcript ASR với ground truth trên từng chunk:
- Chunk nào match tốt, chunk nào diverge
- Character position của hallucination trong merged transcript

**Scripts cần tạo:**
| Script | Chức năng |
|--------|-----------|
| `scripts/analyze_hallucination.py` | Tổng hợp: tính chunks, map RTTM, text alignment |
| `scripts/waveform_analyzer.py` | Phân tích waveform + energy profile |

**Commands:**
```bash
python scripts/analyze_hallucination.py --file "media_148954_1768789819598 (1).mp3" --file "media_149291_1769069811005.mp3"
python scripts/waveform_analyzer.py --file "audio/media_148954_1768789819598 (1).mp3" --output reports/hallucination_analysis/
python scripts/waveform_analyzer.py --file "audio/media_149291_1769069811005.mp3" --output reports/hallucination_analysis/
```

---

### Pha 2: Controlled Experiments (cần server)

#### 2.1 — Isolate chunk nghi ngờ
Cắt audio đúng tại chunk boundaries và chạy inference riêng:
```bash
# media_148954: cắt chunk 4 (42-57s) và chunk 5 (56-71s)
ffmpeg -i "audio/media_148954_…mp3" -ss 42 -t 15 tmp/test_148954_chunk4.wav
ffmpeg -i "audio/media_148954_…mp3" -ss 56 -t 15 tmp/test_148954_chunk5.wav

# media_149291: cắt chunk 3 (28-43s)  
ffmpeg -i "audio/media_149291_…mp3" -ss 28 -t 15 tmp/test_149291_chunk3.wav

# Chạy ASR trên từng chunk đơn lẻ
python run_asr.py --audio tmp/test_148954_chunk4.wav
```

#### 2.2 — VAD-aware chunking test
Tạo script "smart chunk" sử dụng VAD boundaries thay vì fixed 15s:
```bash
python scripts/vad_smart_chunk.py --file "audio/media_148954_…mp3" --output tmp/smart_chunks/
# Chạy ASR trên từng smart chunk
```

#### 2.3 — Prompt engineering test
Test thay đổi system prompt cho mỗi chunk:
- Tăng cường "日本語のみ" constraint
- Thêm context từ chunk trước (nối transcript chunk N-1 vào prompt chunk N)

#### 2.4 — Re-run full file khi server idle
Để loại trừ tính ngẫu nhiên (temperature=0 nên lẽ ra deterministic):
```bash
python run_asr.py --audio "audio/media_148954_…mp3" --server-audio-dir /path/on/server
```

---

### Pha 3: Tổng hợp & Giải pháp

#### 3.1 — Report
Tạo `reports/hallucination_analysis/findings.md`:
- Nguyên nhân gốc xác nhận
- Bằng chứng cụ thể (waveform + text alignment)

#### 3.2 — Giải pháp ưu tiên

| Ưu tiên | Giải pháp | Thay đổi code |
|---------|-----------|---------------|
| **P0** | **Language Detection Guardrail**: Detect ký tự Latin/tiếng Anh trong output JP | Sửa [_check_hallucination_guardrails()](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#203-233) |
| **P1** | **VAD-aware Chunking**: Chia chunk theo speech boundaries (VAD segments), không fixed 15s | Sửa [run_inference_with_config()](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#358-401) |
| **P2** | **Intra-chunk VAD**: Loại silence **giữa** mỗi chunk trước khi inference | Mới — thêm stage giữa VAD trim và inference |
| **P3** | **Context Carry-over**: Nối transcript chunk trước vào prompt chunk sau | Sửa [_run_inference_for_chunk()](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#131-201) |
| **P4** | **Smart Merge**: Implement overlap dedup (hiện là TODO) | Sửa [_merge_chunk_transcripts()](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#235-261) |

---

## Verification Plan

### Pha 1 — Tự động (offline)
```bash
python scripts/analyze_hallucination.py   # → output chunk map + text alignment
python scripts/waveform_analyzer.py       # → output waveform charts
```

### Pha 2 — Cần server  
1. Chạy Voxtral server
2. Thực hiện experiments 2.1→2.4 tuần tự
3. So sánh transcript mới vs transcript cũ + GT

### Pha 3 — Sau khi có kết quả  
1. Tổng hợp findings
2. Implement P0 (guardrail tiếng Anh — nhanh nhất), deploy, re-test
3. Implement P1-P2 nếu P0 chưa đủ
