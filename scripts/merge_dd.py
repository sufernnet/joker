#!/usr/bin/env python3
"""
DD.m3u 合并脚本（港台频道版）- 终极稳定完整版
"""

import requests
import re
from datetime import datetime
import sys
import time

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/港台大陆"
TW_SOURCE_URL = "https://yang.sufern001.workers.dev"
OUTPUT_FILE = "DD.m3u"

SOURCE_GROUPS = ["港台频道", "新聞频道"]
TARGET_TW_GROUP = "•台湾「限制」"

HK_GROUP = "HK"
TW_GROUP = "TW"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ================== 工具函数 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download(url, desc, retries=3):
    for attempt in range(retries):
        try:
            log(f"下载 {desc}... ({attempt+1}/{retries})")
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text
        except Exception as e:
            log(f"失败: {e}")
            time.sleep(3)
    return None


# ================== 名称清洗核心 ==================

def clean_tw_channel_name(name):
    """
    去除频道名末尾的：
    「xxx」  【xxx】  (xxx)
    """
    original = name

    # 去除末尾括号内容
    name = re.sub(r'\s*[「【(][^」】)]*[」】)]\s*$', '', name)

    # 再清理分辨率等残留
    name = re.sub(r'\s*720[pP]\s*$', '', name)
    name = re.sub(r'\s*1080[pP]\s*$', '', name)
    name = re.sub(r'\s*[Hh][Dd]\s*$', '', name)

    name = name.strip()

    if name != original:
        log(f"清洗: '{original}' -> '{name}'")

    return name


# ================== 解析函数 ==================

def extract_channels_from_file(content, target_groups):
    lines = content.splitlines()
    channels = []
    in_section = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if any(f"{group},#genre#" in line for group in target_groups):
            in_section = True
            continue

        if in_section:
            if ",#genre#" in line:
                in_section = False
                continue

            if "," in line and "://" in line:
                try:
                    name, url = line.split(",", 1)
                    channels.append((name.strip(), url.strip()))
                except:
                    continue

    return channels


def parse_m3u_for_group(content, target_group):
    lines = content.splitlines()
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:") and f'group-title="{target_group}"' in line:
            name = line.split(",")[-1].strip()
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if not url.startswith("#"):
                    channels.append((line, name, url))
                    i += 1
        i += 1
    return channels


# ================== 主程序 ==================

def main():
    log("开始生成 DD.m3u")

    bb = download(BB_URL, "BB源")
    gat = download(GAT_URL, "港台源")
    tw = download(TW_SOURCE_URL, "台湾源")

    if not bb:
        sys.exit(1)

    # ===== HK 处理 =====
    hk_channels = []
    if gat:
        hk_raw = extract_channels_from_file(gat, SOURCE_GROUPS)
        hk_channels = [(name.strip(), url.strip()) for name, url in hk_raw]

    # ===== TW 处理 =====
    tw_channels = []
    if tw:
        tw_raw = parse_m3u_for_group(tw, TARGET_TW_GROUP)

        for extinf_line, original_name, url in tw_raw:
            cleaned_name = clean_tw_channel_name(original_name)

            # 替换 group-title
            modified = re.sub(
                r'group-title="[^"]*"',
                f'group-title="{TW_GROUP}"',
                extinf_line
            )

            # 替换逗号后面的频道名
            modified = re.sub(
                r',\s*[^,]*$',
                f',{cleaned_name}',
                modified
            )

            tw_channels.append((modified, url))

    # ===== 生成输出 =====
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# 生成时间: {timestamp}\n\n"

    # 写入 BB
    for line in bb.splitlines():
        if not line.startswith("#EXTM3U"):
            output += line + "\n"

    # 写入 HK
    if hk_channels:
        output += f"\n# {HK_GROUP}频道\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n{url}\n'

    # 写入 TW
    if tw_channels:
        output += f"\n# {TW_GROUP}频道\n"
        for extinf_line, url in tw_channels:
            output += extinf_line + "\n" + url + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    log("生成完成")


if __name__ == "__main__":
    main()
