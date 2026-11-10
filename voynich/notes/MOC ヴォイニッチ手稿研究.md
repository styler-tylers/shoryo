---
tags:
  - 未解読文書
  - ヴォイニッチ手稿
  - MOC
aliases:
  - Voynich Manuscript 研究
created: 2026-11-10
---

# MOC ヴォイニッチ手稿研究

> [!summary] 要旨
> 未解読の写本 [[ヴォイニッチ手稿（Beinecke MS 408）]] を、転写データの統計から調べる研究の入口。
> 解読を目指す前に、「文章がどんな規則で書かれているか」を数えて確かめる段階。

## 史料

- [[ヴォイニッチ手稿（Beinecke MS 408）]] — 写本そのもの。Yale Beinecke 蔵、全頁デジタル公開【A】
- [[ZL転写ファイル]] — 全文の EVA 転写（Zandbergen, 版 3b）【B】
- IT 転写（高橋健, 1999 年版）・RF 参照転写 — 比較に使用。史料ノートは未作成【B】
- [[Singulion Structure and the Voynich Manuscript]] — Layfield & Davis (2026)。二つ折り 1 枚ずつ読む作りだったという論文【B】

## 調査ログ

- [[2026-11-10 ヴォイニッチ手稿 定量分析]] — 単語頻度・語頭語尾・行頭行末・語彙の移り変わり（第 1 回）
- [[2026-11-10 ヴォイニッチ手稿 転写比較と行頭形の検証]] — 3 つの転写での再現確認と、行頭形・行末形の検証（第 2 回）
- [[2026-11-10 ヴォイニッチ手稿 元の並びの推定]] — 二つ折り単位で語彙の似たものを隣に並べた候補（第 3 回）
- [[2026-11-10 ヴォイニッチ手稿 singulion 仮説の検証]] — Layfield & Davis (2026) の再現。星・レシピの並びが論文と一致（第 4 回）
- [[2026-11-10 ヴォイニッチ手稿 絵と文章の対応（色の予備実験）]] — 絵の色と語彙の対応は植物セクション内では見られず（第 5 回）
- [[2026-11-10 ヴォイニッチ手稿 ラベルの分析]] — ラベルは本文と形が違うが、同じ頁の本文での言及は偶然並み（第 6 回）
- [[2026-11-10 ヴォイニッチ手稿 自己引用説の検証]] — 上の行を見て書いた形跡はあるが小さい（第 7 回）

## 方法論

- [[頁順の問題]] — 現在の綴じ順は元の並びと違う可能性が高い。どの分析が並びに依存するか
- [[植物＝解剖図仮説の分類案]] — 植物の根は器官、葉はダミーという仮説の分類項目と検定（照合の前に記録）
- [[地上部と根の不一致の調査案]] — 地上部と根が別々の手本から描かれたか（合成図）を調べる基準と検定（照合前に記録）

## 概念（未作成のノートを含む）

- [[EVA]] — Extensible Voynich Alphabet。未知の文字をローマ字に置き換える転写の表記法
- [[Currier 言語]] — Prescott Currier が区別した言語 A と B。語彙・語尾が大きく異なる
- [[ガロウズ字形]] — `k t p f` などの背の高い字形。段落頭に集中する
- [[Zipf の法則]] — 語の順位と頻度の関係。自然言語では指数がほぼ 1

## 道具

- このリポジトリの `voynich/`: 分析スクリプト一式（使い方は `voynich/README.md`）
  - `word_freq.py` 単語頻度 / `affix.py` 語頭・語尾 / `line_position.py` 行頭・行末 / `vocab_shift.py` 語彙の移り変わり
  - `line_forms.py` 行頭形・行末形の検証 / `compare_transcriptions.py` 転写の比較 / `reorder.py` 元の並びの推定
  - `spread.py` `initials.py` `page_images.py` 画像の取得・組み立て / `image_text.py` 絵と文章の対応 / `labels.py` ラベルの分析 / `pharma_labels.py` 薬学ラベル対応表（[[薬学ラベル対応表]]） / `self_citation.py` 自己引用説の検証

## 外部資料

- Layfield & Davis「Singulion Structure and the Voynich Manuscript」*Digital Medievalist* 19 (2026), doi:10.4000/16k0a — 二つ折り 1 枚ずつ読む作りだったという説【B】
- voynich.nu（René Zandbergen）: 来歴・研究史・転写データ https://www.voynich.nu/
- Voynich Ninja: 研究者のフォーラム https://www.voynich.ninja/
- Yale University Press 版 複製本 *The Voynich Manuscript*（2016, Raymond Clemens 編）【未見】

> [!question] 研究の大きな問い
> - 文章は自然言語（を暗号化したもの）か、規則的に生成された無意味な文字列か
> - 言語 A と B の違いは何に由来するか
> - 行・段落・二つ折りの規則は、書写の手順について何を語るか
> - 元の頁の並びを、絵のつながりと語彙の類似度から復元できるか
