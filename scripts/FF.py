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

FILTER_KEYWORDS = ["720p"]

# ================== 工具函数 ==================
def clean_name(name):
    """深度清洗名称：合并凤凰系列，去除频道号和后缀"""
    n = name.strip()
    
    # 1. 针对凤凰系列的特殊清洗（如：鳳凰香港台 CH612 -> 鳳凰香港）
    if "鳳凰" in n or "凤凰" in n:
        if "中文" in n or "卫视" in n: n = "凤凰中文"
        elif "资讯" in n or "資訊" in n: n = "凤凰资讯"
        elif "香港" in n: n = "凤凰香港"
        elif "电影" in n: n = "凤凰电影"
        return n

    # 2. 通用后缀清理：去除 (HK), [TW], CH612 等
    n = re.sub(r'[\(\[\{].*?[\)\]\}]', '', n) # 去除括号内容
    n = re.sub(r'(?i)CH\d+', '', n)          # 去除 CH+数字
    n = re.sub(r'\s+', ' ', n)               # 合并多余空格
    
    return n.strip()

def get_hk_priority(name):
    """HK排序：所有凤凰字样置顶 -> Now -> TVB -> HOY -> RTHK -> 其他"""
    # 凤凰系列置顶 (优先级 0-3)
    if "凤凰中文" in name: return 0
    if "凤凰资讯" in name: return 1
    if "凤凰香港" in name: return 2
    if "凤凰" in name: return 3
    
    # 其他系列
    n = name.upper()
    if "NOW" in n: return 10
    if any(k in n for k in ["TVB", "翡翠", "无线", "明珠", "J2"]): return 11
    if "HOY" in n: return 12
    if "RTHK" in n: return 13
    return 100

def get_tw_priority(name):
    """TW排序：Love Nature -> 中天 -> 民视 -> 三立 -> TVBS -> 其他"""
    n = name.upper()
    if "LOVE NATURE" in n: return 0
    if "中天" in n: return 1
    if "民视" in n: return 2
    if "三立" in n: return 3
    if "TVBS" in n: return 4
    return 100

# ================== 核心处理 ==================
def process_channels(content):
    lines = content.splitlines()
    # temp_data: {Group: {URL: Name}}
    temp_data = {new_name: {} for new_name in CATEGORY_MAPPING.values()}
    current_group_raw = None
    
    for line in lines:
        line = line.strip()
        if not line or ",#genre#" in line:
            if ",#genre#" in line:
                current_group_raw = line.split(",")[0].strip()
            continue
            
        if "," in line and "://" in line:
            name_raw, url = line.split(",", 1)
            url = url.strip()
            
            if any(k.lower() in name_raw.lower() for k in FILTER_KEYWORDS):
                continue

            target_group = None
            # 逻辑：从“📺新聞”提取凤凰资讯，或从常规分类提取
            if current_group_raw == "📺新聞" and "鳳凰資訊" in name_raw:
                target_group = "HK"
            elif current_group_raw in CATEGORY_MAPPING:
                target_group = CATEGORY_MAPPING[current_group_raw]

            if target_group:
                pure_name = clean_name(name_raw)
                # URL 去重逻辑
                if url not in temp_data[target_group]:
                    temp_data[target_group][url] = pure_name
                else:
                    # 如果 URL 相同，保留更简洁的名称
                    if len(pure_name) < len(temp_data[target_group][url]):
                        temp_data[target_group][url] = pure_name

    final_data = {}
    for group, mapping in temp_data.items():
        # 将字典转回列表 [(name, url), ...]
        channel_list = [(name, url) for url, name in mapping.items()]
        
        # 应用排序逻辑
        if group == "HK":
            channel_list.sort(key=lambda x: (get_hk_priority(x[0]), x[0]))
        elif group == "TW":
            channel_list.sort(key=lambda x: (get_tw_priority(x[0]), x[0]))
        else:
            channel_list.sort(key=lambda x: x[0])
            
        final_data[group] = channel_list
        
    return final_data

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在合并并生成 FF.m3u...")
    
    try:
        bb = requests.get(BB_URL, timeout=15).text
        raw_content = requests.get(GAT_URL, timeout=15).text
    except Exception as e:
        print(f"网络请求失败: {e}")
        return

    channel_dict = process_channels(raw_content)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# FF.m3u | 更新时间: {timestamp}\n\n"

    # 1. 写入本地 BB 分组内容
    for line in bb.splitlines():
        if not line.startswith("#EXTM3U"):
            output += line + "\n"

    # 2. 写入清洗后的 HK, TW, Sports 分组
    for group in ["HK", "TW", "Sports"]:
        channels = channel_dict[group]
        if channels:
            output += f"\n# {group} 频道 ({len(channels)})\n"
            for name, url in channels:
                output += f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n'

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"🎉 任务完成！文件已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
