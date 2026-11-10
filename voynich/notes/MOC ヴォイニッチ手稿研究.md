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

## 調査ログ

- [[2026-11-10 ヴォイニッチ手稿 定量分析]] — 単語頻度・語頭語尾・行頭行末・語彙の移り変わり（第 1 回）

## 概念（未作成のノートを含む）

- [[EVA]] — Extensible Voynich Alphabet。未知の文字をローマ字に置き換える転写の表記法
- [[Currier 言語]] — Prescott Currier が区別した言語 A と B。語彙・語尾が大きく異なる
- [[ガロウズ字形]] — `k t p f` などの背の高い字形。段落頭に集中する
- [[Zipf の法則]] — 語の順位と頻度の関係。自然言語では指数がほぼ 1

## 道具

- このリポジトリの `voynich/`: 分析スクリプト一式（使い方は `voynich/README.md`）
  - `word_freq.py` 単語頻度 / `affix.py` 語頭・語尾 / `line_position.py` 行頭・行末 / `vocab_shift.py` 語彙の移り変わり

## 外部資料

- voynich.nu（René Zandbergen）: 来歴・研究史・転写データ https://www.voynich.nu/
- Voynich Ninja: 研究者のフォーラム https://www.voynich.ninja/
- Yale University Press 版 複製本 *The Voynich Manuscript*（2016, Raymond Clemens 編）【未見】

> [!question] 研究の大きな問い
> - 文章は自然言語（を暗号化したもの）か、規則的に生成された無意味な文字列か
> - 言語 A と B の違いは何に由来するか
> - 行・段落・二つ折りの規則は、書写の手順について何を語るか
