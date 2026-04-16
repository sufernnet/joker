#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import asyncio
import aiohttp
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===================== 路径配置 =====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

SOURCE_URL = "https://yang.sufern001.workers.dev/"

OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

# ===================== ⭐ 新增：扩展源 =====================

EXTRA_URLS = [
    "https://tzdr.com/iptv.txt",
    "https://live.kilvn.com/iptv.m3u",
    "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "http://175.178.251.183:6689/live.m3u",
    "https://m3u.ibert.me/ycl_iptv.m3u",
    "https://codeberg.org/Jsnzkpg/Jsnzkpg/raw/Jsnzkpg/Jsnzkpg1.m3u",
    "https://2026.xymm.ccwu.cc",
    "https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u",
    "https://iptv.catvod.com/list.php?token=e222e4d00c9d1945c3387a6c63b434577afbefd92f01f3fa39da76f154997133"
]

CCTV_TARGET = [
    "世界地理","兵器科技","怀旧剧场","第一剧场",
    "女性时尚","风云足球","风云音乐","央视台球"
]

CHC_TARGET = [
    "CHC影迷电影","CHC家庭影院","CHC动作电影","HC家庭影院"
]

BAD_KEYWORDS = ["测试","购物","广告"]

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png"
}

# ===================== TW 白名单 =====================

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

REMOVE_YT_IDS = [
    "fN9uYWCjQaw","7j92Myu2wzg","f6Kq93wnaZ8",
    "BOy2xDU1LC8","vr3XyVCR4T0","o_-hSMgpAzs",
]

# ===================== 工具函数（原样） =====================

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

# ===================== ⭐ TW =====================

def fetch_tw_from_source(lines):
    parsed = parse_m3u_full("\n".join(lines))

    temp = []
    for name, extinf, url in parsed:
        group = parse_group_from_extinf(extinf)
        if group == TW_SOURCE_GROUP:
            temp.append((name.strip(), extinf, url))

    temp = deduplicate(temp)

    channel_map = {}
    for name, extinf, url in temp:
        channel_map.setdefault(name, []).append((extinf, url))

    result = []
    used = set()

    for target in TW_TARGET_ORDER:
        for name in channel_map:
            if target in name and name not in used:
                extinf, url = channel_map[name][0]
                result.append((name, extinf, url))
                used.add(name)
                break

    return result

# ===================== ⭐ 新增功能 =====================

def parse_m3u(content):
    lines = content.splitlines()
    data, ext = [], None
    for l in lines:
        l = l.strip()
        if l.startswith("#EXTINF"):
            ext = l
        elif l.startswith("http") and ext:
            name = parse_name_from_extinf(ext)
            if not any(x in name for x in BAD_KEYWORDS):
                data.append((name, ext, l))
    return data

def parse_txt(content):
    data = []
    for l in content.splitlines():
        if "," in l and "http" in l:
            name, url = l.split(",", 1)
            if not any(x in name for x in BAD_KEYWORDS):
                ext = f'#EXTINF:-1 group-title="未知",{name.strip()}'
                data.append((name.strip(), ext, url.strip()))
    return data

def load_extra():
    all_data = []
    for url in EXTRA_URLS:
        raw = download(url)
        if not raw:
            continue
        if "#EXTINF" in raw:
            all_data += parse_m3u(raw)
        else:
            all_data += parse_txt(raw)
    return all_data

def check(url):
    try:
        start = time.time()
        r = requests.get(url, timeout=5, stream=True)
        if r.status_code == 200:
            return url, time.time() - start
    except:
        pass
    return url, 999

def pick_best(urls):
    best_url, best_time = None, 999
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check, u) for u in urls]
        for f in as_completed(futures):
            url, t = f.result()
            if t < best_time:
                best_time, best_url = t, url
    return best_url

def fix_logo(name, extinf):
    if name in LOGO_MAP:
        logo = LOGO_MAP[name]
        if 'tvg-logo="' in extinf:
            extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{logo}"')
    return extinf

# ===================== 主程序 =====================

def main():
    content = download(SOURCE_URL)
    lines = content.splitlines()

    # HK
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

    # TW
    tw_channels = fetch_tw_from_source(lines)

    # ⭐ 新增：数字 + CHC
    extra_data = load_extra()

    cctv_map = {}
    for n,e,u in extra_data:
        if n in CCTV_TARGET:
            cctv_map.setdefault(n, []).append((e,u))

    cctv = []
    for name in CCTV_TARGET:
        if name in cctv_map:
            best = pick_best([u for _,u in cctv_map[name]])
            ext = cctv_map[name][0][0]
            cctv.append((name, ext, best))

    chc_map = {}
    for n,e,u in extra_data:
        if n in CHC_TARGET:
            chc_map.setdefault(n, []).append((e,u))

    chc = []
    for name in CHC_TARGET:
        if name in chc_map:
            best = pick_best([u for _,u in chc_map[name]])
            ext = chc_map[name][0][0]
            chc.append((name, ext, best))

    # ===================== 输出 =====================

    output = "#EXTM3U\n\n"

    try:
        with open(BB_FILE,"r",encoding="utf-8") as f:
            output += re.sub(r'^#EXTM3U','',f.read())+"\n"
    except:
        pass

    # 数字
    output += "\n# 数字\n"
    for n,e,u in cctv:
        output += normalize_group(e,"数字")+"\n"+u+"\n"

    # CHC
    output += "\n# CHC\n"
    for n,e,u in chc:
        e = fix_logo(n,e)
        output += normalize_group(e,"CHC")+"\n"+u+"\n"

    # HK
    output += "\n# HK\n"
    for n,e,u in hk_channels:
        output += normalize_group(e,"HK")+"\n"+u+"\n"

    # TW
    output += "\n# TW\n"
    for n,e,u in tw_channels:
        output += normalize_group(e,"TW")+"\n"+u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(output)

    print("✅ 完成:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
