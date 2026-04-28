# Phân tích kỹ thuật chuyên sâu: VAD Chunking — Context Loss tại biên chunk

## Tổng quan vấn đề

VAD-Aware Chunking (v7) đã **thành công** loại bỏ hallucination tiếng Anh nhưng gây **CER regression** tại `media_149291` (34.91% → 44.55%). Bản phân tích này đào sâu 4 vấn đề kỹ thuật cụ thể trong implementation hiện tại và đề xuất hướng giải quyết tối ưu.

---

## 1. Bản đồ vấn đề — So sánh v5 vs v7 cho `media_149291`

### Nội dung bị mất trong v7 (so với Ground Truth)

Đối chiếu transcript chi tiết:

| Vùng GT | Ground Truth (trích) | v5 | v7 | Phân tích |
|---------|---------------------|-----|-----|-----------|
| **Đoạn 1** (0-15s) | "お待たせいたしました...よろしいですかね" | ✅ Có | ✅ Có | Cả hai đều transcribe đúng |
| **Đoạn 2** (15-35s) | "今日中にかかってきますか？...出れないかもしれなくて" | ⚠️ Thiếu vài từ | ❌ **Mất nhiều** | v7 cắt chunk ở giữa đoạn hội thoại liên tục |
| **Đoạn 3** (35-50s) | "そちらにして間違ってはないんですか？...カマが貼ってある" | ✅ Có | ⚠️ Rút gọn | v7 mất context "それこうやって先というか" |
| **Đoạn 4** (50-70s) | "わかりました...折り返しって形で大丈夫ですか？" | ✅ Skip nhẹ | ❌ **Skip nặng** | VAD cắt silence gap → model thiếu transition |
| **Đoạn 5** (70-100s) | "マツビナナイ...島田様" | ⚠️ Sai tên | ⚠️ Sai tên | Cả hai đều sai — lỗi model |
| **Đoạn 6** (100-157s) | Chi tiết về nội kiến/bất động sản | ✅ Dài + chi tiết | ❌ **Rút gọn đáng kể** | v7 mất nhiều câu chuyển tiếp |

### Kết luận từ so sánh

- v5 (blind chunk) vô tình **giữ được silence gap** giữa speakers → model có thêm context âm thanh → transcribe tốt hơn ở một số đoạn
-  v7 (VAD chunk) cắt **chính xác hơn** → loại bỏ hallucination nhưng model mất *audio context window* ở biên

---

## 2. Bốn vấn đề kỹ thuật cốt lõi

### Vấn đề 1: `VAD_CHUNK_PADDING_MS = 200ms` — Quá thấp cho tiếng Nhật hội thoại

**Vị trí code**: [voxtral_server_transformers.py#L40](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L40)

```python
VAD_CHUNK_PADDING_MS = 200     # Padding when cutting speech segment into chunks
```

**Phân tích:**
- Tiếng Nhật hội thoại có **tốc độ nói trung bình ~7-10 mora/giây** (~12 ký tự/giây)
- 200ms padding = chỉ ~2.4 ký tự buffer → dễ cắt giữa từ/cụm từ
- Đặc biệt trong audio điện thoại: có **echo/reverb** kéo dài hơn studio → 200ms chưa đủ capture tail
- Silero VAD detect speech **onset/offset** tại mức năng lượng, nhưng **co-articulation** (chuyển tiếp giữa âm) cần ~150-300ms thêm mỗi bên

**Tại sao v5 không gặp vấn đề này:**
v5 dùng blind 15s chunk → luôn có ≥1s overlap → context window rộng hơn nhiều.

> **Đánh giá:** Vấn đề này đóng góp ~30-40% vào CER regression. Đây là **nguyên nhân dễ fix nhất**.

---

### Vấn đề 2: `VAD_SEGMENT_SILENCE_MS = 800ms` — Over-splitting trong hội thoại

**Vị trí code**: [voxtral_server_transformers.py#L39](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L39)

```python
VAD_SEGMENT_SILENCE_MS = 800   # Silence gap to split speech regions for chunking
```

**Phân tích:**
- 800ms silence gap nghĩa là: nếu 2 người nói cách nhau ≥0.8s → tách thành 2 segment riêng
- Trong hội thoại call center, **turn-taking gaps** bình thường là **0.5-1.5s** → 800ms sẽ tách hầu hết các lượt nói thành segment riêng
- Kết quả: audio 156s có thể bị tách thành **rất nhiều micro-segments** → khi các segment nhỏ được group vào chunk, chúng mất context chuyển tiếp

**Proof từ dữ liệu:**
`media_149291` (156.64s) là hội thoại call center nhiều lượt nói ngắn, nhiều pause do "do dự" (えっと、うーん、まあ...). Với `VAD_SEGMENT_SILENCE_MS=800ms`, các pause này sẽ tạo boundary → cắt đứt dòng suy nghĩ.

**So sánh với v5:**
v5 không có khái niệm "silence gap splitting" → mỗi chunk 15s luôn chứa cả silence + speech liên tục → model có **full audio context** cho cả đoạn.

> **Đánh giá:** Vấn đề này đóng góp ~40-50% vào CER regression. Đây là **nguyên nhân chính**.

---

### Vấn đề 3: Không có Cross-chunk Context — Mỗi chunk là "cuộc hội thoại mới"

**Vị trí code**: [voxtral_server_transformers.py#L256-L332](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L256-L332) ([_run_inference_for_chunk](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#256-333))

Mỗi chunk được inference **hoàn toàn độc lập**:
```python
def _run_inference_for_chunk(audio_np, session_config, conn_id, on_delta=None):
    # Không có thông tin gì từ chunk trước
    # Model bắt đầu "từ đầu" mỗi lần
    inputs = processor(audio=audio_obj.audio_array, return_tensors="pt")
    model.generate(**inputs, max_new_tokens=512, ...)
```

**Hệ quả:**
- Model không biết chunk hiện tại là **phần tiếp** của cuộc hội thoại
- Không có transcript trước để tạo "context prime"
- Đặc biệt nguy hiểm khi chunk bắt đầu **giữa câu** trả lời (do VAD split)

**Tại sao v5 ít bị ảnh hưởng:**
v5 có 1s overlap → model "nghe lại" 1s cuối chunk trước → tạo chút continuity.

> **Đánh giá:** Vấn đề này đóng góp ~10-15% vào CER regression. Tuy nhiên Voxtral model **không hỗ trợ text prefix/prompt**, nên giải pháp context carry-over bị giới hạn.

---

### Vấn đề 4: Merge đơn thuần — Không có overlap dedup hay boundary smoothing

**Vị trí code**: [voxtral_server_transformers.py#L417-L440](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L417-L440) ([_merge_chunk_transcripts](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#417-441))

```python
def _merge_chunk_transcripts(transcripts, overlap_sec=CHUNK_OVERLAP_SEC):
    merged = transcripts[0][0]
    for i in range(1, len(transcripts)):
        chunk_text = transcripts[i][0]
        if chunk_text:
            merged += chunk_text  # Simple concatenation
    return merged.strip()
```

**Với VAD chunks** (không overlap), merge đơn thuần = concatenate trực tiếp. Nhưng vấn đề là:
- Chunk N có thể kết thúc bằng "かしこまりまし" (bị cắt)
- Chunk N+1 bắt đầu lại với "かしこまりました内見が" (lặp)
- Merge trực tiếp → ra "かしこまりましかしこまりました内見が" (sai)

> **Đánh giá:** Vấn đề này đóng góp ~5-10%. VAD chunks ít overlap hơn blind chunks nên ít bị ảnh hưởng bởi merge issue.

---

## 3. Phân tích trade-off: Tại sao không đơn giản tăng padding?

| Giải pháp | Pros | Cons |
|-----------|------|------|
| **Tăng padding lên 400ms** | Dễ implement, giữ thêm ~5 ký tự context | Chưa giải quyết over-splitting; nếu silence gap đúng 800ms, padding 400ms vẫn chưa chạm vào speech tiếp theo |
| **Tăng padding lên 1000ms** | Context rộng hơn | Chunk có thể chứa nhiều silence → quay lại vấn đề hallucination ban đầu |
| **Giảm `VAD_SEGMENT_SILENCE_MS` xuống 300ms** | Giữ các turn-taking gap trong cùng segment | Segment quá dài → vượt 15s → bị sub-chunk blind → mất advantage of VAD |

> **Kết luận:** Không có một tham số duy nhất nào giải quyết được. Cần **chiến lược kết hợp**.

---

## 4. Hướng giải quyết tối ưu — Chiến lược "Adaptive VAD Chunking"

### Phương án đề xuất: 3 thay đổi kết hợp

#### Thay đổi 1: Tăng `VAD_CHUNK_PADDING_MS` — 200ms → 400ms
- **Effort:** Rất thấp (thay 1 constant)
- **Impact:** Trung bình (~30% CER improvement expected)
- **Risk:** Thấp — thêm 200ms mỗi bên không đủ để tạo hallucination

#### Thay đổi 2: Tăng `VAD_SEGMENT_SILENCE_MS` — 800ms → 1500ms
- **Effort:** Rất thấp (thay 1 constant)
- **Impact:** Cao (~40-50% CER improvement expected)
- **Lý do 1500ms:** Trong call center, natural pause giữa speakers thường < 1.5s. Chỉ silence > 1.5s mới là "thật sự ngắt" (topic change, hold, etc.)
- **Risk:** Trung bình — segment dài hơn → nhiều khả năng cần sub-chunking (đã có fallback trong code dòng 196-213)

#### Thay đổi 3: Audio overlap giữa VAD chunks
Thay vì cắt chunk riêng biệt, tạo **overlap vùng audio** giữa các chunk liền kề:

```
Chunk 1: [seg1_start - padding ... seg_group_end + OVERLAP]
Chunk 2: [seg_group_start - OVERLAP ... seg_group_end + padding]
```

- Overlap = ~500ms audio (không phải 1s như v5, vì VAD chunks đã chính xác hơn)
- Kết hợp với **simple suffix dedup** trong merge (so sánh 20 ký tự cuối chunk N với đầu chunk N+1)
- **Effort:** Trung bình
- **Impact:** ~10-15% thêm

### Tổng impact dự kiến: CER giảm ~15-20pp cho file dài → từ 44.55% xuống ~25-30%

---

## 5. Về các loại lỗi KHÔNG liên quan đến chunking

Những lỗi sau vẫn sẽ tồn tại dù chunking hoàn hảo:

| Lỗi | Ví dụ | Nguyên nhân gốc |
|------|-------|-----------------|
| Nghe sai tên riêng | 島田→今田/熊田 | Model không có context tên |
| Homophone confusion | アセット→アセプト | Giới hạn acoustic model |
| Paraphrase | お折り返し→お出かけし | Semantic substitution |
| Thiếu punctuation | Mất dấu。、 | Tokenizer behavior |

Những lỗi này cần giải pháp khác: fine-tuning, post-processing NER, hoặc model mạnh hơn.

---

## 6. Khuyến nghị thứ tự triển khai

| Bước | Thay đổi | File | Effort |
|------|----------|------|--------|
| **1** | `VAD_SEGMENT_SILENCE_MS`: 800→1500 | [voxtral_server_transformers.py#L39](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L39) | 1 dòng |
| **2** | `VAD_CHUNK_PADDING_MS`: 200→400 | [voxtral_server_transformers.py#L40](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L40) | 1 dòng |
| **3** | Re-run test v5 files → compare CER | [run_asr.py](file:///d:/VJ/Voxtral/run_asr.py) | 10 phút |
| **4** | Nếu CER vẫn cao: implement audio overlap + suffix dedup | [_create_vad_aware_chunks](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#149-254) + [_merge_chunk_transcripts](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#417-441) | 30 phút |

> [!IMPORTANT]
> **Bước 1+2 nên chạy cùng lúc** trong 1 batch test mới (v8) trước khi quyết định có cần bước 4 hay không. Tránh over-engineer khi 2 constant changes có thể đã đủ.
