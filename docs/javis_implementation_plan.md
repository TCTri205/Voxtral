# Kế Hoạch Tích Hợp Javis ASR Để So Sánh Hallucination Với Voxtral

## Mục tiêu

Bổ sung một runner ASR cho **Javis** để benchmark song song với **Voxtral** trên cùng bộ audio, cùng ground truth, cùng pipeline đánh giá, nhằm so sánh:

- chất lượng transcript
- mức độ hallucination
- tốc độ inference

Mục tiêu của tài liệu này là chốt một kế hoạch đủ chặt để có thể implement trực tiếp mà không phải tự quyết thêm các điểm quan trọng trong lúc làm.

## Phạm vi và nguyên tắc so sánh công bằng

Benchmark mặc định phải dùng cấu hình **raw-baseline** để giảm sai lệch giữa hai engine.

- Với Javis, mặc định tắt:
  - `noise_suppression`
  - `webrtc_denoise_enabled`
  - `detect_speaker`
  - `verify_with_transcribe_api`
  - `save_processed_audio`
  - `save_recorded_audio`
- Với Voxtral, giữ nguyên pipeline hiện tại của `run_asr.py`.
- Hai engine phải dùng cùng preprocessing ở phía client:
  - resample về mono 16 kHz
  - encode PCM16 little-endian
  - pacing chunk giống nhau theo `--chunk-interval`

Nếu cần đánh giá thêm hiệu quả denoise của Javis, đó là **profile benchmark thứ hai**, không trộn với raw-baseline khi so sánh chính.

## Giả định triển khai đã chốt

Các quyết định dưới đây được coi là contract của v1:

- Javis là **API chạy local hoặc trong mạng nội bộ**, gọi trực tiếp từ máy benchmark.
- V1 **không** bao gồm Colab, ngrok, notebook hosting, hay `server-audio-dir` cho Javis.
- Javis dùng endpoint WebSocket đầy đủ qua `--ws-url` hoặc biến môi trường `JAVIS_WS_URL`.
- Auth Javis là **bắt buộc** ở môi trường benchmark v1:
  - `JAVIS_SESSION_ID`
  - `JAVIS_TOKEN`
- Layout thư mục kết quả **giữ nguyên** theo convention hiện tại của repo:
  - `results/DATE_vN`
  - không thêm prefix `javis_` hay `voxtral_` vào tên thư mục ở v1
- Phân biệt engine bằng metadata trong `results.json` và log/report, không bằng đổi tên thư mục.

## Khác biệt protocol đã xác nhận

### Voxtral (`/v1/realtime`) - đã có trong repo

Theo [run_asr.py](/D:/VJ/Voxtral/run_asr.py):

| Bước | Message |
|------|---------|
| Config | `{"type":"session.update","session":{...}}` |
| Stream | `input_audio_buffer.append` với audio base64 trong JSON |
| Commit | `{"type":"input_audio_buffer.commit"}` |
| Result | `{"type":"response.audio_transcript.done","transcript":"..."}` |
| Keepalive | `{"type":"session.keepalive"}` |

### Javis (`/api/v4/ws/improved`) - đã xác nhận từ tài liệu trong repo

Theo [ws_improved_v4.md](/D:/VJ/Voxtral/docs/ws_improved_v4.md):

| Bước | Message |
|------|---------|
| Connect | server gửi `{"type":"config"}` |
| Start | client gửi `{"event":"start", ...}` |
| Ready | server gửi `{"type":"ready"}` |
| Stream | client gửi binary PCM16 raw trực tiếp |
| Stop | client gửi `{"event":"stop"}` |
| Result | server gửi `partial` rồi `final` |

Các điểm đã xác nhận trong repo:

- Audio Javis là **raw binary PCM16**, không bọc JSON.
- Javis hỗ trợ các option xử lý phụ như denoise, diarization, verification.
- `start` payload có `session_id` và `token`.
- `final` message trong tài liệu có `text` và metadata verification.

### Điểm chưa được repo xác nhận tuyệt đối

Repo hiện **không xác nhận chắc chắn** rằng `final` luôn chứa `segments[]`.

- [ws_improved_v4.md](/D:/VJ/Voxtral/docs/ws_improved_v4.md) chỉ minh họa `segments` ở message `partial`.
- `final` trong tài liệu repo chỉ thể hiện `text` và metadata verification.

Vì vậy khi implement client:

- nguồn transcript chuẩn mặc định là `final["text"]`
- nếu runtime thực tế có `final["segments"]`, có thể parse thêm như enhancement
- không được coi `final["segments"]` là contract bắt buộc

**Note về `recorded_audio`:** Message `recorded_audio` chỉ được gửi khi `save_recorded_audio = true`. Với raw-baseline config (`save_recorded_audio: false`), message này sẽ không xuất hiện. Tuy nhiên, client nên ignore gracefully nếu nhận được (không crash).

## Thiết kế `run_asr_javis.py`

### Mục tiêu

Tạo file mới [run_asr_javis.py](/D:/VJ/Voxtral/run_asr_javis.py) với output tương thích `results.json` của [run_asr.py](/D:/VJ/Voxtral/run_asr.py), để các bước đánh giá hiện có vẫn dùng lại được.

### Interface CLI

Giữ các cờ chung tương thích với `run_asr.py` khi có ý nghĩa:

- `--audio`
- `--audio_dir`
- `--resume`
- `--chunk-interval`
- `--response-timeout`
- `--debug`
- `--debug-frames`
- `--llm-eval`
- `--llm-model`
- `--ground-truth`
- `--timestamps-dir`

Chốt cấu hình endpoint theo hướng **URL đầy đủ** để tránh rule ghép URL mơ hồ:

- thêm `--ws-url`
- env mặc định: `JAVIS_WS_URL`

Không dùng `--host`/`--port` làm interface chính cho Javis.

### Auth và cấu hình nhạy cảm

`session_id` và `token` được lấy từ env:

- `JAVIS_SESSION_ID`
- `JAVIS_TOKEN`

Hai biến này là **bắt buộc** trong benchmark v1. Nếu thiếu, client phải fail sớm với lỗi cấu hình rõ ràng trước khi mở kết nối WebSocket.

Không giả định server sẽ cấp lại `session_id` hoặc `token` trong handshake.

Yêu cầu an toàn:

- không ghi `token`
- không ghi `session_id`
- không dump toàn bộ `start` payload vào `log_debug.txt`

### Start payload mặc định

Raw-baseline mặc định:

```json
{
  "event": "start",
  "sample_rate": 16000,
  "format": "pcm16",
  "language": "ja",
  "detect_speaker": false,
  "noise_suppression": false,
  "denoiser": "demucs",
  "webrtc_denoise_enabled": false,
  "webrtc_enable_ns": true,
  "webrtc_agc_type": 1,
  "webrtc_aec_type": 0,
  "webrtc_enable_vad": false,
  "webrtc_frame_ms": 10,
  "webrtc_ns_level": 0,
  "verify_with_transcribe_api": false,
  "save_processed_audio": false,
  "save_recorded_audio": false,
  "session_id": "<from env>",
  "token": "<from env>"
}
```

Các cờ Javis-specific cần expose tối thiểu:

- `--language`
- `--noise-suppression`
- `--denoiser`
- `--verify-with-transcribe-api`

Không cần expose toàn bộ `webrtc_*` ở phiên bản đầu nếu mục tiêu chính là benchmark raw-baseline.

### Luồng xử lý

1. Kết nối tới `--ws-url`.
2. Chờ `{"type":"config"}` trong timeout handshake riêng.
3. Gửi `start` payload.
4. Chờ `{"type":"ready"}` trong timeout handshake riêng.
5. Stream audio PCM16 raw theo chunk.
6. Gửi `{"event":"stop"}`.
7. Thu `partial` nếu có, chờ `final`.
8. Trích transcript:
   - ưu tiên `final["text"]`
   - nếu `final["text"]` rỗng và có `final["segments"]`, ghép `segments[].text`
9. Trả output cùng schema thực tế của `run_asr.py`.

### Schema output tương thích

`results.json` của Javis phải giữ các field cốt lõi giống `run_asr.py`:

- `file`
- `status`
- `transcript`
- `duration`
- `connect_time`
- `stream_time`
- `wait_after_commit`
- `total_time`
- `total_rtf`
- `inference_rtf`
- `error_type`
- `error_message`

Có thể thêm metadata nếu không phá evaluator hiện có:

- `engine: "javis"`
- `profile: "raw-baseline"`

## Tích hợp với benchmark và evaluator hiện có

### `benchmark_runner.py`

Cần sửa [benchmark_runner.py](/D:/VJ/Voxtral/benchmark_runner.py) để thêm:

```python
parser.add_argument(
    "--engine",
    type=str,
    default="voxtral",
    choices=["voxtral", "javis"],
    help="ASR engine to benchmark",
)
```

Logic chạy:

- `--engine voxtral` -> gọi `python run_asr.py ...`
- `--engine javis` -> gọi `python run_asr_javis.py ...`

### Forwarding rule theo engine

Runner phải tách rõ cờ nào có nghĩa cho engine nào:

- Với `voxtral`, giữ behavior hiện tại:
  - cho phép `--host`
  - cho phép `--port`
  - cho phép `--delay`
  - cho phép `--server-audio-dir`
- Với `javis`, chỉ forward các cờ có nghĩa:
  - `--audio`
  - `--audio_dir`
  - `--chunk-interval`
  - `--response-timeout`
  - `--debug`
  - `--debug-frames`
  - `--llm-eval`
  - `--llm-model`
  - `--ground-truth`
  - `--timestamps-dir`
  - `--resume`
  - `--ws-url`
  - các cờ Javis-specific như `--language`, `--noise-suppression`, `--denoiser`, `--verify-with-transcribe-api`

Runner không được truyền `--host`, `--port`, `--delay`, `--server-audio-dir` sang `run_asr_javis.py`, vì đây là cờ chỉ có nghĩa với Voxtral ở thiết kế hiện tại.

### Quy ước output directory

Giữ nguyên convention hiện tại của repo:

- `results/19-04-2026_v1`
- `results/19-04-2026_v2`

Lý do chốt theo hướng này:

- `benchmark_runner.py` hiện giả định `results/DATE_vN`
- `--date` hiện build glob theo `results/{date}_v*`
- logic range filter hiện parse suffix `_vN`
- đổi tên thư mục để thêm prefix engine sẽ làm phạm vi sửa lớn hơn cần thiết

Phân biệt engine bằng metadata và validation:

- `results.json` nên có field `engine`
- runner nên in rõ engine trong banner và log
- nếu `--resume` trỏ vào thư mục đã có `results.json` với `engine` khác, phải fail sớm thay vì trộn kết quả hai engine

### Mức độ reuse thực tế

Các thành phần sau vẫn có thể reuse theo đúng nghĩa thực dụng:

- [evaluate_metrics.py](/D:/VJ/Voxtral/evaluate_metrics.py)
- `llm_evaluator/*`
- `ground_truth.json`
- `audio/`
- `timestamps/`

Nhưng không nên ghi là “reuse hoàn toàn không cần thay đổi” cho toàn bộ pipeline, vì phần chọn engine ở runner và phần compare chéo hai engine là logic mới.

## Thiết kế `compare_engines.py`

Tạo file mới [compare_engines.py](/D:/VJ/Voxtral/compare_engines.py) để so sánh hai run directory.

### Input

- `--voxtral-run <dir>`
- `--javis-run <dir>`

V1 chỉ nhận đúng hai thư mục cụ thể để giảm mơ hồ. Chưa mở rộng sang glob ở phiên bản đầu.

### Nguồn dữ liệu cho từng metric

Phải chốt file nguồn cụ thể:

- `results.json`
  - per-file transcript
  - CER
  - RTF
  - các field HRS/RF sau khi chạy `evaluate_metrics.py`
- `llm_eval_summary.json`
  - `hallucination_rate`
  - `error_distribution`
  - `severity_distribution`
- `llm_eval_details.csv`
  - chỉ dùng cho drill-down nếu file tồn tại

Không coi toàn bộ “run directory” là một input mơ hồ mà không chỉ rõ file nguồn.

### Output

Markdown report + JSON summary gồm:

- per-file CER diff
- average CER diff
- HRS comparison
- average inference RTF comparison
- LLM hallucination rate comparison
- error type distribution comparison
- severity distribution comparison

Không đưa “overall recommendation theo weighted score” ở v1 nếu chưa chốt công thức. Nếu muốn có kết luận tổng hợp, phải định nghĩa rõ trọng số ngay trong tài liệu riêng.

## Error handling và yêu cầu an toàn

`run_asr_javis.py` phải map lỗi về cùng pattern với `run_asr.py`:

- `status = "failed"`
- `error_type`
- `error_message`

Các case bắt buộc xử lý:

- thiếu `JAVIS_WS_URL`
- thiếu `JAVIS_SESSION_ID`
- thiếu `JAVIS_TOKEN`
- timeout chờ `config`
- timeout chờ `ready`
- timeout chờ `final`
- server gửi `{"type":"error","message":"..."}`
- auth failure
- `final` thiếu transcript hợp lệ
- websocket close bất thường

Lưu ý khác biệt contract:

- Voxtral hiện đọc lỗi từ `data["error"]`
- Javis theo tài liệu repo trả lỗi với field `message`

Client Javis không được copy nguyên logic parse lỗi của Voxtral mà phải parse theo contract Javis.

## Verification plan

### Automated tests

1. Unit test cho `run_asr_javis.py`
   - mock WebSocket server theo protocol Javis
   - verify thứ tự `config -> start -> ready -> binary stream -> stop -> final`
   - verify transcript extraction ưu tiên `final.text`
   - verify fallback khi chỉ có `segments`

2. Failure-path tests
   - thiếu `JAVIS_WS_URL`
   - thiếu `JAVIS_SESSION_ID`
   - thiếu `JAVIS_TOKEN`
   - timeout ở `config`
   - timeout ở `ready`
   - timeout ở `final`
   - server error có `message`
   - `final` malformed

3. Full pipeline test
   - chạy `benchmark_runner.py --engine javis ...`
   - verify tạo đúng thư mục kết quả theo convention hiện tại
   - verify `evaluate_metrics.py` chạy được
   - verify `llm_evaluator.batch_runner` chạy được
   - verify `--resume` không trộn kết quả hai engine

### Integration test thủ công

Khi có endpoint thật và credentials hợp lệ:

```bash
python run_asr_javis.py --audio audio/silence_60s.wav --ws-url <JAVIS_WS_URL> --debug
```

Sau đó chạy benchmark trên cùng bộ audio cho cả hai engine và so sánh bằng:

```bash
python compare_engines.py --voxtral-run <voxtral_dir> --javis-run <javis_dir>
```

Không có bước Colab hay host tunnel trong quy trình này.

## External reference assumptions

Các điểm dưới đây có thể đúng theo reference ngoài repo, nhưng phải coi là giả định cho tới khi integration test xác nhận:

- endpoint production cụ thể của Javis ngoài môi trường local benchmark
- danh sách language option đầy đủ ngoài `ja`, `vi`, `en`, `auto`
- sự hiện diện của `segments` trong `final`
- hình dạng lỗi auth thực tế ngoài field `message`

Những giả định này không được ghi trong code như contract chắc chắn nếu chưa được test thật.

## Kết luận triển khai

Phạm vi v1 nên tập trung vào:

- thêm `run_asr_javis.py`
- thêm `--engine` vào `benchmark_runner.py`
- giữ output `results.json` tương thích
- giữ naming `results/DATE_vN`
- thêm `compare_engines.py` đọc đúng `results.json` và `llm_eval_summary.json`
- dùng raw-baseline làm cấu hình so sánh mặc định
- coi Javis là local API có auth bắt buộc qua env

Không mở rộng sang:

- Colab/ngrok cho Javis
- `server-audio-dir` cho Javis
- tuning WebRTC toàn diện
- diarization benchmark
- verification benchmark riêng
- weighted recommendation
