# -*- coding: utf-8 -*-
# 🔥 Joker IPTV 定制版（CHC独立提取版）

import os
import re
import time
import asyncio
import aiohttp
import requests
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"
CHC_SOURCE = "https://live.45678888.xyz/sub?kbQyhXwA=m3u"

OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

# ================= CHC目标 =================

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

# ================= 工具 =================

def download(url):
    return requests.get(url, timeout=30).text


def normalize(s):
    s = (s or "").lower()
    s = re.sub(r"[\s\-_.·]", "", s)
    s = re.sub(r"(hd|4k|标清|高清|频道)", "", s)
    return s

# ================= CHC提取 =================

def extract_chc_channels(content):
    result = []
    name = ""

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("#EXTINF"):
            if "," in line:
                name = line.split(",", 1)[1]

        elif line.startswith("http"):
            n = normalize(name)

            for k, std in TARGET_CHC_KEYWORDS.items():
                if normalize(k) in n:
                    result.append((std, line))
                    break

        # 兼容 txt
        elif "," in line:
            a, b = line.split(",", 1)
            if b.startswith("http"):
                n = normalize(a)
                for k, std in TARGET_CHC_KEYWORDS.items():
                    if normalize(k) in n:
                        result.append((std, b.strip()))
                        break

    # 去重
    seen = set()
    final = []
    for n, u in result:
        if u not in seen:
            seen.add(u)
            final.append((n, u))

    return final

# ================= CHC写入 =================

def build_extinf(name):
    logo = f"https://raw.githubusercontent.com/xiasufern/AA/main/icon/{name}.png"
    return f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="{logo}" group-title="CHC",{name}'


def append_chc(bb_content, chc_list):
    if not chc_list:
        return bb_content

    lines = bb_content.splitlines()
    out = lines[:]

    # 插入到最后
    out.append("")
    out.append("# CHC")

    for name, url in chc_list:
        out.append(build_extinf(name))
        out.append(url)

    return "\n".join(out) + "\n"

# ================= 主程序 =================

def main():
    print("抓取 CHC 专用源...")
    content = download(CHC_SOURCE)
    chc_list = extract_chc_channels(content)

    print("CHC抓取数量:", len(chc_list))

    output = '#EXTM3U\n\n'

    # 保留原 BB
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

    print("✅ CHC 已独立注入完成")


if __name__ == "__main__":
    main()
