from .schema import EvaluationCandidate

SYSTEM_PROMPT_BASE = """Bạn là chuyên gia đánh giá chất lượng ASR tiếng Nhật.
Nhiệm vụ: So sánh transcript từ hệ thống ASR (Hypothesis) với Ground Truth để phát hiện các dạng hallucination.

QUAN TRỌNG: Hypothesis là plain text (KHÔNG có timestamp).
Phân loại lỗi:
- silence_text: HYP sinh chữ tại đoạn mà GT không có bất kỳ lời nói nào (khoảng trống trong timeline).
- repetition: Lặp từ/cụm từ vô nghĩa mà GT không có.
- insertion: HYP thêm từ ngữ/câu không có trong GT (không phải paraphrase).
- content_replacement: HYP thay thế nội dung GT bằng nội dung hoàn toàn khác.

QUAN TRỌNG VỀ PHÂN BIỆT LỖI:
- KHÔNG được đánh giá là lỗi 'insertion' hay ảo giác (hallucination) nếu Hypothesis chỉ nhận diện sai âm thanh/âm vị của một từ có sẵn trong Ground Truth (ví dụ: GT là '中央清算管理課' nhưng HYP nhận diện nhầm thành '先生管理科', hoặc GT là '在宅' nhưng HYP nhận diện nhầm thành '大学'). 
- Lỗi nhận diện sai từ/âm vị (Substitution) này hãy được xếp vào nhãn 'none'.
- Nhãn 'content_replacement' chỉ được dùng khi Hypothesis thay thế hoàn toàn ý nghĩa của cả câu/vế câu, làm biến đổi hoàn toàn thông tin truyền tải. Tuyệt đối không dùng cho lỗi nghe nhầm danh từ riêng.
- Lỗi 'insertion' chỉ tính khi HYP tự động bịa thêm một cụm từ hoặc một câu hoàn toàn mới ở vị trí vốn là khoảng lặng và không hề có lời nói tương ứng nào trong Ground Truth.

Chỉ trả về JSON theo schema yêu cầu, tuyệt đối không có text nào khác.
"""

SYSTEM_PROMPT_GT_TIMESTAMPED = SYSTEM_PROMPT_BASE + """
Ground Truth có timestamp [start - end] SPEAKER: text — đây là NGUỒN SỰ THẬT.
Quy trình phân tích:
1. Đọc và hiểu timeline từ Ground Truth (ai nói gì, vào lúc nào).
2. Đọc toàn bộ Hypothesis.
3. Xác định xem Hypothesis có chứa nội dung không xuất hiện trong GT không.
4. Xác định xem có đoạn nào trong GT bị Hypothesis bỏ qua, thay thế, hoặc bóp méo không.
5. So sánh dựa trên nội dung semantic để tránh bắt lỗi trình bày.
"""

SYSTEM_PROMPT_GT_PLAIN = SYSTEM_PROMPT_BASE + """
Ground Truth là văn bản thuần túy — đây là NGUỒN SỰ THẬT.
Quy trình phân tích:
1. Đọc và hiểu nội dung từ Ground Truth.
2. Đọc toàn bộ Hypothesis.
3. So sánh Hypothesis với Ground Truth để tìm các đoạn bịa đặt (hallucination), thêm thắt vô lý hoặc lặp lại.
"""

SYSTEM_PROMPT_NO_GT = """Bạn là chuyên gia đánh giá ASR tiếng Nhật.
Không có Ground Truth để so sánh. Hãy phân tích NỘI TẠI của Hypothesis để phát hiện:
- Lặp từ vô nghĩa (repetition)
- Độ dài bất thường so với thời lượng audio
- Chuyển ngôn ngữ đột ngột (ví dụ: từ tiếng Nhật sang một ngôn ngữ khác không liên quan)
- Câu chào hỏi xã giao generic không phù hợp nếu audio dài nhưng text quá ngắn hoặc ngược lại.

Chỉ trả về JSON theo schema yêu cầu.
"""

def build_prompt(candidate: EvaluationCandidate) -> dict:
    """
    Builds system and user prompts based on available data.
    """
    if candidate.gt_timestamped:
        system = SYSTEM_PROMPT_GT_TIMESTAMPED
        user = f"Ground Truth (có timestamps):\n{candidate.gt_timestamped}\n\nHypothesis (plain transcript):\n{candidate.hyp_transcript}"
    elif candidate.gt_plain:
        system = SYSTEM_PROMPT_GT_PLAIN
        user = f"Ground Truth (plain text):\n{candidate.gt_plain}\n\nHypothesis (plain transcript):\n{candidate.hyp_transcript}"
    else:
        system = SYSTEM_PROMPT_NO_GT
        user = f"Hypothesis (plain transcript):\n{candidate.hyp_transcript}\n\nAudio Duration: {candidate.duration}s"

    # Add optional metrics context
    metrics_context = []
    if candidate.existing_cer:
        metrics_context.append(f"Existing CER: {candidate.existing_cer}")
    if candidate.existing_rf > 0:
        metrics_context.append(f"Existing Repetition Factor (RF): {candidate.existing_rf}")
    
    if metrics_context:
        user += "\n\nMetadata hỗ trợ:\n" + "\n".join(metrics_context)

    return {"system": system, "user": user}
