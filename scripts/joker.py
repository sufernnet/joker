#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import asyncio
import aiohttp
import requests
from datetime import datetime

# ===================== 路径配置 =====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

SOURCE_URL = "https://yang.sufern001.workers.dev/"

OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

# ===================== TW过滤 =====================

TW_FILTER_KEYWORDS = [
    # 体育（重点：博斯）
    "博斯", "BOS", "SPORT", "体育",

    # 宗教
    "宗教", "church", "佛", "禅",

    # 少儿
    "少儿", "儿童", "卡通", "动漫", "anime"
]

# ===================== 工具函数 =====================

def download(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def deduplicate(channels):
    seen = set()
    result = []
    for name, extinf, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, extinf, url))
    return result

def normalize_group(extinf, group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"', 1)

def parse_name(extinf):
    return extinf.split(",", 1)[1].strip() if "," in extinf else ""

def parse_group(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""

def is_bad_youtube(url):
    REMOVE_YT_IDS = [
        "fN9uYWCjQaw","7j92Myu2wzg","f6Kq93wnaZ8",
        "BOy2xDU1LC8","vr3XyVCR4T0","o_-hSMgpAzs",
    ]
    return any(i in url for i in REMOVE_YT_IDS)

# ===================== 解析M3U =====================

def parse_m3u_lines(lines):
    result = []
    extinf = None
    group = None
    name = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            extinf = line
            group = parse_group(line)
            name = parse_name(line)

        elif line.startswith("http"):
            if extinf and name:
                result.append((name, extinf, group, line))

    return result

# ===================== TW提取（核心） =====================

def fetch_tw_channels(lines):
    result = []

    parsed = parse_m3u_lines(lines)

    for name, extinf, group, url in parsed:

        if group != TW_SOURCE_GROUP:
            continue

        name_lower = name.lower()

        # 过滤关键词
        if any(k.lower() in name_lower for k in TW_FILTER_KEYWORDS):
            continue

        result.append((name, extinf, url))

    result = deduplicate(result)

    print("TW频道数:", len(result))
    return result

# ===================== 主程序 =====================

def main():
    print("下载主源...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    # ===================== HK =====================

    hk_channels = []
    extinf = group = name = None

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            extinf = line
            group = parse_group(line)
            name = parse_name(line)

        elif line.startswith("http"):
            if group == HK_SOURCE_GROUP and not is_bad_youtube(line):
                hk_channels.append((name, extinf, line))

    hk_channels = deduplicate(hk_channels)
    print("HK频道数:", len(hk_channels))

    # ===================== TW（已修改） =====================

    print("提取 TW（台湾限制 + 过滤博斯/宗教/少儿）...")
    tw_channels = fetch_tw_channels(lines)

    # ===================== 输出 =====================

    output = '#EXTM3U\n\n'

    # BB
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            bb = re.sub(r'^#EXTM3U', '', f.read())
            output += bb + "\n"
    except:
        print("未加载 BB.m3u")

    # HK
    output += "\n# HK\n"
    for n, e, u in hk_channels:
        output += normalize_group(e, "HK") + "\n"
        output += u + "\n"

    # TW
    output += "\n# TW\n"
    for n, e, u in tw_channels:
        output += normalize_group(e, "TW") + "\n"
        output += u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ 完成:", OUTPUT_FILE)

# ===================== 启动 =====================

if __name__ == "__main__":
    main()
