# Implementation Plan - Voxtral ASR Improvements (Based on v4/v5 Results)

## Context

Kết quả benchmark từ v4 và v5 cho thấy hệ thống đã đạt độ ổn định cao (CER giống nhau tuyệt đối 38.49%), nhưng vẫn còn các vấn đề nghiêm trọng cần giải quyết.

## Key Findings from v4/v5 Analysis

1. **Hallucination Rate vẫn cao (81.82%):**
   - `media_148414`: CER 55.61%, Language Collapse không thể phục hồi
   - `media_148439`: CER 31.73%, High Severity do Context Collapse
   - Lỗi "Hi, Joseph. How are you?" vẫn xuất hiện

2. **Language Collapse Recovery chưa hiệu quả:**
   - 3/11 retry thất bại (2 file bị ảnh hưởng: media_148414, media_149291)
   - File `media_148414` có retry nhưng failed, kèm hallucination_warning

3. **Server Performance Issues:**
   - File dài (`media_149291` - 156s) gây high keepalive warnings

## Action Items

### Priority 1: Post-processing Filter for Hallucination

**Mục tiêu:** Loại bỏ các câu tiếng Anh và social expressions formulaic trước khi trả về kết quả.

**Cài đặt:**
1. Thêm filter loại bỏ các câu tiếng Anh cụ thể:
   - "Hi, Joseph. How are you?" / "Hi, Joseph. I'm sorry."
   - "Just the Asaga."
   - "Thank you for calling."

2. Vị trí: Sau quá trình merge chunks, trước khi trả về transcript.

### Priority 2: Improve Language Collapse Recovery

**Mục tiêu:** Tăng tỷ lệ thành công của retry mechanism.

**Cài đặt:**
1. Tăng `LANG_COLLAPSE_CONTEXT_SEC` từ 5s lên 8s để cung cấp đủ context tiếng Nhật
2. Thêm mechanism: nếu retry failed, thử lại với anchor khác (neighbor after thay vì before)
3. Thêm fallback: post-processing removal nếu retry vẫn failed

### Priority 3: Server Stability for Long Files

**Mục tiêu:** Giảm high keepalive warnings cho file > 2 phút.

**Cài đặt:**
1. Giảm `CHUNK_LIMIT_SEC` xuống còn 12s cho audio dài > 120s
2. Tăng keepalive interval từ 5s lên 3s để giảm delay perceived

## Implementation Details

### File: voxtral_server_transformers.py

```python
# Post-processing hallucination patterns
HALLUCINATION_PATTERNS = [
    r"Hi, Joseph\. How are you\?",
    r"Hi, Joseph\. I'm sorry\.",
    r"Just the Asaga\.",
    r"Thank you for calling\.",
]

def _remove_hallucination_patterns(transcript: str) -> str:
    """Remove known hallucination patterns from transcript."""
    import re
    for pattern in HALLUCINATION_PATTERNS:
        transcript = re.sub(pattern, "", transcript)
    return transcript.strip()
```

### Testing Plan

1. Chạy benchmark lại với post-processing filter
2. Kiểm tra `media_148414` - kỳ vọng CER giảm từ 55.61%
3. Kiểm tra `media_148439` - kỳ vọng hallucination removal
4. Verify không ảnh hưởng đến các file khác