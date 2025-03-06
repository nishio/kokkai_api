#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
国会会議録APIから発言データを取得しCSV出力するスクリプト

国立国会図書館が提供する国会会議録検索システムのAPIを使用して、
指定したキーワードと期間に基づいて国会での発言データを取得し、
CSVファイルに出力します。
"""

import argparse
import csv
import json
import sys
import time
import requests


API_URL = "https://kokkai.ndl.go.jp/api/speech"


def fetch_records(keyword, start_date, end_date, max_retries=3, retry_delay=2):
    """
    単一キーワードでAPIから発言データを取得し、リストで返す。
    ページングに対応。取得結果は重複は含まないものとする。
    
    Args:
        keyword (str): 検索キーワード
        start_date (str): 検索開始日 (YYYY-MM-DD)
        end_date (str): 検索終了日 (YYYY-MM-DD)
        max_retries (int): API接続失敗時の最大リトライ回数
        retry_delay (int): リトライ間の待機時間（秒）
        
    Returns:
        list: 発言レコードのリスト
    """
    records = []
    start_record = 1
    max_records = 100  # 1リクエストあたり最大件数
    total_fetched = 0
    total_records = None

    while True:
        params = {
            "any": keyword,
            "from": start_date,
            "until": end_date,
            "startRecord": start_record,
            "maximumRecords": max_records,
            "recordPacking": "json"  # 常にJSON形式で取得
        }
        
        # リトライロジック
        for retry in range(max_retries):
            try:
                r = requests.get(API_URL, params=params, timeout=30)
                if r.status_code == 200:
                    break
                print(f"APIリクエスト失敗 (ステータスコード: {r.status_code})、リトライ中... ({retry+1}/{max_retries})")
                time.sleep(retry_delay)
            except requests.exceptions.RequestException as e:
                if retry < max_retries - 1:
                    print(f"接続エラー: {e}, リトライ中... ({retry+1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    sys.exit(f"APIへの接続に失敗しました: {e}")
        
        if r.status_code != 200:
            sys.exit(f"APIエラー: ステータスコード {r.status_code}")
        
        try:
            # JSONをパース
            try:
                data = json.loads(r.text)
                
                # 総レコード数を取得
                total_records = int(data.get("numberOfRecords", 0))
                
                # レコードがない場合は終了
                if total_records == 0:
                    print(f"キーワード '{keyword}' に一致する結果はありませんでした。")
                    break
                
                # レコードを取得
                speech_records = data.get("speechRecord", [])
                if not speech_records:
                    break
                
                # リストでない場合（単一レコードの場合）はリストに変換
                if not isinstance(speech_records, list):
                    speech_records = [speech_records]
                
                batch_size = len(speech_records)
                total_fetched += batch_size
                
                # 進捗表示
                if total_records > max_records:
                    print(f"  {total_fetched}/{total_records} 件取得中... ({(total_fetched/total_records*100):.1f}%)")
                
                for speech_rec in speech_records:
                    # 会議録情報を別途取得して辞書に追加
                    meeting_record = {}
                    for tag in ["issueID", "session", "nameOfHouse", "nameOfMeeting", "issue", "date"]:
                        meeting_record[tag] = speech_rec.get(tag, "")
                    
                    speech_rec["meetingRecord"] = meeting_record
                    records.append(speech_rec)
                
                # ページング処理
                next_position = data.get("nextRecordPosition")
                if next_position is None:
                    break
                
                next_position_int = int(next_position)
                if next_position_int > total_records or next_position_int <= start_record:
                    break
                
                # APIに負荷をかけないよう少し待機
                if total_records > max_records:
                    time.sleep(0.5)
                
                start_record = next_position_int
                
            except json.JSONDecodeError as e:
                sys.exit(f"JSONパースに失敗しました: {e}")
                
        except Exception as e:
            sys.exit(f"データ処理中にエラーが発生しました: {e}")
    
    return records


def main():
    """
    メイン関数：コマンドライン引数を解析し、APIからデータを取得してCSVに出力する
    """
    parser = argparse.ArgumentParser(description="国会会議録APIから発言データを取得しCSV出力するスクリプト")
    parser.add_argument("--keywords", nargs="+", required=True, help="検索キーワード（複数指定でOR検索）")
    parser.add_argument("--start-date", default="2023-01-01", help="検索開始日 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2023-12-31", help="検索終了日 (YYYY-MM-DD)")
    parser.add_argument("--output", default="output.csv", help="出力CSVファイル名")
    parser.add_argument("--max-retries", type=int, default=3, help="API接続失敗時の最大リトライ回数")
    
    args = parser.parse_args()
    
    # 日付形式の簡易チェック
    for date_str, date_name in [(args.start_date, "開始日"), (args.end_date, "終了日")]:
        if not (len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-'):
            sys.exit(f"日付形式エラー: {date_name}は'YYYY-MM-DD'形式で指定してください")
    
    all_records = []
    seen_speech_ids = set()
    
    # 複数キーワードについて個別に検索し、結果を統合（重複はspeechIDで除外）
    for kw in args.keywords:
        print(f"キーワード '{kw}' で検索中...")
        try:
            recs = fetch_records(kw, args.start_date, args.end_date, args.max_retries)
            
            # 重複除外しながらレコードを追加
            for rec in recs:
                speech_id = rec.get("speechID")
                if speech_id and speech_id in seen_speech_ids:
                    continue
                if speech_id:
                    seen_speech_ids.add(speech_id)
                all_records.append(rec)
                
        except KeyboardInterrupt:
            print("\n処理を中断しました。")
            sys.exit(1)
    
    if not all_records:
        print("取得されたレコードがありません。")
        sys.exit(0)
    
    # CSV出力用フィールド（comment-idは連番で採番）
    fieldnames = [
        "comment-id",       # 発言ID（整数：連番）
        "meeting-id",       # 会議録ID
        "session",          # 国会回次
        "name_of_house",    # 院名
        "name_of_meeting",  # 会議名
        "issue",            # 号数
        "date",             # 開催日
        "speech_order",     # 発言順序
        "speaker",          # 発言者名
        "speaker_group",    # 所属会派
        "speaker_position", # 発言者肩書き
        "speaker_role",     # 発言者役割
        "comment-body",     # 発言テキスト
        "speech_url"        # 発言ページURL
    ]
    
    try:
        with open(args.output, mode="w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=",")
            writer.writeheader()
            comment_id = 1
            
            print(f"CSVファイルに {len(all_records)} 件のレコードを書き出し中...")
            
            for rec in all_records:
                # meetingRecordはspeechRecordの子要素としてあるはず
                meeting = rec.get("meetingRecord", {})
                row = {
                    "comment-id": comment_id,
                    "meeting-id": meeting.get("issueID", ""),
                    "session": meeting.get("session", ""),
                    "name_of_house": meeting.get("nameOfHouse", ""),
                    "name_of_meeting": meeting.get("nameOfMeeting", ""),
                    "issue": meeting.get("issue", ""),
                    "date": meeting.get("date", ""),
                    "speech_order": rec.get("speechOrder", ""),
                    "speaker": rec.get("speaker", ""),
                    "speaker_group": rec.get("speakerGroup", ""),
                    "speaker_position": rec.get("speakerPosition", ""),
                    "speaker_role": rec.get("speakerRole", ""),
                    "comment-body": rec.get("speech", ""),
                    "speech_url": rec.get("speechURL", "")
                }
                writer.writerow(row)
                comment_id += 1
                
        print(f"CSV出力完了: {args.output} に {comment_id - 1} 件のレコードを書き出しました。")
    except IOError as e:
        sys.exit(f"ファイル出力エラー: {e}")
    except Exception as e:
        sys.exit(f"CSV出力エラー: {e}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n処理を中断しました。")
        sys.exit(1)
