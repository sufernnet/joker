#!/usr/bin/env python3
import requests
from datetime import datetime

SOURCE_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = "Gather.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

HK_GROUP = "HK"
TW_GROUP = "TW"


def download(url):
    r = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0"
    })
    r.raise_for_status()
    return r.text


def main():
    print("下载源文件...")
    content = download(SOURCE_URL)

    lines = content.splitlines()

    hk = []
    tw = []

    current_group = None
    current_name = None

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            # 提取 group-title
            if 'group-title="' in line:
                current_group = line.split('group-title="')[1].split('"')[0]
            else:
                current_group = None

            # 提取频道名（逗号后）
            if "," in line:
                current_name = line.split(",")[-1].strip()
            else:
                current_name = None

        elif line.startswith("http"):
            url = line.strip()

            if not current_group or not current_name:
                continue

            name_lower = current_name.lower()

            # HK 组
            if current_group == HK_SOURCE_GROUP:
                hk.append((current_name, url))

            # TW 组
            elif current_group == TW_SOURCE_GROUP:
                if (
                    "4gtv" in name_lower
                    or "ofiii" in name_lower
                    or "龍華" in current_name
                    or "龙华" in current_name
                ):
                    tw.append((current_name, url))

    print("HK:", len(hk))
    print("TW:", len(tw))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = "#EXTM3U\n\n"
    output += f"# Gather.m3u\n# 生成时间: {timestamp}\n\n"

    # 写 HK
    if hk:
        output += f"# {HK_GROUP}\n"
        for name, url in hk:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n'
            output += f"{url}\n"

    # 写 TW
    if tw:
        output += f"\n# {TW_GROUP}\n"
        for name, url in tw:
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{name}\n'
            output += f"{url}\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("完成")


if __name__ == "__main__":
    main()
