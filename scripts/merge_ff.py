#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gather IPTV Generator
功能：
- 下载源 M3U
- 提取 HK
- 合并远程 TW.m3u
- 剔除指定 YouTube 源
- 去重
- 合并 BB.m3u
- 输出 Gather.m3u
- 保留 tvg-id / tvg-name / tvg-logo
"""

import requests
import re
from datetime import datetime

# ===================== 基础配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"
OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

# ===================== 精准剔除 YouTube ID =====================

REMOVE_YT_IDS = [
    "fN9uYWCjQaw",
    "7j92Myu2wzg",
    "f6Kq93wnaZ8",
    "BOy2xDU1LC8",
    "vr3XyVCR4T0",
    "o_-hSMgpAzs",
]

# ===================== 工具函数 =====================

def download(url):
    r = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    r.raise_for_status()
    return r.text


def is_bad_youtube(url):
    for yt_id in REMOVE_YT_IDS:
        if yt_id in url:
            return True
    return False


def deduplicate(channels):
    """
    channels: [(name, extinf, url), ...]
    按 url 去重
    """
    seen = set()
    result = []
    for name, extinf, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, extinf, url))
    return result


def normalize_group(extinf_line, new_group):
    """
    把 #EXTINF 行里的 group-title 改成指定分组
    若没有 group-title，则补上
    """
    if 'group-title="' in extinf_line:
        extinf_line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', extinf_line)
    else:
        if extinf_line.startswith("#EXTINF:-1 "):
            extinf_line = extinf_line.replace("#EXTINF:-1 ", f'#EXTINF:-1 group-title="{new_group}" ', 1)
        elif extinf_line.startswith("#EXTINF:-1"):
            extinf_line = extinf_line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"', 1)
    return extinf_line


def parse_name_from_extinf(extinf_line):
    if "," in extinf_line:
        return extinf_line.split(",", 1)[1].strip()
    return ""


def parse_m3u_full(content):
    """
    返回:
    [
        (name, extinf, url),
        ...
    ]
    """
    lines = content.splitlines()
    channels = []

    current_extinf = None
    current_name = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_extinf = line
            current_name = parse_name_from_extinf(line)

        elif line.startswith("http"):
            if current_extinf and current_name:
                channels.append((current_name, current_extinf, line))

    return channels


# ===================== 主程序 =====================

def main():
    print("下载源...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    hk_channels = []
    current_group = None
    current_name = None
    current_extinf = None

    # 解析 HK
    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_extinf = line

            if 'group-title="' in line:
                current_group = line.split('group-title="')[1].split('"')[0]
            else:
                current_group = None

            current_name = parse_name_from_extinf(line)

        elif line.startswith("http"):
            url = line.strip()

            if not current_group or not current_name or not current_extinf:
                continue

            if current_group == HK_SOURCE_GROUP:
                if is_bad_youtube(url):
                    continue
                hk_channels.append((current_name, current_extinf, url))

    # 解析 TW
    print("下载 TW.m3u...")
    tw_content = download(TW_M3U_URL)
    tw_channels = parse_m3u_full(tw_content)

    # 去重
    hk_channels = deduplicate(hk_channels)
    tw_channels = deduplicate(tw_channels)

    print("HK:", len(hk_channels))
    print("TW:", len(tw_channels))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = '#EXTM3U\n\n'
    output += f"# Gather.m3u\n# 生成时间: {timestamp}\n\n"

    # 合并 BB
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("#EXTM3U"):
                    output += line
        output = output.rstrip() + "\n\n"
        print("已合并 BB.m3u")
    except:
        print("未找到 BB.m3u，跳过")

    # HK
    if hk_channels:
        output += "# HK\n"
        for name, extinf, url in hk_channels:
            output += normalize_group(extinf, "HK") + "\n"
            output += url + "\n"

    # TW
    if tw_channels:
        output += "\n# TW\n"
        for name, extinf, url in tw_channels:
            output += normalize_group(extinf, "TW") + "\n"
            output += url + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ Gather.m3u 生成完成")


if __name__ == "__main__":
    main()
