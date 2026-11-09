# ヴォイニッチ手稿 単語頻度分析

René Zandbergen の **ZL 転写ファイル**（IVTFF 形式・EVA 表記, 版 3b / 2025-05-13）を読み込み、
単語の頻度・基本統計・Zipf 指数を出力するスクリプトです。標準ライブラリのみで動作します（Python 3.9+）。

- 転写ファイル: https://www.voynich.nu/data/ZL3b-n.txt （初回実行時に `voynich/data/` へ自動ダウンロード。リポジトリには含めません）
- 原本画像: Yale Beinecke MS 408 — https://collections.library.yale.edu/catalog/2002046

## 使い方

```sh
python3 voynich/word_freq.py                         # 全体の上位 30 語と基本統計
python3 voynich/word_freq.py --top 100 --csv voynich/out/freq.csv   # 全語の頻度表を CSV へ
python3 voynich/word_freq.py --language A            # Currier 言語 A のページのみ
python3 voynich/word_freq.py --illustration H --locus P   # 植物セクションの本文（ラベル除外）
python3 voynich/word_freq.py --by L                  # 言語 A / B を比較（特徴語つき）
python3 voynich/word_freq.py --by I --top 10         # 挿絵種別ごとに比較
python3 voynich/word_freq.py --help                  # 全オプション
```

### 絞り込み（カンマ区切りで複数可）

| オプション | 意味 | 値 |
|---|---|---|
| `--language` | Currier 言語 | `A`, `B` |
| `--hand` | 筆写者（Lisa Fagin Davis の分類） | `1`〜`5` |
| `--illustration` | 挿絵種別 | `H` 植物, `A` 天文, `C` 宇宙論, `Z` 黄道, `B` 生物, `P` 薬学, `S` 星, `T` 文字のみ |
| `--quire` | クワイア | `A`〜`T` |
| `--page` | ページ | `f1r,f1v` など |
| `--locus` | 行の種類 | `P` 段落, `L` ラベル, `C` 円形, `R` 放射状 |

### 比較（`--by`）

ページ属性（`L` 言語, `H` 筆写者, `I` 挿絵, `Q` クワイア など）でグループに分け、
グループごとに統計・頻度表と **特徴語**（そのグループで他より有意に多い語。対数尤度比 G² で順位付け）を出力します。
属性が未指定のページは「未指定」グループになります。

## 単語化のルール（既定値）

| ZL の記法 | 意味 | 既定の扱い | 変更オプション |
|---|---|---|---|
| `.` | 単語区切り | 区切る | — |
| `,` | 不確かな単語区切り | 区切る | `--comma-join` で連結 |
| `[a:o]` | 異読 | 最初の読みを採用 | `--alt 1` で 2 番目 |
| `{ckh}` | 合字 | 括弧を外して中身を採用 | — |
| `?` | 判読不能文字 | その語を除外 | `--keep-uncertain` |
| `@185;` | 稀少文字 | そのまま 1 語に含める | `--drop-rare` で除外 |
| `<->` `<~>` | 挿絵による中断 | 単語区切り | — |
| `<!...>` `<%>` `<$>` | コメント・段落の始まり/終わり | 削除 | — |

注意:
- 筆写者・言語などの属性は**ページ単位**で判定します。行中の筆写者交代マーク（`<@H=2>` など、f115r の 2 箇所のみ）は反映しません。
- 平均語長は EVA の文字数です。`ch` や `sh` のように 2 文字で 1 字形を表すものも 2 文字と数えます。

## 実行例（全体）

```
総語数 (token)   : 38346
異なり語数 (type): 8093
タイプ/トークン比: 0.2111
Zipf 指数        : 1.022
  1  daiin  845  2.20%
  2  ol     545  1.42%
  3  chedy  505  1.32%
```

言語 A では `daiin`, `chor`, `chol`, `cthy` が、言語 B では `chedy`, `shedy`, `qokeedy`, `qokedy` が特徴語として出ます（Currier が 1976 年に指摘した A/B の差と同じ傾向です）。

## テスト

```sh
python3 -m unittest discover voynich
```
