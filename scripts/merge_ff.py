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
- 排序
- 合并 BB.m3u
- 输出 Gather.m3u
"""

import requests
import re
from datetime import datetime

# ===================== 基础配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"
OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"
EPG_URL = "https://epg.136605.xyz/9days.xml.gz,https://epg.iill.top/epg,https://bit.ly/a1xepg,https://epg.catvod.com/epg.xml,https://7pal.short.gy/alex-epg,https://bit.ly/a1xepg"

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

# ===================== 精准剔除 YouTube ID =====================

REMOVE_YT_IDS = [
    "fN9uYWCjQaw",  # 凤凰资讯
    "7j92Myu2wzg",  # CCTV4
    "f6Kq93wnaZ8",  # CCTV4 美洲
    "BOy2xDU1LC8",  # CGTN
    "vr3XyVCR4T0",  # 中天新闻
    "o_-hSMgpAzs",  # TVBS
]

# ===================== TW 关键词剔除 =====================

REMOVE_TW_KEYWORDS = [
    "大愛電視","好消息","國會頻道","東森購物","新唐人","人間衛視",
    "幸福空間","車迷","金光布袋戲","原住民族電視","客家電視",
    "LiveABC","ELTA生活英語","Smart知識","達文西","滾動力",
    "INULTRA","Global Trekker","LUXE TV","TV5MONDE","TRACE",
    "GINX","DreamWorks","精選動漫","經典卡通","MOMO親子",
    "Nick Jr","尼克兒童","Pet Club","KMTV","Lifetime",
    "fun探索","HITS","ROCK","豬哥亮","采昌","CLASSICA",
    "Mezzo","CMusic","FashionTV","倪珍播新聞","半島國際",
    "DW德國之聲","FRANCE24","NHK 新聞","CNBC Asia",
    "SBN 全球財經","Bloomberg","DayStar","第1商業",
    "amc電影","MCE 我的歐洲電影","影迷數位電影",
    "影迷數位紀實","CinemaWorld"
]

# ===================== 工具函数 =====================

def download(url):
    r = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0"
    })
    r.raise_for_status()
    return r.text


def clean_tw_name(name):
    name = re.sub(r'「4gTV」', '', name, flags=re.IGNORECASE)
    name = re.sub(r'「ofiii」', '', name, flags=re.IGNORECASE)
    return name.strip()


def should_remove_tw(name):
    for k in REMOVE_TW_KEYWORDS:
        if k.lower() in name.lower():
            return True
    return False


def is_bad_youtube(url):
    for yt_id in REMOVE_YT_IDS:
        if yt_id in url:
            return True
    return False


def deduplicate(channels):
    seen = set()
    result = []
    for name, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, url))
    return result


def sort_tw_channels(channels):

    priority_top = ["Love Nature", "歷史頻道", "亞洲旅遊"]

    def key_func(item):
        name = item[0]

        for i, k in enumerate(priority_top):
            if k in name:
                return (0, i)

        if "中天" in name:
            return (1, name)
        if "民视" in name or "民視" in name:
            return (2, name)
        if "寰宇" in name:
            return (3, name)
        if "鏡電視" in name or "鏡新聞" in name:
            return (4, name)
        if "龍華" in name or "龙华" in name:
            return (5, name)

        return (6, name)

    return sorted(channels, key=key_func)


def parse_m3u_channels(content):
    lines = content.splitlines()
    channels = []

    current_name = None

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            if "," in line:
                current_name = line.split(",")[-1].strip()
            else:
                current_name = None

        elif line.startswith("http"):
            url = line.strip()
            if current_name:
                channels.append((current_name, url))

    return channels


# ===================== 主程序 =====================

def main():

    print("下载源...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    hk_channels = []
    tw_channels = []

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

            # HK
            if current_group == HK_SOURCE_GROUP:

                if is_bad_youtube(url):
                    continue

                hk_channels.append((current_name, url))

    # 改为合并远程 TW.m3u
    print("下载 TW.m3u...")
    tw_content = download(TW_M3U_URL)
    tw_channels = parse_m3u_channels(tw_content)

    # 去重
    hk_channels = deduplicate(hk_channels)
    tw_channels = deduplicate(tw_channels)

    # 排序
    tw_channels = sort_tw_channels(tw_channels)

    print("HK:", len(hk_channels))
    print("TW:", len(tw_channels))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# Gather.m3u\n# 生成时间: {timestamp}\n\n"

    # 合并 BB
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("#EXTM3U"):
                    output += line
        print("已合并 BB.m3u")
    except:
        print("未找到 BB.m3u，跳过")

    # HK
    if hk_channels:
        output += "\n# HK\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="HK",{name}\n'
            output += f"{url}\n"

    # TW
    if tw_channels:
        output += "\n# TW\n"
        for name, url in tw_channels:
            output += f'#EXTINF:-1 group-title="TW",{name}\n'
            output += f"{url}\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ Gather.m3u 生成完成")


if __name__ == "__main__":
    main()
