#!/usr/bin/env python3
"""
DD.m3u 合并脚本（港台频道版）- SPORTS增强完整版
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

def clean_tw_channel_name(name):
    """清洗台湾频道名称，去除末尾的各种括号及其内容"""
    # 匹配末尾的各种括号（包括「」、【】、()）及其内容
    cleaned = re.sub(r'\s*[「【(][^」】)]*[」】)]\s*$', '', name)
    return cleaned.strip()

# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        sys.exit(1)

    gat_content = download(GAT_URL, "港台大陆源文件") or ""
    tw_source_content = download(TW_SOURCE_URL, "台湾源文件") or ""

    hk_channels = []
    tw_channels = []
    sports_channels = []

    # ===== 解析GAT源获取HK频道 =====
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

    # ===== TW 处理 =====
    if tw_source_content:
        lines = tw_source_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF:") and f'group-title="{TARGET_TW_GROUP}"' in line:
                raw_name = line.split(",")[-1].strip()
                cleaned_name = clean_tw_channel_name(raw_name)
                if i+1 < len(lines):
                    url = lines[i+1].strip()
                    if "博斯" in cleaned_name:
                        sports_channels.append((line, cleaned_name, url))
                    else:
                        tw_channels.append((line, cleaned_name, url))
                    i += 1
            # 提取 •體育「Relay」 分组
            elif line.startswith("#EXTINF:") and 'group-title="•體育「Relay」"' in line:
                raw_name = line.split(",")[-1].strip()
                cleaned_name = clean_tw_channel_name(raw_name)
                if i+1 < len(lines):
                    url = lines[i+1].strip()
                    sports_channels.append((line, cleaned_name, url))
                    i += 1
            i += 1

    # ===== 输出 =====
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# DD.m3u\n# 生成时间: {timestamp}\n\n"

    # BB
    for line in bb.splitlines():
        if not line.startswith("#EXTM3U"):
            output += line + "\n"

    # HK（恢复原有的HK处理）
    if hk_channels:
        output += f"\n# {HK_GROUP}频道\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n{url}\n'

    # TW
    if tw_channels:
        output += f"\n# {TW_GROUP}频道\n"
        for extinf_line, cleaned_name, url in tw_channels:
            try:
                # 1️⃣ 替换 group-title
                modified = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{TW_GROUP}"',
                    extinf_line
                )

                # 2️⃣ 替换逗号后面的频道名称
                modified = re.sub(
                    r',\s*[^,]*$',
                    f',{cleaned_name}',
                    modified
                )

                output += modified + "\n" + url + "\n"

            except Exception:
                output += f'#EXTINF:-1 group-title="{TW_GROUP}",{cleaned_name}\n{url}\n'

    # SPORTS
    if sports_channels:
        output += f"\n# {SPORTS_GROUP}频道\n"
        for extinf_line, cleaned_name, url in sports_channels:
            try:
                # 1️⃣ 替换 group-title
                modified = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{SPORTS_GROUP}"',
                    extinf_line
                )

                # 2️⃣ 替换逗号后面的频道名称
                modified = re.sub(
                    r',\s*[^,]*$',
                    f',{cleaned_name}',
                    modified
                )

                output += modified + "\n" + url + "\n"

            except Exception:
                output += f'#EXTINF:-1 group-title="{SPORTS_GROUP}",{cleaned_name}\n{url}\n'

    total = len(tw_channels) + len(sports_channels)
    output += f"\n# 统计: TW({len(tw_channels)}) + SPORTS({len(sports_channels)}) = {total}\n"

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write(output)

    log("生成完成")

if __name__ == "__main__":
    main()
