#!/usr/bin/env python3
import requests
import re
from datetime import datetime

# ================== 配置 ==================
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/iptvpro.txt"
OUTPUT_FILE = "FF.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 定义主提取分组
CATEGORY_MAPPING = {
    "🇭🇰香港": "HK",
    "🇹🇼台湾": "TW",
    "⛹️‍体育": "Sports"
}

# 过滤关键词
FILTER_KEYWORDS = ["720p"]

# ================== 工具函数 ==================
def clean_name(name):
    """去除 (HK)、(TW) 等后缀，并执行特定的名称合并逻辑"""
    n = name.strip()
    # 基础后缀清理
    n = re.sub(r'[\(\[\{](HK|TW|港|台)[\)\]\}]', '', n, flags=re.IGNORECASE)
    
    # 凤凰系列特定合并映射
    if n in ["鳳凰中文台", "鳳凰卫视", "凤凰卫视"]: return "凤凰中文"
    if n in ["鳳凰香港台", "鳳凰香港"]: return "凤凰香港"
    if n == "鳳凰資訊": return "凤凰资讯"
    
    return n.strip()

def get_hk_priority(name):
    """HK排序：凤凰中文→凤凰资讯→凤凰香港→Now→TVB→HOY→RTHK→其他"""
    if "凤凰中文" in name: return 0
    if "凤凰资讯" in name: return 1
    if "凤凰香港" in name: return 2
    n = name.upper()
    if "NOW" in n: return 3
    if any(k in n for k in ["TVB", "翡翠", "无线", "明珠", "J2"]): return 4
    if "HOY" in n: return 5
    if "RTHK" in n: return 6
    return 7

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
    # 存储结构: {Group: {URL: Name}}
    temp_data = {new_name: {} for new_name in CATEGORY_MAPPING.values()}
    current_group_raw = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 识别原始分组
        if ",#genre#" in line:
            current_group_raw = line.split(",")[0].strip()
            continue
            
        if "," in line and "://" in line:
            name_raw, url = line.split(",", 1)
            url = url.strip()
            
            # 过滤 720p
            if any(k.lower() in name_raw.lower() for k in FILTER_KEYWORDS):
                continue

            target_group = None
            
            # 逻辑1：如果是“📺新聞”分组，仅提取“鳳凰資訊 (HK)”放入 HK
            if current_group_raw == "📺新聞":
                if "鳳凰資訊" in name_raw:
                    target_group = "HK"
            
            # 逻辑2：常规分组映射 (香港/台湾/体育)
            elif current_group_raw in CATEGORY_MAPPING:
                target_group = CATEGORY_MAPPING[current_group_raw]

            # 执行提取与合并
            if target_group:
                pure_name = clean_name(name_raw)
                # URL 去重：保留名称更简洁的
                if url not in temp_data[target_group] or len(pure_name) < len(temp_data[target_group][url]):
                    temp_data[target_group][url] = pure_name

    # 排序逻辑
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始生成 FF.m3u...")
    
    # 获取数据
    try:
        bb = requests.get(BB_URL, timeout=20).text
    except:
        bb = ""
    
    raw_content = requests.get(GAT_URL, timeout=20).text
    if not raw_content:
        print("错误：无法读取源文件")
        return

    channel_dict = process_channels(raw_content)
    
    # 组装 M3U
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# FF.m3u | 更新: {timestamp}\n\n"

    # 1. 写入本地 BB 频道
    bb_count = 0
    for line in bb.splitlines():
        if line.startswith("#EXTM3U"): continue
        output += line + "\n"
        if line.startswith("#EXTINF"): bb_count += 1

    # 2. 写入提取的分组
    for group in ["HK", "TW", "Sports"]:
        channels = channel_dict[group]
        if channels:
            output += f"\n# {group} 频道 ({len(channels)})\n"
            for name, url in channels:
                output += f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n'

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"成功生成 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
