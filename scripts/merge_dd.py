#!/usr/bin/env python3
"""
DD.m3u 合并脚本（港澳台直提 + 精确过滤与排序）

功能：
1. 提取“🔮[三网]港澳台直播”分组
2. 重命名为“港澳台”
3. 过滤掉指定频道和指定URL
4. 去重处理：保留标准名称，去掉带"台"字的重复频道
5. 港澳台分组内按新规则排序：
   凤凰中文 → 凤凰资讯 → NOW新闻 → NOW体育 → NOW财经 → NOW直播 → POPC → HOY76~78 → RHK31~32 → TVB系列（TVB翡翠排前面）
6. 合并 BB.m3u
7. 使用固定 EPG

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

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 需要过滤掉的频道关键词（不区分大小写）
FILTER_KEYWORDS = [
    "凤凰电影",
    "人间卫视",
    "邵氏动作",
    "邵氏武侠",
    "邵氏电影",
    "邵氏喜剧",
    "生命电影",
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
    "華藝中文",
    "公视",
    "公视台语台",
    "中旺电视"
]

# 需要过滤掉的特定URL（精确匹配）
FILTER_URLS = [
    "http://iptv.4666888.xyz/iptv2A.php?id=27",  # 凤凰中文特定源
]

# 频道名称标准化映射（用于去重）
# 格式：{"需要去掉的变体": "保留的标准名称"}
NAME_NORMALIZATION = {
    "NOW新闻台": "Now新闻",
    "NOW新闻台 ": "Now新闻",  # 带空格的变体
    "Now新闻台": "Now新闻",
    "now新闻台": "Now新闻",
    "NOW 新闻台": "Now新闻",
    "Now 新闻台": "Now新闻",
}

# 需要优先保留的名称模式（不区分大小写）
PREFERRED_NAMES = [
    "Now新闻",
    "Now体育",
    "Now财经", 
    "Now直播",
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


def should_filter_by_keyword(name):
    """根据关键词检查频道名称是否应该被过滤"""
    name_lower = name.lower()
    for keyword in FILTER_KEYWORDS:
        if keyword.lower() in name_lower:
            log(f"关键词过滤频道: {name} (匹配关键词: {keyword})")
            return True
    return False


def should_filter_by_url(url):
    """根据URL检查频道是否应该被过滤"""
    for filter_url in FILTER_URLS:
        if url == filter_url or url.startswith(filter_url):
            log(f"URL过滤频道: {url}")
            return True
    return False


def normalize_channel_name(name):
    """标准化频道名称（用于去重）"""
    name_stripped = name.strip()
    
    # 检查是否需要标准化
    for variant, standard in NAME_NORMALIZATION.items():
        if name_stripped == variant or name_stripped.lower() == variant.lower():
            log(f"标准化名称: '{name}' -> '{standard}'")
            return standard
    
    return name_stripped


def is_preferred_name(name):
    """检查是否为优先保留的名称"""
    name_lower = name.lower()
    for preferred in PREFERRED_NAMES:
        if name_lower == preferred.lower():
            return True
    return False


def deduplicate_channels(channels):
    """
    去重处理
    策略：对于相同内容的频道，优先保留标准名称，去掉带"台"字的变体
    """
    # 按URL分组
    url_groups = {}
    for name, url in channels:
        if url not in url_groups:
            url_groups[url] = []
        url_groups[url].append(name)
    
    # 对每个URL组进行去重选择
    deduped = []
    for url, names in url_groups.items():
        if len(names) == 1:
            # 只有一个名称，直接使用
            deduped.append((names[0], url))
        else:
            # 多个名称对应同一URL，选择优先保留的
            log(f"发现重复URL: {url}")
            for name in names:
                log(f"  - 名称变体: {name}")
            
            # 优先选择标准名称
            selected = None
            for name in names:
                if is_preferred_name(name):
                    selected = name
                    log(f"  ✅ 选择优先名称: {name}")
                    break
            
            # 如果没有优先名称，选择最短的（通常是不带"台"字的）
            if not selected:
                # 按长度排序，选最短的
                sorted_names = sorted(names, key=len)
                selected = sorted_names[0]
                log(f"  ⚠️ 无优先名称，选择最短的: {selected}")
            
            deduped.append((selected, url))
    
    log(f"去重前频道数: {len(channels)}，去重后: {len(deduped)}")
    return deduped


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
    
    # 过滤频道（关键词过滤）
    keyword_filtered = [(name, url) for name, url in gat_channels if not should_filter_by_keyword(name)]
    log(f"关键词过滤后剩余频道数: {len(keyword_filtered)}")
    
    # 过滤频道（URL过滤）
    url_filtered = [(name, url) for name, url in keyword_filtered if not should_filter_by_url(url)]
    log(f"URL过滤后剩余频道数: {len(url_filtered)}")
    
    # 先标准化名称
    normalized_channels = [(normalize_channel_name(name), url) for name, url in url_filtered]
    
    # 去重处理
    deduped_channels = deduplicate_channels(normalized_channels)
    
    # 排序
    sorted_channels = sort_gat_channels(deduped_channels)
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

    # 统计过滤和去重数量
    keyword_filtered_count = len(gat_channels) - len(keyword_filtered) if gat_channels else 0
    url_filtered_count = len(keyword_filtered) - len(url_filtered)
    deduped_count = len(url_filtered) - len(sorted_channels)

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {TARGET_GROUP}频道数: {len(sorted_channels)}
# 关键词过滤数: {keyword_filtered_count}
# URL过滤数: {url_filtered_count}
# 去重频道数: {deduped_count}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 DD.m3u 生成成功")
        log(f"📺 BB({bb_count}) + 港澳台({len(sorted_channels)}) = {total}")
        if keyword_filtered_count > 0:
            log(f"🗑️ 关键词过滤了 {keyword_filtered_count} 个频道")
        if url_filtered_count > 0:
            log(f"🔗 URL过滤了 {url_filtered_count} 个频道")
        if deduped_count > 0:
            log(f"🔄 去重了 {deduped_count} 个重复频道")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
