import sys
sys.path.insert(0, 'D:/VJ/Voxtral')
from llm_evaluator.voxtral_utils import normalize_japanese, calculate_cer

# Ground truth reference
ref_raw = "はい、中央清算管理課でございます. え、愛知県名古屋市の株式会社アセットジャパンと申しますけども、お世話になります. お世話になっております. え、あの、山内さんをお願いできますでしょうか. すいませーん、山内は他の打ち合わせに出ておりまして、戻りがですね、12時前ぐらいにはなると思うんですけれども. 承知いたしました.じゃあ、急ぎではございませんので、またこちらから改めさせていただきます. あ、わかりました.もう一度、お名前をお伺いしてよろしいですか.アセットジャパンの… はい、伊藤でございます. 伊藤様ですね、かしこまりました. はい、じゃあ、あの、じゃあ、一言すいません、ご伝言お願いできますでしょうか. はい、どうぞ. はい、え、またあの山内様宛にですね、あの東浦町、今度はですね、あの東浦町の物件について、あのメールでお問い合わせいたしますとお伝えください. あ, かしこまりました.お伝えいたします. はい、ありがとうございます.失礼いたします. はい, よろしくお願いいたします.失礼いたします。"

# Hypothesis from test 1 segments
hyp_raw = (
    "Hi, Joseph. I'm sorry."
    "株式会社アセットジャパンといいますけれども、お世話になります。"
    "おめでとうか"
    ""
    "急ぎではございませんのでまたこちらから改めさせていただきます"
    "名前が関してよろしいですか?窃盗ジャパンの伊藤でございます"
    "一言すいませんご伝言をお願いできますでしょうか"
    "どうぞまた山内様宛てにですね東浦町"
    "今度は東浦町の物件についてメールでお問い合わせ"
    "しましたお伝えください確かまりましたお伝えいたしますはいありがとうございます"
    ""
)

ref_norm = normalize_japanese(ref_raw)
hyp_norm = normalize_japanese(hyp_raw)

print(f"Normalized reference length: {len(ref_norm)}")
print(f"Normalized hypothesis length: {len(hyp_norm)}")

cer_val = calculate_cer(hyp_norm, ref_norm)
print(f"CER (normalized): {cer_val:.4f} ({cer_val*100:.2f}%)")
