# Kế hoạch Triển khai Chi tiết - VAD Chunk V10 (25/05/2026) - Bản Cập nhật Bảo mật & An toàn

Tài liệu này trình bày phân tích đối chiếu chuyên sâu từ V9 và kế hoạch hành động chi tiết để xây dựng phiên bản V10, nhằm giải quyết triệt để các vấn đề còn tồn tại về độ chính xác (CER), tốc độ xử lý (RTF), ảo giác cục bộ, và hệ thống đánh giá tự động (LLM Evaluator). 

Bản cập nhật này sửa đổi các lỗ hổng thiết kế từ phiên bản nháp trước đó nhằm đảm bảo tính an toàn, tránh overfit benchmark, và chuẩn hóa các chỉ số đo lường.

---

## 1. Đối chiếu & Phân tích chuyên sâu từ V9

### 1.1. Những cải tiến đã kiểm chứng (Điểm neo `2e3e402`)
*   **Chống mất chữ đầu câu:** VAD Padding (300ms/350ms) đã đưa tỷ lệ lỗi Deletion về 0.
*   **Chống ảo giác trên Silence:** High-Pass Filter (80Hz) loại bỏ nhiễu hum/rumble hiệu quả, giữ HRS (Silence) ở mức 0.00%.
*   **Khớp biên mượt mà:** Siết chặt Fuzzy Overlap (khoảng cách biên giảm từ 15 xuống 6 ký tự, khớp tối thiểu 10 ký tự) giúp triệt tiêu các từ đệm bị lặp thừa khi ghép chunk.

### 1.2. Phân tích lỗ hổng thiết kế & Phản biện kỹ thuật

#### 1. Lọc trôi ngôn ngữ (Language Collapse) cục bộ quá hẹp
*   *Hạn chế bản nháp cũ:* Regex cũ `[A-Za-z\s']{12,}` chỉ lọc được chữ Latin (English/Spanish). Trên thực tế, mô hình có thể bị trôi sang các hệ ngôn ngữ phi Nhật Bản khác (như Hindi/Devanagari, Cyrillic). Ngoài ra, nếu dùng whitelist cứng theo từ vựng (allowlist) để tránh chặn nhầm các tên viết tắt doanh nghiệp/dự án hợp lệ trong hội thoại (như "AJ", "Asset Japan", "PMG", "Voxtral"), thiết kế này sẽ rất khó scale trong production và dễ tạo ra false positive/false negative khi gặp khách hàng, domain mới hoặc các acronym khác.
*   *Giải pháp V10:* Bỏ hẳn whitelist theo từ/cụm từ. Chuyển đổi thành bộ lọc **non-Japanese drift** dựa trên phân loại script, tỷ lệ ký tự (script ratio), và độ dài chuỗi ký tự liên tục (run-length thresholds):
    1.  **Chữ phi-Latin phi-Nhật** (như Cyrillic/Devanagari): Nhạy bén, kích hoạt khi chuỗi ký tự liên tục $\ge 10$ ký tự (trong cấu hình hội thoại tiếng Nhật doanh nghiệp, đây là tín hiệu drift rất mạnh).
    2.  **Chữ Latin** (English/Romaji): Không trigger bừa bãi chỉ vì dài. Chỉ trigger khi chuỗi Latin liên tục đủ dài ($\ge 50$ ký tự) VÀ tỷ lệ tiếng Nhật trong segment rất thấp ($jp\_ratio < 0.15$). Điều này cho phép dung thứ cho việc nói trộn tiếng Anh/Romaji văn phòng thông thường.

#### 2. Rủi ro "Overfit Benchmark" từ Domain Post-Processing Map
*   *Rủi ro:* Việc hardcode map trực tiếp từ cụm từ sai sang đúng (ví dụ: `先生管理科` $\rightarrow$ `中央清算管理課`) sẽ làm CER đẹp lên một cách giả tạo trên tập test (test set leakage), không phản ánh năng lực thực tế của mô hình acoustic.
*   *Giải pháp V10:* Xem đây là **Domain Glossary** có thể cấu hình được (configurable glossary). Thiết kế các cụm regex map phải đi kèm context hoặc có độ dài/độ đặc trưng cao để tránh sửa nhầm các câu hội thoại thông thường (ví dụ: không được map từ generic như `先生` đơn lẻ). CER cải thiện từ map này phải được tách biệt rõ ràng, không được tính vào cải tiến chất lượng của pipeline ASR gốc.

#### 3. Sự mập mờ trong định nghĩa RTF (Real-Time Factor)
*   *Làm rõ chỉ số:* V9 ghi nhận RTF 1.354 trong báo cáo speech-only nhưng aggregate RTF trong kết quả benchmark lại là 1.1195. 
*   *Chuẩn hóa V10:* Tách biệt rõ 3 khái niệm:
    1.  **Speech-Only Inference RTF:** Thời gian xử lý trung bình chỉ tính trên 9 file có chứa tiếng nói (Mục tiêu V10: $\le 1.0$).
    2.  **All-Files Aggregate Inference RTF:** Thời gian xử lý trung bình tính trên toàn bộ 11 file test bao gồm cả file im lặng/nhiễu (Mục tiêu V10: $\le 0.9$).
    3.  **Total RTF:** Tổng thời gian xử lý toàn trình đo từ client (bao gồm đọc file, thiết lập kết nối, truyền dữ liệu mạng, và chờ server trả kết quả), nhưng **không bao gồm** thời gian chạy đánh giá LLM Evaluation (vì LLM Evaluation là một tiến trình phân tích độc lập chạy sau khi file kết quả `results.json` được tạo ra).

---

## 2. Kế hoạch triển khai V10 hôm nay

### Bước 1: Triển khai bộ lọc Script/Ratio-based non-Japanese Drift
Thay thế và nâng cấp hàm `_detect_language_collapse` trong [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py) bằng cơ chế phát hiện trôi ngôn ngữ không dùng whitelist, hoạt động như một post-decoding guardrail theo deployment profile.

*   **Cấu hình Chính sách (đầu file):**
    ```python
    import os
    
    # Cấu hình phát hiện trôi ngôn ngữ theo profile triển khai
    ASR_DRIFT_GUARDRAIL_PROFILE = os.getenv("ASR_DRIFT_GUARDRAIL_PROFILE", "ja_business")
    ASR_ENABLE_SCRIPT_DRIFT_RECOVERY = os.getenv("ASR_ENABLE_SCRIPT_DRIFT_RECOVERY", "true").lower() == "true"
    ASR_LATIN_COLLAPSE_MIN_CHARS = int(os.getenv("ASR_LATIN_COLLAPSE_MIN_CHARS", "50"))
    ```

*   **Logic Drift Detection tổng quát (Sản xuất an toàn):**
    ```python
    import unicodedata

    def _is_latin_char(c: str) -> bool:
        """Kiểm tra ký tự c có thuộc hệ Latin Unicode hay không (bao gồm cả các ký tự có dấu như é, ñ, ü...)."""
        try:
            return "LATIN" in unicodedata.name(c)
        except ValueError:
            return False

    def _detect_language_collapse(transcript: str) -> dict:
        """
        Phát hiện trôi ngôn ngữ (Language Drift) tổng quát dựa trên script, tỷ lệ (ratio), 
        và độ dài chuỗi ký tự liên tục, không sử dụng whitelist từ vựng.
        """
        text = transcript.strip()
        if len(text) == 0:
            return {"is_collapsed": True, "jp_ratio": 0.0, "reason": "empty_transcript"}
        if len(text) < LANG_COLLAPSE_MIN_CHARS:
            return {"is_collapsed": False, "jp_ratio": 1.0, "reason": "too_short"}
        
        # 1. Check Chinese drift patterns (Giữ nguyên từ V9)
        PURE_CHINESE_CHARS = set("這这們们誰谁麼么嗎吗吧呢我你health她它") - set("health")
        PURE_CHINESE_PHRASES = ["這是", "是デ", "我的", "我們", "你是", "他們", "不是", "不要", "不用", "謝謝"]
        
        has_chinese_char = any(c in PURE_CHINESE_CHARS for c in text)
        has_chinese_phrase = any(p in text for p in PURE_CHINESE_PHRASES)
        
        if has_chinese_char or has_chinese_phrase:
            reason_detail = []
            if has_chinese_char:
                matched_chars = "".join(sorted(list(set(c for c in text if c in PURE_CHINESE_CHARS))))
                reason_detail.append(f"Chinese chars found: {matched_chars}")
            if has_chinese_phrase:
                matched_phrases = [p for p in PURE_CHINESE_PHRASES if p in text]
                reason_detail.append(f"Chinese phrases found: {matched_phrases}")
            return {
                "is_collapsed": True,
                "jp_ratio": 0.0,
                "reason": f"Chinese drift: {'; '.join(reason_detail)}",
            }
            
        # 2. Tách các phân đoạn ký tự liên tục phi-Nhật (runs of non-Japanese characters)
        current_run = []
        runs = []
        for c in text:
            if c.isalpha() and not _is_japanese_char(c):
                current_run.append(c)
            elif c in " '" and current_run: # Cho phép dấu cách/nháy đơn ở giữa chuỗi
                current_run.append(c)
            else:
                if current_run:
                    runs.append("".join(current_run))
                    current_run = []
        if current_run:
            runs.append("".join(current_run))
            
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return {"is_collapsed": False, "jp_ratio": 1.0, "reason": "no_alpha"}
        
        jp_letters = [c for c in letters if _is_japanese_char(c)]
        ratio = len(jp_letters) / len(letters)
        
        # 3. Phân tích từng run để phát hiện drift nếu chế độ recovery được bật
        if ASR_ENABLE_SCRIPT_DRIFT_RECOVERY:
            for run in runs:
                run_clean = run.strip()
                letters_only = "".join(c for c in run_clean if c.isalpha())
                if not letters_only:
                    continue
                    
                # Sử dụng Unicode để nhận diện Latin chính xác (bao gồm cả accented Latin é, ñ, ü...)
                is_latin = all(_is_latin_char(c) for c in letters_only)
                
                if is_latin:
                    # Với Latin (English/Romaji): chỉ trigger collapse khi chuỗi liên tục >= ASR_LATIN_COLLAPSE_MIN_CHARS
                    # VÀ tỷ lệ tiếng Nhật trong câu rất thấp (< 15%)
                    if len(letters_only) >= ASR_LATIN_COLLAPSE_MIN_CHARS and ratio < 0.15:
                        return {
                            "is_collapsed": True,
                            "jp_ratio": round(ratio, 3),
                            "reason": f"Latin drift: continuous run of {len(letters_only)} chars with low JP ratio ({ratio:.1%})"
                        }
                else:
                    # Với các script phi-Latin, phi-Nhật (Cyrillic, Devanagari...):
                    # Rất nhạy bén (ngưỡng >= 10 ký tự liên tục) đối với profile "ja_business"
                    if ASR_DRIFT_GUARDRAIL_PROFILE == "ja_business" and len(letters_only) >= 10:
                        return {
                            "is_collapsed": True,
                            "jp_ratio": round(ratio, 3),
                            "reason": f"Non-Japanese/Non-Latin script drift: continuous run of {len(letters_only)} chars"
                        }
        
        return {
            "is_collapsed": False,
            "jp_ratio": round(ratio, 3),
            "reason": "ok",
        }
    ```

### Bước 2: Thử nghiệm giảm VAD Padding để hạ RTF
*   **Vị trí thay đổi:** Đầu file [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L35-L39).
*   **Điều chỉnh:**
    ```python
    VAD_PADDING_LEFT_MS = 200        # Giảm từ 300ms xuống 200ms
    VAD_PADDING_RIGHT_MS = 200       # Giảm từ 350ms xuống 200ms
    VAD_CHUNK_PADDING_LEFT_MS = 200  # Giảm từ 300ms xuống 200ms
    VAD_CHUNK_PADDING_RIGHT_MS = 200 # Giảm từ 300ms xuống 200ms
    ```
*   **Kiểm soát rủi ro:** Nếu benchmark cho thấy lỗi Deletion xuất hiện lại, sẽ rollback ngay lập tức từng bước 25ms.

### Bước 3: Triển khai Domain Glossary Configurable & Cơ chế Truyền dẫn raw_transcript
Để hỗ trợ đo đạc CER khách quan mà không che mờ năng lực thực tế của mô hình (Overfit Benchmark), hệ thống cần propagate song song cả `raw_transcript` (kết quả gốc trước glossary) và `transcript` (kết quả sau glossary) từ Server -> Client -> Metrics Report.

#### 1. Cấu hình Glossary Động ở Server
*   **Vị trí thay đổi:** Định nghĩa hàm load và sửa lỗi ở đầu file [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py).
*   **Hành vi mặc định an toàn:** Nếu không cấu hình `ASR_GLOSSARY_PATH`, mặc định trả về dictionary trống `{}` để tránh làm sai lệch dữ liệu thử nghiệm chung. Chỉ sử dụng `DEFAULT_GLOSSARY` khi biến môi trường `ASR_USE_DEFAULT_GLOSSARY=true`.
*   **Đoạn code tích hợp:**
    ```python
    import json

    # Glossary mặc định để demo / dự phòng nếu được kích hoạt
    DEFAULT_GLOSSARY = {
        r"先生管理科": "中央清算管理課",
        r"精算管理課": "中央清算管理課",
        r"ダンタク": "在宅",
        r"アセプトジャパン": "アセットジャパン",
        r"生徒キャパン": "アセットジャパン",
        r"水建設\s*of\s*安田": "建設のエスタ",
        r"水建設の安田": "建設のエスタ",
    }

    def _load_domain_glossary() -> dict:
        glossary_path = os.environ.get("ASR_GLOSSARY_PATH", "")
        if not glossary_path:
            if os.environ.get("ASR_USE_DEFAULT_GLOSSARY", "false").lower() == "true":
                return DEFAULT_GLOSSARY
            return {}
            
        try:
            with open(glossary_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to load glossary from {glossary_path}: {e}")
            return {}

    def _apply_domain_glossary(text: str) -> str:
        if not text:
            return text
        glossary = _load_domain_glossary()
        processed = text
        for pattern, replacement in glossary.items():
            processed = re.sub(pattern, replacement, processed)
        return processed
    ```

#### 2. Propagate raw_transcript qua WebSocket Payload (Server Side)
*   **Vị trí thay đổi:** File [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py).
*   **Sửa đổi hàm định nghĩa kết quả:**
    ```python
    def _inference_result(transcript: str, raw_transcript: str | None = None, vad_result: dict | None = None, lang_collapse_retries: list | None = None, chunk_telemetry: list | None = None) -> dict:
        return {
            "transcript": transcript,
            "raw_transcript": raw_transcript if raw_transcript is not None else transcript,
            "vad_config": _vad_config_metadata(),
            "vad_result": vad_result or {},
            "lang_collapse_retries": lang_collapse_retries or [],
            "chunk_telemetry": chunk_telemetry or [],
        }
    ```
*   **Sửa đổi hàm `_run_inference_sync`:**
    Áp dụng glossary ở cuối tiến trình và truyền cả `raw_transcript` vào `_inference_result`:
    ```python
    # ... cuối hàm _run_inference_sync ...
    raw_transcript = best_transcript
    transcript = _apply_domain_glossary(raw_transcript)
    elapsed = time.time() - t_inf_start
    
    _slog(conn_id, f"inference_finished  elapsed={elapsed:.2f}s  transcript_len={len(transcript)}  raw_len={len(raw_transcript)}")
    vad_result = dict(vad_info)
    vad_result["hallucination_warning"] = guardrail_result["is_suspicious"]
    vad_result["hallucination_severity"] = best_severity
    return _inference_result(transcript, raw_transcript, vad_result, lang_collapse_retries, chunk_telemetry)
    ```

#### 3. Cập nhật Client Nhận dữ liệu (Client Side)
*   **Vị trí thay đổi:** File [run_asr.py](file:///d:/VJ/Voxtral/run_asr.py).
*   **Hành động:**
    - Tại block nhận message `response.audio_transcript.done` (khoảng dòng 210), load thêm `raw_transcript` từ websocket payload:
      ```python
      final_transcript = data.get('transcript', '')
      raw_transcript = data.get('raw_transcript', final_transcript)
      ```
    - Ghi nhận `raw_transcript` vào kết quả trả về của `transcription_client` (khoảng dòng 257) để lưu trữ vào file `results.json`:
      ```python
      "transcript": transcript,
      "raw_transcript": raw_transcript,
      ```

#### 4. Cập nhật Kịch bản Đo lường Song song (Evaluation Side)
*   **Vị trí thay đổi:** File [evaluate_metrics.py](file:///d:/VJ/Voxtral/evaluate_metrics.py).
*   **Hành động:**
    - Tính toán song song cả `raw_cer` (so khớp giữa `raw_transcript` và Ground Truth) và `adjusted_cer` (so khớp giữa `transcript` và Ground Truth) cho mỗi file test.
    - Xuất cả 2 chỉ số này ra bảng chi tiết và phần tóm tắt của báo cáo chất lượng `report.md`.

### Bước 4: Tinh chỉnh Prompt của LLM Evaluator để giảm False Positive
*   **Vị trí thay đổi:** File [prompt_builder.py](file:///d:/VJ/Voxtral/llm_evaluator/prompt_builder.py).
*   **Prompt mới:** Bổ sung quy tắc loại trừ lỗi nghe nhầm (Substitution) khỏi lỗi chèn từ (Insertion) vào `SYSTEM_PROMPT_BASE`:
    ```python
    """
    QUAN TRỌNG VỀ PHÂN BIỆT LỖI:
    - KHÔNG được đánh giá là lỗi 'insertion' hay ảo giác (hallucination) nếu Hypothesis chỉ nhận diện sai âm thanh/âm vị của một từ có sẵn trong Ground Truth (ví dụ: GT là '中央清算管理課' nhưng HYP nhận diện nhầm thành '先生管理科', hoặc GT là '在宅' nhưng HYP nhận diện nhầm thành '大学'). 
    - Lỗi nhận diện sai từ/âm vị (Substitution) này hãy được xếp vào nhãn 'none'.
    - Nhãn 'content_replacement' chỉ được dùng khi Hypothesis thay thế hoàn toàn ý nghĩa của cả câu/vế câu, làm biến đổi hoàn toàn thông tin truyền tải. Tuyệt đối không dùng cho lỗi nghe nhầm danh từ riêng.
    - Lỗi 'insertion' chỉ tính khi HYP tự động bịa thêm một cụm từ hoặc một câu hoàn toàn mới ở vị trí vốn là khoảng lặng và không hề có lời nói tương ứng nào trong Ground Truth.
    """
    ```

### Bước 5: Cập nhật Server Version để theo dõi vòng đời
*   **Vị trí thay đổi:** File [voxtral_server_transformers.py](file:///d:/VJ/Voxtral/voxtral_server_transformers.py#L66).
*   **Hành động:** Thay đổi hằng số phiên bản server:
    ```python
    _SERVER_VERSION = "2026-05-25.v10"
    ```
*   **Mục tiêu:** Giúp phân biệt rõ ràng trong file log và metadata kết quả benchmark để chứng minh server đã thực sự restart và chạy đúng code V10 mới nhất, loại trừ trường hợp cache lại phiên bản cũ (`2026-05-18.v15`).

---

## 3. Kế hoạch xác thực & Acceptance Gates (Chặt chẽ)

### 3.1. Quy trình thực hiện (Precondition)
1.  **Áp dụng toàn bộ code V10** vào server `voxtral_server_transformers.py`, client `run_asr.py`, `evaluate_metrics.py` và evaluator.
2.  **Khởi động lại server ASR** để chắc chắn server đang chạy đúng mã nguồn V10:
    ```powershell
    # Khởi động lại dịch vụ hoặc tiến trình python voxtral_server_transformers.py
    ```
3.  **Chạy Benchmark client:**
    Client phải chạy bằng chế độ truyền file giống hệt V9 (sử dụng cùng các cờ như `--server-audio-dir`, `--chunk-interval`, `--response-timeout` nếu có).
    Lệnh chạy đề xuất sử dụng local path (hoặc server-side path tùy thuộc chế độ cấu hình của V9):
    ```powershell
    # Mode chạy local client-side gửi audio byte
    python benchmark_runner.py --audio_dir audio --llm-eval --runs 1
    
    # Hoặc mode chạy server-side đọc audio trực tiếp nếu V9 dùng mode này:
    # python benchmark_runner.py --audio_dir audio --server-audio-dir audio --llm-eval --runs 1
    ```
4.  **Chạy Script so sánh thoái lùi (Regression Check):**
    Sử dụng kết quả chạy V10 mới nhất so sánh trực tiếp với kết quả benchmark của V9 (nằm trong thư mục `results/21-05-2026_v6/results.json`) để xác minh chi tiết thay đổi CER và phát hiện lỗi thụt lùi (regression).

### 3.2. Cổng chấp nhận kết quả (Acceptance Gates)

Để V10 được coi là **thành công**, kết quả chạy thử phải vượt qua các chốt kiểm soát sau:

| Chỉ số / Cổng kiểm soát | Giá trị V9 | Mục tiêu V10 | Đánh giá đạt |
|---|---|---|---|
| **Lỗi Deletion đầu câu** | **0** | **Phải bằng 0** | Không để xảy ra thoái lùi do giảm Padding |
| **Lỗi Empty-on-speech** | **0** | **Phải bằng 0** | Không có file nói nào bị biến thành rỗng |
| **Speech-Only Inference RTF** | **1.354** | **<= 1.00** | Rút ngắn thời gian xử lý thực tế |
| **All-Files Avg Inference RTF** | **1.119** | **<= 0.90** | Đảm bảo tốc độ tổng thể đạt yêu cầu |
| **Speech-Only Raw CER** | **34.54%** | **<= 34.54%** | Đảm bảo hiệu suất mô hình acoustic gốc không bị thoái lùi |
| **Giới hạn thoái lùi per-file** | N/A | **<= 2.0%** | Không có file đơn lẻ nào bị tăng Raw CER quá 2.0% so với V9 (`results/21-05-2026_v6/results.json`) |
| **High-severity Hallucinations** | **0** | **Phải bằng 0** | Triệt tiêu hoàn toàn lặp vô hạn và trôi Latin |
| **Drift False Recovery Rate** | N/A | **0%** | Bộ lọc trôi ngôn ngữ không kích hoạt nhầm trên hội thoại tiếng Nhật bình thường (đo bằng: số lần `lang_collapse_retries` kích hoạt sai trên các file Nhật chuẩn = 0; hoặc mọi retry phải ghi lại matched_text và reason cụ thể để phục vụ việc đối chiếu thủ công) |
| **LLM Insertion False Positive** | **100% (9/11 file)** | **error_distribution.insertion <= 3/9 speech files** | Giảm thiểu tối đa việc gán nhãn sai lỗi chèn âm vị thành lỗi ảo giác |

### 3.3. Chỉ số Tham chiếu & Phụ (Secondary/Reference Metrics)
Các chỉ số dưới đây được theo dõi để đánh giá hiệu quả của các tiến trình post-processing bổ sung, nhưng **không** được dùng làm tiêu chí bắt buộc (Gate) để pass V10:

*   **Speech-Only Glossary-adjusted CER (V9: 34.54% | Mục tiêu V10: <= 10.00%)**: Chỉ số này đo lường sự cải thiện về mặt từ vựng/domain sau khi áp dụng Domain Glossary. Đây là chỉ số tham chiếu riêng biệt để tránh rủi ro "Overfit Benchmark".

---
**Kế hoạch được lập bởi:** Antigravity (Gemini 3.5 Flash)
**Đường dẫn lưu trữ:** `reports/vad_chunk_v10/implementation_plan_v10.md`
