#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DD.m3u 构建系统（终极过滤版）
"""

import requests
from datetime import datetime
import re

# ================= 配置 =================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
HK_SOURCE_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
TW_SOURCE_URL = "https://yang.sufern001.workers.dev"

OUTPUT_FILE = "DD.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

GROUP_HK = "HK"
GROUP_TW = "TW"
GROUP_SPORTS = "SPORTS"

REMOVE_KEYWORDS = ["FainTV", "ofiii", "4gTV"]

SPORTS_KEYWORDS = [
    "博斯",
    "緯來體育",
    "NOW体育",
    "Now体育"
]

# ===== 频道剔除列表 =====
REMOVE_CHANNELS = [
    "東森購物",
    "少儿频道",
    "半島國際新聞",
    "兒童頻道",
    "MOMO運動綜合",
    "LiveABC互動英語頻道",
    "GINX Esports TV",
    "DW德國之聲",
    "DreamWorks 夢工廠動畫",
    "CLASSICA 古典樂",
    "Arirang TV",
    "Bloomberg TV"
]

HK_ORDER = [
    "凤凰中文","凤凰资讯","凤凰香港台",
    "Now新闻","Now体育","Now财经","Now直播",
    "HOY76","HOY77","HOY78",
    "翡翠台","翡翠台4K","明珠台",
    "TVB plus","TVB1","TVBJ1","TVB功夫",
    "TVB千禧经典","TVB娱乐新闻台","TVB星河",
    "无线新闻台",
    "ViuTV","ViuTV6",
    "RHK31","RHK32",
    "CH5综合","CH8综合","CHU综合"
]

# ================= 工具 =================

def download(url):
    try:
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except:
        return ""

# ================= 名称清洗 =================

def normalize_channel_name(name):
    name = name.strip()

    for kw in REMOVE_KEYWORDS:
        name = re.sub(rf'「?\s*{kw}\s*」?', '', name, flags=re.IGNORECASE)

    name = re.sub(r'台$', '', name)
    name = re.sub(r'\d+$', '', name)
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

# ================= 过滤判断 =================

def should_remove_channel(name):
    for kw in REMOVE_CHANNELS:
        if kw.lower() in name.lower():
            return True
    return False

# ================= 分组判断 =================

def determine_group(name, default_group):
    for kw in SPORTS_KEYWORDS:
        if kw.lower() in name.lower():
            return GROUP_SPORTS
    return default_group

# ================= 提取 =================

def extract_hk_channels(content):
    lines = content.splitlines()
    channels = []
    in_section = False

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        if not in_section and "港澳台直播" in raw:
            in_section = True
            continue

        if in_section:
            if "#genre#" in raw and "港澳台直播" not in raw:
                break

            if "," in raw and "://" in raw:
                name, url = raw.split(",", 1)
                channels.append((name.strip(), url.strip(), GROUP_HK))

    return channels

def extract_tw_limited(content):
    lines = content.splitlines()
    channels = []

    for i in range(len(lines)):
        line = lines[i].strip()
        if line.startswith("#EXTINF") and 'group-title="•台湾「限制」"' in line:
            name = line.split(",", 1)[1].strip()
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url.startswith("http"):
                    channels.append((name, url, GROUP_TW))

    return channels

# ================= 合并 =================

def merge_channels(channel_list):
    merged = {}

    for name, url, group in channel_list:

        normalized = normalize_channel_name(name)

        if should_remove_channel(normalized):
            continue

        key = normalized.lower()
        final_group = determine_group(normalized, group)

        if key not in merged:
            merged[key] = {
                "name": normalized,
                "group": final_group,
                "urls": set()
            }

        merged[key]["urls"].add(url)

    return merged

# ================= 排序 =================

def hk_sort_weight(name):
    for idx, key in enumerate(HK_ORDER):
        if key.lower() in name.lower():
            return idx
    return 999

# ================= 主流程 =================

def main():

    bb_content = download(BB_URL)
    hk_source = download(HK_SOURCE_URL)
    tw_source = download(TW_SOURCE_URL)

    all_channels = (
        extract_hk_channels(hk_source) +
        extract_tw_limited(tw_source)
    )

    merged = merge_channels(all_channels)

    hk, tw, sports = [], [], []

    for data in merged.values():
        if data["group"] == GROUP_HK:
            hk.append(data)
        elif data["group"] == GROUP_TW:
            tw.append(data)
        else:
            sports.append(data)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# 生成时间: {timestamp}\n\n"

    # HK
    output += "\n### HK ###\n"
    for item in sorted(hk, key=lambda x: (hk_sort_weight(x["name"]), x["name"].lower())):
        output += f'\n#EXTINF:-1 group-title="{GROUP_HK}",{item["name"]}\n'
        for u in sorted(item["urls"]):
            output += u + "\n"

    # TW
    output += "\n### TW ###\n"
    for item in sorted(tw, key=lambda x: x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="{GROUP_TW}",{item["name"]}\n'
        for u in sorted(item["urls"]):
            output += u + "\n"

    # SPORTS
    output += "\n### SPORTS ###\n"
    for item in sorted(sports, key=lambda x: x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="{GROUP_SPORTS}",{item["name"]}\n'
        for u in sorted(item["urls"]):
            output += u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("🎯 精简版 DD.m3u 生成完成")

if __name__ == "__main__":
    main()
