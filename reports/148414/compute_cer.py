import sys

# Ground truth reference for media_148414 (full transcript)
ref = "はい、中央清算管理課でございます. え、愛知県名古屋市の株式会社アセットジャパンと申しますけども、お世話になります. お世話になっております. え、あの、山内さんをお願いできますでしょうか. すいませーん、山内は他の打ち合わせに出ておりまして、戻りがですね、12時前ぐらいにはなると思うんですけれども. 承知いたしました.じゃあ、急ぎではございませんので、またこちらから改めさせていただきます. あ、わかりました.もう一度、お名前をお伺いしてよろしいですか.アセットジャパンの… はい、伊藤でございます. 伊藤様ですね、かしこまりました. はい、じゃあ、あの、じゃあ、一言すいません、ご伝言お願いできますでしょうか. はい、どうぞ. はい、え、またあの山内様宛にですね、あの東浦町、今度はですね、あの東浦町の物件について、あのメールでお問い合わせいたしますとお伝えください. あ, かしこまりました.お伝えいたします. はい、ありがとうございます.失礼いたします. はい, よろしくお願いいたします.失礼いたします。"

# Concatenated model outputs from test 1 (per-segment inference)
hyp = (
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

print(f"Reference length: {len(ref)}")
print(f"Hypothesis length: {len(hyp)}")

def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

distance = levenshtein(ref, hyp)
cer = distance / len(ref)
print(f"Edit distance: {distance}")
print(f"CER: {cer:.4f} ({cer*100:.2f}%)")
