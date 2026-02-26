#!/usr/bin/env python3
"""
EE.m3u 合并脚本（港台频道版）

功能：
1. 提取“港台频道”分组
2. 重命名为“港澳台”
3. 过滤掉指定频道和指定URL
4. 去除频道名称中的分辨率标记（如“HD 1080p”、“1080p”）
5. 去重处理：保留标准名称，去掉带"台"字的重复频道
6. 按“香港在前，台湾在后”的规则排序，各系列内部顺序精细化：
   香港：凤凰中文 → 凤凰资讯 → 凤凰香港 → Now系列（新闻/体育/财经/直播）→ HOY系列（按数字）→ TVB系列（翡翠优先）→ ViuTV → CH5~CH8 → 其他香港
   台湾：民视系列 → 台视系列 → 纬来系列 → 龙华系列 → 其他台湾
7. 合并 BB.m3u
8. 使用固定 EPG

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/港台大陆"
OUTPUT_FILE = "EE.m3u"

SOURCE_GROUP = "港台频道"
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
    "TVB千禧经典540p",
    "TVB无线千禧",
    "中視HD 720p",
    "台視HD 720p",
    "生命电影",
    "ASTV",
    "亚洲卫视",
    "Channel 5",
    "Channel 8",
    "Channel U",
    "GOODTV",
    "好消息",
    "民视720p",
    "緯來綜合",
    "民視旅遊",
    "民視影劇",
    "三立台湾台",
    "三立戏剧台",
    "三立综合台720p",
    "三立都会台",
    "龙华偶像720p",
    "华视HD 720p",
    "唐NTD",
    "唐人卫视",
    "唯心电视",
    "星空卫视",
    "星空音乐",
    "澳门综艺",
    "華藝中文",
    "公視戲劇",
    "公视台语台",
    "中旺电视"
]

# 需要过滤掉的特定URL（精确匹配）
FILTER_URLS = [
    "http://iptv.4666888.xyz/iptv2A.php?id=27",  # 凤凰中文特定源
]

# 频道名称标准化映射（用于去重）
NAME_NORMALIZATION = {
    "NOW新闻台": "Now新闻",
    "NOW新闻台 ": "Now新闻",
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

# 台湾频道关键词（用于区分台湾/香港）
TAIWAN_KEYWORDS = [
    "民视", "台视", "纬来", "龙华", "八大", "东森", "三立", "中视", "华视",
    "TVBS", "非凡", "年代", "壹电视", "寰宇", "靖天", "爱尔达", "中天", "高点"
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


def clean_channel_name(name):
    """去除频道名称末尾的分辨率标记如 'HD 1080p', '1080p' 等"""
    original = name
    # 去除末尾常见的分辨率标记
    name = re.sub(r'\s*[Hh][Dd]\s*1080[pP]?\s*$', '', name)
    name = re.sub(r'\s*1080[pP]\s*$', '', name)
    name = re.sub(r'\s*[Hh][Dd]\s*$', '', name)
    # 去除可能留下的空格
    name = name.strip()
    if name != original:
        log(f"清洗名称: '{original}' -> '{name}'")
    return name


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
    url_groups = {}
    for name, url in channels:
        if url not in url_groups:
            url_groups[url] = []
        url_groups[url].append(name)
    
    deduped = []
    for url, names in url_groups.items():
        if len(names) == 1:
            deduped.append((names[0], url))
        else:
            log(f"发现重复URL: {url}")
            for name in names:
                log(f"  - 名称变体: {name}")
            
            selected = None
            for name in names:
                if is_preferred_name(name):
                    selected = name
                    log(f"  ✅ 选择优先名称: {name}")
                    break
            
            if not selected:
                sorted_names = sorted(names, key=len)
                selected = sorted_names[0]
                log(f"  ⚠️ 无优先名称，选择最短的: {selected}")
            
            deduped.append((selected, url))
    
    log(f"去重前频道数: {len(channels)}，去重后: {len(deduped)}")
    return deduped


# ================== 新的排序逻辑 ==================

def is_taiwan(name):
    """根据关键词判断是否为台湾频道"""
    name_lower = name.lower()
    for kw in TAIWAN_KEYWORDS:
        if kw.lower() in name_lower:
            return True
    return False


def get_hk_group_and_sub(name):
    """
    返回香港频道的主组优先级和内部排序子键
    主组优先级：0凤凰中文,1凤凰资讯,2凤凰香港,3Now系列,4HOY系列,5TVB系列,6ViuTV,7CH5~8,8其他香港
    子键用于组内精细排序
    """
    name_lower = name.lower()

    # 凤凰中文
    if "凤凰中文" in name or ("凤凰" in name and "中文" in name):
        return (0, 0)

    # 凤凰资讯
    if "凤凰资讯" in name or ("凤凰" in name and "资讯" in name):
        return (1, 0)

    # 凤凰香港
    if "凤凰香港" in name or ("凤凰" in name and "香港" in name):
        return (2, 0)

    # Now系列
    if "now" in name_lower:
        if "新闻" in name or "news" in name_lower:
            sub = 0
        elif "体育" in name or "sports" in name_lower:
            sub = 1
        elif "财经" in name or "finance" in name_lower:
            sub = 2
        elif "直播" in name or "live" in name_lower:
            sub = 3
        else:
            sub = 4
        return (3, sub)

    # HOY系列
    if "hoy" in name_lower:
        match = re.search(r'(\d+)', name)
        if match:
            sub = int(match.group(1))
        else:
            sub = 99
        return (4, sub)

    # TVB系列
    if any(k in name_lower for k in ["tvb", "翡翠", "明珠", "j2", "无线"]):
        if "翡翠" in name:
            sub = 0
        elif "明珠" in name:
            sub = 1
        elif "j2" in name_lower:
            sub = 2
        else:
            sub = 3
        return (5, sub)

    # ViuTV系列
    if "viu" in name_lower:
        return (6, 0)

    # CH5~CH8
    if "ch5" in name_lower or "ch8" in name_lower or "channel 5" in name_lower or "channel 8" in name_lower:
        match = re.search(r'[ch\s]*(\d+)', name_lower)
        if match:
            sub = int(match.group(1))
        else:
            sub = 99
        return (7, sub)

    # 其他香港频道
    return (8, 0)


def get_tw_group_and_sub(name):
    """
    返回台湾频道的主组优先级和内部排序子键
    主组优先级：0民视系列,1台视系列,2纬来系列,3龙华系列,4其他台湾
    """
    name_lower = name.lower()

    if "民视" in name:
        return (0, 0)
    if "台视" in name:
        return (1, 0)
    if "纬来" in name:
        return (2, 0)
    if "龙华" in name:
        return (3, 0)
    return (4, 0)


def sort_gat_channels(channels):
    """
    新的排序函数：先香港后台湾，各系列内部按指定顺序
    排序键格式：(region, group, sub, name)
        region: 0=香港, 1=台湾
        group: 各区域内主组优先级
        sub: 组内精细排序键
        name: 最后按名称字母顺序
    """
    def key_func(item):
        name, _ = item
        if is_taiwan(name):
            region = 1
            group, sub = get_tw_group_and_sub(name)
        else:
            region = 0
            group, sub = get_hk_group_and_sub(name)
        return (region, group, sub, name)

    return sorted(channels, key=key_func)


# ================== 主流程 ==================

def main():
    log("开始生成 EE.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    gat = download(GAT_URL, "港台频道源") or ""
    
    # 提取频道
    gat_channels = extract_gat_channels(gat) if gat else []
    log(f"提取后原始频道数: {len(gat_channels)}")
    
    # 清洗名称：去除分辨率标记
    cleaned_channels = [(clean_channel_name(name), url) for name, url in gat_channels]
    log(f"清洗后频道数: {len(cleaned_channels)}")
    
    # 过滤频道（关键词过滤）
    keyword_filtered = [(name, url) for name, url in cleaned_channels if not should_filter_by_keyword(name)]
    log(f"关键词过滤后剩余频道数: {len(keyword_filtered)}")
    
    # 过滤频道（URL过滤）
    url_filtered = [(name, url) for name, url in keyword_filtered if not should_filter_by_url(url)]
    log(f"URL过滤后剩余频道数: {len(url_filtered)}")
    
    # 标准化名称（用于去重）
    normalized_channels = [(normalize_channel_name(name), url) for name, url in url_filtered]
    
    # 去重处理
    deduped_channels = deduplicate_channels(normalized_channels)
    
    # 排序
    sorted_channels = sort_gat_channels(deduped_channels)
    log(f"排序完成")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# EE.m3u
# 生成时间: {timestamp}
# 更新频率: 每天 06:00 / 17:00
# EPG: {EPG_URL}
# GitHub Actions 自动生成

"""

    bb_count = 0
    for line in bb.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        output += line + "\n"
        if line.startswith("#EXTINF"):
            bb_count += 1

    if sorted_channels:
        output += f"\n# {TARGET_GROUP}频道 ({len(sorted_channels)})\n"
        for name, url in sorted_channels:
            output += f'#EXTINF:-1 group-title="{TARGET_GROUP}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(sorted_channels)

    keyword_filtered_count = len(cleaned_channels) - len(keyword_filtered) if cleaned_channels else 0
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
        log("🎉 EE.m3u 生成成功")
        log(f"📺 BB({bb_count}) + {TARGET_GROUP}({len(sorted_channels)}) = {total}")
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
