# Zenn 記事統計データ分析指示書

このドキュメントは、本リポジトリで収集・蓄積された Zenn の記事統計データベースを分析するコーディングエージェント向けの手引きです。

## データセット仕様 (`zenn_stats.db.gz`)

データは `zenn_stats.db.gz` を解凍した SQLite データベース **`zenn_stats.db`** の **`articles`** テーブルに格納されています。
[northward1/zenn-stats-crawler: Zennの記事の統計データとそのクローラー](https://github.com/northward1/zenn-stats-crawler)から最新のデータをダウンロードしています。

### テーブルスキーマ (`articles`)

| カラム名                    | データ型    | 説明                                                                              |
| :-------------------------- | :---------- | :-------------------------------------------------------------------------------- |
| `id`                        | INTEGER     | 自動採番 ID                                                                       |
| `url_hash`                  | TEXT        | 記事 URL のソルト付き SHA-256 ハッシュ（記事ごとの一意識別子）                    |
| `article_type`              | TEXT        | 記事分類種別（`"tech"` または `"idea"`）                                          |
| `title_hash`                | TEXT        | 記事タイトルのハッシュ値                                                          |
| `user_name_hash`            | TEXT        | 記事著者のユーザー ID ハッシュ値                                                  |
| `published_at`              | TEXT        | 初回公開日時（ISO 8601 形式、例: `2024-01-01T12:00:00+09:00` または UTC）         |
| `comments_count`            | INTEGER     | コメント数                                                                        |
| `liked_count`               | INTEGER     | いいね合計数 (`authenticated_liked_count` + `anonymous_liked_count`)              |
| `authenticated_liked_count` | INTEGER     | ログインユーザーによるいいね数                                                    |
| `anonymous_liked_count`     | INTEGER     | 非ログインユーザーによるいいね数                                                  |
| `bookmarked_count`          | INTEGER     | ブックマーク数                                                                    |
| `topics`                    | TEXT        | 付与トピックの JSON 配列文字列（例: `'["python", "sqlite"]'`）                    |
| `publication_plan`          | TEXT / NULL | Publication 契約プラン（`"free"`, `"pro"`, `"connect"`）。個人投稿の場合は `NULL` |
| `publication_name_hash`     | TEXT / NULL | 所属 Publication 名のハッシュ値。個人投稿の場合は `NULL`                          |
| `crawled_at`                | TEXT        | クロール実行日時（ISO 8601 UTC 形式）                                             |
| `status`                    | TEXT        | クロール成否（`"success"` または `"failed"`）                                     |
| `http_status`               | INTEGER     | レスポンスステータスコード（200, 404, 500 等）                                    |
| `error_message`             | TEXT        | エラー時の詳細メッセージ                                                          |

### データ抽出・前処理時の留意点

- **クロール成功レコードの選別**:
  - `status = 'success'` のレコードのみを分析対象としてください。
- **スナップショット性（時系列蓄積）**:
  - 定期クローラーにより同一記事（`url_hash`）が複数回クロールされる設計となっています。横断的な現状スナップショットの集計を行う際は、各記事の最新レコード（`MAX(crawled_at)`）を抽出してください。
  - （※複数回クロールされた記事が存在する場合は、推移や変動の分析を行うことも可能です）
- **トピックの展開**:
  - `topics` カラムは JSON 配列文字列（例: `'["react", "next.js"]'`）です。トピックごとの集計を行う際は JSON パースを行ってください。
  - トピックが空の記事も存在しますが、それは、トピックを設定していない記事として扱えばよいです。
- **日時のタイムゾーン**:
  - `published_at` は ISO 8601 形式です。時間帯や曜日別の分析を行う際は日本時間（JST: UTC+9）への変換を推奨します。

## Zenn 公式仕様とドメイン知識

分析や考察の解釈を深めるために、以下の Zenn 特有の背景知識を活用してください。

### 1. Tech（技術記事）と Idea（アイデア記事）の区分

- [投稿カテゴリー「Tech」「Idea」の選び方 | Zenn](https://zenn.dev/tech-or-idea)
- 著者が投稿時に選択する区分です。
- **Tech**: ソフトウェアやハードウェアについて、実際に動かして検証した内容や具体的な実装コード解説、トラブルシューティングなど。
- **Idea**: キャリア論、マネジメント、イベント参加レポ、ツール・サービスのまとめなど、技術に直接関係しないものや抽象的なまとめ。
- ※内容に応じて運営側でカテゴリが調整されることがあります。

### 2. いいね機能（非ログイン Like）

- **2026年8月17日**より、非ログインユーザーでも記事に Like を送れる機能が導入されました。
  - [ログインせずに投稿へLikeできる機能を試験的にリリースしました | What's New in Zenn](https://info.zenn.dev/2026-08-17-non-login-like)
- 画面上は合算（`liked_count`）で表示されますが、データ上は「ログインユーザー Like (`authenticated_liked_count`)」と「非ログイン Like (`anonymous_liked_count`)」に分かれています。
- **公式方針として、Trending（トレンド）やランキングのスコア算定には非ログイン Like は使用されず、ログイン Like が重視されています**。
- 分析時には、合計 Like だけでなくログイン Like の分布や「0 Like（初動）」の割合などに着目するのも有効です。

### 3. ブックマーク機能

- 後で見返したい記事を保存する機能として、**2025年1月**にリリースされました。
  - [記事をブックマークして管理できるようになりました | What's New in Zenn](https://info.zenn.dev/2025-01-16-release-bookmark)
- 「いいね（読んだ直後のリアクション）」と「ブックマーク（ストック・後で参照）」で読者の行動特性が異なる可能性があります。

### 4. Publication 機能

- 企業やチームが専用メディアを開設・運営できる機能です（2022年後半より提供）。
  - [Publication機能のオープンβ開始に関するお知らせ | What's New in Zenn](https://info.zenn.dev/publication-open-beta-announce)
  - [Publication機能が正式リリース＆本日よりProプランをご利用いただけます！ | What's New in Zenn](https://info.zenn.dev/2024-01-22-publication-pro-release)
- プランには `free`, `pro`, `connect` が存在します。
- 個人アカウントによる発信（`publication_plan IS NULL`）と企業・チームメディアによる発信で、発信内容やエンゲージメントに違いが見られる場合があります。
