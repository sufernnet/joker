#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DD.m3u 构建系统（增强版）
功能：
- HK / TW 分组
- SPORTS 自动归类
- 清洗频道名
- 同名频道合并多链接
"""

import requests
from datetime import datetime
import re
from collections import defaultdict

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

# ================= 工具 =================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url, desc):
    try:
        log(f"下载 {desc} ...")
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        log(f"✅ {desc} 下载成功")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return ""

# ================= 名称清洗 =================

def clean_channel_name(name):
    name = name.strip()

    # 删除 FainTV / ofiii / 4gTV
    for kw in REMOVE_KEYWORDS:
        name = re.sub(rf'「?\s*{kw}\s*」?', '', name, flags=re.IGNORECASE)

    # 删除尾部数字（NOW体育1 → NOW体育）
    name = re.sub(r'\d+$', '', name)

    # 删除多余空格
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

# ================= 分组判断 =================

def determine_group(name, default_group):

    for kw in SPORTS_KEYWORDS:
        if kw.lower() in name.lower():
            return GROUP_SPORTS

    return default_group

# ================= 提取函数 =================

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
            try:
                name = line.split(",", 1)[1].strip()
            except:
                continue

            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url.startswith("http"):
                    channels.append((name, url, GROUP_TW))

    return channels

# ================= 合并频道 =================

def merge_channels(channel_list):
    """
    同名频道合并多个链接
    """
    merged = defaultdict(lambda: {"group": "", "urls": []})

    for name, url, group in channel_list:
        clean_name = clean_channel_name(name)
        final_group = determine_group(clean_name, group)

        if merged[clean_name]["group"] == "":
            merged[clean_name]["group"] = final_group

        if url not in merged[clean_name]["urls"]:
            merged[clean_name]["urls"].append(url)

    return merged

# ================= 主流程 =================

def main():
    log("开始生成 DD.m3u")

    bb_content = download(BB_URL, "BB.m3u")
    hk_source = download(HK_SOURCE_URL, "香港源")
    tw_source = download(TW_SOURCE_URL, "台湾源")

    hk_channels = extract_hk_channels(hk_source)
    tw_channels = extract_tw_limited(tw_source)

    all_channels = hk_channels + tw_channels

    merged = merge_channels(all_channels)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# 生成时间: {timestamp}\n\n"

    # ===== BB 原样 =====
    for line in bb_content.splitlines():
        if not line.startswith("#EXTM3U"):
            output += line + "\n"

    # ===== 输出合并频道 =====
    for name in sorted(merged.keys()):
        group = merged[name]["group"]
        urls = merged[name]["urls"]

        output += f'\n#EXTINF:-1 group-title="{group}",{name}\n'
        for u in urls:
            output += f"{u}\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    log("🎉 DD.m3u 生成成功")

if __name__ == "__main__":
    main()
