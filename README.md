## 国会議事録API取得スクリプト

`scripts/kokkai_api.py` は国立国会図書館が提供する国会会議録検索システムのAPIを使用して、指定したキーワードと期間に基づいて国会での発言データを取得し、CSVファイルに出力するスクリプトです。

### 必要条件

- Python 3.6以上
- requests ライブラリ

### インストール

```bash
cd scripts
pip install -r requirements.txt
```

### 使用方法

```bash
python kokkai_api.py --keywords "キーワード1" "キーワード2" --start-date "2023-01-01" --end-date "2023-12-31" --output "output.csv"
```

#### 引数

- `--keywords`: 検索キーワード（複数指定可能、OR検索）
- `--start-date`: 検索開始日（YYYY-MM-DD形式、デフォルト: 2023-01-01）
- `--end-date`: 検索終了日（YYYY-MM-DD形式、デフォルト: 2023-12-31）
- `--output`: 出力CSVファイル名（デフォルト: output.csv）
- `--max-retries`: API接続失敗時の最大リトライ回数（デフォルト: 3）

#### 出力CSVの列

- `comment-id`: 発言ID（整数：連番）
- `meeting-id`: 会議録ID
- `session`: 国会回次
- `name_of_house`: 院名
- `name_of_meeting`: 会議名
- `issue`: 号数
- `date`: 開催日
- `speech_order`: 発言順序
- `speaker`: 発言者名
- `speaker_group`: 所属会派
- `speaker_position`: 発言者肩書き
- `speaker_role`: 発言者役割
- `comment-body`: 発言テキスト
- `speech_url`: 発言ページURL

### 注意事項

- APIへの過度な負荷を避けるため、大量のデータを取得する場合は適切な期間に区切って実行してください。
- 検索結果が多い場合、処理に時間がかかることがあります。
