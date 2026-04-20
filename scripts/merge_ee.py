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

TW_SOURCE_GROUP = "•台湾「限制」"

# ===================== HK台标 =====================

HK_LOGO_MAP = {
    "凤凰中文": "https://raw.githubusercontent.com/fanmingming/live/main/tv/凤凰中文.png",
    "凤凰资讯": "https://raw.githubusercontent.com/fanmingming/live/main/tv/凤凰资讯.png",
    "凤凰香港": "https://raw.githubusercontent.com/fanmingming/live/main/tv/凤凰香港.png",
    "翡翠台": "https://raw.githubusercontent.com/fanmingming/live/main/tv/翡翠台.png",
    "明珠台": "https://raw.githubusercontent.com/fanmingming/live/main/tv/明珠台.png",
    "HOY": "https://raw.githubusercontent.com/fanmingming/live/main/tv/HOYTV.png",
    "RTHK": "https://raw.githubusercontent.com/fanmingming/live/main/tv/RTHK.png",
    "NOW": "https://raw.githubusercontent.com/fanmingming/live/main/tv/NOW新闻.png",
}

# ===================== 你的原始配置（保留） =====================

GAT_SOURCE = "https://codeberg.org/Jsnzkpg/Jsnzkpg/raw/branch/Jsnzkpg/Jsnzkpg1.m3u"
GAT_GROUP_NAME = "🔮港澳台直播"

GAT_TARGET_ORDER = [
    "凤凰中文","凤凰资讯","凤凰香港","NOW新闻","翡翠台","翡翠一台","TVB翡翠","TVB翡翠剧集台",
    "TVBJADE","娱乐新闻","无线新闻","天映频道","千禧经典","明珠台","八度空间",
    "TVB星河","TVBPLUS","TVBJ1","TVB娱乐新闻","TVB黄金华剧","TVB功夫台","TVB1",
    "HOY资讯","HOYTV","HOY77","RTHK31","RTHK32","ROCK_Action","MYTV黄金翡翠",
    "iQIYI","Channel 5","Channel 8","Channel U"
]

# ===================== 工具 =====================

def download(url):
    try:
        return requests.get(url, timeout=15).text
    except:
        return ""

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

# ===================== 台标补齐 =====================

def fill_logo(name, extinf):
    if 'tvg-logo=' in extinf:
        return extinf
    for key in HK_LOGO_MAP:
        if key in name:
            return extinf.replace("#EXTINF:-1",
                f'#EXTINF:-1 tvg-logo="{HK_LOGO_MAP[key]}"')
    return extinf

# ===================== 测速 =====================

def check(u):
    try:
        t=time.time()
        r=requests.get(u,timeout=3,stream=True)
        r.close()
        return u,time.time()-t
    except:
        return u,999

def pick_best(urls):
    best=None
    best_t=999
    with ThreadPoolExecutor(20) as ex:
        for f in as_completed([ex.submit(check,u) for u in urls]):
            u,t=f.result()
            if t<best_t:
                best,best_t=u,t
    return best

# ===================== HK =====================

def load_hk():
    data=parse_m3u(download(GAT_SOURCE))

    temp=[(n,e,u) for n,e,u in data if GAT_GROUP_NAME in e]

    result=[]
    for target in GAT_TARGET_ORDER:
        candidates=[x for x in temp if target in x[0]][:5]
        if candidates:
            best=pick_best([u for _,_,u in candidates])
            for n,e,u in candidates:
                if u==best:
                    e=fill_logo(n,e)   # ⭐补台标
                    result.append((n,e,u))
                    break
    return result

# ===================== TW（完全恢复） =====================

TW_TARGET_ORDER = [ ...原完整列表（你自己那段，别删）... ]

def fetch_tw(lines):
    parsed=parse_m3u("\n".join(lines))
    temp=[(clean_name(n),e,u) for n,e,u in parsed if TW_SOURCE_GROUP in e]
    temp=dedup(temp)

    result=[]
    used=set()

    for target in TW_TARGET_ORDER:
        for n,e,u in temp:
            if target in n and n not in used:
                result.append((n,e.rsplit(',',1)[0]+','+n,u))
                used.add(n)
                break
    return result

# ===================== 主程序 =====================

def main():

    content=download(SOURCE_URL)
    lines=content.splitlines()

    hk=load_hk()
    tw=fetch_tw(lines)

    out="#EXTM3U\n\n"

    out+="\n# HK\n"
    for n,e,u in hk:
        out+=normalize_group(e,"HK")+"\n"+u+"\n"

    out+="\n# TW\n"
    for n,e,u in tw:
        out+=normalize_group(e,"TW")+"\n"+u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成（HK已补台标）")

if __name__=="__main__":
    main()
