---
tags:
  - 史料
  - 未解読文書
  - ヴォイニッチ手稿
aliases:
  - ZL transliteration
  - ZL3b-n.txt
  - Zandbergen-Landini 転写
created: 2026-11-10
source: https://www.voynich.nu/data/ZL3b-n.txt
---

# ZL転写ファイル

> [!summary] 史料概要
> [[ヴォイニッチ手稿（Beinecke MS 408）]] の全文を、EVA（ローマ字による置き換え表記）で書き起こした機械可読データ。
> René Zandbergen が管理し、版 3b（2025-05-13）。原本ではなく現代の研究者による転写なので B 級（編纂物相当）。

## 書誌情報

- René Zandbergen「ZL transliteration file, updated from EVMT project, Version 3b of 13/05/2025」https://www.voynich.nu/data/ZL3b-n.txt （2026-11-09 取得、411,671 バイト）。【B】
- 転写の解説: René Zandbergen「Transliteration of the text」https://www.voynich.nu/transcr.html （2026-11-09 閲覧）。【B】
- 旧版 ZL3a（`ZL3a-n.txt`）は 2026-11-09 時点で取得できなかった（HTTP 404）。

## 本研究に関わる記載内容

- 書式は IVTFF 2.0（`#=IVTFF Eva- 2.0 M 5`）。1 行 = 1 ロカス（`<f1r.1,@P0>` のように頁・行番号・位置・種類を付す）。
- 各頁の見出しに頁属性が付く。本研究で使ったもの:

| 記号 | 意味 | 値の例 |
|---|---|---|
| `$Q` | クワイア（綴じの単位） | A〜T |
| `$B` | クワイア内の二つ折り（bifolio）番号 | 1〜6 |
| `$I` | 挿絵の種類 | H 植物, B 生物・浴場, S 星・レシピ, P 薬学 など |
| `$L` | [[Currier 言語]] | A, B |
| `$C` | Currier の筆写者区分（推定） | 1〜5, X, Y |
| `$H` | 筆写者（分類の出典は未確認） | 1〜5 |

- 不確かさの記法: `,` 不確かな単語区切り、`[a:o]` 異読、`?` 判読不能文字、`{ckh}` 合字、`@185;` 稀少文字。

## 評価・注意点

- 単語の区切り・文字の同定・異読の選択は転写者の判断を含む。分析結果は「ZL 版の読み」に依存する。
- ZL ファイル自体には `$H` `$C` の定義が書かれていない。各頁のコメントには「Currier's language A, hand 1」のような記載がある。

> [!warning] 未検証
> `$H`（値 1〜5）は Lisa Fagin Davis の 5 筆写者分類、`$C`（値 1〜5, X, Y）は Currier の筆写者区分と推定しているが、
> voynich.nu 上で定義を確認できていない。旧版の LSI 転写ファイルでは `$H` が「Currier's hand」（値 1〜5, X, Y）と説明されているとの検索結果があり【未見、ウェブ検索結果の要約より重引】、
> ZL3b では値の種類からみて `$C` がそれに当たると考えられる。Davis の論文と IVTFF の仕様書で確認することを次のアクションとする。

- 段落の始まり（`<%>`）・終わり（`<$>`）も転写者の判断による。

> [!question] 未解決
> 他の転写（Takahashi 版など）で同じ分析をしても結果が変わらないか。転写の違いに対する結果の頑健性は未確認。

## この史料を根拠とする主張

- [[2026-11-10 ヴォイニッチ手稿 定量分析]] — 単語頻度・語頭語尾・行頭行末・語彙の移り変わりの全分析

## 関連ノート

- [[ヴォイニッチ手稿（Beinecke MS 408）]] — 転写元の写本
- [[EVA]] — 転写に使われている表記法
- [[MOC ヴォイニッチ手稿研究]]
