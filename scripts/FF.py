#!/usr/bin/env python3
import requests
import re
from datetime import datetime

# ================== 配置 ==================
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/iptvpro.txt"
OUTPUT_FILE = "FF.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

CATEGORY_MAPPING = {
    "🇭🇰香港": "HK",
    "🇹🇼台湾": "TW",
    "⛹️‍体育": "Sports"
}

# 仅剔除带 720p 的频道
FILTER_KEYWORDS = ["720p"]

# ================== 工具函数 ==================
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def clean_name(name):
    """去除 (HK)、(TW)、[HK] 等后缀及多余空格"""
    name = re.sub(r'[\(\[\{](HK|TW|港|台)[\)\]\}]', '', name, flags=re.IGNORECASE)
    return name.strip()

def get_hk_priority(name):
    """HK排序：凤凰→Now→TVB→HOY→RTHK→其他"""
    n = name.upper()
    if "凤凰" in n: return 0
    if "NOW" in n: return 1
    if "TVB" in n or "翡翠" in n or "无线" in n: return 2
    if "HOY" in n: return 3
    if "RTHK" in n: return 4
    return 5

def get_tw_priority(name):
    """TW排序：Love Nature→中天→民视→三立→TVBS→其他"""
    n = name.upper()
    if "LOVE NATURE" in n: return 0
    if "中天" in n: return 1
    if "民视" in n: return 2
    if "三立" in n: return 3
    if "TVBS" in n: return 4
    return 5

# ================== 核心处理 ==================
def process_channels(content):
    lines = content.splitlines()
    # 临时存储：{Group: {URL: Name}} 用于合并相似频道（去重）
    temp_data = {new_name: {} for new_name in CATEGORY_MAPPING.values()}
    current_group = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        if ",#genre#" in line:
            raw_group = line.split(",")[0].strip()
            current_group = CATEGORY_MAPPING.get(raw_group)
            continue
            
        if current_group and "," in line and "://" in line:
            name, url = line.split(",", 1)
            if any(k.lower() in name.lower() for k in FILTER_KEYWORDS):
                continue
            
            # 清理名称
            pure_name = clean_name(name)
            url = url.strip()
            
            # 合并相似频道：如果 URL 相同，保留较短/较干净的名称
            if url not in temp_data[current_group]:
                temp_data[current_group][url] = pure_name
            else:
                if len(pure_name) < len(temp_data[current_group][url]):
                    temp_data[current_group][url] = pure_name

    # 转换为列表并排序
    final_data = {}
    for group, mapping in temp_data.items():
        channel_list = [(name, url) for url, name in mapping.items()]
        
        if group == "HK":
            channel_list.sort(key=lambda x: (get_hk_priority(x[0]), x[0]))
        elif group == "TW":
            channel_list.sort(key=lambda x: (get_tw_priority(x[0]), x[0]))
        else:
            channel_list.sort(key=lambda x: x[0])
            
        final_data[group] = channel_list
    return final_data

def main():
    log("开始生成 FF.m3u (带精细排序与去重)...")
    bb = requests.get(BB_URL).text if requests.get(BB_URL).status_code==200 else ""
    raw_content = requests.get(GAT_URL).text
    
    if not raw_content: return

    channel_dict = process_channels(raw_content)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    
    # 1. 写入 BB 频道
    bb_count = 0
    for line in bb.splitlines():
        if line.startswith("#EXTM3U"): continue
        output += line + "\n"
        if line.startswith("#EXTINF"): bb_count += 1

    # 2. 写入 排序后的频道
    extracted_total = 0
    for group in ["HK", "TW", "Sports"]:
        channels = channel_dict[group]
        if channels:
            output += f"\n# {group}频道 ({len(channels)})\n"
            for name, url in channels:
                output += f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n'
                extracted_total += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    log(f"🎉 FF.m3u 生成成功！总数: {bb_count + extracted_total}")

if __name__ == "__main__":
    main()
