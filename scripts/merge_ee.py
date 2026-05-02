#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===================== 路径 =====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

SOURCE_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = os.path.join(ROOT_DIR, "EE.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

# ===================== ⭐ 港澳台精选（替换 HK） =====================

GAT_SOURCE = "https://codeberg.org/Jsnzkpg/Jsnzkpg/raw/branch/Jsnzkpg/Jsnzkpg1.m3u"
GAT_GROUP_NAME = "🔮港澳台直播"

GAT_TARGET_ORDER = [
    "凤凰中文", "凤凰资讯", "凤凰香港", "NOW新闻", "翡翠台", "翡翠一台", "TVB翡翠", "TVB翡翠(马来)", "TVB翡翠剧集台",
    "TVBJADE", "娱乐新闻", "无线新闻", "天映频道", "千禧经典", "明珠台", "八度空间",
    "TVB星河", "TVBPLUS", "TVBJ1", "TVB娱乐新闻", "TVB黄金华剧", "TVB功夫台", "TVB1",
    "HOY资讯", "HOYTV", "HOY77", "RTHK31", "RTHK32", "ROCK_Action", "MYTV黄金翡翠",
    "iQIYI", "Astro AEC", "Astro AOD", "Channel 5", "Channel 8", "Channel U"
]

# ===================== EXTRA =====================

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
    "世界地理", "兵器科技", "怀旧剧场", "第一剧场",
    "女性时尚", "风云足球", "风云音乐", "央视台球"
]

# 👉 MV（替代原CHC）
MV_TARGET_ORDER = [
    "CHC动作电影", "CHC家庭影院", "CHC影迷电影",
    "ROCK Action", "ROCK Xstream", "ROCK Entertainment",
    "HBO王牌", "Cinemax", "Cinemax精选",
    "龙华电影", "龙华经典", "龙华偶像", "龙华日韩"
]

LONGHUA_KEYWORDS = ["龙华电影", "龙华经典", "龙华偶像", "龙华日韩"]

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png",
    "CHC家庭影院": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC家庭影院.png",
    "CHC动作电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC动作电影.png"
}

# ===================== 下载 =====================

def download(url, retry=2):
    headers = {"User-Agent": "Mozilla/5.0"}
    for _ in range(retry):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.text
        except:
            time.sleep(1)
    return ""

# ===================== 工具 =====================

def clean_name(name):
    name = re.sub(r'[\(\[\{（【].*?[\)\]\}）】]', '', name)
    name = re.sub(r'「.*?」', '', name)
    return name.strip()

def parse_name(extinf):
    return clean_name(extinf.split(",", 1)[-1])

def parse_group(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""

def normalize_group(extinf, group):
    if not extinf:
        return f'#EXTINF:-1 group-title="{group}",未知'
    if 'group-title="' in extinf:
        result = re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    else:
        result = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')
    return result if result else extinf

def dedup(data):
    seen = set()
    out = []
    for n, e, u in data:
        if u not in seen:
            seen.add(u)
            out.append((n, e, u))
    return out

# ===================== 解析 =====================

def parse_m3u(content):
    lines = content.splitlines()
    out = []
    ext = None
    for l in lines:
        l = l.strip()
        if l.startswith("#EXTINF"):
            ext = l
        elif l.startswith("http") and ext:
            name = parse_name(ext)
            out.append((name, ext, l))
            ext = None
    return out

# ===================== HK =====================

def load_gat():
    raw = download(GAT_SOURCE)
    if not raw:
        return []
    data = parse_m3u(raw)
    temp = [(clean_name(n), e, u) for n, e, u in data if parse_group(e) == GAT_GROUP_NAME]
    temp = dedup(temp)

    result = []
    for target in GAT_TARGET_ORDER:
        candidates = [x for x in temp if target in x[0]]
        if candidates:
            best = pick_best([u for _, _, u in candidates])
            for n, e, u in candidates:
                if u == best:
                    result.append((n, e, u))
                    break
    return result

# ===================== MV =====================

def load_mv():
    raw = download("https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u")
    if not raw:
        return []

    data = parse_m3u(raw)
    temp = [(n, e, u) for n, e, u in data if parse_group(e) == "综合"]
    temp = [(clean_name(n), e, u) for n, e, u in temp]
    temp = dedup(temp)

    result = []
    for target in MV_TARGET_ORDER:
        candidates = [x for x in temp if target in x[0]]
        if candidates:
            urls = [u for _, _, u in candidates]
            best = pick_best(urls)
            for n, e, u in candidates:
                if u == best:
                    result.append((n, e, u))
                    break

    non_lh = [x for x in result if not any(k in x[0] for k in LONGHUA_KEYWORDS)]
    lh = [x for x in result if any(k in x[0] for k in LONGHUA_KEYWORDS)]

    return non_lh + lh

# ===================== TW =====================

def fetch_tw(lines):
    parsed = parse_m3u("\n".join(lines))
    temp = []
    for n, e, u in parsed:
        if parse_group(e) == TW_SOURCE_GROUP:
            temp.append((clean_name(n), e, u))

    temp = dedup(temp)
    return temp

# ===================== 测速 =====================

def check(url):
    try:
        t0 = time.time()
        r = requests.get(url, timeout=5, stream=True)
        if r.status_code == 200:
            return url, time.time() - t0
    except:
        pass
    return url, 999


def pick_best(urls):
    if not urls:
        return None
    best = None
    best_t = 999
    with ThreadPoolExecutor(max_workers=5) as ex:
        for f in as_completed([ex.submit(check, u) for u in urls]):
            u, t = f.result()
            if t < best_t:
                best, best_t = u, t
    return best

# ===================== 主程序 =====================

def main():
    print("开始生成EE.m3u...")

    content = download(SOURCE_URL)
    if not content:
        print("❌ 无法下载源文件")
        return

    lines = content.splitlines()

    hk = load_gat()
    tw = fetch_tw(lines)
    mv = load_mv()

    out = "#EXTM3U\n\n"

    try:
        with open(BB_FILE, encoding="utf-8") as f:
            for l in f:
                if not l.startswith("#EXTM3U"):
                    out += l
    except Exception as e:
        print(f"⚠️ 无法读取 BB.m3u: {e}")

    if mv:
        out += "\n# MV\n"
        for n, e, u in mv:
            out += normalize_group(e, "MV") + "\n" + u + "\n"

    if hk:
        out += "\n# HK\n"
        for n, e, u in hk:
            out += normalize_group(e, "HK") + "\n" + u + "\n"

    if tw:
        out += "\n# TW\n"
        for n, e, u in tw:
            out += normalize_group(e, "TW") + "\n" + u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成")


if __name__ == "__main__":
    main()
