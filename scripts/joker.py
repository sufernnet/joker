# -*- coding: utf-8 -*-
# 🔥 Joker IPTV CHC 双保险版（主备源 + 重试 + 不崩）

import os
import re
import time
import requests
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# 主备源（主：45678888，备：ibert）
CHC_PRIMARY = "https://live.45678888.xyz/sub?kbQyhXwA=m3u"
CHC_BACKUP  = "https://m3u.ibert.me/ycl_iptv.m3u"

OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

TARGET_CHC_KEYWORDS = {
    "动作电影": "动作电影",
    "高清电影": "高清电影",
    "家庭影院": "家庭影院",
    "影迷电影": "影迷电影",
    "淘电影": "淘电影",
    "淘剧场": "淘剧场",
    "淘娱乐": "淘娱乐",
    "萌宠tv": "萌宠TV"
}

# ============== 网络下载（带UA + 重试） ==============

def download(url, retries=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

    for i in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"[{url}] 重试 {i+1}/{retries} 失败:", e)
            time.sleep(2)

    return ""

# ============== 名称归一化 ==============

def normalize(s):
    s = (s or "").lower()
    s = re.sub(r"[\s\-_.·]", "", s)
    s = re.sub(r"(hd|4k|标清|高清|频道)", "", s)
    return s

# ============== 双解析提取 CHC ==============

def extract_chc(content):
    res = []
    name = ""

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("#EXTINF") and "," in line:
            name = line.split(",", 1)[1]

        elif line.startswith("http"):
            n = normalize(name)
            for k, std in TARGET_CHC_KEYWORDS.items():
                if normalize(k) in n:
                    res.append((std, line))
                    break

        elif "," in line:
            a, b = line.split(",", 1)
            if b.startswith("http"):
                n = normalize(a)
                for k, std in TARGET_CHC_KEYWORDS.items():
                    if normalize(k) in n:
                        res.append((std, b.strip()))
                        break

    # 去重
    seen = set()
    out = []
    for n, u in res:
        if u not in seen:
            seen.add(u)
            out.append((n, u))

    return out

# ============== EXTINF 构建 ==============

def build_extinf(name):
    logo = f"https://raw.githubusercontent.com/xiasufern/AA/main/icon/{name}.png"
    return f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="CHC",{name}'

# ============== 注入 CHC 分组 ==============

def append_chc(bb_content, chc_list):
    if not chc_list:
        return bb_content

    lines = bb_content.splitlines()
    out = lines[:]

    out.append("")
    out.append("# CHC")

    for name, url in chc_list:
        out.append(build_extinf(name))
        out.append(url)

    return "\n".join(out) + "\n"

# ============== 主流程 ==============

def main():
    print("抓取 CHC 主源...")
    content = download(CHC_PRIMARY)

    chc_list = extract_chc(content) if content else []

    # 🔥 主源失败或数量太少 → 切备源
    if len(chc_list) < 5:
        print("主源不足，切换备用源...")
        backup = download(CHC_BACKUP)
        if backup:
            chc_list = extract_chc(backup)

    print("最终 CHC 数量:", len(chc_list))

    output = '#EXTM3U\n\n'

    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            bb = f.read()

        bb = re.sub(r'^\s*#EXTM3U\s*', '', bb, flags=re.I)
        bb = append_chc(bb, chc_list)

        output += bb

    except Exception as e:
        print("BB读取失败:", e)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ CHC 双保险注入完成")


if __name__ == "__main__":
    main()
