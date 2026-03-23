#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
from datetime import datetime

# ===================== 基础配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_NEW_SOURCE = "https://tv123.sufern001.workers.dev"

OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"

EPG_URL = "https://epg.136605.xyz/9days.xml.gz,https://epg.iill.top/epg,https://bit.ly/a1xepg,https://epg.catvod.com/epg.xml,https://7pal.short.gy/alex-epg,https://bit.ly/a1xepg"

HK_SOURCE_GROUP = "• Juli 「精選」"

# ===================== 工具函数 =====================

def download(url):
    r = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0"
    })
    r.raise_for_status()
    return r.text


def deduplicate(channels):
    seen = set()
    result = []
    for name, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, url))
    return result


# ===================== 主程序 =====================

def main():

    print("下载主源...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    print("下载TW新源...")
    tw_content = download(TW_NEW_SOURCE)
    tw_lines = tw_content.splitlines()

    hk_channels = []
    tw_channels = []

    current_group = None
    current_name = None

    # ===================== HK（完全不动原逻辑） =====================
    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            if 'group-title="' in line:
                current_group = line.split('group-title="')[1].split('"')[0]
            else:
                current_group = None

            if "," in line:
                current_name = line.split(",")[-1].strip()
            else:
                current_name = None

        elif line.startswith("http"):

            url = line.strip()

            if not current_group or not current_name:
                continue

            if current_group == HK_SOURCE_GROUP:
                hk_channels.append((current_name, url))

    # ===================== TW（全新逻辑，只提取四季線上） =====================
    current_group = None
    current_name = None

    for line in tw_lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            if 'group-title="' in line:
                current_group = line.split('group-title="')[1].split('"')[0]
            else:
                current_group = None

            if "," in line:
                current_name = line.split(",")[-1].strip()
            else:
                current_name = None

        elif line.startswith("http"):

            url = line.strip()

            if not current_group or not current_name:
                continue

            # ✅ 只提取 🌴四季線上
            if current_group == "🌴四季線上":
                tw_channels.append((current_name, url))

    # ✅ 只保留去重（不排序、不过滤）
    hk_channels = deduplicate(hk_channels)
    tw_channels = deduplicate(tw_channels)

    print("HK:", len(hk_channels))
    print("TW:", len(tw_channels))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===================== 输出 =====================
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# Gather.m3u\n# 生成时间: {timestamp}\n\n"

    # BB（完全不动）
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("#EXTM3U"):
                    output += line
        print("已合并 BB.m3u")
    except:
        print("未找到 BB.m3u，跳过")

    # HK（不动）
    if hk_channels:
        output += "\n# HK\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="HK",{name}\n'
            output += f"{url}\n"

    # TW（新源）
    if tw_channels:
        output += "\n# TW\n"
        for name, url in tw_channels:
            output += f'#EXTINF:-1 group-title="TW",{name}\n'
            output += f"{url}\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ Gather.m3u 生成完成")


if __name__ == "__main__":
    main()
