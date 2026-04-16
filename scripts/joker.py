#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gather IPTV Generator
（仅修改 TW 来源 + 自动测速选最快）
"""

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
TW_API_URL = "http://192.168.100.1:50008/channel?type=m3u&token=iawXxRTd4cKZioJfMdbjCLlGuvgQx6tcHLnrUhQHtNadRSpDZ3EvBaSDVVAhaARZ"

OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"

# ===================== 精准剔除 YouTube =====================

REMOVE_YT_IDS = [
    "fN9uYWCjQaw","7j92Myu2wzg","f6Kq93wnaZ8",
    "BOy2xDU1LC8","vr3XyVCR4T0","o_-hSMgpAzs",
]

# ===================== CCTV / CHC =====================

TARGET_CCTV = {
    "CCTV世界地理","CCTV兵器科技","CCTV女性时尚",
    "CCTV怀旧剧场","CCTV文化精品","CCTV第一剧场",
    "CCTV风云足球","CCTV风云音乐","CCTV央视台球"
}

TARGET_CCTV_ORDER = list(TARGET_CCTV)

TARGET_CHC = {
    "CHC动作电影","CHC高清电影","CHC家庭电影",
    "CHC家庭影院","CHC影迷电影"
}

TARGET_CHC_ORDER = list(TARGET_CHC)

CCTV_SOURCES = [
    "https://tzdr.com/iptv.txt",
    "https://live.kilvn.com/iptv.m3u",
    "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "http://175.178.251.183:6689/live.m3u",
    "https://m3u.ibert.me/ycl_iptv.m3u",
    "https://live.45678888.xyz/sub?kbQyhXwA=m3u"
]

TEST_TIMEOUT = 10

# ===================== 工具函数 =====================

def download(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def is_bad_youtube(url):
    return any(i in url for i in REMOVE_YT_IDS)

def deduplicate(channels):
    seen, result = set(), []
    for name, extinf, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, extinf, url))
    return result

def normalize_group(extinf, group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"', 1)

def parse_name(extinf):
    return extinf.split(",", 1)[1].strip() if "," in extinf else ""

def parse_group(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""

def parse_m3u_full(content):
    lines = content.splitlines()
    res = []
    extinf = None
    for line in lines:
        line=line.strip()
        if line.startswith("#EXTINF"):
            extinf=line
        elif line.startswith("http") and extinf:
            res.append((parse_name(extinf), extinf, line))
    return res

# ===================== 测速 =====================

async def test_stream(session, url):
    start = time.time()
    try:
        async with session.get(url, timeout=TEST_TIMEOUT) as r:
            if r.status == 200:
                return True, time.time()-start
    except:
        pass
    return False, None

# ===================== ⭐ TW核心逻辑 =====================

async def fetch_best_tw_channels():
    print("抓取 TW 接口...")

    try:
        content = download(TW_API_URL)
    except Exception as e:
        print("TW 获取失败:", e)
        return []

    channels = parse_m3u_full(content)

    # 按频道分组
    group_map = {}
    for name, extinf, url in channels:
        group_map.setdefault(name.strip(), []).append((extinf, url))

    result = []

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:

        for name, items in group_map.items():
            tasks = [test_stream(session, u) for _, u in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            best_url = None
            best_time = None

            for r, (extinf, url) in zip(results, items):
                if isinstance(r, Exception):
                    continue
                ok, t = r
                if ok and (best_time is None or t < best_time):
                    best_time = t
                    best_url = url

            # 兜底
            if not best_url:
                best_url = items[0][1]

            result.append((name, items[0][0], best_url))

    print("TW频道数:", len(result))
    return result

# ===================== 主程序 =====================

def main():
    print("下载源...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    hk_channels = []
    extinf = group = name = None

    for line in lines:
        line=line.strip()
        if line.startswith("#EXTINF"):
            extinf=line
            group=parse_group(line)
            name=parse_name(line)
        elif line.startswith("http"):
            if group==HK_SOURCE_GROUP and not is_bad_youtube(line):
                hk_channels.append((name, extinf, line))

    hk_channels = deduplicate(hk_channels)

    # ⭐ TW（唯一修改点）
    tw_channels = asyncio.run(fetch_best_tw_channels())

    output = '#EXTM3U\n\n'

    # BB
    try:
        with open(BB_FILE,"r",encoding="utf-8") as f:
            output += re.sub(r'^#EXTM3U','',f.read()) + "\n"
    except:
        pass

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
