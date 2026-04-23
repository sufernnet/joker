#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===================== 配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"

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

# ⭐ 新增 MYTV 源
MYTV_URL = "https://php.946985.filegear-sg.me/jackTV.m3u"

OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

CCTV_TARGET = [
    "世界地理","兵器科技","怀旧剧场","第一剧场",
    "女性时尚","风云足球","风云音乐","央视台球"
]

CHC_TARGET = [
    "CHC影迷电影","CHC家庭影院","CHC动作电影"
]

# ⭐ 目标频道
MYTV_TARGET = ["Love Nature 4K", "AXN", "PopC", "tvN"]

BAD_KEYWORDS = ["测试", "购物", "广告"]

# ===================== 台标修复 =====================

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png",
    "CHC家庭影院": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC家庭影院.png",
    "CHC动作电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC动作电影.png"
}

def fix_logo(name, extinf):
    if name in LOGO_MAP:
        logo = LOGO_MAP[name]
        if 'tvg-logo="' in extinf:
            extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{logo}"')
    return extinf

# ===================== 下载 =====================

def download(url, retry=2):
    headers = {"User-Agent": "Mozilla/5.0"}
    for i in range(retry):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.text
        except:
            print(f"重试 {i+1} 失败: {url}")
    print(f"跳过: {url}")
    return ""

# ===================== 解析 =====================

def parse_name(extinf):
    return extinf.split(",", 1)[-1].strip()

def parse_group(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""

def parse_m3u(content):
    lines = content.splitlines()
    data, ext = [], None

    for l in lines:
        l = l.strip()
        if l.startswith("#EXTINF"):
            ext = l
        elif l.startswith("http") and ext:
            name = parse_name(ext)
            if not any(x in name for x in BAD_KEYWORDS):
                data.append((name, ext, l))
    return data

# ===================== ⭐ MYTV 提取 =====================

def load_mytv():
    raw = download(MYTV_URL)
    data = parse_m3u(raw)

    result = {}

    for n, e, u in data:
        if parse_group(e) != "MYTV":
            continue

        for target in MYTV_TARGET:
            if target.lower() in n.lower():
                result[target] = u

    return result

# ===================== 工具 =====================

def dedup(data):
    seen, out = set(), []
    for n, e, u in data:
        if u not in seen:
            seen.add(u)
            out.append((n, e, u))
    return out

def set_group(extinf, group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')

# ===================== 主程序 =====================

def main():
    print("主源...")
    main_data = parse_m3u(download(SOURCE_URL))

    print("TW...")
    tw_data = parse_m3u(download(TW_M3U_URL))

    print("MYTV...")
    mytv_map = load_mytv()

    hk = dedup([x for x in main_data if HK_SOURCE_GROUP in x[1]])
    tw = dedup(tw_data)

    # ⭐ 构造插入频道（强制模板格式）
    mytv_channels = []
    for name in MYTV_TARGET:
        if name in mytv_map:
            url = mytv_map[name]

            ext = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" tvg-logo="" group-title="HK",{name}'
            mytv_channels.append((name, ext, url))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out = "#EXTM3U\n\n"
    out += f"# 更新时间 {now}\n\n"

    try:
        with open(BB_FILE, encoding="utf-8") as f:
            for l in f:
                if not l.startswith("#EXTM3U"):
                    out += l
        out += "\n"
    except:
        pass

    # ===================== HK（插入逻辑）=====================

    out += "\n# HK\n"

    inserted = False

    for n, e, u in hk:
        out += set_group(e, "HK") + "\n" + u + "\n"

        # ⭐ 在凤凰香港后插入
        if not inserted and "鳳凰衛視·香港" in n:
            for cn, ce, cu in mytv_channels:
                out += ce + "\n" + cu + "\n"
            inserted = True

    # 如果没找到锚点，就追加
    if not inserted:
        for cn, ce, cu in mytv_channels:
            out += ce + "\n" + cu + "\n"

    # ===================== TW =====================

    out += "\n# TW\n"
    for n, e, u in tw:
        out += set_group(e, "TW") + "\n" + u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成")

if __name__ == "__main__":
    main()
