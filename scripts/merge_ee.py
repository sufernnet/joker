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

TW_SOURCE_GROUP = "•台湾「限制」"

# ===================== ⭐ HK 容灾 =====================

GAT_SOURCE = "https://codeberg.org/Jsnzkpg/Jsnzkpg/raw/branch/Jsnzkpg/Jsnzkpg1.m3u"
GAT_GROUP_NAME = "🔮港澳台直播"

HK_TARGET = [
    "凤凰中文","凤凰资讯","凤凰香港","NOW新闻","翡翠台","TVB",
    "明珠台","HOY","RTHK","无线新闻"
]

# ===================== EXTRA =====================

EXTRA_URLS = [
    "https://tzdr.com/iptv.txt",
    "https://live.kilvn.com/iptv.m3u",
    "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "https://m3u.ibert.me/ycl_iptv.m3u",
]

# ===================== CCTV / CHC =====================

CCTV_TARGET = [
    "世界地理","兵器科技","怀旧剧场","第一剧场",
    "女性时尚","风云足球","风云音乐","央视台球"
]

CHC_TARGET = [
    "CHC影迷电影","CHC家庭影院","CHC动作电影"
]

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png",
    "CHC家庭影院": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC家庭影院.png",
    "CHC动作电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC动作电影.png"
}

# ===================== 下载 =====================

def download(url):
    try:
        return requests.get(url, timeout=15).text
    except:
        return ""

# ===================== 工具 =====================

def clean_name(name):
    return re.sub(r'[\(\[\{（【].*?[\)\]\}）】]|「.*?」','',name).strip()

def parse_m3u(content):
    lines=content.splitlines()
    out=[]
    ext=None
    for l in lines:
        if l.startswith("#EXTINF"):
            ext=l
        elif l.startswith("http") and ext:
            name=clean_name(ext.split(",")[-1])
            out.append((name,ext,l))
    return out

def dedup(data):
    seen=set()
    out=[]
    for n,e,u in data:
        if u not in seen:
            seen.add(u)
            out.append((n,e,u))
    return out

def normalize_group(extinf,group):
    return re.sub(r'group-title="[^"]*"',f'group-title="{group}"',extinf)

# ===================== 测速 =====================

def check(u):
    try:
        t=time.time()
        requests.get(u,timeout=4)
        return u,time.time()-t
    except:
        return u,999

def pick_best(urls):
    best=None
    best_t=999
    with ThreadPoolExecutor(5) as ex:
        for f in as_completed([ex.submit(check,u) for u in urls]):
            u,t=f.result()
            if t<best_t:
                best,best_t=u,t
    return best

# ===================== ⭐ HK 容灾核心 =====================

def load_hk_resilient():

    # 主源
    main=parse_m3u(download(GAT_SOURCE))

    # 备用源
    extra=[]
    for url in EXTRA_URLS:
        extra+=parse_m3u(download(url))

    all_data = main + extra

    result=[]

    for key in HK_TARGET:
        candidates=[(n,e,u) for n,e,u in all_data if key in n]

        if not candidates:
            continue

        best=pick_best([u for _,_,u in candidates])

        for n,e,u in candidates:
            if u==best:
                result.append((n,e,u))
                break

    return dedup(result)

# ===================== CHC =====================

def load_chc():
    raw=download("https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u")
    data=parse_m3u(raw)

    temp=[(n,e,u) for n,e,u in data if "上海" in e and n in CHC_TARGET]

    out=[]
    for name in CHC_TARGET:
        urls=[u for n,e,u in temp if n==name]
        if urls:
            best=pick_best(urls)
            ext=[e for n,e,u in temp if n==name][0]
            if name in LOGO_MAP:
                ext=re.sub(r'tvg-logo="[^"]*"',f'tvg-logo="{LOGO_MAP[name]}"',ext)
            out.append((name,ext,best))
    return out

# ===================== CCTV =====================

def load_cctv():
    data=[]
    for url in EXTRA_URLS:
        data+=parse_m3u(download(url))

    out=[]
    for name in CCTV_TARGET:
        urls=[u for n,e,u in data if n==name]
        if urls:
            best=pick_best(urls)
            ext=[e for n,e,u in data if n==name][0]
            out.append((name,ext,best))
    return out

# ===================== TW（完全不动） =====================

def fetch_tw(content):
    data=parse_m3u(content)
    return [(n,e,u) for n,e,u in data if TW_SOURCE_GROUP in e]

# ===================== 主程序 =====================

def main():

    content=download(SOURCE_URL)

    hk = load_hk_resilient()
    tw = fetch_tw(content)
    cctv = load_cctv()
    chc = load_chc()

    out="#EXTM3U\n\n"

    out+="\n# 数字\n"
    for n,e,u in cctv:
        out+=normalize_group(e,"数字")+"\n"+u+"\n"

    out+="\n# CHC\n"
    for n,e,u in chc:
        out+=normalize_group(e,"CHC")+"\n"+u+"\n"

    out+="\n# HK（容灾）\n"
    for n,e,u in hk:
        out+=normalize_group(e,"HK")+"\n"+u+"\n"

    out+="\n# TW\n"
    for n,e,u in tw:
        out+=normalize_group(e,"TW")+"\n"+u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成（HK已容灾）")

if __name__=="__main__":
    main()
