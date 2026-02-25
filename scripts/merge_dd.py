#!/usr/bin/env python3
"""
DD.m3u 合并脚本（港澳台直提 + 精确过滤与排序）

功能：
1. 提取“🔮[三网]港澳台直播”分组
2. 重命名为“港澳台”
3. 过滤掉指定频道
4. 港澳台分组内按新规则排序：
   凤凰中文 → 凤凰资讯 → NOW新闻 → NOW体育 → NOW财经 → NOW直播 → POPC → HOY76~78 → RHK31~32 → TVB系列（TVB翡翠排前面）
5. 合并 BB.m3u
6. 使用固定 EPG

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
OUTPUT_FILE = "DD.m3u"

SOURCE_GROUP = "🔮[三网]港澳台直播"
TARGET_GROUP = "港澳台"

EPG_URL = "http://epg.51zmt.top:8000/e.xml"

# 需要过滤掉的频道关键词（不区分大小写）
FILTER_KEYWORDS = [
    "凤凰电影",
    "ASTV",
    "亚洲卫视",
    "Channel 5",
    "Channel 8",
    "Channel U",
    "GOODTV",
    "好消息",
    "唐NTD",
    "唐人卫视",
    "唯心电视",
    "星空卫视",
    "星空音乐",
    "澳门综艺",
    "邵氏武侠",
    "邵氏电影",
    "邵氏喜剧",
    "華藝中文",
    "公视",
    "公视台语台",
    "中旺电视"
]

# ================== 工具 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download(url, desc):
    try:
        log(f"下载 {desc}...")
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        log(f"✅ {desc} 下载成功 ({len(r.text)} 字符)")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return None


def extract_gat_channels(content):
    lines = content.splitlines()
    channels = []
    in_section = False
    marker = f"{SOURCE_GROUP},#genre#"

    log(f"开始提取分组：{SOURCE_GROUP}")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if marker in line:
            in_section = True
            log(f"✅ 在第 {i+1} 行找到目标分组")
            continue

        if in_section:
            if ",#genre#" in line:
                log("到达下一个分组，停止提取")
                break

            if "," in line and "://" in line:
                name, url = line.split(",", 1)
                channels.append((name.strip(), url.strip()))

    log(f"提取到 {len(channels)} 个频道")
    return channels


def should_filter(name):
    """检查频道名称是否应该被过滤"""
    name_lower = name.lower()
    for keyword in FILTER_KEYWORDS:
        if keyword.lower() in name_lower:
            log(f"过滤频道: {name} (匹配关键词: {keyword})")
            return True
    return False


def sort_gat_channels(channels):
    """
    排序权重（越小越靠前）：
    0: 凤凰中文
    1: 凤凰资讯
    2: NOW新闻
    3: NOW体育
    4: NOW财经
    5: NOW直播
    6: POPC
    7: HOY 76-78
    8: RHK 31-32
    9: TVB系列（TVB翡翠最前）
    10: 其他
    """
    def weight(name):
        name_lower = name.lower()
        
        # 凤凰中文
        if "凤凰中文" in name or ("凤凰卫视" in name and "中文" in name):
            return (0, "00_凤凰中文")
        
        # 凤凰资讯
        if "凤凰资讯" in name or ("凤凰卫视" in name and "资讯" in name):
            return (1, "01_凤凰资讯")
        
        # NOW新闻
        if "now新闻" in name_lower or "now 新闻" in name_lower:
            return (2, "02_NOW新闻")
        
        # NOW体育
        if "now体育" in name_lower or "now 体育" in name_lower:
            return (3, "03_NOW体育")
        
        # NOW财经
        if "now财经" in name_lower or "now 财经" in name_lower:
            return (4, "04_NOW财经")
        
        # NOW直播
        if "now直播" in name_lower or "now 直播" in name_lower:
            return (5, "05_NOW直播")
        
        # POPC
        if "popc" in name_lower:
            return (6, "06_POPC")
        
        # HOY 76-78
        if "hoy" in name_lower and any(x in name_lower for x in ["76", "77", "78"]):
            return (7, f"07_HOY_{name}")
        
        # RHK 31-32
        if "rhk" in name_lower and any(x in name_lower for x in ["31", "32"]):
            return (8, f"08_RHK_{name}")
        
        # TVB系列
        if "tvb" in name_lower:
            # TVB翡翠台排在最前
            if "翡翠" in name:
                return (9, "09_TVB翡翠")
            # 其他TVB
            return (9, f"09_TVB_{name}")
        
        # 其他频道
        return (10, name)

    return sorted(channels, key=lambda x: weight(x[0]))


# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    gat = download(GAT_URL, "港澳台直播源") or ""
    
    # 提取频道
    gat_channels = extract_gat_channels(gat) if gat else []
    log(f"提取后原始频道数: {len(gat_channels)}")
    
    # 过滤频道
    filtered_channels = [(name, url) for name, url in gat_channels if not should_filter(name)]
    log(f"过滤后剩余频道数: {len(filtered_channels)}")
    
    # 排序
    sorted_channels = sort_gat_channels(filtered_channels)
    log(f"排序完成")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===== M3U 头 =====
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# DD.m3u
# 生成时间: {timestamp}
# 更新频率: 每天 06:00 / 17:00
# EPG: {EPG_URL}
# GitHub Actions 自动生成

"""

    # ===== BB =====
    bb_count = 0
    for line in bb.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        output += line + "\n"
        if line.startswith("#EXTINF"):
            bb_count += 1

    # ===== 港澳台 =====
    if sorted_channels:
        output += f"\n# {TARGET_GROUP}频道 ({len(sorted_channels)})\n"
        for name, url in sorted_channels:
            output += f'#EXTINF:-1 group-title="{TARGET_GROUP}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(sorted_channels)

    # 统计过滤数量
    filtered_count = len(gat_channels) - len(sorted_channels) if gat_channels else 0

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {TARGET_GROUP}频道数: {len(sorted_channels)}
# 过滤频道数: {filtered_count}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 DD.m3u 生成成功")
        log(f"📺 BB({bb_count}) + 港澳台({len(sorted_channels)}) = {total}")
        if filtered_count > 0:
            log(f"🗑️ 过滤了 {filtered_count} 个频道")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
