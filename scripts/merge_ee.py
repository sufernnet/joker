#!/usr/bin/env python3
"""
EE.m3u 合并脚本（港台频道版 + 新聞频道）

功能：
1. HK 从 SOURCE_URL 中提取指定分组
2. TW 从远程 4TV.m3u 提取
3. 将频道分为 HK 和 TW 两个独立分组，无法识别的频道全部归入 TW
4. 过滤掉指定频道（包括三立台、澳门/澳视频道、民視影劇、民視旅遊等）
5. 去除频道名称中的分辨率标记（如“HD 1080p”、“1080p”）
6. 按指定顺序对 HK 和 TW 分组分别排序
7. 合并 BB.m3u
8. 使用固定 EPG

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"

# HK 来源
SOURCE_URL = "https://yang.sufern001.workers.dev/"
HK_SOURCE_GROUP = "• Juli 「精選」"

# TW 来源
TW_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/4TV.m3u"

OUTPUT_FILE = "EE.m3u"

# 输出分组名称
HK_GROUP = "HK"
TW_GROUP = "TW"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 需要过滤掉的频道关键词（不区分大小写）
FILTER_KEYWORDS = [
    # 原有过滤项
    "凤凰电影",
    "人间卫视",
    "邵氏动作",
    "邵氏武侠",
    "邵氏电影",
    "邵氏喜剧",
    "生命电影",
    "ASTV",
    "亚洲卫视",
    "GOODTV",
    "好消息",
    "唐NTD",
    "唐人卫视",
    "唯心电视",
    "星空卫视",
    "星空音乐",
    "華藝中文",
    "中旺电视",
    "中天娱乐",
    "中天新聞",
    "中天新聞1080p(梯子)",
    "中天新聞720p",
    "中天综合",
    "寰宇新聞台",
    "寰宇新聞台720p",
    "年代新聞",
    "東森新聞台",
    
    # 新增过滤项：三立台全部
    "三立台湾台",
    "三立戏剧台",
    "三立都会台",
    "三立综合台",
    "三立新闻台",
    "三立iNEWS",
    
    # 新增过滤项：澳门/澳视频道全部
    "澳门",
    "澳视",
    "澳视澳门",
    "澳视Macau",
    "澳门综艺",
    "澳门体育",
    "澳视高清",
    "澳视生活",
    "澳视中文",
    "澳视体育",
    "澳视新闻",
    "澳视财经",
    
    # 新增过滤项：民視影劇、民視旅遊
    "民視影劇",
    "民视综艺",
    "民视影劇",
    "民視旅遊",
    "民视旅游",
    "民視旅遊台",
    "民视旅游台",
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
    "翡翠台4K": "翡翠台4K",
    "翡翠台": "翡翠台",
    "明珠台": "明珠台",
    "TVB plus": "TVB plus",
    "TVB1": "TVB1",
    "TVBJ1": "TVBJ1",
    "TVB功夫720p": "TVB功夫",
    "TVB千禧经典": "TVB千禧经典",
    "TVB娱乐新闻台720p": "TVB娱乐新闻台",
    "TVB星河720p": "TVB星河",
    "无线新闻台": "无线新闻台",
    "ViuTV": "ViuTV",
    "ViuTV6": "ViuTV6",
    "RHK31": "RHK31",
    "RHK32": "RHK32",
    "CH5综合": "CH5综合",
    "CH8综合": "CH8综合",
    "CHU综合": "CHU综合",
    "CCTV13新闻": "CCTV13新闻",
    "八度空间": "八度空间",
    "天映经典": "天映经典",
    "镜新聞": "镜新聞",
    "民视": "民视",
    "民视台湾台": "民视台湾台",
    "民視新聞台": "民視新聞台",
    "民視第一台": "民視第一台",
    "民视综艺": "民视综艺",
    "CTS華視新聞资讯": "CTS華視新聞资讯",
    "龙华偶像": "龙华偶像",
    "龙华偶像1080": "龙华偶像",
    "龙华戏剧": "龙华戏剧",
    "龙华日韩": "龙华日韩",
    "龙华经典": "龙华经典",
    "中視": "中視",
    "中視新聞": "中視新聞",
    "公視": "公視",
    "台視": "台視",
    "緯來精彩720p": "緯來精彩",
    "环球电视台720p": "环球电视台",
    "台视新闻": "台视新闻",
    "台视综合": "台视综合",
    "TVBS精采台": "TVBS精采台",
    "中视经典": "中视经典",
    "中视菁采": "中视菁采",
    "八大精彩台": "八大精彩台",
    "八大綜藝台": "八大綜藝台",
    "华视": "华视",
    "华视教育体育文化": "华视教育体育文化",
    "非凡新聞HD 720p": "非凡新聞",
}

# 需要优先保留的名称模式（不区分大小写）
PREFERRED_NAMES = [
    "Now新闻",
    "Now体育",
    "Now财经", 
    "Now直播",
    "翡翠台",
    "翡翠台4K",
    "明珠台",
]

# ================== HK频道指定顺序 ==================
HK_ORDER = [
    "凤凰中文",
    "凤凰资讯",
    "凤凰香港台",
    "Now新闻",
    "Now体育",
    "Now财经",
    "Now直播",
    "HOY76",
    "HOY77",
    "HOY78",
    "翡翠台",
    "翡翠台4K",
    "明珠台",
    "TVB plus",
    "TVB1",
    "TVBJ1",
    "TVB功夫",
    "TVB千禧经典",
    "TVB娱乐新闻台",
    "TVB星河",
    "无线新闻台",
    "ViuTV",
    "ViuTV6",
    "RHK31",
    "RHK32",
    "CH5综合",
    "CH8综合",
    "CHU综合",
    "CCTV13新闻",
    "八度空间",
    "天映经典",
]

# ================== TW频道指定顺序 ==================
TW_ORDER = [
    "镜新聞",
    "民视",
    "民视台湾台",
    "民視新聞台",
    "民視第一台",
    "民视综艺",
    "CTS華視新聞资讯",
    "龙华偶像",
    "龙华戏剧",
    "龙华日韩",
    "龙华经典",
    "中視",
    "中視新聞",
    "公視",
    "台視",
    "緯來精彩",
    "环球电视台",
    "台视新闻",
    "台视综合",
    "TVBS精采台",
    "中视经典",
    "中视菁采",
    "八大精彩台",
    "八大綜藝台",
    "华视",
    "华视教育体育文化",
    "非凡新聞",
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


def extract_channels_from_m3u_group(content, target_group):
    """
    从标准 M3U 中提取指定 group-title 的频道
    返回 [(name, url), ...]
    """
    lines = content.splitlines()
    channels = []
    current_group = None
    current_name = None

    log(f"开始从 M3U 中提取分组: {target_group}")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            if 'group-title="' in line:
                try:
                    current_group = line.split('group-title="')[1].split('"')[0]
                except Exception:
                    current_group = None
            else:
                current_group = None

            if "," in line:
                current_name = line.split(",", 1)[1].strip()
            else:
                current_name = None

        elif line.startswith("http"):
            if current_group == target_group and current_name:
                channels.append((current_name, line))
    
    log(f"总共从分组 '{target_group}' 提取到 {len(channels)} 个频道")
    return channels


def extract_channels_from_m3u_all(content):
    """
    从标准 M3U 提取全部频道
    返回 [(name, url), ...]
    """
    lines = content.splitlines()
    channels = []
    current_name = None

    log("开始从 TW M3U 提取全部频道")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            if "," in line:
                current_name = line.split(",", 1)[1].strip()
            else:
                current_name = None

        elif line.startswith("http"):
            if current_name:
                channels.append((current_name, line))

    log(f"总共从 TW M3U 提取到 {len(channels)} 个频道")
    return channels


def clean_channel_name(name):
    """去除频道名称末尾的分辨率标记如 'HD 1080p', '1080p' 等"""
    original = name
    name = re.sub(r'\s*[Hh][Dd]\s*1080[pP]?\s*$', '', name)
    name = re.sub(r'\s*1080[pP]\s*$', '', name)
    name = re.sub(r'\s*[Hh][Dd]\s*$', '', name)
    name = re.sub(r'\s*720[pP]\s*$', '', name)
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
    策略：对于相同内容的频道，优先保留标准名称
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


# ================== 分组判断函数 ==================

def is_hk_channel(name):
    """判断是否为香港频道"""
    hk_identifiers = [
        "凤凰", "Now", "HOY", "翡翠", "明珠", "TVB", "无线", "Viu", "RHK",
        "CH5", "CH8", "CHU", "CCTV13", "八度空间", "天映"
    ]
    name_lower = name.lower()
    for identifier in hk_identifiers:
        if identifier.lower() in name_lower:
            return True
    return False


def is_tw_channel(name):
    """判断是否为台湾频道"""
    tw_identifiers = [
        "镜新聞", "民视", "民視", "華視", "CTS", "龙华", "中視", "公視", 
        "台視", "緯來", "环球", "TVBS", "八大", "华视", "非凡"
    ]
    name_lower = name.lower()
    for identifier in tw_identifiers:
        if identifier.lower() in name_lower:
            return True
    return False


# ================== 自定义排序函数 ==================

def sort_by_custom_order(channels, order_list):
    """
    根据指定的顺序列表对频道进行排序
    不在列表中的频道按名称字母顺序排序，但放在列表内频道的后面
    """
    order_map = {name: i for i, name in enumerate(order_list)}
    
    def key_func(item):
        name, _ = item
        base_name = re.sub(r'\s*(?:HD|1080p|720p|4K).*$', '', name).strip()
        
        if name in order_map:
            return (0, order_map[name])
        elif base_name in order_map:
            return (0, order_map[base_name])
        for idx, order_name in enumerate(order_list):
            if order_name in name:
                return (0, idx)
        return (1, name)
    
    return sorted(channels, key=key_func)


# ================== 主流程 ==================

def main():
    log("开始生成 EE.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    # HK：从 SOURCE_URL 提取指定分组
    hk_content = download(SOURCE_URL, "HK源文件") or ""
    hk_raw_channels = extract_channels_from_m3u_group(hk_content, HK_SOURCE_GROUP) if hk_content else []

    # TW：从 4TV.m3u 提取全部频道
    tw_content = download(TW_URL, "TW 4TV.m3u") or ""
    tw_raw_channels = extract_channels_from_m3u_all(tw_content) if tw_content else []

    log(f"HK 原始频道数: {len(hk_raw_channels)}")
    log(f"TW 原始频道数: {len(tw_raw_channels)}")

    # HK 处理
    hk_cleaned = [(clean_channel_name(name), url) for name, url in hk_raw_channels]
    hk_keyword_filtered = [(name, url) for name, url in hk_cleaned if not should_filter_by_keyword(name)]
    hk_url_filtered = [(name, url) for name, url in hk_keyword_filtered if not should_filter_by_url(url)]
    hk_normalized = [(normalize_channel_name(name), url) for name, url in hk_url_filtered]
    hk_deduped = deduplicate_channels(hk_normalized)

    # TW 处理
    tw_cleaned = [(clean_channel_name(name), url) for name, url in tw_raw_channels]
    tw_keyword_filtered = [(name, url) for name, url in tw_cleaned if not should_filter_by_keyword(name)]
    tw_url_filtered = [(name, url) for name, url in tw_keyword_filtered if not should_filter_by_url(url)]
    tw_normalized = [(normalize_channel_name(name), url) for name, url in tw_url_filtered]
    tw_deduped = deduplicate_channels(tw_normalized)

    # 为保持原逻辑风格，HK 只保留识别为 HK 的；TW 放全部 TW 源
    hk_channels = [(name, url) for name, url in hk_deduped if is_hk_channel(name) or not is_tw_channel(name)]
    tw_channels = tw_deduped

    log(f"HK频道数: {len(hk_channels)}")
    log(f"TW频道数: {len(tw_channels)}")

    # 分别排序
    sorted_hk = sort_by_custom_order(hk_channels, HK_ORDER)
    sorted_tw = sort_by_custom_order(tw_channels, TW_ORDER)

    log("排序完成")

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

    # 写入 HK 分组
    if sorted_hk:
        output += f"\n# {HK_GROUP}频道 ({len(sorted_hk)})\n"
        for name, url in sorted_hk:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n'
            output += f"{url}\n"

    # 写入 TW 分组
    if sorted_tw:
        output += f"\n# {TW_GROUP}频道 ({len(sorted_tw)})\n"
        for name, url in sorted_tw:
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(sorted_hk) + len(sorted_tw)

    hk_keyword_filtered_count = len(hk_cleaned) - len(hk_keyword_filtered) if hk_cleaned else 0
    hk_url_filtered_count = len(hk_keyword_filtered) - len(hk_url_filtered) if hk_keyword_filtered else 0
    hk_deduped_count = len(hk_url_filtered) - len(hk_deduped) if hk_url_filtered else 0

    tw_keyword_filtered_count = len(tw_cleaned) - len(tw_keyword_filtered) if tw_cleaned else 0
    tw_url_filtered_count = len(tw_keyword_filtered) - len(tw_url_filtered) if tw_keyword_filtered else 0
    tw_deduped_count = len(tw_url_filtered) - len(tw_deduped) if tw_url_filtered else 0

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {HK_GROUP}频道数: {len(sorted_hk)}
# {TW_GROUP}频道数: {len(sorted_tw)}
# HK关键词过滤数: {hk_keyword_filtered_count}
# HK URL过滤数: {hk_url_filtered_count}
# HK去重频道数: {hk_deduped_count}
# TW关键词过滤数: {tw_keyword_filtered_count}
# TW URL过滤数: {tw_url_filtered_count}
# TW去重频道数: {tw_deduped_count}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 EE.m3u 生成成功")
        log(f"📺 BB({bb_count}) + HK({len(sorted_hk)}) + TW({len(sorted_tw)}) = {total}")
        if hk_keyword_filtered_count > 0:
            log(f"🗑️ HK 关键词过滤了 {hk_keyword_filtered_count} 个频道")
        if hk_url_filtered_count > 0:
            log(f"🔗 HK URL过滤了 {hk_url_filtered_count} 个频道")
        if hk_deduped_count > 0:
            log(f"🔄 HK 去重了 {hk_deduped_count} 个重复频道")
        if tw_keyword_filtered_count > 0:
            log(f"🗑️ TW 关键词过滤了 {tw_keyword_filtered_count} 个频道")
        if tw_url_filtered_count > 0:
            log(f"🔗 TW URL过滤了 {tw_url_filtered_count} 个频道")
        if tw_deduped_count > 0:
            log(f"🔄 TW 去重了 {tw_deduped_count} 个重复频道")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
