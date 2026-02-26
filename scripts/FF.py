#!/usr/bin/env python3
import requests
import re
from datetime import datetime

# ================== 配置 ==================
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
# 新的数据源
GAT_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/iptvpro.txt"
OUTPUT_FILE = "FF.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 提取关键词与目标分组映射
CATEGORY_MAPPING = {
    "🇭🇰香港": "HK",
    "🇹🇼台湾": "TW",
    "⛹️‍体育": "Sports"
}

# 仅剔除带 720p 的频道
FILTER_KEYWORDS = ["720p"]

# ================== 工具 ==================
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url, desc):
    try:
        log(f"下载 {desc}...")
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return None

def extract_channels(content):
    """从文本中按关键词提取并重命名分组"""
    lines = content.splitlines()
    extracted = {new_name: [] for new_name in CATEGORY_MAPPING.values()}
    current_group = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 识别分组行 (例如: 🇭🇰香港,#genre#)
        if ",#genre#" in line:
            raw_group = line.split(",")[0].strip()
            current_group = CATEGORY_MAPPING.get(raw_group)
            continue
            
        # 提取频道
        if current_group and "," in line and "://" in line:
            name, url = line.split(",", 1)
            # 过滤 720p
            if any(k.lower() in name.lower() for k in FILTER_KEYWORDS):
                continue
            extracted[current_group].append((name.strip(), url.strip()))
            
    return extracted

# ================== 主流程 ==================
def main():
    log("开始生成 FF.m3u ...")
    bb = download(BB_URL, "BB.m3u")
    raw_content = download(GAT_URL, "iptvpro 数据源")
    
    if not raw_content: return

    # 提取并分类
    channel_dict = extract_channels(raw_content)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# FF.m3u | 生成时间: {timestamp}\n\n"

    # 1. 写入 BB 频道
    bb_count = 0
    if bb:
        for line in bb.splitlines():
            if line.startswith("#EXTM3U"): continue
            output += line + "\n"
            if line.startswith("#EXTINF"): bb_count += 1

    # 2. 写入 提取的频道 (按 HK, TW, Sports 顺序)
    extracted_total = 0
    for group_name in ["HK", "TW", "Sports"]:
        channels = channel_dict[group_name]
        if channels:
            output += f"\n# {group_name} 频道 ({len(channels)})\n"
            for name, url in channels:
                output += f'#EXTINF:-1 group-title="{group_name}",{name}\n{url}\n'
                extracted_total += 1

    # 3. 统计
    output += f"\n# 统计: BB({bb_count}) + HK/TW/Sports({extracted_total}) = {bb_count + extracted_total}\n"

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log(f"🎉 FF.m3u 生成成功，总计 {bb_count + extracted_total} 个频道")
    except Exception as e:
        log(f"❌ 保存失败: {e}")

if __name__ == "__main__":
    main()
