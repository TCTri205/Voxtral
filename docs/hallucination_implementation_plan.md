# Kế hoạch Triển khai: Đánh giá Hallucination bằng LLM [HOÀN THÀNH]

## 1. Mục tiêu

Tài liệu này chuyển hóa ý tưởng trong `docs/llm_based_hallucination_evaluation_plan.md` thành kế hoạch triển khai bám sát code hiện tại của repo:

- `run_asr.py` tạo `results/<run_dir>/results.json`, `report.md`, `log_debug.txt`
- `evaluate_metrics.py` đang tính `HRS`, `RF`, `CER` và ghi ngược lại vào `results.json`
- Ground truth hiện có ở hai nguồn:
  - `ground_truth.json`: plain transcript để tính CER
  - `timestamps/*.txt`: transcript có timestamp/speaker để làm ngữ cảnh cho LLM

Mục tiêu là bổ sung một tầng đánh giá semantic bằng LLM để phân loại các trường hợp hallucination mà `CER`, `RF`, `HRS` chưa mô tả được, nhưng không thay thế pipeline hiện có.

## 2. Thiết kế được chốt

### 2.1 Package mới: `llm_evaluator/`

Tạo package mới ở thư mục gốc repo:

```text
llm_evaluator/
├── __init__.py
├── voxtral_utils.py
├── schema.py
├── data_loader.py
├── prompt_builder.py
├── llm_caller.py
├── report_exporter.py
└── batch_runner.py
```

### 2.2 Utilities dùng chung

#### `llm_evaluator/voxtral_utils.py`

Chứa các hàm dùng chung, không để logic này nằm rải rác ở nhiều file:

- `normalize_japanese(text: str) -> str`
  - Di chuyển nguyên logic hiện có từ `evaluate_metrics.py`.
  - `evaluate_metrics.py` sẽ import lại từ đây để tránh duplication.
- `canonical_stem(path_or_name: str) -> str`
  - Lấy basename.
  - Bỏ extension nếu có.
  - Lowercase.
  - Chuẩn hóa khoảng trắng và ngoặc về dạng ổn định.
  - Chuyển mọi chuỗi ký tự không phải `[a-z0-9]` thành `_`.
  - Gộp nhiều `_` liên tiếp thành một `_`.
  - Không xóa thông tin `(1)` hay `_(1)`. Chỉ chuẩn hóa để:
    - `media_148284_1767766514646 (1).mp3`
    - `media_148284_1767766514646_(1).txt`
    cùng map về một canonical stem.

Quy tắc này được chốt để tránh ghép nhầm file khi dữ liệu thực tế đang dùng cả hai biến thể tên.

### 2.3 Schema đầu ra LLM

Chốt dùng **schema đơn giản, một kết luận chính cho mỗi file**, đúng với thiết kế gốc trong `llm_based_hallucination_evaluation_plan.md`. Không dùng `hallucinations: List[...]` ở v1 vì:

- batch hiện chỉ cần một nhãn chính để tổng hợp thống kê
- prompt và exporter đơn giản hơn
- giảm rủi ro parse lỗi hoặc output dài không cần thiết

#### `llm_evaluator/schema.py`

```python
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
```

Quy tắc:

- `has_hallucination=False` thì `primary_error="none"`, `severity="none"`
- `review_status` mặc định do LLM trả về, nhưng có thể bị override bởi heuristic ở exporter

### 2.4 Data loading và matching

#### `llm_evaluator/data_loader.py`

Triển khai các hàm:

- `load_results(results_json_path) -> list[dict]`
  - Đọc `results.json`
  - Chỉ lấy record `status == "success"`
- `load_ground_truth_map(ground_truth_path) -> dict[str, str]`
  - Đọc `ground_truth.json`
  - Index theo `canonical_stem(key)`
- `load_timestamp_map(timestamps_dir) -> dict[str, str]`
  - Đọc toàn bộ `*.txt` trong `timestamps/`
  - Index theo `canonical_stem(filename)`
- `load_evaluation_candidates(results_json_path, ground_truth_path="ground_truth.json", timestamps_dir="timestamps") -> list[EvaluationCandidate]`

Quy tắc ghép dữ liệu:

1. Lấy `canonical_id = canonical_stem(result["file"])`
2. Match sang `ground_truth.json` bằng `canonical_id`
3. Match sang `timestamps/` bằng `canonical_id`
4. Không fail nếu thiếu một trong hai nguồn GT
5. Nếu thiếu cả `gt_plain` và `gt_timestamped`, candidate vẫn được tạo nhưng sẽ chạy ở `no_gt` mode

Không có fuzzy matching ngoài `canonical_stem`. Không thêm heuristic “gần đúng” khác trong v1 để tránh ghép sai âm thầm.

### 2.5 Prompt builder

#### `llm_evaluator/prompt_builder.py`

Xuất ra 2 string: `system_prompt`, `user_prompt`.

Có 3 mode:

- `gt_timestamped_mode`: khi có `gt_timestamped`
- `gt_plain_mode`: khi không có `gt_timestamped` nhưng có `gt_plain`
- `no_gt_mode`: khi thiếu cả `gt_timestamped` và `gt_plain`

Quy tắc prompt:

- Ưu tiên `gt_timestamped` làm reference frame cho LLM
- Nếu không có `gt_timestamped` nhưng có `gt_plain`, vẫn dùng `gt_plain` để so sánh semantic ở mức không có timeline, thay vì rơi thẳng xuống `no_gt_mode`
- Không truyền bản normalize vào prompt chính; giữ nguyên văn bản gốc để LLM có ngữ cảnh tự nhiên
- Nếu cần, có thể bổ sung một dòng metadata ngắn:
  - `existing_cer`
  - `existing_rf`
  - `duration`
- Không yêu cầu chain-of-thought
- Chỉ yêu cầu JSON theo schema

Lý do không truyền transcript đã normalize:

- `normalize_japanese` phù hợp cho CER hơn là cho semantic judging
- giữ nguyên chuỗi giúp LLM nhận diện chuyển ngôn ngữ, dấu hiệu lịch sự, proper noun tốt hơn

### 2.6 LLM caller

#### `llm_evaluator/llm_caller.py`

Sử dụng:

- `openai.AsyncOpenAI`
- model mặc định: `gpt-4o-mini`
- `temperature=0.0`
- structured output parse vào `EvaluationResult`
- **Quản lý Key**: Hỗ trợ xoay vòng (round-robin) nếu cấu hình nhiều key để tránh rate limit.

Triển khai:

- `async evaluate_single(candidate, client, model) -> EvaluationResult`
- `async evaluate_batch(candidates, model, concurrency=5) -> list[EvaluationResult]`

Yêu cầu:

- Có `asyncio.Semaphore(concurrency)`
- Nếu API call fail ở một file, không làm hỏng cả batch
- Trả về record lỗi dạng fallback:
  - `has_hallucination=False`
  - `primary_error="none"`
  - `review_status="manual_review"`
  - `reasoning="LLM call failed: ..."`

### 2.7 Exporter và heuristic

#### `llm_evaluator/report_exporter.py`

Sinh 3 file trong cùng `run_dir` với `results.json`:

- `llm_eval_details.csv`
- `llm_eval_summary.json`
- `llm_eval_report.md`

Không append vào `report.md` ở v1.

Lý do:

- `report.md` hiện là output thuần từ `evaluate_metrics.py`
- append sẽ gây khó xử lý rerun và `--resume`
- tách riêng `llm_eval_report.md` giúp output idempotent, rõ nguồn gốc hơn

Heuristic override bắt buộc:

- Nếu `existing_cer` parse được thành số và `existing_cer > 50.0`
- và `has_hallucination == False`
- thì set `review_status = "manual_review"`

`llm_eval_summary.json` phải có:

```json
{
  "run_dir": "results/17-04-2026_v2",
  "model_used": "gpt-4o-mini",
  "total_files": 11,
  "evaluated_files": 11,
  "with_gt_timestamped": 9,
  "without_gt_timestamped": 2,
  "hallucination_rate": 0.0,
  "manual_review_rate": 0.0,
  "error_distribution": {},
  "severity_distribution": {},
  "existing_metrics": {
    "avg_cer": "45.03%",
    "avg_inference_rtf": 1.890,
    "hrs": 0.0
  }
}
```

`avg_cer` lấy trung bình từ các giá trị `existing_cer` parse được trong batch, không tự tính lại CER ở exporter.

### 2.9 Quản lý Multiple API Keys (Mới)

 Để xử lý batch lớn mà không bị nghẽn (Rate Limit), hệ thống sẽ:

- Đọc biến môi trường `OPENAI_API_KEYS` (dạng chuỗi phân tách bằng dấu phẩy).
- `llm_caller.py` sẽ khởi tạo một danh sách `AsyncOpenAI` clients tương ứng.
- Mỗi request trong `evaluate_batch` sẽ sử dụng một client từ pool theo cơ chế **Round-Robin**.
- Nếu một key bị lỗi `429` (Rate Limit), caller sẽ tự động thử lại với key tiếp theo trong danh sách (backoff retry).

### 2.8 Batch runner

#### `llm_evaluator/batch_runner.py`

CLI entry point riêng, không nhúng logic trực tiếp vào `run_asr.py`.

CLI tối thiểu:

```bash
python -m llm_evaluator.batch_runner \
  --results results/17-04-2026_v2/results.json \
  --ground-truth ground_truth.json \
  --timestamps timestamps \
  --model gpt-4o-mini
```

Quy tắc:

- `batch_runner.py` phải tự gọi `load_dotenv()` để hỗ trợ cả trường hợp chạy standalone, không chỉ khi được `run_asr.py` gọi subprocess
- Tự resolve `run_dir = dirname(results_json_path)`
- Ghi 3 output vào `run_dir`
- Không sửa `results.json`
- Exit code khác 0 nếu toàn bộ batch runner fail trước khi gọi được evaluator

## 3. Tích hợp với code hiện tại

### 3.1 `evaluate_metrics.py`

Refactor tối thiểu:

- Import `normalize_japanese` từ `llm_evaluator.voxtral_utils`
- Không đổi behavior CLI hiện tại
- Chưa hỗ trợ `--gt timestamps/` trong đợt này

Lý do:

- `evaluate_metrics.py` hiện đang chạy ổn với `ground_truth.json`
- hỗ trợ thêm GT directory là thay đổi hợp lý nhưng không bắt buộc để LLM evaluator hoạt động
- nên tách làm bước sau nếu thật sự cần CER reconstructed từ timestamps

### 3.2 `run_asr.py`

Thêm flag:

- `--llm-eval`
- `--llm-model` với default `gpt-4o-mini`
- `--ground-truth` với default `ground_truth.json`
- `--timestamps-dir` với default `timestamps`

Thứ tự pipeline sau khi chạy xong batch:

1. `run_asr.py` ghi `results.json`
2. `run_asr.py` gọi `evaluate_metrics.py` để sinh `report.md`, đồng thời truyền `--gt <ground_truth>` mặc định để `CER` tiếp tục xuất hiện trong report tự động
3. Nếu có `--llm-eval`, `run_asr.py` gọi:

```bash
python -m llm_evaluator.batch_runner \
  --results <results.json> \
  --ground-truth <ground_truth> \
  --timestamps <timestamps_dir> \
  --model <llm_model>
```

Nếu LLM evaluator fail:

- chỉ log warning
- không làm fail cả `run_asr.py`

### 3.3 `requirements.txt`

Thêm:

- `openai>=1.40.0`
- `pydantic>=2.0`

Không thêm thư viện khác trong v1 nếu chưa cần.

## 4. Kế hoạch verify

### 4.1 Unit-level checks

Viết test cho:

- `canonical_stem`
  - `.mp3` vs `.txt`
  - `(1)` vs `_(1)`
  - case-insensitive
- `load_evaluation_candidates`
  - có cả `gt_plain` và `gt_timestamped`
  - chỉ có `gt_plain`
  - không có GT

### 4.2 Prompt smoke checks

Chạy calibration trên đúng 5 file đã nêu trong tài liệu phương pháp:

- low CER:
  - `media_148284_1767766514646 (1).mp3`
  - `media_148393_1767860211615 (1).mp3`
- high CER:
  - `media_148414_1767922241264 (1).mp3`
  - `media_149291_1769069811005.mp3`
  - `media_148280_1767762915627.mp3`

Kỳ vọng:

- file `media_148414_1767922241264 (1).mp3` có khả năng bị gắn `content_replacement` hoặc `insertion` vì transcript tiếng Anh `"Hi, Joseph. I'm sorry."` lệch mạnh khỏi GT
- 2 file low CER không nên bị gắn hallucination mức cao

### 4.3 E2E integration

Chạy:

```bash
python run_asr.py --audio_dir audio --llm-eval
```

Kiểm tra:

- `results/<run_dir>/report.md` vẫn sinh như cũ
- có thêm:
  - `llm_eval_details.csv`
  - `llm_eval_summary.json`
  - `llm_eval_report.md`
- rerun với `--resume` không làm hỏng output cũ

## 5. Giả định và giới hạn

- `OPENAI_API_KEY` có sẵn trong môi trường hoặc `.env`
- LLM evaluation là lớp bổ sung semantic, không phải ground truth tuyệt đối
- Không dùng `timestamps/*.txt` để tính lại CER trong đợt này
- Không append LLM section vào `report.md` trong v1
- Không hỗ trợ nhiều provider trong v1; chỉ chốt OpenAI trước
- Không dùng multi-label output trong v1; mỗi file chỉ có một `primary_error`
