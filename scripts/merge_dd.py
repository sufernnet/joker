#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DD.m3u 合并脚本
- BB 原样保留
- 香港单独一组
- 台湾「限制」单独一组
- 自动去掉频道名中的 FainTV / ofiii / 4gTV
- SPORTS 规则仍保留
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

HK_GROUP_NAME = "香港"
TW_GROUP_NAME = "台湾限制"
SPORTS_GROUP_NAME = "SPORTS"

REMOVE_KEYWORDS = ["FainTV", "ofiii", "4gTV"]

# ================= 工具 =================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url, desc):
    try:
        log(f"下载 {desc} ...")
        r = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*"
            }
        )
        r.raise_for_status()
        log(f"✅ {desc} 下载成功 (长度 {len(r.text)})")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return ""

# ================= 名称清洗 =================

def clean_channel_name(name):
    """
    删除 FainTV / ofiii / 4gTV
    自动清除「」和多余空格
    """

    name = name.strip()

    for kw in REMOVE_KEYWORDS:
        # 删除带「关键字」
        name = re.sub(rf'「?\s*{kw}\s*」?', '', name, flags=re.IGNORECASE)

    # 删除多余空格
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

def assign_group(name, default_group):
    """
    如果频道名包含 SPORTS 关键字才归类（目前仅示例保留）
    """
    return default_group

# ================= 香港提取 =================

def extract_hk_channels(content):
    lines = content.splitlines()
    channels = []
    in_section = False

    log("开始提取香港频道")

    HK_KEYWORDS = [
        "香港", "凤凰", "Now", "TVB",
        "HOY", "RHK", "Viu", "有线"
    ]

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
                name = name.strip()
                url = url.strip()

                if any(k.lower() in name.lower() for k in HK_KEYWORDS):
                    channels.append((name, url))

    log(f"香港频道数: {len(channels)}")
    return channels

# ================= 台湾提取 =================

def extract_tw_limited(content):
    lines = content.splitlines()
    channels = []

    log('开始提取 group-title="•台湾「限制」"')

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
                    channels.append((name, url))

    log(f"台湾限制频道数: {len(channels)}")
    return channels

# ================= 去重 =================

def deduplicate(channels):
    seen = {}
    for name, url in channels:
        if url not in seen:
            seen[url] = name

    result = [(name, url) for url, name in seen.items()]
    log(f"去重后频道数: {len(result)}")
    return result

# ================= 排序 =================

def sort_channels(channels):
    return sorted(channels, key=lambda x: x[0].lower())

# ================= 主流程 =================

def main():
    log("开始生成 DD.m3u")

    bb_content = download(BB_URL, "BB.m3u")
    hk_source = download(HK_SOURCE_URL, "香港源")
    tw_source = download(TW_SOURCE_URL, "台湾源")

    hk_channels = sort_channels(deduplicate(extract_hk_channels(hk_source)))
    tw_channels = sort_channels(deduplicate(extract_tw_limited(tw_source)))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# DD.m3u
# 生成时间: {timestamp}
# 香港 + 台湾限制
# 自动清洗频道名
# EPG: {EPG_URL}

"""

    # ===== BB =====
    bb_count = 0
    for line in bb_content.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        output += line + "\n"
        if line.startswith("#EXTINF"):
            bb_count += 1

    # ===== 香港 =====
    if hk_channels:
        output += f"\n# {HK_GROUP_NAME}频道 ({len(hk_channels)})\n"
        for name, url in hk_channels:
            clean_name = clean_channel_name(name)
            output += f'#EXTINF:-1 group-title="{HK_GROUP_NAME}",{clean_name}\n'
            output += f"{url}\n"

    # ===== 台湾限制 =====
    if tw_channels:
        output += f"\n# {TW_GROUP_NAME}频道 ({len(tw_channels)})\n"
        for name, url in tw_channels:
            clean_name = clean_channel_name(name)
            output += f'#EXTINF:-1 group-title="{TW_GROUP_NAME}",{clean_name}\n'
            output += f"{url}\n"

    total = bb_count + len(hk_channels) + len(tw_channels)

    output += f"""

# 统计
# BB频道数: {bb_count}
# 香港频道数: {len(hk_channels)}
# 台湾限制频道数: {len(tw_channels)}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    log("🎉 DD.m3u 生成成功")

if __name__ == "__main__":
    main()
