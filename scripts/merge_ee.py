#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

SOURCE_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = os.path.join(ROOT_DIR, "EE.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

GAT_SOURCE = "https://codeberg.org/Jsnzkpg/Jsnzkpg/raw/branch/Jsnzkpg/Jsnzkpg1.m3u"
GAT_GROUP_NAME = "🔮港澳台直播"

GAT_TARGET_ORDER = [
    "凤凰中文","凤凰资讯","凤凰香港","NOW新闻","翡翠台","翡翠一台","TVB翡翠","TVB翡翠剧集台",
    "TVBJADE","娱乐新闻","无线新闻","天映频道","千禧经典","明珠台","八度空间",
    "TVB星河","TVBPLUS","TVBJ1","TVB娱乐新闻","TVB黄金华剧","TVB功夫台","TVB1",
    "HOY资讯","HOYTV","HOY77","RTHK31","RTHK32","ROCK_Action","MYTV黄金翡翠",
    "iQIYI","Channel 5","Channel 8","Channel U"
]

EXTRA_URLS = [
    "https://tzdr.com/iptv.txt",
    "https://live.kilvn.com/iptv.m3u",
    "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",
]

CCTV_TARGET = ["世界地理","兵器科技","怀旧剧场","第一剧场","女性时尚"]

CHC_TARGET = ["CHC影迷电影","CHC家庭影院","CHC动作电影"]

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png",
    "CHC家庭影院": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC家庭影院.png",
    "CHC动作电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC动作电影.png"
}

# ===================== download =====================

def download(url):
    try:
        return requests.get(url, timeout=15).text
    except:
        return ""

# ===================== parse =====================

def clean_name(name):
    return re.sub(r'[\(\[\{（【].*?[\)\]\}）】]|「.*?」', '', name).strip()

def parse_m3u(content):
    out = []
    ext = None
    for l in content.splitlines():
        if l.startswith("#EXTINF"):
            ext = l
        elif l.startswith("http") and ext:
            name = clean_name(ext.split(",")[-1])
            out.append((name, ext, l))
    return out

def parse_group(ext):
    m = re.search(r'group-title="([^"]*)"', ext)
    return m.group(1) if m else ""

def dedup(data):
    s = set()
    r = []
    for n,e,u in data:
        if u not in s:
            s.add(u)
            r.append((n,e,u))
    return r

# ===================== speed =====================

def check(u):
    try:
        t = time.time()
        r = requests.get(u, timeout=3, stream=True)
        r.close()
        return u, time.time()-t
    except:
        return u, 999

def pick_best(urls):
    best=None
    bt=999
    with ThreadPoolExecutor(max_workers=20) as ex:
        for f in as_completed([ex.submit(check,u) for u in urls]):
            u,t=f.result()
            if t<bt:
                best,bt=u,t
    return best

# ===================== HK =====================

def load_hk():
    raw = download(GAT_SOURCE)
    data = parse_m3u(raw)

    temp = [(n,e,u) for n,e,u in data if GAT_GROUP_NAME in e]
    temp = dedup(temp)

    out=[]
    for t in GAT_TARGET_ORDER:
        c = [x for x in temp if t in x[0]][:5]
        if not c:
            continue
        best = pick_best([u for _,_,u in c])
        for n,e,u in c:
            if u == best:
                out.append((n,e,u))
                break
    return out

# ===================== CHC（已修复核心问题） =====================

def load_chc():
    raw = download("https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u")
    data = parse_m3u(raw)

    # ✔ 放宽一点匹配（解决你说的“一个都没有”）
    temp = []
    for n,e,u in data:
        if "上海" not in e:
            continue
        for t in CHC_TARGET:
            if t.replace("CHC","") in n or t in n:
                temp.append((t,e,u))

    out=[]
    for name in CHC_TARGET:
        urls=[u for n,e,u in temp if n==name]
        if not urls:
            continue

        best = pick_best(urls)
        ext = [e for n,e,u in temp if n==name][0]

        if name in LOGO_MAP:
            ext = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{LOGO_MAP[name]}"', ext)

        out.append((name,ext,best))

    return out

# ===================== CCTV =====================

def load_cctv():
    data=[]
    for u in EXTRA_URLS:
        raw=download(u)
        if "#EXTINF" in raw:
            data+=parse_m3u(raw)

    out=[]
    for n in CCTV_TARGET:
        urls=[u for x,e,u in data if x==n]
        if urls:
            best=pick_best(urls)
            ext=[e for x,e,u in data if x==n][0]
            out.append((n,ext,best))
    return out

# ===================== BB（修复点） =====================

def load_bb():
    if not os.path.exists(BB_FILE):
        return ""
    try:
        with open(BB_FILE,"r",encoding="utf-8") as f:
            return f.read()
    except:
        return ""

# ===================== TW（不动） =====================

TW_SOURCE_GROUP = "•台湾「限制」"

def fetch_tw(lines):
    parsed=parse_m3u("\n".join(lines))
    temp=[(clean_name(n),e,u) for n,e,u in parsed if TW_SOURCE_GROUP in e]
    temp=dedup(temp)

    used=set()
    out=[]

    for t in TW_TARGET_ORDER:
        for n,e,u in temp:
            if t in n and n not in used:
                out.append((n,e.rsplit(",",1)[0]+","+n,u))
                used.add(n)
                break
    return out

TW_TARGET_ORDER = TW_TARGET_ORDER  # 保持你原来的完整列表

# ===================== main =====================

def main():
    content = download(SOURCE_URL)
    lines = content.splitlines()

    hk = load_hk()
    chc = load_chc()
    cctv = load_cctv()
    tw = fetch_tw(lines)
    bb = load_bb()

    out = "#EXTM3U\n\n"

    if bb:
        out += bb + "\n"

    out += "\n# 数字\n"
    for n,e,u in cctv:
        out += e + "\n" + u + "\n"

    out += "\n# CHC\n"
    for n,e,u in chc:
        out += e + "\n" + u + "\n"

    out += "\n# HK\n"
    for n,e,u in hk:
        out += e + "\n" + u + "\n"

    out += "\n# TW\n"
    for n,e,u in tw:
        out += e + "\n" + u + "\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成")

if __name__=="__main__":
    main()
