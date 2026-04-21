# Phụ lục (Appendix): Case study có timestamp (Timeline Case Studies)

## Nguồn dữ liệu
- Snapshot date: `2026-04-21`
- Voxtral runs: `18-04-2026_v1` đến `19-04-2026_v10` (15 run, thư mục `results/`)
- Javis runs: `19-04-2026_v1` đến `19-04-2026_v10` (10 run, thư mục `results_javis/`)
- Record count: `275` inference record trên `11` file
- Unified snapshot files: [multi_run_records.csv](./data/multi_run_records.csv), [multi_run_summary.json](./data/multi_run_summary.json)

## Nguyên tắc chọn case (Case Selection Criteria)
- Chỉ chọn các file xuất hiện trong thống kê tổng thể và có `timestamps/` cùng `rttm/` để truy vết.
- File này không tự tạo metric mới; mọi số liệu đều lấy từ snapshot liên-run trong `reports/data/`.

## Sai ngôn ngữ hoặc sai hoàn toàn (Language Error or Absolute Failure): `media_148414_1767922241264 (1).mp3`

### Quan sát dữ liệu (Data Observations)
- Engine trọng tâm: `voxtral`; mean CER 100.0%, std CER 0.0%, mean RTF 1.825.
- Engine đối chứng `javis` có mean CER 39.5%. Xác suất `javis` tốt hơn về CER trên file này là 100.0%.
- LLM-eval trên `voxtral`: hallucination rate 93.3%, high severity rate 93.3%.
- Audio quality: rolloff 2364 Hz, flatness 0.072, RMS trung bình 0.030.
- RTTM: 21 segment, 2 speaker, khoảng 52.4 giây có thoại trong `rttm/media_148414_1767922241264.rttm`.
- GT excerpt: [0.746 - 2.837] SPEAKER 1: はい、中央清算管理課でございます。 [3.129 - 8.094] SPEAKER 2: え、愛知県名古屋市の株式会社アセットジャパンと申しますけども、お世話になります。 [7.492 - 8.838] SPEAKER 1: お世話になっております。
- Hypothesis excerpt dùng minh họa: Hi, Joseph. I'm sorry.

### Giả thuyết kỹ thuật (Technical Hypotheses)
- Đây là một lỗi có tính lặp lại của Voxtral trên file narrowband này, vì transcript hash bất biến qua mọi run và CER cố định 100.00%.
- Việc hypothesis rơi sang một câu tiếng Anh rất ngắn gợi ý failure mode nhận dạng sai ngôn ngữ hoặc collapse decoder; đây là suy luận từ đầu ra, không phải fact về kiến trúc nội bộ.

## Looping hoặc thay thế nội dung (Looping or Content Replacement): `media_148439_1767926711644 (1).mp3`

### Quan sát dữ liệu (Data Observations)
- Engine trọng tâm: `javis`; mean CER 41.4%, std CER 23.9%, mean RTF 0.009.
- Engine đối chứng `voxtral` có mean CER 35.1%. Xác suất `voxtral` tốt hơn về CER trên file này là 30.0%.
- LLM-eval trên `javis`: hallucination rate 100.0%, high severity rate 60.0%.
- Audio quality: rolloff 2141 Hz, flatness 0.071, RMS trung bình 0.025.
- RTTM: 18 segment, 2 speaker, khoảng 22.1 giây có thoại trong `rttm/media_148439_1767926711644.rttm`.
- GT excerpt: [2.339 - 4.027] SPEAKER 1: Assetojapanのクマガイでございます。 [4.578 - 6.290] SPEAKER 2: あ、お世話になります。 [5.871 - 7.153] SPEAKER 1: お世話になります。すいません、先ほどの来週の、あのー、( cần check lại đoạn ni )お打ち合わせの件なんですけども。
- Hypothesis excerpt dùng minh họa: 그렇게 와닌가 없으신데요. 네, 감사합니다. 감사합니다. 네, 알겠습니다. 감사합니다. 수고하세요. 네, 수고하세요. 수고하셨습니다. 네, 네, 감사합니다. 네,ありがとうございます. 네,はい. 네,お話しさせていただきます. 네,ありがとうございました. 네,お願いします. 네, 안녕하세요. 네, 저희는 네, 감사합니다. 안녕하세요. 네, 선생님. 네, 고맙습니다. 네, 여러분. 네, 저희가. 네, 안녕히 계십시오. 네, 여보세요. 네, 그러면은. 네

### Giả thuyết kỹ thuật (Technical Hypotheses)
- Javis có nhiều transcript hash khác nhau trên file này và xuất hiện các run CER rất cao, phù hợp với failure mode looping hoặc drift nội dung.
- Sự chênh lệch lớn giữa các run cho thấy đây không phải lỗi tất định của riêng file, mà là lỗi có xác suất xảy ra khi điều kiện giải mã xấu.

## Bỏ sót hoặc ngắt sớm (Omission or Early Truncation): `media_149291_1769069811005.mp3`

### Quan sát dữ liệu (Data Observations)
- Engine trọng tâm: `voxtral`; mean CER 97.8%, std CER 0.0%, mean RTF 0.611.
- Engine đối chứng `javis` có mean CER 91.5%. Xác suất `javis` tốt hơn về CER trên file này là 50.0%.
- LLM-eval trên `voxtral`: hallucination rate 0.0%, high severity rate 0.0%.
- Audio quality: rolloff 1891 Hz, flatness 0.041, RMS trung bình 0.039.
- RTTM: 45 segment, 2 speaker, khoảng 156.7 giây có thoại trong `rttm/media_149291_1769069811005.rttm`.
- GT excerpt: [0.900 - 9.722] SPEAKER 1: お待たせいたしました。はい、ちょっと担当はただいま席を外しておりまして不在にしておりまして、うちでお折り返しご連絡させていただきたいんですけれども、折り返しお電話させていただく際に、今かけていただいてる携帯の番号でよろしいですかね。 [2.175 - 2.458] SPEAKER 2: はい。かせん、あの、今日中にかかってきますか？ [6.272 - 6.702] SPEAKER 1: あ、ちょっと確認させていただきますのでちょっと、今日中がもしかしたら難しいかもしれないんですけれども、明日以降でも大丈夫そうですか？
- Hypothesis excerpt dùng minh họa: (không có excerpt ngắn trong llm_eval)

### Giả thuyết kỹ thuật (Technical Hypotheses)
- Voxtral chỉ tạo một hypothesis ngắn trong khi file có thời lượng thoại lớn, nên giả thuyết hợp lý nhất là ngắt sớm hoặc bỏ sót phần lớn nội dung.
- File này cũng cho thấy Javis có tail risk lớn: mean CER gần ngang Voxtral nhưng variance rất cao, nên không thể chỉ đọc trung bình mà kết luận ổn định.

## Giữ cấu trúc tốt hơn ở narrowband (Structure Preservation in Narrowband): `media_148394_1767860189485 (1).mp3`

### Quan sát dữ liệu (Data Observations)
- Engine trọng tâm: `javis`; mean CER 24.7%, std CER 4.1%, mean RTF 0.009.
- Engine đối chứng `voxtral` có mean CER 33.7%. Xác suất `voxtral` tốt hơn về CER trên file này là 0.0%.
- LLM-eval trên `javis`: hallucination rate 100.0%, high severity rate 0.0%.
- Audio quality: rolloff 2402 Hz, flatness 0.099, RMS trung bình 0.014.
- RTTM: 15 segment, 2 speaker, khoảng 21.0 giây có thoại trong `rttm/media_148394_1767860189485.rttm`.
- GT excerpt: [0.958 - 1.849] SPEAKER 1: はい、マルケンです。 [2.199 - 5.223] SPEAKER 2: あ、いつもお世話になってます。AJテクノロジーズの山下です。 [5.421 - 6.130] SPEAKER 1: あ、お世話になります。
- Hypothesis excerpt dùng minh họa: ありがとうございます。そんなります。すみません。

### Giả thuyết kỹ thuật (Technical Hypotheses)
- Trên file narrowband này, Javis giữ cấu trúc hội thoại gần GT hơn Voxtral ở phần lớn run, dù vẫn có insertion mức medium.
- Rolloff thấp hỗ trợ giả thuyết rằng băng thông hẹp làm Voxtral suy giảm mạnh hơn về cấu trúc, nhưng đây vẫn chỉ là tương quan quan sát được trong snapshot.
