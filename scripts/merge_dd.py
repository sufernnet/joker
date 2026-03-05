#!/usr/bin/env python3
"""
DD.m3u 合并脚本（港台频道版）- SPORTS增强完整版
新增功能：从台湾源提取 •體育「Relay」 分组频道到 SPORTS
"""

import requests
import re
from datetime import datetime
import sys
import time

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/港台大陆"
TW_SOURCE_URL = "https://yang.sufern001.workers.dev"
OUTPUT_FILE = "DD.m3u"

SOURCE_GROUPS = ["港台频道", "新聞频道"]
TARGET_TW_GROUP = "•台湾「限制」"
TARGET_SPORTS_RELAY_GROUP = "•體育「Relay」"  # 新增：体育Relay分组

HK_GROUP = "HK"
TW_GROUP = "TW"
SPORTS_GROUP = "SPORTS"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ================== 过滤关键词 ==================

FILTER_KEYWORDS = [
    "凤凰电影","人间卫视","邵氏动作","邵氏武侠","邵氏电影","邵氏喜剧",
    "生命电影","ASTV","亚洲卫视","GOODTV","好消息","唐NTD","唐人卫视",
    "唯心电视","星空卫视","星空音乐","華藝中文","中旺电视","人間衛視",
    "澳门","澳视","澳视澳门","澳视Macau","澳门综艺","澳门体育","豬哥亮歌廳秀",
    "澳视高清","澳视生活","澳视中文","澳视体育","澳视新闻","澳视财经",
    "DW德國之聲","MCE 我的歐洲電影","SBN 全球財經","ELTA生活英語",
    "國會頻道 1","國會頻道 2","國會頻道1","國會頻道2","半島國際新聞",
    "大愛電視","好萊塢電影","尼克兒童頻道","幸福空間居家","台灣啟示錄",
    "影迷數位紀實","影迷數位電影","東森幼幼","MOMO運動綜合","第1商業",
    "東森購物 一","東森購物 二","東森購物 三","東森購物 四","金光布袋戲",
    "歡樂兒童","韓國娛樂台 KMTV","韓國娛樂台","KMTV","新唐人亚太台",
]

FILTER_URLS = [
    "http://iptv.4666888.xyz/iptv2A.php?id=27",
    "https://tv.iill.top/4gtv/4gtv-live007",
    "https://tv.iill.top/4gtv/4gtv-live106",
    "https://tv.iill.top/4gtv/4gtv-live105",
    "https://tv.iill.top/4gtv/4gtv-live206",
    "https://tv.iill.top/4gtv/litv-ftv15",
    "https://tv.iill.top/4gtv/4gtv-4gtv011",
    "https://hls.iill.top/api/YoYo-TV/index.m3u8",
    "https://tv.iill.top/4gtv/4gtv-live047",
    "https://tv.iill.top/4gtv/4gtv-live048",
    "https://tv.iill.top/4gtv/4gtv-live046",
    "https://tv.iill.top/4gtv/4gtv-live0499",
    "https://tv.iill.top/FainTV/22768",
    "https://tv.iill.top/4gtv/4gtv-4gtv016",
]

# ================== 工具函数 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url, desc, retries=3):
    for attempt in range(retries):
        try:
            log(f"下载 {desc}... (尝试 {attempt+1}/{retries})")
            r = requests.get(url, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
            r.raise_for_status()
            return r.text
        except Exception as e:
            log(f"失败: {e}")
            time.sleep(3)
    return None

def is_sports_channel(name):
    return "博斯" in name if name else False

def modify_group_title(extinf_line, new_group):
    """修改EXTINF行中的group-title为新的分组名"""
    modified = re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', extinf_line)
    # 确保频道名称正确（保留逗号后的部分）
    parts = modified.rsplit(",", 1)
    if len(parts) == 2:
        return parts[0] + "," + parts[1].strip()
    return modified

# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u ...")

    # 下载各个源
    bb = download(BB_URL, "BB.m3u")
    if not bb:
        sys.exit(1)

    gat_content = download(GAT_URL, "港台大陆源文件") or ""
    tw_source_content = download(TW_SOURCE_URL, "台湾源文件") or ""

    # 存储各类频道
    hk_channels = []      # 格式: (name, url)
    tw_channels = []      # 格式: (extinf_line, name, url)
    sports_channels = []  # 格式: (extinf_line, name, url)

    # ===== 解析GAT源获取HK频道（保持原有逻辑）=====
    if gat_content:
        lines = gat_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF:"):
                # 检查是否属于目标分组
                if any(f'group-title="{group}"' in line for group in SOURCE_GROUPS):
                    if i+1 < len(lines):
                        url = lines[i+1].strip()
                        # 跳过过滤的URL
                        if url in FILTER_URLS:
                            i += 1
                            continue
                        
                        name = line.split(",")[-1].strip()
                        
                        # 应用关键词过滤
                        skip = False
                        for keyword in FILTER_KEYWORDS:
                            if keyword in name:
                                skip = True
                                break
                        
                        if not skip:
                            hk_channels.append((name, url))
                    i += 1
            i += 1

    # ===== TW源解析（增强版）=====
    if tw_source_content:
        lines = tw_source_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检查是否为EXTINF行
            if line.startswith("#EXTINF:"):
                # 确保有下一行且不是注释行
                if i+1 < len(lines):
                    url = lines[i+1].strip()
                    
                    # 跳过空URL或注释行
                    if not url or url.startswith('#'):
                        i += 1
                        continue
                    
                    # 获取频道名称（逗号后的部分）
                    name = line.split(",")[-1].strip()
                    
                    # 判断1: 检查是否为体育Relay分组
                    if f'group-title="{TARGET_SPORTS_RELAY_GROUP}"' in line:
                        log(f"找到体育Relay频道: {name}")
                        sports_channels.append((line, name, url))
                    
                    # 判断2: 检查是否为台湾限制分组
                    elif f'group-title="{TARGET_TW_GROUP}"' in line:
                        # 根据频道名判断是否为体育频道
                        if "博斯" in name:
                            log(f"找到博斯体育频道: {name}")
                            sports_channels.append((line, name, url))
                        else:
                            tw_channels.append((line, name, url))
                    
                    # 可选：可以在这里添加对其他分组的处理
                    # else: ...
                    
                i += 1  # 跳过URL行
            i += 1

    # ===== 去重处理（基于URL）=====
    # 对体育频道去重
    unique_sports = {}
    for item in sports_channels:
        extinf, name, url = item
        if url not in unique_sports:
            unique_sports[url] = item
    
    # 对TW频道去重
    unique_tw = {}
    for item in tw_channels:
        extinf, name, url = item
        if url not in unique_tw:
            unique_tw[url] = item

    # ===== 生成输出文件 =====
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# DD.m3u\n# 生成时间: {timestamp}\n\n"

    # 添加BB源内容（跳过EXTM3U行）
    for line in bb.splitlines():
        if not line.startswith("#EXTM3U"):
            output += line + "\n"

    # 添加HK频道
    if hk_channels:
        output += f"\n# {HK_GROUP}频道\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n{url}\n'

    # 添加TW频道
    if unique_tw:
        output += f"\n# {TW_GROUP}频道\n"
        for extinf_line, name, url in unique_tw.values():
            modified = modify_group_title(extinf_line, TW_GROUP)
            output += modified + "\n" + url + "\n"

    # 添加SPORTS频道（包含博斯和体育Relay）
    if unique_sports:
        output += f"\n# {SPORTS_GROUP}频道\n"
        for extinf_line, name, url in unique_sports.values():
            modified = modify_group_title(extinf_line, SPORTS_GROUP)
            output += modified + "\n" + url + "\n"

    # 添加统计信息
    total_tw = len(unique_tw)
    total_sports = len(unique_sports)
    total_hk = len(hk_channels)
    output += f"\n# 统计: HK({total_hk}) + TW({total_tw}) + SPORTS({total_sports}) = {total_hk + total_tw + total_sports}\n"

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    log(f"生成完成！共处理: HK({total_hk}), TW({total_tw}), SPORTS({total_sports})")
    log(f"输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
