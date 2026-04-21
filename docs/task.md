# Voxtral ASR Baseline Setup & Execution

## Giai đoạn 1: Chuẩn bị & Thiết lập (Đã hoàn thành)

- [x] Rà soát và loại bỏ các logic vLLM cũ (Legacy Cleanup - Reviewed by Codex Agent)

- [x] Đọc và hiểu tài liệu của mô hình `mistralai/Voxtral-Mini-4B-Realtime-2602`
- [x] Phân tích lý thuyết về các vấn đề ảo giác (hallucination)
- [x] Rà soát 9 tệp âm thanh mẫu trong thư mục `audio/`
- [x] Hoàn thiện script Python `run_asr.py` (V1: Batch, metrics, RTF)
- [x] Tạo script `generate_test_samples.py` cho stress test
- [x] Cập nhật `voxtral_baseline.ipynb` với Ngrok tunnel
- [x] Cập nhật `README_SETUP.md` với hướng dẫn chi tiết

## Giai đoạn 2: Thực thi & Kiểm chứng (Tiếp theo)

- [ ] Chạy stress test (Silence/Noise) từ máy Local trỏ đến Colab
- [ ] Tổng hợp kết quả RTF và Latency vào `results.json`
- [ ] Phân tích kết quả ảo giác thực tế và cập nhật `voxtral_hallucination_analysis.md`
- [ ] Đánh giá hiệu năng dựa trên các mức `delay` khác nhau (240ms, 480ms, 1200ms)

---
*Ghi chú: Đã sẵn sàng tất cả công cụ và môi trường để thực hiện Giai đoạn 2.*
