#!/usr/bin/env python3
import requests
from datetime import datetime
import re

SOURCE_URL = "https://yang.sufern001.workers.dev/"
BB_FILE = "BB.m3u"
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


def clean_tw_name(name):
    # 去掉「4gTV」和「ofiii」
    name = re.sub(r'「4gTV」', '', name, flags=re.IGNORECASE)
    name = re.sub(r'「ofiii」', '', name, flags=re.IGNORECASE)
    return name.strip()


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

            name_lower = current_name.lower()

            # HK
            if current_group == HK_SOURCE_GROUP:
                hk.append((current_name, url))

            # TW
            elif current_group == TW_SOURCE_GROUP:
                if (
                    "4gtv" in name_lower
                    or "ofiii" in name_lower
                    or "龍華" in current_name
                    or "龙华" in current_name
                ):
                    clean_name = clean_tw_name(current_name)
                    tw.append((clean_name, url))

    print("HK:", len(hk))
    print("TW:", len(tw))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = "#EXTM3U\n\n"
    output += f"# Gather.m3u\n# 生成时间: {timestamp}\n\n"

    # 合并 BB.m3u
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            bb_content = f.read()
        output += bb_content + "\n"
        print("BB.m3u 已合并")
    except:
        print("未找到 BB.m3u，跳过")

    # 写 HK
    if hk:
        output += f"\n# {HK_GROUP}\n"
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

    print("🎉 Gather.m3u 生成完成")


if __name__ == "__main__":
    main()
