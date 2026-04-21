from typing import Literal
from pydantic import BaseModel, Field

class EvaluationCandidate(BaseModel):
    filename: str
    canonical_id: str
    hyp_transcript: str
    gt_timestamped: str | None = None
    gt_plain: str | None = None
    duration: float | None = None
    existing_cer: str | None = None
    existing_rf: int = 0
    existing_inference_rtf: float | None = None

class EvaluationResult(BaseModel):
    filename: str
    has_hallucination: bool
    primary_error: Literal[
        "silence_text",
        "repetition",
        "insertion",
        "content_replacement",
        "none",
    ] = "none"
    evidence_hyp_text: str | None = Field(
        default=None,
        description="Đoạn text trong hypothesis là bằng chứng của kết luận",
    )
    evidence_gt_context: str | None = Field(
        default=None,
        description="Đoạn ground truth tương ứng để đối chiếu; có thể kèm timestamp",
    )
    severity: Literal["high", "medium", "low", "none"] = "none"
    confidence: Literal["high", "medium", "low"] = "low"
    review_status: Literal["auto_accept", "manual_review"] = "auto_accept"
    reasoning: str = Field(
        description="Giải thích ngắn gọn, tối đa 2 câu"
    )
    existing_cer: str | None = None
    existing_rf: int = 0
    existing_inference_rtf: float | None = None
