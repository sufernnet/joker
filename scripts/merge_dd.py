#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DD.m3u 构建系统（BB完全原样保留版）

结构：
BB 原样复制
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

# ================= 名称清洗（只用于新增部分） =================

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

# ================= 提取 TW + 体育 Relay =================

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

# ================= 合并（只合并新增部分） =================

def merge_new_channels(channel_list):
    merged = {}

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

        if url not in merged[key]["urls"]:
            merged[key]["urls"].append(url)

    return merged

# ================= 主流程 =================

def main():

    bb_content = download(BB_URL)
    hk_content = download(HK_SOURCE_URL)
    tw_content = download(TW_SOURCE_URL)

    hk_channels = extract_hk(hk_content)
    tw_channels = extract_tw(tw_content)

    merged_new = merge_new_channels(hk_channels + tw_channels)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# 生成时间: {timestamp}\n\n"

    # ====== BB 原样复制 ======
    output += bb_content.strip() + "\n"

    # ====== 新增部分 ======

    hk_list = []
    tw_list = []
    sports_list = []

    for data in merged_new.values():
        if data["group"] == GROUP_HK:
            hk_list.append(data)
        elif data["group"] == GROUP_TW:
            tw_list.append(data)
        else:
            sports_list.append(data)

    # HK
    output += "\n\n### HK ###\n"
    for item in sorted(hk_list,key=lambda x:x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="HK",{item["name"]}\n'
        for u in item["urls"]:
            output += u+"\n"

    # TW
    output += "\n\n### TW ###\n"
    for item in sorted(tw_list,key=lambda x:x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="TW",{item["name"]}\n'
        for u in item["urls"]:
            output += u+"\n"

    # SPORTS
    output += "\n\n### SPORTS ###\n"
    for item in sorted(sports_list,key=lambda x:x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="SPORTS",{item["name"]}\n'
        for u in item["urls"]:
            output += u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(output)

    print("✅ DD.m3u 已生成（BB完全保持原样）")

if __name__ == "__main__":
    main()
