#!/usr/bin/env python3
"""
DD.m3u 合并脚本（基于 EE.m3u 修改）

功能：
1. 保留 BB.m3u 所有内容
2. 从 https://yang.sufern001.workers.dev 提取 group-title="•台湾「限制」" 的频道作为 TW 分组
3. 清洗 TW 频道名称：去除末尾的「Relay」、「FainTV」、「4gTV」等标记
4. 过滤掉名称全是英文的 TW 频道
5. HK 分组和排序规则完全保留（从原港台大陆源提取）
6. 输出文件为 DD.m3u

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
# 港台大陆源（用于提取HK频道）
GAT_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/港台大陆"
# 新的 TW 源地址
TW_SOURCE_URL = "https://yang.sufern001.workers.dev"
OUTPUT_FILE = "DD.m3u"

# 需要从港台大陆源文件中提取的两个分组名（用于HK）
SOURCE_GROUPS = ["港台频道", "新聞频道"]

# 要提取的目标分组名（从新源中）
TARGET_TW_GROUP = "•台湾「限制」"

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

# 需要从 TW 频道名称中去除的后缀标记
TW_NAME_SUFFIXES_TO_REMOVE = [
    "「Relay」", "「FainTV」", "「4gTV」", "「CatchPlay」",
    "【Relay】", "【FainTV】", "【4gTV】", "【CatchPlay】",
    "(Relay)", "(FainTV)", "(4gTV)", "(CatchPlay)",
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

# ================== 工具函数 ==================

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


def extract_channels_from_file(content, target_groups):
    """
    从文件内容中提取指定分组列表中的所有频道。
    返回一个包含所有找到的频道的列表。
    """
    lines = content.splitlines()
    all_channels = []
    in_section = False
    current_group_marker = None

    log(f"开始从文件中提取分组: {target_groups}")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 检查是否是目标分组的开始标记
        for group in target_groups:
            marker = f"{group},#genre#"
            if marker in line:
                in_section = True
                current_group_marker = group
                log(f"✅ 在第 {i+1} 行找到目标分组: {group}")
                break

        if in_section:
            # 如果遇到下一个分组的标记，则停止当前分组的提取
            if ",#genre#" in line and current_group_marker not in line:
                log(f"到达下一个分组 '{line.split(',')[0]}'，停止提取 '{current_group_marker}'")
                in_section = False
                current_group_marker = None
                continue

            if "," in line and "://" in line:
                name, url = line.split(",", 1)
                all_channels.append((name.strip(), url.strip()))

    log(f"总共从文件中提取到 {len(all_channels)} 个频道")
    return all_channels


def parse_m3u_for_group(content, target_group):
    """
    从 M3U 格式的内容中，提取指定 group-title 的频道。
    返回列表，每个元素为 (频道名称, 流URL)
    """
    lines = content.splitlines()
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # 检查是否包含目标 group-title
            if f'group-title="{target_group}"' in line:
                # 提取频道名称（最后一个逗号之后的部分）
                name_part = line.split(',')[-1].strip()
                # 下一行应该是 URL
                if i + 1 < len(lines) and not lines[i+1].startswith('#'):
                    url = lines[i+1].strip()
                    channels.append((name_part, url))
                    i += 1  # 跳过已处理的 URL 行
            i += 1
        else:
            i += 1
    log(f"从源中提取到 {len(channels)} 个属于 '{target_group}' 的频道")
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


def clean_tw_channel_name(name):
    """清洗 TW 频道名称：去除指定的后缀标记"""
    original = name
    for suffix in TW_NAME_SUFFIXES_TO_REMOVE:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break
    name = name.strip()
    if name != original:
        log(f"清洗 TW 名称: '{original}' -> '{name}'")
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


def is_mostly_english(name):
    """判断频道名称是否主要是英文（用于过滤）"""
    if not name:
        return False
    # 移除中文字符
    non_chinese = re.sub(r'[\u4e00-\u9fff]', '', name)
    non_chinese_stripped = non_chinese.replace(' ', '')
    # 如果非中文字符数量超过总字符数的一半，认为是英文为主
    if len(non_chinese_stripped) > len(name) / 2:
        if re.search('[a-zA-Z]', non_chinese_stripped):
            log(f"过滤全英文/多英文频道: {name}")
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
    log("开始生成 DD.m3u ...")

    # 1. 下载 BB.m3u
    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    # 2. 下载港台大陆源文件（用于提取 HK 频道）
    gat_content = download(GAT_URL, "港台大陆源文件 (用于提取HK)") or ""
    
    # 3. 下载新的 TW 源文件
    tw_source_content = download(TW_SOURCE_URL, "台湾源文件 (用于提取TW)") or ""

    # ================== 处理 HK 频道 ==================
    hk_channels = []
    if gat_content:
        # 从港台大陆源中提取所有频道
        all_source_channels = extract_channels_from_file(gat_content, SOURCE_GROUPS)
        
        # 清洗名称
        cleaned_channels = [(clean_channel_name(name), url) for name, url in all_source_channels]
        
        # 过滤（关键词和URL）
        keyword_filtered = [(name, url) for name, url in cleaned_channels if not should_filter_by_keyword(name)]
        url_filtered = [(name, url) for name, url in keyword_filtered if not should_filter_by_url(url)]
        
        # 标准化名称
        normalized = [(normalize_channel_name(name), url) for name, url in url_filtered]
        
        # 去重
        deduped = deduplicate_channels(normalized)
        
        # 识别并提取 HK 频道
        for name, url in deduped:
            if is_hk_channel(name):
                hk_channels.append((name, url))
        
        log(f"HK 频道处理完成，共 {len(hk_channels)} 个")

    # ================== 处理 TW 频道（来自新源）==================
    tw_channels = []
    if tw_source_content:
        # 从新源中提取目标分组的频道
        tw_raw = parse_m3u_for_group(tw_source_content, TARGET_TW_GROUP)
        
        # 清洗名称（去除后缀）
        tw_cleaned = [(clean_tw_channel_name(name), url) for name, url in tw_raw]
        
        # 过滤英文名称的频道
        tw_no_english = [(name, url) for name, url in tw_cleaned if not is_mostly_english(name)]
        
        # 应用原有的关键词和URL过滤（作为安全网）
        tw_keyword_filtered = [(name, url) for name, url in tw_no_english if not should_filter_by_keyword(name)]
        tw_final = [(name, url) for name, url in tw_keyword_filtered if not should_filter_by_url(url)]
        
        tw_channels = tw_final
        log(f"TW 频道处理完成：原始 {len(tw_raw)} -> 清洗后 {len(tw_cleaned)} -> 过滤英文后 {len(tw_no_english)} -> 最终 {len(tw_final)} 个")

    # 分别排序
    sorted_hk = sort_by_custom_order(hk_channels, HK_ORDER)
    sorted_tw = sort_by_custom_order(tw_channels, TW_ORDER)

    log(f"排序完成")

    # ================== 生成输出文件 ==================
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# DD.m3u
# 生成时间: {timestamp}
# 更新频率: 每天 06:00 / 17:00
# EPG: {EPG_URL}
# GitHub Actions 自动生成

"""

    # 写入 BB 内容
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

    # 写入 TW 分组（来自新源）
    if sorted_tw:
        output += f"\n# {TW_GROUP}频道 ({len(sorted_tw)})\n"
        for name, url in sorted_tw:
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{name}\n'
            output += f"{url}\n"

    # 统计信息
    total = bb_count + len(sorted_hk) + len(sorted_tw)

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {HK_GROUP}频道数: {len(sorted_hk)}
# {TW_GROUP}频道数: {len(sorted_tw)}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 DD.m3u 生成成功")
        log(f"📺 BB({bb_count}) + HK({len(sorted_hk)}) + TW({len(sorted_tw)}) = {total}")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
