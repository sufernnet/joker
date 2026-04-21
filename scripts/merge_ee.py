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

CHC_TARGET = [
    "CHC影迷电影", "CHC家庭影院", "CHC动作电影"
]

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png",
    "CHC家庭影院": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC家庭影院.png",
    "CHC动作电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC动作电影.png"
}

# ===================== 频道台标替换（仅限HK分组） =====================

# 定义台标的映射
HK_LOGO_MAP = {
    "凤凰中文": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/凤凰中文.png",
    "凤凰资讯": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/凤凰资讯.png",
    "凤凰香港": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/凤凰香港.png",
    "NOW新闻": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/NOW新闻.png",
    "翡翠台": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/翡翠.png",
    "翡翠一台(TVB1)": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/翡翠一台(TVB1).png",
    "TVB翡翠剧集台(TVBDRAMA)": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/TVB翡翠剧集台(TVBDRAMA).png",
    "TVBJADE(HD)": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/翡翠.png",
    "娱乐新闻": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/娱乐新闻.png",
    "无线新闻": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/无线新闻.png",
    "天映频道马来西亚": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/天映频道马来西亚.png",
    "千禧经典": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/千禧经典.png",
    "八度空间": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/八度空间.png",
    "TVB星河": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/TVB星河.png",
    "TVBPLUS": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/TVBPLUS.png",
    "TVBJ1": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/TVBJ1.png",
    "TVB娱乐新闻": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/TVB娱乐新闻.png",
    "TVB黄金华剧": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/黄金华剧.png",
    "TVB功夫台": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/TVB功夫.png",
    "TVB1": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/翡翠一台(TVB1).png",
    "HOY资讯": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/HOYTV资讯.png",
    "HOYTV": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/HOYTV.png",
    "HOY77": "https://epg.112114.xyz/logo/HOY77.png",
    "RTHK31": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/RTHK31.png",
    "RTHK32": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/RTHK32.png",
    "ROCK_Action": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/ROCKACTION.png",
    "MYTV黄金翡翠": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/黄金华剧.png",
    "iQIYI": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/爱奇艺.png",
    "Astro AEC": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/Astro_AEC.png",
    "Astro AOD": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/Astro_AOD.png",
    "Channel 5": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/Channel 5.png",
    "Channel 8": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/Channel 8.png",
    "Channel U": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/Channel U.png"
}

# ===================== 下载 =====================

def download(url, retry=2):
    headers={"User-Agent":"Mozilla/5.0"}
    for _ in range(retry):
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

# ===================== ⭐ 港澳台精选 =====================

def load_gat():
    raw = download(GAT_SOURCE)
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
                    # 检查是否为HK分组，并替换台标
                    if n in HK_LOGO_MAP:
                        new_ext = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{HK_LOGO_MAP[n]}"', e)
                        result.append((n, new_ext, u))
                    else:
                        result.append((n, e, u))
                    break
    return result

# ===================== CHC =====================

def load_chc():
    raw=download("https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u")
    data=parse_m3u(raw)

    temp=[(n,e,u) for n,e,u in data if parse_group(e)=="上海" and n in CHC_TARGET]

    chc=[]
    for name in CHC_TARGET:
        urls=[u for n,e,u in temp if n==name]
        if urls:
            best=pick_best(urls)
            ext=[e for n,e,u in temp if n==name][0]
            if name in LOGO_MAP:
                ext=re.sub(r'tvg-logo="[^"]*"',f'tvg-logo="{LOGO_MAP[name]}"',ext)
            chc.append((name,ext,best))
    return chc

# ===================== CCTV =====================

def load_cctv():
    data=[]
    for url in EXTRA_URLS:
        raw=download(url)
        if "#EXTINF" in raw:
            data+=parse_m3u(raw)
        else:
            data+=parse_txt(raw)

    result=[]
    for name in CCTV_TARGET:
        urls=[u for n,e,u in data if n==name]
        if urls:
            best=pick_best(urls)
            ext=[e for n,e,u in data if n==name][0]
            result.append((name,ext,best))
    return result

# ===================== TW（完全按照参考代码修改） =====================

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

# ===================== 主程序 =====================

def main():

    content=download(SOURCE_URL)
    lines=content.splitlines()

    hk = load_gat()     # ⭐ 替换 HK
    tw = fetch_tw(lines)

    # 中天新聞台插入（完全对齐参考代码）
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

    cctv = load_cctv()
    chc = load_chc()

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
