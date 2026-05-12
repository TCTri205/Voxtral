# Optimize VAD & Hallucination Recovery Plan

Kế hoạch này nhằm khắc phục triệt để tình trạng model (Voxtral/Mistral) bị ảo giác (hallucination) sinh ra tiếng Anh ở đầu file do VAD nhận diện nhầm tiếng ồn/tiếng thở thành giọng nói.

## Đánh giá các thay đổi đề xuất

Kế hoạch của bạn **rất hợp lý và mang tính thực tiễn cao**. Dưới đây là phân tích chi tiết cho từng điểm:

1. **VAD_THRESHOLD (0.5 → 0.65)**: Hoàn toàn đồng ý. Silero VAD khá nhạy, việc tăng lên 0.65 sẽ giúp lọc bỏ các tiếng thở nhẹ và nhiễu nền ở đầu file.
2. **VAD_MIN_SPEECH_DURATION_MS (250 → 400)**: Rất tốt. Nó sẽ bỏ qua các âm thanh tạp (như tạch lưỡi, tiếng sột soạt) dưới 400ms. Tuy có rủi ro nhỏ là bỏ sót các từ đệm cực ngắn (như "はい" nói nhanh), nhưng như bạn nói, trong bối cảnh cuộc gọi doanh nghiệp, độ ổn định quan trọng hơn nhiều so với một từ đệm.
3. **VAD_PADDING_MS (500 → 300)**: Thay đổi này rất "đắt giá". Giảm padding xuống 300ms vẫn giữ an toàn cho đầu/cuối câu nhưng loại bỏ được 200ms "âm thanh rác" có thể làm mồi cho ảo giác.
4. **Dùng `RETRY_TEMPERATURE = 0.5` cho lần Retry**: Rất chính xác. Nếu dùng Greedy Search (Temperature = 0) cho lần retry, model rất dễ đi vào "vết xe đổ" cũ bất chấp có thêm context. Tăng temperature lên 0.5 giúp model "thoát vòng lặp" và tính toán lại xác suất từ vựng mượt mà hơn.
5. **Fallback cắt 500ms cho Chunk 0**: Đây là một bước bảo vệ an toàn (fail-safe) tuyệt vời. Vì fallback này *chỉ kích hoạt* khi chunk 0 bị lỗi tiếng Anh VÀ đã dùng Anchor thất bại, nên lúc này transcript ban đầu đằng nào cũng không xài được. Việc hy sinh 500ms đầu tiên để cứu toàn bộ nội dung tiếng Nhật phía sau là sự đánh đổi hoàn toàn xứng đáng.

---

## User Review Required

> [!IMPORTANT]
> Cần xác nhận chi tiết implement cho Fallback Chunk 0: Nếu nhóm chunk bị lỗi chứa Chunk 0 (vd: `group = [0]`), ta sẽ tạo ra một audio mới bằng cách lấy audio của nhóm đó và cắt bỏ 500ms đầu tiên (`cutoff_samples = int(0.5 * 16000)`). Sau đó chạy lại inference (không cần anchor nữa). Nếu kết quả tốt, nó sẽ thay thế transcript của chunk. Bạn có đồng ý với logic code này không?

## Proposed Changes

### `voxtral_server_transformers.py`

#### 1. Cập nhật các hằng số VAD
```python
# Silero VAD configuration (optimized for Japanese telephone audio)
VAD_THRESHOLD = 0.65  # Speech probability threshold (0.0-1.0)
VAD_MIN_SPEECH_DURATION_MS = 400  # Minimum speech segment duration to be considered
VAD_MIN_SILENCE_DURATION_MS = 100  # Minimum silence gap to split segments

# Online VAD-Aware Chunking config
VAD_SEGMENT_SILENCE_MS = 800   # Silence gap to split speech regions for chunking
VAD_CHUNK_PADDING_MS = 200     # Padding when cutting speech segment into chunks
VAD_PADDING_MS = 300  # Padding around speech segments to avoid cutting off audio
```

#### 2. Áp dụng Temperature 0.5 cho Phase 2 Retry
Tại Phase 2 (Language Collapse Recovery), tạo một bản copy của `retry_config` và cập nhật temperature:
```python
temp_retry_config = retry_config.copy()
temp_retry_config["temperature"] = str(RETRY_TEMPERATURE)
```
Thay thế `retry_config` bằng `temp_retry_config` trong hàm `_run_inference_for_chunk` khi thực hiện Retry nhóm (và cả Fallback).

#### 3. Implement Fallback cho Chunk 0
Trong khối `else` khi retry với Anchor thất bại (`not retry_detection["is_collapsed"]` là False):
```python
if 0 in group:
    _slog(conn_id, f"[LangCollapse] Group {group} retry FAILED, trying fallback for Chunk 0 (trim 500ms)")
    cutoff_samples = int(0.5 * 16000)
    group_audio = np.concatenate([chunks[i]['audio_np'] for i in group])
    
    if len(group_audio) > cutoff_samples + int(0.5 * 16000): # Ensure at least 0.5s remains
        fallback_audio = group_audio[cutoff_samples:]
        fallback_transcript, _ = _run_inference_for_chunk(fallback_audio, temp_retry_config, conn_id)
        fallback_detection = _detect_language_collapse(fallback_transcript)
        
        if not fallback_detection["is_collapsed"]:
            for j, idx in enumerate(group):
                if j == 0:
                    transcripts[idx] = (fallback_transcript, transcripts[idx][1])
                else:
                    transcripts[idx] = ("", transcripts[idx][1])
            lang_retries.append({"group": group, "anchor": anchor_idx, "status": "fixed_fallback_trim"})
            _slog(conn_id, f"[LangCollapse] Group {group} fixed via 500ms trim fallback")
        else:
            lang_retries.append({"group": group, "anchor": anchor_idx, "status": "failed_fallback"})
            _slog(conn_id, f"[LangCollapse] Group {group} fallback FAILED, keeping original")
    else:
        lang_retries.append({"group": group, "anchor": anchor_idx, "status": "failed"})
        _slog(conn_id, f"[LangCollapse] Group {group} audio too short for fallback")
else:
    lang_retries.append({"group": group, "anchor": anchor_idx, "status": "failed"})
    _slog(conn_id, f"[LangCollapse] Group {group} retry FAILED (ratio {retry_detection['ascii_ratio']}), keeping original")
```

## Verification Plan

### Automated Tests
- Chạy `python run_asr.py --audio "media_148414_1767922241264 (1).mp3"` và xác nhận ở đầu file không còn xuất hiện `Hi, Joseph...`. Transcript phải bắt đầu từ `はい、中央清算管理課...`.
- Chạy Benchmark trên tập mẫu (5-10 file chất lượng bình thường) để kiểm tra độ tin cậy của VAD, xem các tinh chỉnh này có ảnh hưởng tiêu cực tới các file đã hoạt động tốt hay không.

### Manual Verification
- Kiểm tra file log JSON (`results.json`): xem metadata `vad_config` đã hiển thị đúng các giá trị 0.65, 400, 300 hay chưa.
- Kiểm tra mốc `first_speech_start_sec` trong kết quả vad_result xem nó đã dịch chuyển khỏi khu vực 0.7s để tiến đến khu vực giọng nói thật (1-3s) hay chưa.
- Kiểm tra list `lang_collapse_retries` để theo dõi các thao tác recovery và xem `fallback_trim` có được kích hoạt và hoạt động đúng không.
