#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import asyncio
import aiohttp
import requests
from datetime import datetime

# ===================== 路径配置 =====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

SOURCE_URL = "https://yang.sufern001.workers.dev/"

OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

# ===================== TW 白名单（顺序即输出顺序） =====================

TW_TARGET_ORDER = [
    "Love Nature","亞洲旅遊","民視第一台","民視台灣台","民視","華視",
    "中天新聞台","寰宇新聞","寰宇新聞台灣台","寰宇財經","三立綜合台",
    "ELTA娛樂","靖天綜合","Global Trekker","鏡電視新聞台","東森新聞",
    "華視新聞","民視新聞","TVBS新聞台","三立iNEWS","東森財經新聞",
    "中視新聞","TVBS","民視綜藝","豬哥亮歌廳秀","靖天育樂",
    "KLT-靖天國際台","NICE TV 靖天歡樂台","靖天資訊","TVBS歡樂台",
    "韓國娛樂台","ROCK Entertainment","Lifetime 娛樂頻道","電影原聲台CMusic",
    "TRACE Urban","Mezzo Live HD","INULTRA","TRACE Sport Stars","車迷 TV",
    "GINX Esports TV","民視旅遊","滾動力 Rollor","fun探索娛樂台",
    "ELTATW","MagellanTV頻道","民視影劇","HITS頻道","八大精彩",
    "FashionTV 時尚頻道","CI 罪案偵查頻道","視納華仁紀實頻道",
    "影迷數位紀實台","ROCK Action","采昌影劇","靖天映畫","靖天電影",
    "影迷數位電影台","amc 電影台","Cinema World",
    "My Cinema Europe HD 我的歐洲電影","CNBC Asia 財經台","經典電影台",
    "中視","Smart知識台","三立新聞iNEWS","龍華洋片","龍華卡通",
    "龍華電影","龍華日韓","龍華偶像","龍華戲劇","龍華經典","DayStar"
]

# ===================== 原有变量 =====================

TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"

REMOVE_YT_IDS = [
    "fN9uYWCjQaw","7j92Myu2wzg","f6Kq93wnaZ8",
    "BOy2xDU1LC8","vr3XyVCR4T0","o_-hSMgpAzs",
]

# ===================== 工具函数（原样保留） =====================

def download(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def is_bad_youtube(url):
    return any(i in url for i in REMOVE_YT_IDS)

def deduplicate(channels):
    seen = set()
    result = []
    for name, extinf, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, extinf, url))
    return result

def normalize_group(extinf_line, new_group):
    if 'group-title="' in extinf_line:
        extinf_line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', extinf_line)
    else:
        extinf_line = extinf_line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"', 1)
    return extinf_line

def parse_name_from_extinf(extinf_line):
    return extinf_line.split(",",1)[1].strip() if "," in extinf_line else ""

def parse_group_from_extinf(extinf_line):
    m = re.search(r'group-title="([^"]*)"', extinf_line)
    return m.group(1).strip() if m else ""

def parse_m3u_full(content):
    lines = content.splitlines()
    res = []
    extinf=None
    for line in lines:
        line=line.strip()
        if line.startswith("#EXTINF"):
            extinf=line
        elif line.startswith("http") and extinf:
            res.append((parse_name_from_extinf(extinf),extinf,line))
    return res

# ===================== ⭐ TW核心（唯一新增逻辑） =====================

def fetch_tw_from_source(lines):
    parsed = parse_m3u_full("\n".join(lines))

    # 先筛选台湾限制分组
    temp = []
    for name, extinf, url in parsed:
        group = parse_group_from_extinf(extinf)
        if group == TW_SOURCE_GROUP:
            temp.append((name.strip(), extinf, url))

    temp = deduplicate(temp)

    # 建立频道映射
    channel_map = {}
    for name, extinf, url in temp:
        channel_map.setdefault(name, []).append((extinf, url))

    result = []
    used = set()

    # 按顺序筛选
    for target in TW_TARGET_ORDER:
        for name in channel_map:
            if target in name and name not in used:
                extinf, url = channel_map[name][0]
                result.append((name, extinf, url))
                used.add(name)
                break

    print("TW(筛选后):", len(result))
    return result

# ===================== 主程序 =====================

def main():
    print("下载源...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    # HK（完全不动）
    hk_channels = []
    current_group = None
    current_name = None
    current_extinf = None

    for line in lines:
        line=line.strip()
        if line.startswith("#EXTINF"):
            current_extinf=line
            current_group=parse_group_from_extinf(line)
            current_name=parse_name_from_extinf(line)
        elif line.startswith("http"):
            if current_group==HK_SOURCE_GROUP and not is_bad_youtube(line):
                hk_channels.append((current_name,current_extinf,line))

    hk_channels = deduplicate(hk_channels)

    # ⭐ TW（唯一修改点）
    print("提取 TW（台湾限制白名单）...")
    tw_channels = fetch_tw_from_source(lines)

    # ===================== 输出 =====================

    output = "#EXTM3U\n\n"

    # BB（不动）
    try:
        with open(BB_FILE,"r",encoding="utf-8") as f:
            output += re.sub(r'^#EXTM3U','',f.read())+"\n"
    except:
        pass

    # HK（不动）
    output += "\n# HK\n"
    for n,e,u in hk_channels:
        output += normalize_group(e,"HK")+"\n"+u+"\n"

    # TW（输出）
    output += "\n# TW\n"
    for n,e,u in tw_channels:
        output += normalize_group(e,"TW")+"\n"+u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(output)

    print("✅ 完成:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
