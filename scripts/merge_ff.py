#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import time
from datetime import datetime

# ===================== 基础配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"
EXTRA_M3U_URL = "https://live.45678888.xyz/sub?kbQyhXwA=m3u"

OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

# ===================== 频道定义 =====================

CCTV_TARGET = [
    "世界地理", "兵器科技", "怀旧剧场", "第一剧场",
    "女性时尚", "风云足球", "风云音乐", "央视台球"
]

CHC_TARGET = [
    "CHC影迷电影", "CHC家庭影院", "CHC动作电影",
    "HC家庭影院", "淘电影", "萌宠TV"
]

# ===================== 工具函数 =====================

def download(url):
    return requests.get(url, timeout=30).text


def parse_name(extinf):
    return extinf.split(",", 1)[-1].strip()


def parse_m3u(content):
    lines = content.splitlines()
    data = []
    ext = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            ext = line
        elif line.startswith("http") and ext:
            name = parse_name(ext)
            data.append((name, ext, line))
    return data


def deduplicate(channels):
    seen = set()
    out = []
    for n, e, u in channels:
        if u not in seen:
            seen.add(u)
            out.append((n, e, u))
    return out


def normalize_group(extinf, group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')


# ===================== 嗅探测速 =====================

def check_speed(url):
    try:
        start = time.time()
        r = requests.get(url, timeout=5, stream=True)
        if r.status_code == 200:
            return time.time() - start
    except:
        pass
    return 999


def pick_best(urls):
    best = None
    best_time = 999

    for u in urls:
        t = check_speed(u)
        if t < best_time:
            best_time = t
            best = u

    return best


# ===================== 主程序 =====================

def main():
    print("下载主源...")
    main_data = parse_m3u(download(SOURCE_URL))

    print("下载 TW...")
    tw_data = parse_m3u(download(TW_M3U_URL))

    print("下载扩展源...")
    extra_data = parse_m3u(download(EXTRA_M3U_URL))

    # ================= HK =================
    hk = []
    for n, e, u in main_data:
        if HK_SOURCE_GROUP in e:
            hk.append((n, e, u))

    hk = deduplicate(hk)

    # ================= TW =================
    tw = deduplicate(tw_data)

    # ================= 央视 =================
    cctv_dict = {}

    for n, e, u in extra_data:
        if n in CCTV_TARGET:
            cctv_dict.setdefault(n, []).append((e, u))

    cctv_final = []
    for name in CCTV_TARGET:
        if name in cctv_dict:
            best = pick_best([u for _, u in cctv_dict[name]])
            ext = cctv_dict[name][0][0]
            cctv_final.append((name, ext, best))

    # ================= CHC =================
    chc_dict = {}

    for n, e, u in extra_data:
        if n in CHC_TARGET:
            chc_dict.setdefault(n, []).append((e, u))

    chc_final = []
    for name in CHC_TARGET:
        if name in chc_dict:
            best = pick_best([u for _, u in chc_dict[name]])
            ext = chc_dict[name][0][0]
            chc_final.append((name, ext, best))

    # ================= 输出 =================

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out = "#EXTM3U\n\n"
    out += f"# 生成时间 {now}\n\n"

    # BB
    try:
        with open(BB_FILE, encoding="utf-8") as f:
            for l in f:
                if not l.startswith("#EXTM3U"):
                    out += l
        out += "\n"
    except:
        pass

    # HK
    out += "# HK\n"
    for n, e, u in hk:
        out += normalize_group(e, "HK") + "\n" + u + "\n"

    # TW
    out += "\n# TW\n"
    for n, e, u in tw:
        out += normalize_group(e, "TW") + "\n" + u + "\n"

    # 浙江后插入 CHC（简单策略：直接插入新组）
    out += "\n# CHC\n"
    for n, e, u in chc_final:
        out += normalize_group(e, "CHC") + "\n" + u + "\n"

    # 央视（最后）
    out += "\n# 央视补充\n"
    for n, e, u in cctv_final:
        out += normalize_group(e, "央视") + "\n" + u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成：Gather.m3u")


if __name__ == "__main__":
    main()
