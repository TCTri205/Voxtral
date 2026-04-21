# WebSocket `/api/v4/ws/improved`

Real-time audio transcription qua WebSocket với các tùy chọn denoise, diarization và verification.

## Connection

```
ws://host:port/api/v4/ws/improved
```

## Protocol Flow

```
Client                              Server
  |── connect ──────────────────────▶|
  |◀──────────── {"type":"config"} ──|
  |── {"event":"start", ...} ───────▶|
  |◀──────────── {"type":"ready"} ───|
  |── binary PCM16 audio ──────────▶|
  |── binary PCM16 audio ──────────▶|
  |◀──── {"type":"partial", ...} ────|
  |◀──── {"type":"partial", ...} ────|
  |── {"event":"stop"} ────────────▶|
  |◀── {"type":"recorded_audio"} ────|
  |◀──────── {"type":"final"} ──────|
```

## Audio Format

| Property    | Value                    |
|-------------|--------------------------|
| Encoding    | PCM16 (signed int16)     |
| Channels    | Mono                     |
| Sample rate | 16000 Hz                 |
| Byte order  | Little-endian            |

## Start Message (Input)

Client gửi JSON message đầu tiên với `"event": "start"` để khởi tạo session.

```json
{
  "event": "start",
  "sample_rate": 16000,
  "format": "pcm16",
  "language": "ja",
  "detect_speaker": false,
  "noise_suppression": true,
  "denoiser": "demucs",
  "webrtc_denoise_enabled": false,
  "webrtc_enable_ns": true,
  "webrtc_agc_type": 1,
  "webrtc_aec_type": 0,
  "webrtc_enable_vad": false,
  "webrtc_frame_ms": 10,
  "webrtc_ns_level": 0,
  "save_processed_audio": false,
  "save_recorded_audio": false,
  "session_id": "abc-123",
  "token": "access_token_here"
}
```

### Options chi tiết

#### Core

| Field | Type | Default | Mô tả |
|-------|------|---------|-------|
| `event` | string | **required** | Phải là `"start"` |
| `sample_rate` | int | `16000` | Sample rate audio đầu vào |
| `format` | string | `"pcm16"` | Định dạng audio |
| `language` | string | `"ja"` | Ngôn ngữ (`ja`, `vi`, `en`, `auto`) |

#### Noise Suppression (Backend Denoise)

| Field | Type | Default | Mô tả |
|-------|------|---------|-------|
| `noise_suppression` | bool | `true` | Bật/tắt backend denoise (demucs hoặc df). Khi `false`, audio không qua bước denoise backend. |
| `denoiser` | string | `"demucs"` | Loại denoiser backend: `"demucs"`, `"df"` (DeepFilterNet), hoặc `"webrtc"`. Chỉ 1 trong 3 được dùng tại 1 thời điểm. |

#### WebRTC Realtime Denoise

WebRTC denoise chạy **realtime trên từng chunk** trước khi audio được đưa vào transcription engine. Hoạt động **độc lập** với backend denoise ở trên.

| Field | Type | Default | Range | Mô tả |
|-------|------|---------|-------|-------|
| `webrtc_denoise_enabled` | bool | `false` | | Bật WebRTC APM realtime denoise |
| `webrtc_enable_ns` | bool | `true` | | Noise suppression module |
| `webrtc_agc_type` | int | `1` | 0–2 | Auto gain control. `0`=off, `1`=Adaptive Digital, `2`=Adaptive Analog |
| `webrtc_aec_type` | int | `0` | 0–3 | Echo cancellation. `0`=off, `1`=echo_control_mobile, `2`=echo_cancellation, `3`=echo_canceller3 |
| `webrtc_enable_vad` | bool | `false` | | Voice Activity Detection |
| `webrtc_frame_ms` | int | `10` | 5–20 | Kích thước frame xử lý (ms) |
| `webrtc_ns_level` | int | `0` | 0–3 | Mức noise suppression. Càng cao càng aggressive |

#### Speaker Diarization

| Field | Type | Default | Mô tả |
|-------|------|---------|-------|
| `detect_speaker` | bool | `false` | Bật phân biệt speaker (dùng Sortformer model) |

#### Sentence Verification

Sau khi nhận đủ câu, server gửi batch audio tới transcribe API để verify lại kết quả realtime.

| Field | Type | Default | Mô tả |
|-------|------|---------|-------|
| `verify_with_transcribe_api` | bool | `true` | Bật verification |
| `verify_sentence_count` | int | `4` | Số câu tích lũy trước khi verify |
| `verify_save_audio` | bool | `true` | Lưu audio segment dùng để verify |
| `verify_min_tokens` | int | `25` | Số token tối thiểu để trigger verify |
| `verify_silence_timeout_s` | float | `3.0` | Timeout im lặng (giây) trước khi tự verify |

#### Audio Recording & Spend Tracking

| Field | Type | Default | Mô tả |
|-------|------|---------|-------|
| `save_processed_audio` | bool | `false` | Lưu audio đã xử lý (sau denoise) |
| `save_recorded_audio` | bool | `false` | Lưu audio raw và denoised, trả URL khi stop |
| `session_id` | string | `null` | ID session cho spend tracking |
| `token` | string | `null` | Access token cho spend tracking & balance check |

## Output Messages (Server → Client)

### `config`

Gửi ngay sau khi connect.

```json
{"type": "config", "useAudioWorklet": true, "api_version": "v4"}
```

### `ready`

Gửi sau khi nhận `start` và khởi tạo xong.

```json
{
  "type": "ready",
  "api_version": "v4",
  "webrtc_denoise": {
    "sample_rate": 16000,
    "frame_ms": 10,
    "enable_ns": true,
    "agc_type": 1,
    "aec_type": 0,
    "enable_vad": false,
    "ns_level": 0
  }
}
```

> `webrtc_denoise` chỉ xuất hiện khi `webrtc_denoise_enabled = true`.

### `partial`

Kết quả transcription realtime (streaming liên tục).

```json
{
  "type": "partial",
  "text": "こんにちは",
  "speaker_id": 0,
  "language": "ja",
  "segments": [...]
}
```

### `recorded_audio`

Gửi khi `save_recorded_audio = true`, trước message `final`.

```json
{
  "type": "recorded_audio",
  "api_version": "v4",
  "raw_audio_url": "https://...",
  "denoised_audio_url": "https://..."
}
```

### `final`

Kết thúc session.

```json
{
  "type": "final",
  "text": "",
  "api_version": "v4",
  "verification_json_path": "/path/to/verification.json",
  "verification_count": 3
}
```

> `verification_json_path` và `verification_count` chỉ có khi verification được bật.

### `error`

```json
{"type": "error", "message": "Exceeds maximum budget"}
```

### `pong`

Phản hồi cho `{"event": "ping"}`.

```json
{"type": "pong"}
```

## Tắt toàn bộ option — giữ Raw Audio

Để server chỉ nhận audio và transcribe mà **không** qua bất kỳ bước xử lý phụ nào:

```json
{
  "event": "start",
  "sample_rate": 16000,
  "format": "pcm16",
  "language": "ja",

  "noise_suppression": false,
  "webrtc_denoise_enabled": false,
  "detect_speaker": false,
  "save_processed_audio": false,
  "save_recorded_audio": false
}
```

| Tắt gì | Field | Giá trị |
|---------|-------|---------|
| Backend denoise (demucs/df) | `noise_suppression` | `false` |
| WebRTC realtime denoise | `webrtc_denoise_enabled` | `false` |
| Speaker diarization | `detect_speaker` | `false` |
| Sentence verification | `verify_with_transcribe_api` | `false` |
| Lưu audio đã xử lý | `save_processed_audio` | `false` |
| Lưu audio raw/denoised | `save_recorded_audio` | `false` |

Với config trên, audio PCM16 được đưa **thẳng** vào transcription engine mà không bị biến đổi.
