#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EE IPTV Generator（HK + TW + BB）
"""

import requests
import re
from datetime import datetime

# ===================== 基础配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/4TV.m3u"
OUTPUT_FILE = "EE.m3u"
BB_FILE = "BB.m3u"   # ✅ 恢复

HK_SOURCE_GROUP = "• Juli 「精選」"

# ===================== HK 强制前三 =====================

HK_TOP3 = [
    "鳳凰衛視中文",
    "鳳凰衛視資訊",
    "鳳凰衛視香港",
]

# ===================== HK 排序 =====================

HK_ORDER = [
    "Now新闻","Now体育","Now财经","Now直播",
    "HOY76","HOY77","HOY78",
    "翡翠台","翡翠台4K","明珠台",
    "TVB plus","TVB1","TVBJ1","TVB功夫","TVB千禧经典",
    "TVB娱乐新闻台","TVB星河","无线新闻台",
    "ViuTV","ViuTV6",
    "RHK31","RHK32",
    "CH5综合","CH8综合","CHU综合",
    "CCTV13新闻","八度空间","天映经典",
]

# ===================== 过滤 =====================

REMOVE_YT_IDS = [
    "fN9uYWCjQaw","7j92Myu2wzg","f6Kq93wnaZ8",
    "BOy2xDU1LC8","vr3XyVCR4T0","o_-hSMgpAzs",
]

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


def parse_m3u(content):
    lines = content.splitlines()
    res, extinf, name = [], None, None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            extinf = line
            name = parse_name(line)

        elif line.startswith("http") and extinf and name:
            res.append((name, extinf, line))

    return res


# ===================== HK 排序 =====================

def sort_hk(channels):

    order_map = {n: i for i, n in enumerate(HK_ORDER)}

    def clean(n):
        return re.sub(r'\s*(HD|1080p|720p|4K).*$', '', n).strip()

    def match(a, b):
        return a in b or b in a

    def key(x):
        name = x[0]
        base = clean(name)

        # 🔥 强制前三
        for i, t in enumerate(HK_TOP3):
            if match(t, name):
                return (0, i)

        # 正常排序
        if name in order_map:
            return (1, order_map[name])
        if base in order_map:
            return (1, order_map[base])

        for i, o in enumerate(HK_ORDER):
            if o in name:
                return (1, i)

        return (2, name)

    return sorted(channels, key=key)


# ===================== 主程序 =====================

def main():
    print("下载 HK 源...")
    content = download(SOURCE_URL)

    hk = []
    group = name = extinf = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            extinf = line
            name = parse_name(line)
            group = line.split('group-title="')[1].split('"')[0] if 'group-title="' in line else None

        elif line.startswith("http") and group == HK_SOURCE_GROUP:
            if name and extinf and not is_bad_youtube(line):
                hk.append((name, extinf, line))

    print("下载 TW (4TV)...")
    tw = parse_m3u(download(TW_M3U_URL))

    hk = sort_hk(deduplicate(hk))
    tw = deduplicate(tw)

    print("HK:", len(hk), "TW:", len(tw))

    out = '#EXTM3U\n\n'
    out += f"# Generated: {datetime.now()}\n\n"

    # ✅ BB 拼接（恢复）
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            for l in f:
                if not l.startswith("#EXTM3U"):
                    out += l
        out += "\n"
    except:
        print("⚠️ 未找到 BB.m3u，已跳过")

    # HK
    out += "# HK\n"
    for n, e, u in hk:
        out += normalize_group(e, "HK") + "\n" + u + "\n"

    # TW
    out += "\n# TW\n"
    for n, e, u in tw:
        out += normalize_group(e, "TW") + "\n" + u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("✅ 已生成:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
