#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DD.m3u 构建系统（终极融合版）
包含：
- BB.m3u 合并
- HK 抓取
- TW 限制抓取
- 體育 Relay 抓取
- 自动去 Relay/FainTV/ofiii/4gTV
- 自动频道合并
- 自动分组排序
"""

import requests
from datetime import datetime
import re

# ================= 配置 =================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
HK_SOURCE_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
TW_SOURCE_URL = "https://yang.sufern001.workers.dev"

OUTPUT_FILE = "DD.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

GROUP_HK = "HK"
GROUP_TW = "TW"
GROUP_SPORTS = "SPORTS"

REMOVE_KEYWORDS = ["FainTV", "ofiii", "4gTV", "Relay"]

SPORTS_KEYWORDS = ["博斯", "緯來體育", "NOW体育", "Now体育"]

# 需要从HK移到TW的台湾频道精确列表（完整版）
TW_CHANNELS_IN_HK = [
    # 中视系列
    "中视",
    "中视新闻",
    "中视经典",
    "中视菁采",
    
    # 华视系列
    "华视",
    "华视教育体育文化",
    "华视新闻",
    
    # 台视系列
    "台视",
    "台视新闻",
    "台视财经",
    "臺視綜合",
    
    # 民视系列
    "民视",
    "民視",
    "民视台湾",
    "民视新闻",
    "民视第一",
    "民視影劇",
    "民視綜藝",
    
    # 公视系列
    "公视台语",
    
    # 龙华系列
    "龍華電影",
    "龙华偶像",
    "龙华戏剧",
    "龙华日韩",
    "龙华电影",
    "龙华经典",
    "龍華洋片",
    
    # 其他
    "唐NTD",
    "唐人卫视"
]

REMOVE_CHANNELS = [
    "東森購物","少儿频道","半島國際新聞","兒童頻道",
    "MOMO運動綜合","LiveABC互動英語頻道",
    "GINX Esports TV","DW德國之聲",
    "DreamWorks 夢工廠動畫","CLASSICA 古典樂",
    "Arirang TV","Bloomberg TV",
    "ELTA生活英語","ETtoday綜合","Global Trekker",
    "INULTRA","Pet Club TV","Smart知識",
    "SBN 全球財經","大愛電視","好消息","新唐人亞太"
]

HK_ORDER = [
    "凤凰中文","凤凰资讯","凤凰香港台",
    "Now新闻","Now体育","Now财经","Now直播",
    "HOY76","HOY77","HOY78",
    "翡翠台","翡翠台4K","明珠台",
    "TVB plus","TVB1","TVBJ1","TVB功夫",
    "TVB千禧经典","TVB娱乐新闻台","TVB星河",
    "无线新闻台",
    "ViuTV","ViuTV6",
    "RHK31","RHK32",
    "CH5综合","CH8综合","CHU综合"
]

# ================= 下载 =================

def download(url):
    try:
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except:
        return ""

# ================= 名称标准化 =================

def normalize_name(name):
    name = name.strip()

    for kw in REMOVE_KEYWORDS:
        name = re.sub(rf'「?\s*{kw}\s*」?', '', name, flags=re.IGNORECASE)

    name = re.sub(r'台$', '', name)
    name = re.sub(r'\d+$', '', name)
    name = re.sub(r'\s+', ' ', name)

    return name.strip()

def should_remove(name):
    for kw in REMOVE_CHANNELS:
        if kw.lower() in name.lower():
            return True
    return False

def determine_group(name, default_group):
    # 先检查是否为体育频道
    for kw in SPORTS_KEYWORDS:
        if kw.lower() in name.lower():
            return GROUP_SPORTS
    return default_group

# ================= 提取 BB =================

def extract_bb(content):
    lines = content.splitlines()
    channels = []

    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            name = lines[i].split(",",1)[1].strip()
            if i+1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith("http"):
                    # 读取原分组
                    m = re.search(r'group-title="([^"]*)"', lines[i])
                    group = m.group(1) if m else ""
                    channels.append((name,url,group))
    return channels

# ================= 提取 HK =================

def extract_hk(content):
    lines = content.splitlines()
    channels = []
    in_section = False

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        if not in_section and "港澳台直播" in raw:
            in_section = True
            continue

        if in_section:
            if "#genre#" in raw and "港澳台直播" not in raw:
                break

            if "," in raw and "://" in raw:
                name, url = raw.split(",", 1)
                name = name.strip()
                url = url.strip()
                
                # 判断频道是否在台湾频道列表中
                is_tw_channel = False
                for tw_name in TW_CHANNELS_IN_HK:
                    if tw_name.lower() in name.lower() or name.lower() in tw_name.lower():
                        is_tw_channel = True
                        break
                
                # 如果是台湾频道，分组为TW，否则为HK
                group = GROUP_TW if is_tw_channel else GROUP_HK
                channels.append((name, url, group))
    return channels

# ================= 提取 TW + 体育 Relay =================

def extract_tw(content):
    lines = content.splitlines()
    channels = []

    for i in range(len(lines)):
        line = lines[i].strip()

        if line.startswith("#EXTINF"):

            if 'group-title="•台湾「限制」"' in line:
                name = line.split(",",1)[1].strip()
                url = lines[i+1].strip()
                channels.append((name,url,GROUP_TW))

            if 'group-title="•體育「Relay」"' in line:
                name = line.split(",",1)[1].strip()
                url = lines[i+1].strip()
                channels.append((name,url,GROUP_SPORTS))

    return channels

# ================= 合并 =================

def merge_channels(channel_list):
    merged = {}

    for name,url,group in channel_list:

        normalized = normalize_name(name)
        if should_remove(normalized):
            continue

        key = normalized.lower()
        final_group = determine_group(normalized, group)

        if key not in merged:
            merged[key] = {
                "name": normalized,
                "group": final_group if final_group else group,
                "urls": set()
            }

        merged[key]["urls"].add(url)

    return merged

# ================= 排序 =================

def hk_weight(name):
    for idx,key in enumerate(HK_ORDER):
        if key.lower() in name.lower():
            return idx
    return 999

def tw_weight(name):
    # 台湾频道排序
    tw_order = [
        "中视", "中视新闻", "中视经典", "中视菁采",
        "华视", "华视新闻", "华视教育体育文化",
        "台视", "台视新闻", "台视财经", "臺視綜合",
        "民视", "民視", "民视新闻", "民视第一", "民视台湾", "民視影劇", "民視綜藝",
        "公视", "公视台语",
        "龍華電影", "龙华偶像", "龙华戏剧", "龙华日韩", "龙华电影", "龙华经典", "龍華洋片",
        "唐NTD", "唐人卫视"
    ]
    
    for idx, key in enumerate(tw_order):
        if key in name:
            return idx
    return 999

# ================= 主流程 =================

def main():

    bb = download(BB_URL)
    hk = download(HK_SOURCE_URL)
    tw = download(TW_SOURCE_URL)

    channels = (
        extract_bb(bb) +
        extract_hk(hk) +
        extract_tw(tw)
    )

    merged = merge_channels(channels)

    hk_list, tw_list, sports_list = [],[],[]

    for data in merged.values():
        if data["group"] == GROUP_HK:
            hk_list.append(data)
        elif data["group"] == GROUP_TW:
            tw_list.append(data)
        elif data["group"] == GROUP_SPORTS:
            sports_list.append(data)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# 生成时间: {timestamp}\n\n"

    # HK
    output += "\n### HK ###\n"
    for item in sorted(hk_list,key=lambda x:(hk_weight(x["name"]),x["name"].lower())):
        output += f'\n#EXTINF:-1 group-title="HK",{item["name"]}\n'
        for u in sorted(item["urls"]):
            output += u+"\n"

    # TW
    output += "\n### TW ###\n"
    for item in sorted(tw_list,key=lambda x:(tw_weight(x["name"]),x["name"].lower())):
        output += f'\n#EXTINF:-1 group-title="TW",{item["name"]}\n'
        for u in sorted(item["urls"]):
            output += u+"\n"

    # SPORTS
    output += "\n### SPORTS ###\n"
    for item in sorted(sports_list,key=lambda x:x["name"].lower()):
        output += f'\n#EXTINF:-1 group-title="SPORTS",{item["name"]}\n'
        for u in sorted(item["urls"]):
            output += u+"\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(output)

    print("🚀 DD.m3u 终极融合完成")

if __name__ == "__main__":
    main()
