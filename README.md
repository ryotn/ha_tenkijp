# tenki.jp Weather for Home Assistant

このカスタムコンポーネントは、日本の天気情報サイト「tenki.jp」から天気データを取得し、Home Assistantで利用できるようにします。

**HACS（Home Assistant Community Store）対応！**
HACS経由で簡単にインストール・アップデートが可能です。

## 特徴

- tenki.jpの天気情報をHome Assistantのweatherエンティティとして表示
- config flow対応（UIから簡単に設定可能）
- クラウドポーリング方式

## インストール方法

### HACS経由（推奨）

1. HACSの「カスタムリポジトリ」としてこのリポジトリ（`https://github.com/ryotn/ha_tenkijp`）を追加
2. HACSから「tenki.jp Weather」を検索してインストール
3. Home Assistantを再起動

### 手動インストール

1. このリポジトリをダウンロード
2. `custom_components/tenkijp` フォルダを Home Assistant の `config/custom_components/` 配下に配置
3. Home Assistantを再起動

## 設定方法

1. Home Assistantの「設定」→「デバイスとサービス」→「統合を追加」から「tenki.jp Weather」を検索
2. 地域など必要な情報を入力してセットアップ

## 必要な依存パッケージ

- aiohttp
- beautifulsoup4

## サポート

バグ報告や要望は [GitHub Issue](https://github.com/ryotn/ha_tenkijp/issues) までお願いします。

## ライセンス

MIT License
