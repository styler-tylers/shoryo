---
tags:
  - 手順
  - Obsidian
  - GitHub
created: 2026-11-23
---

# Obsidian と GitHub の連携の手順

Claude Code のセッション（携帯・Mac）で進めた研究のノートを、Mac の Obsidian（保管場所「W」）で読むための手順。2026-11-23 に、ヴォイニッチ研究で設定した。

## 仕組み

- Claude が、研究ごとのブランチ（例: `obsidian-voynich`）に、ノートを push する（リポジトリ `styler-tylers/-`, 非公開）
- Mac では、そのブランチを保管場所「W」の中のフォルダとして取り込んである
- Claude から「更新しました」と言われたら、ターミナルで 1 語を打つ（ヴォイニッチ研究なら `voynich`）
- 携帯の Obsidian でも、iCloud で同期された結果を読める（取り込み自体は Mac で）

## 新しい研究を連携するとき

Claude に「この研究も Obsidian に連携して」と言う。Claude が、ブランチの名前と、Mac で 1 回だけ打つ 2 つのコマンド（取り込みと、1 語のコマンドの登録）を渡す。GitHub へのログイン（`gh auth login`）は、この Mac では済んでいる。

## 約束

- 取り込んだフォルダの中のノートは書き換えない。自分のメモはフォルダの外に書き、`[[ ]]` でリンクする
- 1 語のコマンドで止まったら: そのフォルダで `git fetch && git reset --hard origin/<ブランチの名前>`（フォルダの中で書き換えた分は消える）
- iCloud の共有リンクは使わない

## ほかの Code のセッションでも使うには

スキル「obsidian-github-sync」を claude.ai に登録する（設定 → 機能 → スキル で、zip を上げる）。登録すると、どのセッションでも Claude がこの手順で動く。
