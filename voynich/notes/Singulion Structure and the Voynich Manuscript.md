---
tags:
  - 史料
  - 未解読文書
  - ヴォイニッチ手稿
aliases:
  - Layfield & Davis 2026
  - singulion 論文
  - シンギュリオン論文
created: 2026-11-10
source: https://doi.org/10.4000/16k0a
---

# Singulion Structure and the Voynich Manuscript

> [!summary] 史料概要
> Colin Layfield（マルタ大学）と Lisa Fagin Davis（米国中世アカデミー）による査読論文（2026 年）。
> 潜在意味解析（LSA）と写本学の観察から、[[ヴォイニッチ手稿（Beinecke MS 408）]] はもともと二つ折り 1 枚ずつ（singulion）を順に読む作りで、15 世紀の最初の製本の時点で入れ子の束として綴じ間違えられたと論じる。
> 手稿の後代の研究文献なので B 級。

## 書誌情報

- Colin Layfield, Lisa Fagin Davis「Singulion Structure and the Voynich Manuscript」*Digital Medievalist* 19 (2026)、2026-07-10 オンライン公開、doi:10.4000/16k0a、https://journals.openedition.org/digitalmedievalist/2331 （2026-11-10 閲覧）。本文は CC BY 4.0（図などは個別の条件）。【B】
- 前の論文（同じ著者）: Layfield, C. and Davis, L. F.「The Application of Latent Semantic Analysis to the Voynich Manuscript」*Digital Humanities Quarterly* 20(1) (2026), 1–28。【未見】

> [!warning] 閲覧の範囲
> 掲載頁の本文を、ツールで構成・表・該当箇所の原文を抜き出して確認した。全文の精読は未了。表の数値はツールの抜き出しによるので、引用する前に原文で確認すること。

## 構成

Abstract / Introduction / Research Questions / Latent Semantic Analysis / Manuscript Structure / Method / Results & Analysis（Quire Experiments, Bifolia Experiments, Bifolia Re-ordering Experiments）/ Discussion / Conclusions / Appendix（LSA の次元 k = 75 の根拠など）

## 本研究に関わる記載内容

**方法**
- 転写: ZL 版 2a（2022-03-17, IVTFF 1.7）。不確かな読みの語は除外。約 40 語ごとの「文書」に分け、20 語未満は除外。TF-IDF、LSA の次元 k = 75。
- 対照: 正しく綴じられた中世写本 2 冊 ―『アバディーン動物寓意譚』（Aberdeen University Library MS 24, 13 世紀）、『人間救済の鑑』（Harvard, Houghton Library MS Lat 121, 14 世紀）。
- 頁の関係: confoliate（同じ葉の表と裏）、facing（見開き）、conjoint（二つ折りの中央見開き, 例 78v|81r）。

**結果**

| 写本 | confoliate | facing | conjoint |
|---|---|---|---|
| アバディーン動物寓意譚 | 0.428 | 0.398 | 0.207 |
| 人間救済の鑑 | 0.398 | 0.398 | 0.277 |
| ヴォイニッチ手稿 | 0.383 | 0.298 | 0.433 |

（Table 10。ヴォイニッチの t 検定: confoliate/facing 0.005, confoliate/conjoint 0.168, facing/conjoint 0.000 ― Table 11）

| セクション | 現在の見開きの平均 | 最適な並びの見開きの平均 | 最適な並び（singulion） |
|---|---|---|---|
| 生物・浴場 | 0.461 | 0.517 | 77\|82, 78\|81, 75\|84, 76\|83, 79\|80 |
| 星 | 0.438 | 0.526 | 105\|114, 104\|115, 106\|113, 107\|112, 108\|111, 103\|116 |

（Table 14）

**写本学の証拠**
- 綴じ目をまたぐ絵: 78v|81r（2 本の流れ, Figure 1）、10v|15r（飛び散った染み）、33v|40r（青い花びら）、58v|65r（緑の葉のかけら）、76v|83r（ニンフの右腕）。
- 大きな頭文字: f105r は星のセクションで唯一大きな頭文字で始まる頁で、最適な並びの最初に来る。f76r も絵が無く大きな頭文字で始まる（Figure 4）。
- 製本: Yale の保存担当 Paula Zyats の所見として「縫い直しの跡は 1 回分しかない」（Zyats 2016, 25–26）。最初の縫いは後期ゴシック（1400〜1500 年ごろ）。木の表紙は 1 組だけ（15 世紀か）で、現在の柔らかい羊皮紙の表紙は 19 世紀か。著者は、15 世紀の最初の製本そのものが綴じ間違いだったと論じる。
- 顔料の移り（offset）から、現在の綴じ方は何世紀も前からのもの。

**結論（原文の短い引用）**
- "the entire manuscript is bound out of order"
- "it was originally intended to be read as a series of sequential singulions rather than nested quires"
- "A book whose pages are out of order is almost certainly more difficult to read."

## 評価・注意点

- 著者自身が、偶然の可能性、意味的な類似とは断定できないこと、文章が読めるまで並びは確かめられないことを明記している。
- LSA の空間は検証と同じデータで作られている（汎化の検証ではない）。ヴォイニッチ全体で約 35,000 語と小さい。
- 本研究では、別の方法（単語頻度のコサイン類似度）と別の転写（ZL 3b, IT）で、主な結果（conjoint > confoliate > facing、星のセクションの最適な並び）を再現した。
- 綴じ目をまたぐ絵の 5 組のうち、画像で支持できたのは 3 組。10v|15r の「染み」は論文に図も詳しい説明も無く、特定できなかった。

## この史料を根拠とする主張

- [[2026-11-10 ヴォイニッチ手稿 singulion 仮説の検証]] — 再現と画像の確認
- [[頁順の問題]] — 綴じ目をまたぐ絵、最初の製本が綴じ間違いだったという見方

## 関連ノート

- [[MOC ヴォイニッチ手稿研究]]
- [[ヴォイニッチ手稿（Beinecke MS 408）]]
- [[ZL転写ファイル]] — 論文は版 2a、本研究は版 3b を使用
