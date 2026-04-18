#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===================== 路径 =====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

SOURCE_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

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
    "世界地理","兵器科技","怀旧剧场","第一剧场",
    "女性时尚","风云足球","风云音乐","央视台球"
]

# ✅ 修复这里（删除 HC家庭影院）
CHC_TARGET = [
    "CHC影迷电影","CHC家庭影院","CHC动作电影"
]

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png"
}

REMOVE_YT_IDS = [
    "fN9uYWCjQaw","7j92Myu2wzg","f6Kq93wnaZ8",
    "BOy2xDU1LC8","vr3XyVCR4T0","o_-hSMgpAzs",
]

# ===================== TW 白名单 =====================

TW_TARGET_ORDER = [
    "Love Nature","亞洲旅遊","民視第一台","民視台灣台","民視","華視",
    "寰宇新聞","寰宇新聞台灣台","寰宇財經","三立綜合台",
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

# ===================== 下载 =====================

def download(url, retry=2):
    headers={"User-Agent":"Mozilla/5.0"}
    for i in range(retry):
        try:
            r=requests.get(url,headers=headers,timeout=15)
            if r.status_code==200:
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
    return clean_name(extinf.split(",",1)[-1])

def parse_group(extinf):
    m=re.search(r'group-title="([^"]*)"',extinf)
    return m.group(1) if m else ""

def normalize_group(extinf,group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"',f'group-title="{group}"',extinf)
    return extinf.replace("#EXTINF:-1",f'#EXTINF:-1 group-title="{group}"')

def dedup(data):
    seen=set()
    out=[]
    for n,e,u in data:
        if u not in seen:
            seen.add(u)
            out.append((n,e,u))
    return out

# ===================== 解析 =====================

def parse_m3u(content):
    lines=content.splitlines()
    out=[]
    ext=None
    for l in lines:
        l=l.strip()
        if l.startswith("#EXTINF"):
            ext=l
        elif l.startswith("http") and ext:
            name=parse_name(ext)
            out.append((name,ext,l))
    return out

def parse_txt(content):
    out=[]
    for l in content.splitlines():
        if "," in l and "http" in l:
            name,url=l.split(",",1)
            name=clean_name(name)
            ext=f'#EXTINF:-1 group-title="未知",{name}'
            out.append((name,ext,url))
    return out

# ===================== ⭐ CHC（只从上海提取） =====================

def load_chc_from_shanghai():
    url = "https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u"
    raw = download(url)
    data = parse_m3u(raw)

    result = []

    for n, e, u in data:
        if parse_group(e) != "上海":
            continue

        m = re.search(r'tvg-name="([^"]+)"', e)
        if not m:
            continue

        tvg_name = m.group(1).strip()

        if tvg_name in CHC_TARGET:
            result.append((tvg_name, e, u))

    return result

# ===================== EXTRA =====================

def load_extra():
    data=[]
    for url in EXTRA_URLS:
        raw=download(url)
        if not raw:
            continue
        if "#EXTINF" in raw:
            data+=parse_m3u(raw)
        else:
            data+=parse_txt(raw)
    return data

# ===================== 测速 =====================

def check(url):
    try:
        t0=time.time()
        r=requests.get(url,timeout=5,stream=True)
        if r.status_code==200:
            return url,time.time()-t0
    except:
        pass
    return url,999

def pick_best(urls):
    best=None
    best_t=999
    with ThreadPoolExecutor(max_workers=5) as ex:
        for f in as_completed([ex.submit(check,u) for u in urls]):
            u,t=f.result()
            if t<best_t:
                best,best_t=u,t
    return best

# ===================== TW =====================

def fetch_tw(lines):
    parsed=parse_m3u("\n".join(lines))

    temp=[]
    for n,e,u in parsed:
        if parse_group(e)==TW_SOURCE_GROUP:
            temp.append((clean_name(n),e,u))

    temp=dedup(temp)

    result=[]
    used=set()

    for target in TW_TARGET_ORDER:
        for n,e,u in temp:
            if target in n and n not in used:
                new_e = e.rsplit(',', 1)[0] + ',' + n
                result.append((n, new_e, u))
                used.add(n)
                break
    return result

# ===================== 主程序 =====================

def main():

    content=download(SOURCE_URL)
    lines=content.splitlines()

    main_data=parse_m3u(content)

    hk=[x for x in main_data if HK_SOURCE_GROUP in x[1]]
    hk=dedup(hk)

    tw=fetch_tw(lines)

    custom_extinf = '#EXTINF:-1 tvg-id="中天新聞台" tvg-name="中天新聞台" tvg-logo="https://epg.iill.top/logo/中天新聞台.png" http-user-agent="okhttp/1.9.89",中天新聞台'
    custom_url = "https://v.iill.top/4gtv/4gtv-4gtv009/index.m3u8"
    custom_item = ("中天新聞台", custom_extinf, custom_url)

    insert_index = -1
    for i, (name, _, _) in enumerate(tw):
        if name == "民視":
            insert_index = i + 1
            break
    if insert_index != -1:
        tw.insert(insert_index, custom_item)
    else:
        tw.append(custom_item)

    extra=load_extra()

    # CCTV
    cctv_map={}
    for n,e,u in extra:
        if n in CCTV_TARGET:
            cctv_map.setdefault(n,[]).append((e,u))

    cctv=[]
    for name in CCTV_TARGET:
        if name in cctv_map:
            best=pick_best([u for _,u in cctv_map[name]])
            cctv.append((name,cctv_map[name][0][0],best))

    # ⭐ CHC（只用上海源）
    chc_raw = load_chc_from_shanghai()

    chc_map={}
    for n,e,u in chc_raw:
        chc_map.setdefault(n,[]).append((e,u))

    chc=[]
    for name in CHC_TARGET:
        if name in chc_map:
            best=pick_best([u for _,u in chc_map[name]])
            ext=chc_map[name][0][0]
            if name in LOGO_MAP:
                ext=re.sub(r'tvg-logo="[^"]*"',f'tvg-logo="{LOGO_MAP[name]}"',ext)
            chc.append((name,ext,best))

    # ===================== 输出 =====================

    out="#EXTM3U\n\n"

    try:
        with open(BB_FILE,encoding="utf-8") as f:
            for l in f:
                if not l.startswith("#EXTM3U"):
                    out+=l
    except:
        pass

    out+="\n# 数字\n"
    for n,e,u in cctv:
        out+=normalize_group(e,"数字")+"\n"+u+"\n"

    out+="\n# CHC\n"
    for n,e,u in chc:
        out+=normalize_group(e,"CHC")+"\n"+u+"\n"

    out+="\n# HK\n"
    for n,e,u in hk:
        out+=normalize_group(e,"HK")+"\n"+u+"\n"

    out+="\n# TW\n"
    for n,e,u in tw:
        out+=normalize_group(e,"TW")+"\n"+u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成")

if __name__=="__main__":
    main()
