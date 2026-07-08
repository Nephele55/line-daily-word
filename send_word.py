import csv
import json
import os
import sys

import requests

PUSH_URL = "https://api.line.me/v2/bot/message/push"
WORDS_FILE = "words.csv"
PROGRESS_FILE = "progress.json"
WORDS_PER_DAY = 1  # 一天想送幾個字，改這個數字即可


def load_words():
    """讀單字庫。用 DictReader 讓每一列變成 dict，
    之後都用欄位名稱取值，未來在 CSV 加新欄位（例如 level）也不會壞。"""
    with open(WORDS_FILE, newline="", encoding="utf-8") as f:
        words = list(csv.DictReader(f))
    if not words:
        sys.exit("words.csv 是空的，先加幾個單字進去")
    return words


def load_progress():
    """progress.json 記錄「下一個要送第幾個字」。
    檔案不存在時從 0 開始，讓第一次執行不會炸掉。"""
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"index": 0}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def build_message(picked):
    lines = ["📖 每日單字", "━━━━━━━━━━"]
    for w in picked:
        lines.append(f"{w['word']} ({w['pos']}) {w['meaning']}")
        lines.append(f"例句：{w['example']}")
        lines.append(f"翻譯：{w['example_zh']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def push_to_line(text):
    """呼叫 Messaging API 的 push endpoint。
    push 是「指定 userId 發送」，和 broadcast（發給全部好友）不同：
    額度可控，未來也能對不同學生推不同難度的字。"""
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    user_id = os.environ["LINE_USER_ID"]
    resp = requests.post(
        PUSH_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"to": user_id, "messages": [{"type": "text", "text": text}]},
        timeout=10,
    )
    if resp.status_code != 200:
        # 把 LINE 回傳的錯誤內容印出來再讓 workflow 失敗，
        # 這樣在 Actions log 一眼就能看出是 401（token 錯）還是 400（userId 錯）
        sys.exit(f"推播失敗 {resp.status_code}: {resp.text}")


def main():
    words = load_words()
    progress = load_progress()

    start = progress["index"] % len(words)  # 取餘數：字庫送完一輪自動從頭再來
    picked = [words[(start + i) % len(words)] for i in range(WORDS_PER_DAY)]

    push_to_line(build_message(picked))

    progress["index"] = (start + WORDS_PER_DAY) % len(words)
    save_progress(progress)
    print(f"已送出 {[w['word'] for w in picked]}，下次從第 {progress['index']} 個開始")


if __name__ == "__main__":
    main()
