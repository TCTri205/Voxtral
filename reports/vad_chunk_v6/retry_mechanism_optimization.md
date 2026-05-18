# Báo Cáo Tổng Hợp: Tối Ưu Hóa Cơ Chế Thử Lại & Khôi Phục Chất Lượng Voxtral ASR

Báo cáo này tổng hợp toàn bộ phân tích kỹ thuật về cơ chế thử lại (retry mechanism), chẩn đoán nguyên nhân sự cố sụt giảm chất lượng (regression) ở phiên bản **v14** hiện tại, và thiết lập **kịch bản hành động chi tiết** để khôi phục hệ thống về trạng thái tối ưu nhất vào ngày mai.

---

## 1. So Sánh Hiệu Năng & Xác Định Phiên Bản Ổn Định

Dựa vào việc chạy thực tế tập test 11 file âm thanh chuẩn của Voxtral, hiệu năng giữa phiên bản ổn định cũ và phiên bản hiện tại có sự chênh lệch cực kỳ nghiêm trọng:

| Chỉ số đo lường | Bản ổn định **v11** (Commit `d882aad`) | Bản hiện tại **v14** (Commit `58db424`) | Đánh giá chênh lệch (Delta) |
| :--- | :---: | :---: | :---: |
| **Speech-only Average CER** | **40.93%** | **45.81%** | **+4.88% 📈 (Tệ hơn nhiều)** |
| **Inference Average RTF** | **3.62** | **4.66** | **+1.04 ⏱️ (Chậm hơn 30%)** |
| **Worst-file CER (`media_148439`)** | **30.29%** | **71.15%** | **+40.86% 📈 (Thảm họa)** |
| **V Verdict (Cổng kiểm thử)** | **PASSED (v11)** | **REJECTED (v14)** | **Thất bại toàn bộ các Gate chất lượng** |

### 📌 Commit ổn định cần ghi nhớ:
Bản ổn định đạt kỷ lục CER thấp nhất và tốc độ tối ưu là commit:
👉 **`d882aad481eb2bfc915da9bfd0fa27cdb9969b1e`** *(Tên commit: `fix: remove TimeBasedStoppingCriteria, revert VAD_SEGMENT_SILENCE_MS=700, revert n_range=(3,4,5) - v11`)*.

---

## 2. Phân Tích Nguyên Nhân Chí Mạng Gây Regression Ở v14

Qua việc thực hiện đối chiếu mã nguồn (`git diff d882aad HEAD`), chúng ta xác định được **3 thay đổi sai lệch** trong cấu hình VAD và thuật toán phân chunk ở v14 đã phá hủy chất lượng dịch:

### Yếu tố 1: Tăng VAD Padding lên mức cực đoan (`VAD_PADDING_MS`)
* **Trong bản v11:** `VAD_PADDING_MS = 300` (đệm 300ms im lặng xung quanh câu thoại để tránh cắt cụt nguyên âm).
* **Trong bản v14:** Tăng vọt lên **`1500ms`** (1.5 giây).
* **Hậu quả:** Đệm tới 1.5s im lặng vào đầu và cuối *từng phân đoạn* khiến Whisper phải xử lý các khoảng im lặng bẩn rất lớn. Whisper cực kỳ nhạy cảm với khoảng lặng bẩn và sẽ sinh ra ảo giác lặp từ, hoặc sập ngôn ngữ lạ, đồng thời kéo dài thời gian giải mã của GPU (RTF tăng).

### Yếu tố 2: Hạ thấp ngưỡng VAD quá nhạy (`VAD_THRESHOLD`)
* **Trong bản v11:** `VAD_THRESHOLD = 0.70` (chỉ chọn các đoạn thoại rõ ràng, bỏ qua nhiễu nền telephony).
* **Trong bản v14:** Hạ xuống **`0.45`**.
* **Hậu quả:** Ngưỡng quá thấp khiến tiếng thở dài, tiếng tạch micro hoặc tiếng ồn nền bị hiểu nhầm là giọng nói. Kết hợp với đệm 1500ms ở trên tạo thành các chunk nhiễu khổng lồ gửi sang model để dịch.

### Yếu tố 3: Thay đổi thuật toán phân chia Chunk (`_create_vad_aware_chunks`)
* **Trong bản v11:** Thuật toán phân chunk gộp các phân đoạn tiếng nói một cách mạch lạc, sạch sẽ với giới hạn 15s.
* **Trong bản v14:** Áp dụng thuật toán "targeted speech region" phức tạp, ép buộc mỗi chunk phải dài tối thiểu 3.0s để "tạo ngữ cảnh". Khi kết hợp với ngưỡng VAD nhạy (0.45) và padding lớn (1500ms), ranh giới giữa các chunk bị xóa nhòa, biến các file thoại ngắn thành các khối âm thanh lớn chứa đầy im lặng bẩn.

---

## 3. Tổng Quan Cơ Chế Retry Hiện Tại & Tính Chất "Cực Đoan"

Hệ thống Voxtral hiện tại có cấu trúc thử lại 2 lớp lồng nhau:

* **Lớp 1 (Local Chunk Recovery):** Hoạt động ngay trong quá trình dịch ở T=0.0. Nếu 1 chunk bị sập ngôn ngữ hoặc lặp từ, hệ thống tự động chạy **Sub-chunking** (cắt đôi dịch riêng rồi nối lại) hoặc **Anchor-based Recovery** (ghép neo với chunk khỏe mạnh bên cạnh rồi dịch lại ở T=0.2).
* **Lớp 2 (Global Multi-Temperature Retry):** Hoạt động ở Phase 3 của `_run_inference_sync` sau khi đã ghép toàn bộ file. Nếu phát hiện lỗi `medium` hoặc `high` (tiếng Anh lạ, loops), hệ thống chạy lại **toàn bộ file âm thanh** từ đầu tại `retry_temps = [0.2, 0.5]`.

### Tại sao nó "Cực đoan"?
1. **Lãng phí tài nguyên:** Khi chạy lại toàn bộ file ở T=0.2 và T=0.5, hệ thống phải cắt chunk lại và dịch lại tất cả các chunks lành lặn trước đó.
2. **Vòng lặp đệ quy:** Trong lượt thử lại toàn cục, các cơ chế phục hồi chunk của Lớp 1 lại được kích hoạt đệ quy một lần nữa ở các mức nhiệt độ mới.
3. **Che giấu lỗi tiền xử lý (Preprocessing Masking):** Việc cố gắng dùng GPU để "brute-force" ra văn bản sạch thông qua chuỗi retry phức tạp vô tình che giấu việc bộ lọc tiền xử lý (HPF 80Hz, RMS Norm, Noise Gate) hoạt động kém hoặc để lọt nhiễu.

---

## 4. Kịch Bản Hành Động Chi Tiết Cho Ngày Mai (Action Plan)

Để khôi phục hoàn toàn chất lượng đỉnh cao của v11 và tích hợp cơ chế thử lại tối ưu, hãy thực hiện theo đúng **4 bước cụ thể** sau đây vào ngày mai trong file [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py):

### Bước 1: Khôi phục các Hằng số VAD về bản v11
Mở file [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py) và điều chỉnh các hằng số ở đầu file (khoảng dòng 30-61):

```python
# Chunked inference constants
CHUNK_LIMIT_SEC = 15.0
CHUNK_OVERLAP_SEC = 1.0
VAD_PADDING_MS = 300  # Khôi phục về v11 (300ms để giảm thiểu ảo giác im lặng)

# Silero VAD configuration (optimized for Japanese business conversations)
VAD_THRESHOLD = 0.70  # Khôi phục về v11 (0.70 để lọc nhiễu telephony bẩn)
VAD_MIN_SPEECH_DURATION_MS = 400
VAD_MIN_SILENCE_DURATION_MS = 100

# Online VAD-Aware Chunking config
VAD_SEGMENT_SILENCE_MS = 700   # Giữ nguyên mức tối ưu 700ms của v11
VAD_CHUNK_PADDING_MS = 200

# Hallucination guardrails config
ENABLE_RETRY_HALLUCINATION = True
RETRY_TEMPERATURE = 0.2

# Server version metadata
_SERVER_VERSION = "2026-05-18.v15"  # Tăng phiên bản lên v15 để đánh dấu tối ưu
```

---

### Bước 2: Khôi phục Hàm phân chia Chunk ổn định của v11
Thay thế toàn bộ hàm `_create_vad_aware_chunks` hiện tại (khoảng dòng 287-459) bằng thuật toán phân chunk nhóm cực kỳ ổn định và chính xác của bản v11:

```python
def _create_vad_aware_chunks(audio_np: np.ndarray, speech_timestamps: list, sample_rate: int = 16000, 
                             max_chunk_sec: float = CHUNK_LIMIT_SEC, 
                             padding_ms: int = VAD_CHUNK_PADDING_MS) -> list:
    """
    Group VAD speech segments into chunks <= max_chunk_sec. (Phiên bản v11 ổn định)
    """
    if not speech_timestamps:
        return []
        
    chunks = []
    current_chunk_segments = [speech_timestamps[0]]
    current_chunk_start = speech_timestamps[0]['start']
    current_chunk_end = speech_timestamps[0]['end']
    
    padding_samples = int((padding_ms / 1000.0) * sample_rate)
    max_chunk_samples = int(max_chunk_sec * sample_rate)
    
    for i in range(1, len(speech_timestamps)):
        segment = speech_timestamps[i]
        
        potential_chunk_end = segment['end']
        potential_chunk_size = potential_chunk_end - current_chunk_start
        
        if potential_chunk_size <= max_chunk_samples:
            current_chunk_end = segment['end']
            current_chunk_segments.append(segment)
        else:
            start_idx = max(0, current_chunk_start - padding_samples)
            end_idx = min(len(audio_np), current_chunk_end + padding_samples)
            chunk_audio = audio_np[start_idx:end_idx]
            
            if len(chunk_audio) > max_chunk_samples:
                chunk_duration = len(chunk_audio) / sample_rate
                overlap_sec = CHUNK_OVERLAP_SEC
                n_chunks = max(2, math.ceil(chunk_duration / (max_chunk_sec - overlap_sec * 0.5)))
                effective_duration = chunk_duration - overlap_sec
                step = effective_duration / (n_chunks - 1) if n_chunks > 1 else effective_duration
                step_samples = int(step * sample_rate)
                overlap_samples = int(overlap_sec * sample_rate)

                for idx in range(n_chunks):
                    sub_pos = int(idx * step_samples)
                    sub_end = min(sub_pos + max_chunk_samples, len(chunk_audio))
                    sub_audio = chunk_audio[sub_pos:sub_end]

                    chunks.append({
                        "audio_np": sub_audio,
                        "start_sec": (start_idx + sub_pos) / sample_rate,
                        "end_sec": (start_idx + sub_end) / sample_rate,
                        "segments_count": len(current_chunk_segments) if idx == 0 else 0,
                        "is_sub_chunk": True,
                    })
            else:
                chunks.append({
                    "audio_np": chunk_audio,
                    "start_sec": start_idx / sample_rate,
                    "end_sec": end_idx / sample_rate,
                    "segments_count": len(current_chunk_segments),
                    "is_sub_chunk": False,
                })
            
            current_chunk_start = segment['start']
            current_chunk_end = segment['end']
            current_chunk_segments = [segment]
            
    # Xử lý chunk cuối cùng
    start_idx = max(0, current_chunk_start - padding_samples)
    end_idx = min(len(audio_np), current_chunk_end + padding_samples)
    chunk_audio = audio_np[start_idx:end_idx]
    
    if len(chunk_audio) > max_chunk_samples:
        chunk_duration = len(chunk_audio) / sample_rate
        overlap_sec = CHUNK_OVERLAP_SEC
        n_chunks = max(2, math.ceil(chunk_duration / (max_chunk_sec - overlap_sec * 0.5)))
        effective_duration = chunk_duration - overlap_sec
        step = effective_duration / (n_chunks - 1) if n_chunks > 1 else effective_duration
        step_samples = int(step * sample_rate)

        for idx in range(n_chunks):
            sub_pos = int(idx * step_samples)
            sub_end = min(sub_pos + max_chunk_samples, len(chunk_audio))
            sub_audio = chunk_audio[sub_pos:sub_end]

            chunks.append({
                "audio_np": sub_audio,
                "start_sec": (start_idx + sub_pos) / sample_rate,
                "end_sec": (start_idx + sub_end) / sample_rate,
                "segments_count": len(current_chunk_segments) if idx == 0 else 0,
                "is_sub_chunk": True,
            })
    else:
        chunks.append({
            "audio_np": chunk_audio,
            "start_sec": start_idx / sample_rate,
            "end_sec": end_idx / sample_rate,
            "segments_count": len(current_chunk_segments),
            "is_sub_chunk": False,
        })
        
    return chunks
```

---

### Bước 3: Triển khai Cơ chế Thử lại 1 lần + Strict Rollback
Tìm đến Phase 3 của hàm `_run_inference_sync` (khoảng dòng 1120-1148) và thay đổi vòng lặp retry cũ thành cấu trúc **chỉ thử lại 1 lần duy nhất tại T=0.2 và so sánh nghiêm ngặt**:

```python
    # =========================================================================
    # PHA 3: HALLUCINATION GUARDRAILS & SINGLE-TEMPERATURE RETRY
    # =========================================================================
    guardrail_result = _check_hallucination_guardrails(transcript, trimmed_duration, conn_id, "[Primary] ")
    
    best_transcript = transcript
    best_severity = guardrail_result["severity"]
    severity_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    
    # Chỉ chạy retry đúng 1 lần tại T=0.2 nếu độ nghiêm trọng >= medium
    if guardrail_result["is_suspicious"] and severity_order[best_severity] >= severity_order["medium"] and ENABLE_RETRY_HALLUCINATION:
        r_temp = RETRY_TEMPERATURE  # Cố định ở mức 0.2
        _slog(conn_id, f"[Guardrail] Severity {best_severity} detected. Attempting single retry with temperature={r_temp}...")
        
        retry_transcript, retry_lang_retries, retry_chunk_telemetry = run_inference_with_config(trimmed_audio, temp_override=r_temp)
        retry_guardrail = _check_hallucination_guardrails(retry_transcript, trimmed_duration, conn_id, f"[Retry T={r_temp}] ")
        
        # CHỈ áp dụng nếu độ nghiêm trọng của bản retry THẤP HƠN bản gốc
        if severity_order[retry_guardrail["severity"]] < severity_order[best_severity]:
            _slog(conn_id, f"[Guardrail] Retry T={r_temp} improved severity: {best_severity} -> {retry_guardrail['severity']}. Adopting retry result.")
            best_transcript = retry_transcript
            best_severity = retry_guardrail["severity"]
            guardrail_result = retry_guardrail
            lang_collapse_retries = retry_lang_retries
            chunk_telemetry = retry_chunk_telemetry
        else:
            # Nếu tệ hơn hoặc bằng, bắt buộc chọn kết quả gốc chưa thử lại (Strict Rollback)
            _slog(conn_id, f"[Guardrail] Retry T={r_temp} did NOT improve severity ({best_severity} -> {retry_guardrail['severity']}). Selecting original unretried result.")

    transcript = best_transcript
```

---

### Bước 4: Chạy Xác Thực & Benchmark
Sau khi lưu các thay đổi trên máy chủ, chạy lệnh sau ở terminal để kiểm tra kết quả:

```powershell
python benchmark_runner.py --audio_dir audio --server-audio-dir audio --runs 1 --chunk-interval 0 --host <đường-dẫn-ngrok-server-của-bạn>
```

**Kỳ vọng:**
1. Average Speech-Only CER quay lại mức kỷ lục **`40.93%`** hoặc thấp hơn.
2. Inference RTF trung bình quay lại mức tối ưu **`3.6x`** (nhanh hơn v14 hiện tại tới 30%).
3. Log terminal hiển thị rõ ràng cơ chế rollback hoạt động chính xác khi có nhiễu xảy ra.

---
**Chúc bạn một buổi tối nghỉ ngơi thư giãn. Hẹn gặp lại bạn vào ngày mai để hoàn tất đợt tối ưu hóa này!** 🚀
