#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DD.m3u 构建系统（终极融合版）
包含：
- BB.m3u 合并（原样保留在最前面）
- HK 抓取（从EE.m3u）
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
HK_SOURCE_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/EE.m3u"  # 使用EE.m3u作为HK源
TW_SOURCE_URL = "https://yang.sufern001.workers.dev"

OUTPUT_FILE = "DD.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

GROUP_HK = "HK"
GROUP_TW = "TW"
GROUP_SPORTS = "SPORTS"

REMOVE_KEYWORDS = ["FainTV", "ofiii", "4gTV", "Relay"]

SPORTS_KEYWORDS = ["博斯", "緯來體育", "NOW体育", "Now体育"]

# 台湾电视频道关键词（全面版）
TW_CHANNEL_KEYWORDS = [
    # 无线台
    "台視", "台视", "ttv",
    "中視", "中视", "ctv",
    "華視", "华视", "cts",
    "民視", "民视", "ftv",
    "公視", "公视", "pts",
    
    # 新闻台
    "新聞", "新闻", "news",
    
    # 综合/综艺
    "綜合", "综合", "綜藝", "综艺", "影劇", "影剧", "第一",
    
    # 龙华系列
    "龍華", "龙华", "龍華電影", "龙华电影", "龍華洋片", "龙华日韩", 
    "龙华戏剧", "龙华偶像", "龙华经典",
    
    # 其他台湾频道
    "唐NTD", "唐人卫视",
    
    # 常见的台湾频道名称
    "東森", "东森", "中天", "TVBS", "三立", "非凡", "壹電視", "壹电视",
    "寰宇", "愛爾達", "爱尔达", "緯來", "纬来"
]

# 香港频道关键词（用于确认哪些应该留在HK）
HK_CHANNEL_KEYWORDS = [
    "翡翠", "明珠", "J2", "TVB", "無線", "无线",
    "ViuTV", "ViuTV6", "Now", "HOY", "有線", "有线",
    "鳳凰", "凤凰", "港台電視", "RHK", "CH"
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
    except Exception as e:
        print(f"下载失败 {url}: {e}")
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

def is_taiwan_channel(name):
    """智能判断是否为台湾频道"""
    name_lower = name.lower()
    
    # 检查是否包含台湾关键词
    for kw in TW_CHANNEL_KEYWORDS:
        if kw.lower() in name_lower:
            # 特殊规则：如果同时包含香港关键词，可能不是台湾频道
            is_hk = False
            for hk_kw in HK_CHANNEL_KEYWORDS:
                if hk_kw.lower() in name_lower:
                    is_hk = True
                    break
            
            # 如果是"民视新闻"这样的，虽然包含"新闻"（在TW关键词中），
            # 但"民视"明确是台湾频道，所以返回True
            if "民視" in name or "民视" in name:
                return True
            if "台視" in name or "台视" in name:
                return True
            if "中視" in name or "中视" in name:
                return True
            if "華視" in name or "华视" in name:
                return True
            if "龍華" in name or "龙华" in name:
                return True
            if "唐NTD" in name or "唐人卫视" in name:
                return True
            
            # 如果只有"新闻"而没有其他台湾标识，可能是香港新闻台
            if kw == "新聞" or kw == "新闻" or kw == "news":
                return False
            
            # 其他情况，如果有台湾关键词且不是香港频道，则认为是台湾频道
            if not is_hk:
                return True
    
    return False

def determine_group(name, default_group):
    # 先检查是否为体育频道
    for kw in SPORTS_KEYWORDS:
        if kw.lower() in name.lower():
            return GROUP_SPORTS
    
    # 如果是台湾频道，强制设为TW组
    if is_taiwan_channel(name):
        return GROUP_TW
    
    return default_group

# ================= 提取 BB (原样保留) =================

def extract_bb_raw(content):
    """原样提取BB.m3u的内容，不做任何修改"""
    return content

# ================= 提取 HK (从EE.m3u) =================

def extract_hk(content):
    lines = content.splitlines()
    channels = []
    
    for i in range(len(lines)):
        line = lines[i].strip()
        
        if line.startswith("#EXTINF"):
            name = line.split(",", 1)[1].strip()
            if i+1 < len(lines):
                url = lines[i+1].strip()
                if url.startswith("http"):
                    # 读取原分组
                    m = re.search(r'group-title="([^"]*)"', line)
                    original_group = m.group(1) if m else ""
                    
                    # 使用智能判断来决定分组
                    group = GROUP_TW if is_taiwan_channel(name) else GROUP_HK
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

# ================= 合并 HK/TW/SPORTS =================

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
        "台視", "台视", "中視", "中视", "華視", "华视", "民視", "民视", "公視", "公视",
        "台視新聞", "台视新闻", "中視新聞", "中视新闻", "華視新聞", "华视新闻", "民視新聞", "民视新闻",
        "台視財經", "台视财经", "民視第一", "民视第一", "民視影劇", "民视影剧", "民視綜藝", "民视综艺",
        "龍華電影", "龙华电影", "龍華洋片", "龙华日韩", "龙华戏剧", "龙华偶像", "龙华经典",
        "唐NTD", "唐人卫视"
    ]
    
    for idx, key in enumerate(tw_order):
        if key in name:
            return idx
    return 999

# ================= 主流程 =================

def main():
    print("开始下载源文件...")
    
    bb_content = download(BB_URL)
    hk_content = download(HK_SOURCE_URL)
    tw_content = download(TW_SOURCE_URL)
    
    print("开始处理频道...")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建输出文件
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# 生成时间: {timestamp}\n\n"
    
    # 1. 首先原样输出BB.m3u的内容（放在最前面）
    if bb_content:
        print("添加BB.m3u内容（原样保留）")
        # 移除可能存在的重复#EXTM3U头
        bb_lines = bb_content.splitlines()
        for line in bb_lines:
            if not line.startswith("#EXTM3U"):  # 跳过原有的EXTM3U头
                output += line + "\n"
    else:
        print("警告: BB.m3u下载失败")
    
    output += "\n\n"
    
    # 2. 处理HK源（EE.m3u）
    hk_channels = []
    if hk_content:
        hk_channels = extract_hk(hk_content)
        print(f"从HK源提取到 {len(hk_channels)} 个频道")
    else:
        print("警告: HK源下载失败")
    
    # 3. 处理TW源
    tw_channels = []
    if tw_content:
        tw_channels = extract_tw(tw_content)
        print(f"从TW源提取到 {len(tw_channels)} 个频道")
    else:
        print("警告: TW源下载失败")
    
    # 合并HK和TW的频道（BB已经原样输出，不参与合并）
    all_channels = hk_channels + tw_channels
    merged = merge_channels(all_channels)
    
    # 分类
    hk_list, tw_list, sports_list = [],[],[]
    for data in merged.values():
        if data["group"] == GROUP_HK:
            hk_list.append(data)
        elif data["group"] == GROUP_TW:
            tw_list.append(data)
        elif data["group"] == GROUP_SPORTS:
            sports_list.append(data)
    
    print(f"合并后: HK {len(hk_list)}个, TW {len(tw_list)}个, SPORTS {len(sports_list)}个")
    
    # 添加HK分组
    if hk_list:
        output += "\n### HK ###\n"
        for item in sorted(hk_list, key=lambda x: (hk_weight(x["name"]), x["name"].lower())):
            output += f'\n#EXTINF:-1 group-title="HK",{item["name"]}\n'
            for u in sorted(item["urls"]):
                output += u + "\n"
        output += "\n"
    
    # 添加TW分组
    if tw_list:
        output += "\n### TW ###\n"
        for item in sorted(tw_list, key=lambda x: (tw_weight(x["name"]), x["name"].lower())):
            output += f'\n#EXTINF:-1 group-title="TW",{item["name"]}\n'
            for u in sorted(item["urls"]):
                output += u + "\n"
        output += "\n"
    
    # 添加SPORTS分组
    if sports_list:
        output += "\n### SPORTS ###\n"
        for item in sorted(sports_list, key=lambda x: x["name"].lower()):
            output += f'\n#EXTINF:-1 group-title="SPORTS",{item["name"]}\n'
            for u in sorted(item["urls"]):
                output += u + "\n"
        output += "\n"
    
    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    print(f"🚀 DD.m3u 终极融合完成，已保存到 {OUTPUT_FILE}")
    print(f"文件顺序: BB (原样) → HK → TW → SPORTS")

if __name__ == "__main__":
    main()
