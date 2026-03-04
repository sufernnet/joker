#!/usr/bin/env python3
"""
DD.m3u 合并脚本（香港+台湾双分组）

功能：
1. 从原链接提取香港频道（剔除720p）
2. 从 https://tv.iill.top/m3u/Gather 提取台湾频道
3. 分别放入"香港"和"台湾"两个分组
4. 过滤掉指定频道和指定URL
5. 去重处理
6. 各自分组内按规则排序
7. 合并 BB.m3u
8. 使用固定 EPG

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
HK_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
TW_URL = "https://tv.iill.top/m3u/Gather"
OUTPUT_FILE = "DD.m3u"

HK_SOURCE_GROUP = "🔮[三网]港澳台直播"
TW_SOURCE_GROUP = "•台湾「限制」"
HK_TARGET_GROUP = "香港"
TW_TARGET_GROUP = "台湾"

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
    "中旺电视",
    "中天新闻",  # 台湾可能不需要的频道
    "中视",
    "华视",
]

# 需要过滤掉的特定URL（精确匹配）
FILTER_URLS = [
    "http://iptv.4666888.xyz/iptv2A.php?id=27",  # 凤凰中文特定源
]

# ================== 香港频道配置 ==================

# 香港频道名称标准化映射
HK_NAME_NORMALIZATION = {
    "NOW新闻台": "Now新闻",
    "NOW新闻台 ": "Now新闻",
    "Now新闻台": "Now新闻",
    "now新闻台": "Now新闻",
    "NOW 新闻台": "Now新闻",
    "Now 新闻台": "Now新闻",
}

# 香港频道优先保留名称
HK_PREFERRED_NAMES = [
    "Now新闻",
    "Now体育",
    "Now财经", 
    "Now直播",
]

# 香港频道需要剔除的分辨率（720p及以下）
HK_RESOLUTION_FILTER = ["720p", "540p", "480p", "360p"]

# ================== 台湾频道配置 ==================

# 台湾频道名称标准化映射
TW_NAME_NORMALIZATION = {
    "TVB J1": "TVBJ1",
    "TVB J1 ": "TVBJ1",
    "TVB J1 1080p": "TVBJ1",
    "TVB J1 1080p ": "TVBJ1",
    "TVB J1 HD": "TVBJ1",
    "TVB J1 HD ": "TVBJ1",
    "TVB Plus 1080p": "TVB plus",
    "TVB Plus 1080p ": "TVB plus",
    "TVB Plus HD": "TVB plus",
    "TVB Plus": "TVB plus",
    "TVB 星河": "TVB星河",
    "TVB 星河 720p": "TVB星河",
    "TVB星河 720p": "TVB星河",
    "TVB星河 HD": "TVB星河",
    "TVB 无线千禧": "TVB无线千禧",
    "TVB 无线千禧 1080p": "TVB无线千禧",
    "TVB千禧经典 1080p": "TVB千禧经典",
    "TVB千禧经典 540p": "TVB千禧经典",
    "TVB千禧经典 HD": "TVB千禧经典",
    "TVB 功夫": "TVB功夫",
    "TVB 功夫 720p": "TVB功夫",
    "TVB功夫 HD": "TVB功夫",
    "Now 财经": "Now财经",
    "Now 财经 1080p": "Now财经",
    "Now 财经 HD": "Now财经",
    "Now 直播": "Now直播",
    "Now 直播 1080p": "Now直播",
    "Now 直播 HD": "Now直播",
    "Now 体育": "Now体育",
    "Now 体育 1080p": "Now体育",
    "Now 体育 HD": "Now体育",
    "RHK 31": "RHK31",
    "RHK 31 1080p": "RHK31",
    "RTHK 31": "RHK31",
    "RHK 32": "RHK32",
    "RHK 32 1080p": "RHK32",
    "RTHK 32": "RHK32",
    "HOY 76": "HOY76",
    "HOY 76 1080p": "HOY76",
    "HOY 77": "HOY77",
    "HOY 77 1080p": "HOY77",
    "HOY 78": "HOY78",
    "HOY 78 1080p": "HOY78",
    "凤凰中文 HD": "凤凰中文",
    "凤凰中文 HD 1080p": "凤凰中文",
    "凤凰中文 1080p": "凤凰中文",
    "凤凰资讯 HD": "凤凰资讯",
    "凤凰资讯 HD 1080p": "凤凰资讯",
    "凤凰资讯 1080p": "凤凰资讯",
    "凤凰香港台 HD": "凤凰香港台",
    "凤凰香港台 1080p": "凤凰香港台",
    "ViuTV 1080p": "ViuTV",
    "ViuTV HD": "ViuTV",
    "ViuTV6 1080p": "ViuTV6",
    "ViuTV6 HD": "ViuTV6",
}

# 台湾频道优先保留名称
TW_PREFERRED_NAMES = [
    "翡翠台",
    "明珠台",
    "TVB plus",
    "TVBJ1",
    "TVB星河",
    "TVB无线千禧",
    "TVB千禧经典",
    "TVB功夫",
    "ViuTV",
    "ViuTV6",
    "凤凰中文",
    "凤凰资讯",
    "凤凰香港台",
    "Now财经",
    "Now直播",
    "Now体育",
    "RHK31",
    "RHK32",
    "HOY76",
    "HOY77",
    "HOY78",
]

# ================== 通用工具 ==================

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


def extract_channels_simple(content, source_group):
    """简单格式提取（用于香港源）"""
    lines = content.splitlines()
    channels = []
    in_section = False
    marker = f"{source_group},#genre#"

    log(f"开始提取分组：{source_group}")

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


def extract_channels_m3u(content, source_group):
    """M3U格式提取（用于台湾源）"""
    lines = content.splitlines()
    channels = []
    in_target_group = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # 检查是否是分组标记行
        if (f"{source_group},#genre#" in line or 
            f'group-title="{source_group}"' in line or
            f"# {source_group}" in line):
            in_target_group = True
            log(f"✅ 在第 {i+1} 行找到目标分组: {line}")
            continue
        
        # 如果已经在目标分组内
        if in_target_group:
            # 检查是否进入下一个分组
            if (",#genre#" in line or 
                ('group-title="' in line and not f'group-title="{source_group}"' in line)):
                log("到达下一个分组，停止提取")
                break
            
            # 提取频道信息
            if "://" in line:
                prev_line = lines[i-1].strip() if i > 0 else ""
                
                if prev_line.startswith("#EXTINF"):
                    # 标准M3U格式
                    match = re.search(r'group-title="[^"]*"[^,]*,(.+)$', prev_line)
                    if match:
                        name = match.group(1).strip()
                        channels.append((name, line))
                        log(f"提取频道: {name}")
                elif "," in line and not line.startswith("#"):
                    # 简单格式
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        name, url = parts
                        channels.append((name.strip(), url.strip()))
                        log(f"提取频道: {name}")
    
    log(f"总共提取到 {len(channels)} 个频道")
    return channels


def should_filter_by_keyword(name, custom_keywords=None):
    """根据关键词检查频道名称是否应该被过滤"""
    keywords = custom_keywords if custom_keywords else FILTER_KEYWORDS
    name_lower = name.lower()
    for keyword in keywords:
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


def should_filter_by_resolution(name, resolution_list):
    """根据分辨率过滤"""
    name_lower = name.lower()
    for res in resolution_list:
        if res.lower() in name_lower:
            log(f"分辨率过滤频道: {name} (匹配: {res})")
            return True
    return False


def normalize_channel_name(name, normalization_map):
    """标准化频道名称"""
    name_stripped = name.strip()
    
    # 先去除常见的后缀
    name_clean = re.sub(r'\s*(1080p|720p|540p|4K|HD|FHD|UHD|\([^)]*\)|\[[^\]]*\])\s*$', '', name_stripped, flags=re.IGNORECASE).strip()
    
    # 检查是否需要标准化
    for variant, standard in normalization_map.items():
        if (name_clean == variant or name_clean.lower() == variant.lower() or
            name_stripped == variant or name_stripped.lower() == variant.lower()):
            log(f"标准化名称: '{name_stripped}' -> '{standard}'")
            return standard
    
    return name_clean


def is_preferred_name(name, preferred_names):
    """检查是否为优先保留的名称"""
    name_lower = name.lower()
    for preferred in preferred_names:
        if name_lower == preferred.lower():
            return True
    return False


def deduplicate_channels(channels, preferred_names):
    """去重处理"""
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
            deduped.append((names[0], url))
        else:
            log(f"发现重复URL: {url}")
            for name in names:
                log(f"  - 名称变体: {name}")
            
            # 优先选择标准名称
            selected = None
            for name in names:
                if is_preferred_name(name, preferred_names):
                    selected = name
                    log(f"  ✅ 选择优先名称: {name}")
                    break
            
            # 如果没有优先名称，选择最短的
            if not selected:
                sorted_names = sorted(names, key=len)
                selected = sorted_names[0]
                log(f"  ⚠️ 无优先名称，选择最短的: {selected}")
            
            deduped.append((selected, url))
    
    log(f"去重前频道数: {len(channels)}，去重后: {len(deduped)}")
    return deduped


def sort_hk_channels(channels):
    """香港频道排序"""
    def weight(name):
        name_lower = name.lower()
        
        if "凤凰中文" in name:
            return (0, "00_凤凰中文")
        if "凤凰资讯" in name:
            return (1, "01_凤凰资讯")
        if "now新闻" in name_lower:
            return (2, "02_NOW新闻")
        if "now体育" in name_lower:
            return (3, "03_NOW体育")
        if "now财经" in name_lower:
            return (4, "04_NOW财经")
        if "now直播" in name_lower:
            return (5, "05_NOW直播")
        if "popc" in name_lower:
            return (6, "06_POPC")
        if "hoy" in name_lower and any(x in name_lower for x in ["76", "77", "78"]):
            return (7, f"07_HOY_{name}")
        if "rhk" in name_lower and any(x in name_lower for x in ["31", "32"]):
            return (8, f"08_RHK_{name}")
        if "tvb" in name_lower:
            if "翡翠" in name:
                return (9, "09_TVB翡翠")
            return (9, f"09_TVB_{name}")
        return (10, name)
    
    return sorted(channels, key=lambda x: weight(x[0]))


def sort_tw_channels(channels):
    """台湾频道排序"""
    def weight(name):
        name_lower = name.lower()
        
        if "翡翠台" in name:
            if "4k" in name_lower:
                return (0, "00_翡翠台4K")
            return (0, "00_翡翠台1080p")
        if "明珠台" in name:
            return (1, "01_明珠台")
        if "tvb" in name_lower:
            if "j1" in name_lower:
                return (2, "02_TVBJ1")
            if "plus" in name_lower:
                return (2, "02_TVBplus")
            if "星河" in name:
                return (2, "02_TVB星河")
            if "千禧" in name:
                return (2, "02_TVB千禧")
            if "功夫" in name:
                return (2, "02_TVB功夫")
            return (2, f"02_TVB_{name}")
        if "viu" in name_lower:
            if "viutv6" in name_lower:
                return (3, "03_ViuTV6")
            return (3, "03_ViuTV")
        if "凤凰" in name:
            if "中文" in name:
                return (4, "04_凤凰中文")
            if "资讯" in name:
                return (4, "04_凤凰资讯")
            if "香港" in name:
                return (4, "04_凤凰香港")
            return (4, f"04_凤凰_{name}")
        if "now" in name_lower:
            if "财经" in name:
                return (5, "05_Now财经")
            if "直播" in name:
                return (5, "05_Now直播")
            if "体育" in name:
                return (5, "05_Now体育")
            return (5, f"05_Now_{name}")
        if "rhk" in name_lower or "rthk" in name_lower:
            if "31" in name:
                return (6, "06_RHK31")
            if "32" in name:
                return (6, "06_RHK32")
            return (6, f"06_RHK_{name}")
        if "hoy" in name_lower:
            if "76" in name:
                return (7, "07_HOY76")
            if "77" in name:
                return (7, "07_HOY77")
            if "78" in name:
                return (7, "07_HOY78")
            return (7, f"07_HOY_{name}")
        return (8, name)
    
    return sorted(channels, key=lambda x: weight(x[0]))


def process_channels(channels, 
                    normalization_map, 
                    preferred_names, 
                    sort_func,
                    resolution_filter=None):
    """处理频道流程：过滤、标准化、去重、排序"""
    if not channels:
        return []
    
    # 分辨率过滤
    if resolution_filter:
        channels = [(name, url) for name, url in channels 
                   if not should_filter_by_resolution(name, resolution_filter)]
        log(f"分辨率过滤后剩余: {len(channels)}")
    
    # 关键词过滤
    keyword_filtered = [(name, url) for name, url in channels 
                       if not should_filter_by_keyword(name)]
    log(f"关键词过滤后剩余: {len(keyword_filtered)}")
    
    # URL过滤
    url_filtered = [(name, url) for name, url in keyword_filtered 
                   if not should_filter_by_url(url)]
    log(f"URL过滤后剩余: {len(url_filtered)}")
    
    # 标准化名称
    normalized = [(normalize_channel_name(name, normalization_map), url) 
                  for name, url in url_filtered]
    
    # 去重
    deduped = deduplicate_channels(normalized, preferred_names)
    
    # 排序
    sorted_channels = sort_func(deduped)
    
    return sorted_channels


# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    # 下载香港源
    hk_content = download(HK_URL, "香港直播源") or ""
    
    # 下载台湾源
    tw_content = download(TW_URL, "台湾直播源") or ""
    
    # 提取香港频道
    hk_raw = extract_channels_simple(hk_content, HK_SOURCE_GROUP) if hk_content else []
    log(f"香港原始频道数: {len(hk_raw)}")
    
    # 提取台湾频道
    tw_raw = extract_channels_m3u(tw_content, TW_SOURCE_GROUP) if tw_content else []
    log(f"台湾原始频道数: {len(tw_raw)}")
    
    # 处理香港频道（剔除720p）
    hk_channels = process_channels(
        hk_raw,
        HK_NAME_NORMALIZATION,
        HK_PREFERRED_NAMES,
        sort_hk_channels,
        resolution_filter=HK_RESOLUTION_FILTER
    )
    log(f"香港处理后频道数: {len(hk_channels)}")
    
    # 处理台湾频道
    tw_channels = process_channels(
        tw_raw,
        TW_NAME_NORMALIZATION,
        TW_PREFERRED_NAMES,
        sort_tw_channels
    )
    log(f"台湾处理后频道数: {len(tw_channels)}")

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

    # ===== 香港 =====
    if hk_channels:
        output += f"\n# {HK_TARGET_GROUP}频道 ({len(hk_channels)})\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="{HK_TARGET_GROUP}",{name}\n'
            output += f"{url}\n"

    # ===== 台湾 =====
    if tw_channels:
        output += f"\n# {TW_TARGET_GROUP}频道 ({len(tw_channels)})\n"
        for name, url in tw_channels:
            output += f'#EXTINF:-1 group-title="{TW_TARGET_GROUP}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(hk_channels) + len(tw_channels)

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# 香港频道数: {len(hk_channels)}
# 台湾频道数: {len(tw_channels)}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 DD.m3u 生成成功")
        log(f"📺 BB({bb_count}) + 香港({len(hk_channels)}) + 台湾({len(tw_channels)}) = {total}")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
