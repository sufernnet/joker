#!/usr/bin/env python3
import requests
import re
from datetime import datetime
import os

# ================== 配置 ==================
# 目标源 URL
SOURCE_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = "Gather.m3u"

# 分组名称
SOURCE_HK_GROUP = "• Juli 「精選」"
SOURCE_TW_GROUP = "•台湾「限制」"

TARGET_HK_NAME = "HK"
TARGET_TW_NAME = "TW"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url):
    try:
        log(f"正在下载源数据...")
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        log(f"❌ 下载失败: {e}")
        return None

def parse_m3u_by_group(content):
    """
    解析txt格式或m3u格式的源。
    由于目标源看起来是 txt/m3u 混合格式，我们按行匹配 #genre# 或分组标识。
    """
    lines = content.splitlines()
    hk_channels = []
    tw_channels = []
    
    current_group = ""
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 识别分组行 (针对 txt 格式)
        if ",#genre#" in line:
            current_group = line.split(",")[0].strip()
            continue
            
        # 提取频道
        if "," in line and "://" in line:
            name, url = line.split(",", 1)
            name = name.strip()
            url = url.strip()
            
            # 逻辑 1: 提取 HK 分组
            if current_group == SOURCE_HK_GROUP:
                hk_channels.append((name, url))
                
            # 逻辑 2: 提取 TW 分组，并过滤关键词
            elif current_group == SOURCE_TW_GROUP:
                # 仅保留包含 「4gTV」、ofiii、龍華 的频道
                if any(k in name for k in ["「4gTV」", "ofiii", "龍華", "龙华"]):
                    tw_channels.append((name, url))
                    
    return hk_channels, tw_channels

def deduplicate(channels):
    """简单去重：基于 URL"""
    seen_urls = set()
    unique_channels = []
    for name, url in channels:
        if url not in seen_urls:
            unique_channels.append((name, url))
            seen_urls.add(url)
    return unique_channels

def main():
    log("开始生成 Gather.m3u ...")
    content = download(SOURCE_URL)
    if not content:
        return

    hk_raw, tw_raw = parse_m3u_by_group(content)
    
    # 去重
    hk_final = deduplicate(hk_raw)
    tw_final = deduplicate(tw_raw)
    
    log(f"提取到 HK 频道: {len(hk_final)} 个")
    log(f"提取到 TW 频道: {len(tw_final)} 个")

    # 构建输出内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n'
    output += f"# Generated: {timestamp}\n\n"

    # 写入 HK
    for name, url in hk_final:
        output += f'#EXTINF:-1 group-title="{TARGET_HK_NAME}",{name}\n{url}\n'

    # 写入 TW
    for name, url in tw_final:
        output += f'#EXTINF:-1 group-title="{TARGET_TW_NAME}",{name}\n{url}\n'

    try:
        # 确保在根目录生成，方便 Actions 提交
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log(f"🎉 {OUTPUT_FILE} 生成成功！总计 {len(hk_final) + len(tw_final)} 个频道")
    except Exception as e:
        log(f"❌ 保存文件失败: {e}")

if __name__ == "__main__":
    main()
