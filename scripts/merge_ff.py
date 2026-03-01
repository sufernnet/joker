#!/usr/bin/env python3
"""
Gather.m3u 生成脚本

提取：
1. • Juli 「精選」 → HK
2. •台湾「限制」 中包含 4gTV / ofiii / 龍華 → TW

不做过滤、不去重、不排序
"""

import requests
from datetime import datetime

SOURCE_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = "Gather.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

HK_GROUP = "HK"
TW_GROUP = "TW"


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download(url):
    try:
        log("下载源文件...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        log("下载成功")
        return r.text
    except Exception as e:
        log(f"下载失败: {e}")
        return None


def extract_groups(content):
    lines = content.splitlines()
    hk_channels = []
    tw_channels = []

    current_group = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 识别分组
        if ",#genre#" in line:
            group_name = line.split(",")[0]
            current_group = group_name
            continue

        if "," in line and "://" in line:
            name, url = line.split(",", 1)

            # HK 提取
            if current_group == HK_SOURCE_GROUP:
                hk_channels.append((name.strip(), url.strip()))

            # TW 提取
            elif current_group == TW_SOURCE_GROUP:
                if (
                    "4gTV" in name
                    or "ofiii" in name
                    or "龍華" in name
                ):
                    tw_channels.append((name.strip(), url.strip()))

    return hk_channels, tw_channels


def main():
    log("开始生成 Gather.m3u")

    content = download(SOURCE_URL)
    if not content:
        return

    hk_channels, tw_channels = extract_groups(content)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = "#EXTM3U\n\n"
    output += f"# Gather.m3u\n# 生成时间: {timestamp}\n\n"

    # 写 HK
    if hk_channels:
        output += f"# {HK_GROUP}\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n'
            output += f"{url}\n"

    # 写 TW
    if tw_channels:
        output += f"\n# {TW_GROUP}\n"
        for name, url in tw_channels:
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{name}\n'
            output += f"{url}\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    log("🎉 Gather.m3u 生成成功")
    log(f"HK: {len(hk_channels)} 个")
    log(f"TW: {len(tw_channels)} 个")


if __name__ == "__main__":
    main()
