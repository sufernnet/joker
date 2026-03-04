#!/usr/bin/env python3
"""
DD.m3u 合并脚本（台湾直提 + 精确过滤与排序）

功能：
1. 从 https://tv.iill.top/m3u/Gather 提取“•台湾「限制」”分组
2. 重命名为“台湾”
3. 过滤掉指定频道和指定URL
4. 去重处理：保留标准名称，去掉重复频道
5. 台湾分组内按规则排序
6. 合并 BB.m3u
7. 使用固定 EPG

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
# 更新为新的源地址
GATHER_URL = "https://tv.iill.top/m3u/Gather"
OUTPUT_FILE = "DD.m3u"

SOURCE_GROUP = "•台湾「限制」"
TARGET_GROUP = "台湾"

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
    "中旺电视",
    "公视台语台",  # 保留公视的其他频道
]

# 需要过滤掉的特定URL（精确匹配）
FILTER_URLS = [
    "http://iptv.4666888.xyz/iptv2A.php?id=27",  # 凤凰中文特定源
]

# 频道名称标准化映射（用于去重）
NAME_NORMALIZATION = {
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

# 需要优先保留的名称模式（不区分大小写）
PREFERRED_NAMES = [
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

# ================== 工具 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download(url, desc):
    try:
        log(f"下载 {desc}...")
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        log(f"✅ {desc} 下载成功 ({len(r.text)} 字符)")
        
        # 打印前500个字符以便调试
        log(f"内容预览: {r.text[:500]}")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return None


def extract_gather_channels(content):
    """
    更灵活地提取特定分组的频道
    支持多种M3U格式：
    1. 标准格式：#EXTINF:-1 group-title="分组名",频道名\nURL
    2. 简单格式：频道名,URL
    3. 带注释的格式
    """
    lines = content.splitlines()
    channels = []
    in_target_group = False
    group_marker_found = False
    
    # 先尝试找到目标分组标记
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # 检查是否是分组标记行
        if (f"{SOURCE_GROUP},#genre#" in line or 
            f'group-title="{SOURCE_GROUP}"' in line or
            f"# {SOURCE_GROUP}" in line or
            SOURCE_GROUP in line and "#genre#" in line):
            group_marker_found = True
            in_target_group = True
            log(f"✅ 在第 {i+1} 行找到目标分组标记: {line}")
            continue
        
        # 如果已经在目标分组内
        if in_target_group:
            # 检查是否进入下一个分组（多种可能的分组标记）
            if (",#genre#" in line or 
                ('group-title="' in line and not f'group-title="{SOURCE_GROUP}"' in line) or
                (line.startswith("# ") and "频道" in line)):
                log(f"到达下一个分组: {line}")
                break
            
            # 提取频道信息
            if "://" in line:  # 包含URL的行
                # 检查前一行是否是EXTINF
                prev_line = lines[i-1].strip() if i > 0 else ""
                
                if prev_line.startswith("#EXTINF"):
                    # 标准M3U格式
                    match = re.search(r'tvg-name="([^"]+)"|,([^,]+)$', prev_line)
                    if match:
                        name = match.group(1) or match.group(2)
                        channels.append((name.strip(), line.strip()))
                        log(f"提取频道(标准格式): {name} -> {line[:50]}...")
                elif "," in line and not line.startswith("#"):
                    # 简单格式：频道名,URL
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        name, url = parts
                        channels.append((name.strip(), url.strip()))
                        log(f"提取频道(简单格式): {name} -> {url[:50]}...")
    
    # 如果没有找到分组标记，尝试直接搜索频道
    if not group_marker_found:
        log("未找到分组标记，尝试直接搜索频道...")
        for line in lines:
            line = line.strip()
            if "://" in line and "," in line and not line.startswith("#"):
                parts = line.split(",", 1)
                if len(parts) == 2:
                    name, url = parts
                    # 检查是否是台湾相关的频道（可以根据你的频道列表判断）
                    taiwan_keywords = ["翡翠", "明珠", "TVB", "Viu", "凤凰", "Now", "RHK", "HOY"]
                    if any(k in name for k in taiwan_keywords):
                        channels.append((name.strip(), url.strip()))
                        log(f"直接提取频道: {name} -> {url[:50]}...")
    
    log(f"总共提取到 {len(channels)} 个频道")
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
    
    # 先去除常见的后缀
    name_clean = re.sub(r'\s*(1080p|720p|540p|4K|HD|FHD|UHD|\([^)]*\)|\[[^\]]*\])\s*$', '', name_stripped, flags=re.IGNORECASE).strip()
    
    # 检查是否需要标准化
    for variant, standard in NAME_NORMALIZATION.items():
        if (name_clean == variant or name_clean.lower() == variant.lower() or
            name_stripped == variant or name_stripped.lower() == variant.lower()):
            log(f"标准化名称: '{name_stripped}' -> '{standard}'")
            return standard
    
    return name_clean


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
    策略：对于相同内容的频道，优先保留标准名称
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
            
            # 如果没有优先名称，选择最短的
            if not selected:
                # 按长度排序，选最短的
                sorted_names = sorted(names, key=len)
                selected = sorted_names[0]
                log(f"  ⚠️ 无优先名称，选择最短的: {selected}")
            
            deduped.append((selected, url))
    
    log(f"去重前频道数: {len(channels)}，去重后: {len(deduped)}")
    return deduped


def sort_taiwan_channels(channels):
    """
    台湾频道排序（越小越靠前）：
    0: 翡翠台系列
    1: 明珠台
    2: TVB系列 (J1, plus, 星河, 千禧, 功夫等)
    3: ViuTV
    4: 凤凰系列
    5: Now系列
    6: RHK系列
    7: HOY系列
    8: 其他
    """
    def weight(name):
        name_lower = name.lower()
        
        # 翡翠台系列
        if "翡翠台" in name:
            if "4k" in name_lower:
                return (0, "00_翡翠台4K")
            return (0, "00_翡翠台1080p")
        
        # 明珠台
        if "明珠台" in name:
            return (1, "01_明珠台")
        
        # TVB系列
        if "tvb" in name_lower:
            if "j1" in name_lower or "tvbj1" in name_lower:
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
        
        # ViuTV
        if "viu" in name_lower:
            if "viutv6" in name_lower:
                return (3, "03_ViuTV6")
            return (3, "03_ViuTV")
        
        # 凤凰系列
        if "凤凰" in name:
            if "中文" in name:
                return (4, "04_凤凰中文")
            if "资讯" in name:
                return (4, "04_凤凰资讯")
            if "香港" in name:
                return (4, "04_凤凰香港")
            return (4, f"04_凤凰_{name}")
        
        # Now系列
        if "now" in name_lower:
            if "财经" in name:
                return (5, "05_Now财经")
            if "直播" in name:
                return (5, "05_Now直播")
            if "体育" in name:
                return (5, "05_Now体育")
            return (5, f"05_Now_{name}")
        
        # RHK系列
        if "rhk" in name_lower or "rthk" in name_lower:
            if "31" in name:
                return (6, "06_RHK31")
            if "32" in name:
                return (6, "06_RHK32")
            return (6, f"06_RHK_{name}")
        
        # HOY系列
        if "hoy" in name_lower:
            if "76" in name:
                return (7, "07_HOY76")
            if "77" in name:
                return (7, "07_HOY77")
            if "78" in name:
                return (7, "07_HOY78")
            return (7, f"07_HOY_{name}")
        
        # 其他频道
        return (8, name)

    return sorted(channels, key=lambda x: weight(x[0]))


# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    gather = download(GATHER_URL, "Gather直播源") or ""
    
    # 提取频道
    taiwan_channels = extract_gather_channels(gather) if gather else []
    log(f"提取后原始频道数: {len(taiwan_channels)}")
    
    # 打印前5个频道以便调试
    for i, (name, url) in enumerate(taiwan_channels[:5]):
        log(f"示例频道 {i+1}: {name} -> {url[:50]}...")
    
    # 过滤频道（关键词过滤）
    keyword_filtered = [(name, url) for name, url in taiwan_channels if not should_filter_by_keyword(name)]
    log(f"关键词过滤后剩余频道数: {len(keyword_filtered)}")
    
    # 过滤频道（URL过滤）
    url_filtered = [(name, url) for name, url in keyword_filtered if not should_filter_by_url(url)]
    log(f"URL过滤后剩余频道数: {len(url_filtered)}")
    
    # 先标准化名称
    normalized_channels = [(normalize_channel_name(name), url) for name, url in url_filtered]
    
    # 去重处理
    deduped_channels = deduplicate_channels(normalized_channels)
    
    # 排序
    sorted_channels = sort_taiwan_channels(deduped_channels)
    log(f"排序完成，共 {len(sorted_channels)} 个频道")

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

    # ===== 台湾 =====
    if sorted_channels:
        output += f"\n# {TARGET_GROUP}频道 ({len(sorted_channels)})\n"
        for name, url in sorted_channels:
            output += f'#EXTINF:-1 group-title="{TARGET_GROUP}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(sorted_channels)

    # 统计过滤和去重数量
    keyword_filtered_count = len(taiwan_channels) - len(keyword_filtered) if taiwan_channels else 0
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
        log(f"📺 BB({bb_count}) + 台湾({len(sorted_channels)}) = {total}")
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
