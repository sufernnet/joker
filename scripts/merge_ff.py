#!/usr/bin/env python3
import requests
import re
from datetime import datetime

# ================== 配置 ==================
SOURCE_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = "Gather.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 目标原始分组名
SOURCE_HK_GROUP = "• Juli 「精選」"
SOURCE_TW_GROUP = "•台湾「限制」"

# 输出分组名
TARGET_HK_NAME = "HK"
TARGET_TW_NAME = "TW"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_source(url):
    try:
        log(f"正在从源提取数据: {url}")
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        log(f"❌ 抓取失败: {e}")
        return ""

def parse_content(content):
    hk_list = []
    tw_list = []
    
    # 兼容 M3U 格式解析
    # 匹配模式：#EXTINF:-1 group-title="分组名",名称 \n 链接
    segments = re.findall(r'#EXTINF:.* group-title="([^"]+)".*,(.*?)\n(http.*?)(?=\n#|$)', content, re.DOTALL)
    
    # 如果正则没匹配到，尝试简单文本解析（兼容 TXT 格式）
    if not segments:
        log("未检测到标准 M3U 格式，尝试 TXT 格式解析...")
        current_group = ""
        for line in content.splitlines():
            line = line.strip()
            if "#genre#" in line:
                current_group = line.split(",")[0]
            elif "," in line and "://" in line:
                name, url = line.split(",", 1)
                segments.append((current_group, name.strip(), url.strip()))

    for group, name, url in segments:
        group = group.strip()
        name = name.strip()
        url = url.strip()

        # 逻辑 1: 提取 HK 分组
        if group == SOURCE_HK_GROUP:
            hk_list.append((name, url))
            
        # 逻辑 2: 提取 TW 分组，并过滤关键词
        elif group == SOURCE_TW_GROUP:
            if any(k in name for k in ["「4gTV」", "ofiii", "龍華", "龙华"]):
                hk_name = name.replace("「4gTV」", "").replace("ofiii", "").strip()
                tw_list.append((hk_name, url))
                
    return hk_list, tw_list

def main():
    content = download_source(SOURCE_URL)
    if not content:
        log("错误：未能获取到任何内容")
        return

    hk_channels, tw_channels = parse_content(content)
    
    if not hk_channels and not tw_channels:
        log("⚠️ 警告：解析完成，但未匹配到符合条件的频道！请检查源分组名是否变动。")
    
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n'
    
    for name, url in hk_channels:
        output += f'#EXTINF:-1 group-title="{TARGET_HK_NAME}",{name}\n{url}\n'
        
    for name, url in tw_channels:
        output += f'#EXTINF:-1 group-title="{TARGET_TW_NAME}",{name}\n{url}\n'

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"✅ 任务完成！HK: {len(hk_channels)} 个, TW: {len(tw_channels)} 个。文件已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
