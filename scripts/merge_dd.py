#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DD.m3u 构建系统（BB优先顺序版）

顺序：
BB 原顺序
→ HK
→ TW
→ SPORTS
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

REMOVE_KEYWORDS = ["FainTV", "ofiii", "4gTV", "Relay"]

SPORTS_KEYWORDS = ["博斯", "緯來體育", "NOW体育", "Now体育"]

# ================= 下载 =================

def download(url):
    try:
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except:
        return ""

# ================= 名称标准化 =================

def normalize_name(name):
    name = name.strip()

    for kw in REMOVE_KEYWORDS:
        name = re.sub(rf'「?\s*{kw}\s*」?', '', name, flags=re.IGNORECASE)

    name = re.sub(r'台$', '', name)
    name = re.sub(r'\d+$', '', name)
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

def determine_group(name, default_group):
    for kw in SPORTS_KEYWORDS:
        if kw.lower() in name.lower():
            return GROUP_SPORTS
    return default_group

# ================= 提取 BB =================

def extract_bb(content):
    lines = content.splitlines()
    channels = []

    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            name = lines[i].split(",",1)[1].strip()
            group_match = re.search(r'group-title="([^"]*)"', lines[i])
            group = group_match.group(1) if group_match else ""

            if i+1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith("http"):
                    channels.append((name,url,group))
    return channels

# ================= 提取 HK =================

def extract_hk(content):
    lines = content.splitlines()
    channels = []
    in_section = False

    for line in lines:
        raw = line.strip()

        if not in_section and "港澳台直播" in raw:
            in_section = True
            continue

        if in_section:
            if "#genre#" in raw and "港澳台直播" not in raw:
                break

            if "," in raw and "://" in raw:
                name, url = raw.split(",",1)
                channels.append((name.strip(),url.strip(),GROUP_HK))
    return channels

# ================= 提取 TW =================

def extract_tw(content):
    lines = content.splitlines()
    channels = []

    for i in range(len(lines)):
        line = lines[i].strip()

        if line.startswith("#EXTINF"):

            if 'group-title="•台湾「限制」"' in line:
                name = line.split(",",1)[1].strip()
                url = lines[i+1].strip()
                channels.append((name,url,GROUP_TW))

            if 'group-title="•體育「Relay」"' in line:
                name = line.split(",",1)[1].strip()
                url = lines[i+1].strip()
                channels.append((name,url,GROUP_SPORTS))

    return channels

# ================= 合并 =================

def merge_channels(channel_list):
    merged = {}
    order = []

    for name,url,group in channel_list:

        normalized = normalize_name(name)
        key = normalized.lower()

        final_group = determine_group(normalized, group)

        if key not in merged:
            merged[key] = {
                "name": normalized,
                "group": final_group,
                "urls": []
            }
            order.append(key)

        if url not in merged[key]["urls"]:
            merged[key]["urls"].append(url)

    return merged, order

# ================= 主流程 =================

def main():

    bb_content = download(BB_URL)
    hk_content = download(HK_SOURCE_URL)
    tw_content = download(TW_SOURCE_URL)

    bb_channels = extract_bb(bb_content)
    hk_channels = extract_hk(hk_content)
    tw_channels = extract_tw(tw_content)

    # 关键：BB 放最前面
    all_channels = bb_channels + hk_channels + tw_channels

    merged, order = merge_channels(all_channels)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# 生成时间: {timestamp}\n\n"

    # ====== 先输出 BB 原顺序 ======
    output += "\n### BB ###\n"
    for name,url,group in bb_channels:
        key = normalize_name(name).lower()
        if key in merged:
            data = merged[key]
            output += f'\n#EXTINF:-1 group-title="{group}",{data["name"]}\n'
            for u in data["urls"]:
                output += u+"\n"
            merged.pop(key)

    # ====== 再输出 HK → TW → SPORTS ======

    hk_list = []
    tw_list = []
    sports_list = []

    for data in merged.values():
        if data["group"] == GROUP_HK:
            hk_list.append(data)
        elif data["group"] == GROUP_TW:
            tw_list.append(data)
        else:
            sports_list.append(data)

    output += "\n### HK ###\n"
    for item in sorted(hk_list,key=lambda x:x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="HK",{item["name"]}\n'
        for u in item["urls"]:
            output += u+"\n"

    output += "\n### TW ###\n"
    for item in sorted(tw_list,key=lambda x:x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="TW",{item["name"]}\n'
        for u in item["urls"]:
            output += u+"\n"

    output += "\n### SPORTS ###\n"
    for item in sorted(sports_list,key=lambda x:x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="SPORTS",{item["name"]}\n'
        for u in item["urls"]:
            output += u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(output)

    print("✅ DD.m3u 已按 BB→HK→TW→SPORTS 顺序生成")

if __name__ == "__main__":
    main()
