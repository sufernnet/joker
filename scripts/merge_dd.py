#!/usr/bin/env python3
"""
DD.m3u 合并脚本（港台频道版）- 最终修复版
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
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# ================== 过滤关键词 ==================
FILTER_KEYWORDS = [
    "凤凰电影", "人间卫视", "邵氏动作", "邵氏武侠", "邵氏电影", "邵氏喜剧",
    "生命电影", "ASTV", "亚洲卫视", "GOODTV", "好消息", "唐NTD", "唐人卫视",
    "唯心电视", "星空卫视", "星空音乐", "華藝中文", "中旺电视",
    "澳门", "澳视", "澳视澳门", "澳视Macau", "澳门综艺", "澳门体育",
    "澳视高清", "澳视生活", "澳视中文", "澳视体育", "澳视新闻", "澳视财经",
    "DW德國之聲", "MCE 我的歐洲電影", "SBN 全球財經",
    "國會頻道 1", "國會頻道 2", "國會頻道1", "國會頻道2",
    "大愛電視", "好萊塢電影", "尼克兒童頻道", "幸福空間居家",
    "影迷數位紀實", "影迷數位電影", "東森幼幼",
    "東森購物 一", "東森購物 二", "東森購物 三", "東森購物 四",
    "歡樂兒童", "韓國娛樂台 KMTV", "韓國娛樂台", "KMTV",
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

# ================== 名称标准化 ==================
NAME_NORMALIZATION = {
    "NOW新闻台": "Now新闻", "NOW新闻台 ": "Now新闻", "Now新闻台": "Now新闻",
    "now新闻台": "Now新闻", "NOW 新闻台": "Now新闻", "Now 新闻台": "Now新闻",
    "翡翠台4K": "翡翠台4K", "翡翠台": "翡翠台", "明珠台": "明珠台",
    "TVB plus": "TVB plus", "TVB1": "TVB1", "TVBJ1": "TVBJ1",
    "TVB功夫720p": "TVB功夫", "TVB千禧经典": "TVB千禧经典",
    "TVB娱乐新闻台720p": "TVB娱乐新闻台", "TVB星河720p": "TVB星河",
    "无线新闻台": "无线新闻台", "ViuTV": "ViuTV", "ViuTV6": "ViuTV6",
    "RHK31": "RHK31", "RHK32": "RHK32", "CH5综合": "CH5综合",
    "CH8综合": "CH8综合", "CHU综合": "CHU综合", "CCTV13新闻": "CCTV13新闻",
    "八度空间": "八度空间", "天映经典": "天映经典", "镜新聞": "镜新聞",
    "民视": "民视", "民视台湾台": "民视台湾台", "民視新聞台": "民視新聞台",
    "民視第一台": "民視第一台", "民视综艺": "民视综艺",
    "CTS華視新聞资讯": "CTS華視新聞资讯", "龙华偶像": "龙华偶像",
    "龙华偶像1080": "龙华偶像", "龙华戏剧": "龙华戏剧", "龙华日韩": "龙华日韩",
    "龙华经典": "龙华经典", "中視": "中視", "中視新聞": "中視新聞",
    "公視": "公視", "台視": "台視", "緯來精彩720p": "緯來精彩",
    "环球电视台720p": "环球电视台", "台视新闻": "台视新闻",
    "台视综合": "台视综合", "TVBS精采台": "TVBS精采台",
    "中视经典": "中视经典", "中视菁采": "中视菁采",
    "八大精彩台": "八大精彩台", "八大綜藝台": "八大綜藝台",
    "华视": "华视", "华视教育体育文化": "华视教育体育文化",
    "非凡新聞HD 720p": "非凡新聞",
}

PREFERRED_NAMES = [
    "Now新闻", "Now体育", "Now财经", "Now直播",
    "翡翠台", "翡翠台4K", "明珠台",
]

# ================== 需要从 TW 频道名称中去除的后缀标记 ==================
TW_NAME_SUFFIXES_TO_REMOVE = [
    "「4gTV」", "「ofiii」", "「FainTV」", "「Relay」", "「CatchPlay」",
    "【4gTV】", "【ofiii】", "【FainTV】", "【Relay】", "【CatchPlay】",
    "(4gTV)", "(ofiii)", "(FainTV)", "(Relay)", "(CatchPlay)",
    "「4GTV」", "「Ofiii」", "「faintv」", "「relay」",
    "「4gtv」", "「OFIII」", "「FAINTV」", "「RELAY」",
]

# ================== HK频道顺序 ==================
HK_ORDER = [
    "凤凰中文", "凤凰资讯", "凤凰香港台", "Now新闻", "Now体育", "Now财经",
    "Now直播", "HOY76", "HOY77", "HOY78", "翡翠台", "翡翠台4K", "明珠台",
    "TVB plus", "TVB1", "TVBJ1", "TVB功夫", "TVB千禧经典", "TVB娱乐新闻台",
    "TVB星河", "无线新闻台", "ViuTV", "ViuTV6", "RHK31", "RHK32",
    "CH5综合", "CH8综合", "CHU综合", "CCTV13新闻", "八度空间", "天映经典",
]

# ================== TW频道顺序 ==================
TW_ORDER = [
    "Love Nature", "Love Nature 4K", "Love Nature 野生", "Love Nature 自然",
    "中天新聞", "中天綜合", "中天娛樂", "中天亞洲",
    "民視", "民視新聞", "民視第一台", "民視台灣台", "民視影劇", "民視綜藝",
    "寰宇新聞", "寰宇新聞台灣", "寰宇新聞2", "寰宇綜合", "寰宇財經",
    "中視", "中視新聞", "中視經典", "中視菁采",
    "三立台灣台", "三立都會台", "三立戲劇台", "三立綜合台", "三立新聞台", "三立iNEWS",
]

GROUP_WEIGHTS = {
    "Love Nature": 1, "中天": 2, "民視": 3, "民视": 3,
    "寰宇": 4, "中視": 5, "中视": 5, "三立": 6, "其他": 7,
}

# ================== 工具函数 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download(url, desc, retries=3):
    for attempt in range(retries):
        try:
            log(f"下载 {desc}... (尝试 {attempt + 1}/{retries})")
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            content = r.text
            if not content or len(content) < 10:
                log(f"⚠️ {desc} 下载内容为空，重试...")
                continue
            log(f"✅ {desc} 下载成功 ({len(content)} 字符)")
            return content
        except Exception as e:
            log(f"❌ {desc} 下载失败 (尝试 {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    return None


def extract_channels_from_file(content, target_groups):
    lines = content.splitlines()
    all_channels = []
    in_section = False
    current_group_marker = None

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        for group in target_groups:
            if f"{group},#genre#" in line:
                in_section = True
                current_group_marker = group
                log(f"✅ 找到目标分组: {group}")
                break

        if in_section:
            if ",#genre#" in line and current_group_marker not in line:
                in_section = False
                current_group_marker = None
                continue

            if "," in line and "://" in line:
                try:
                    name, url = line.split(",", 1)
                    all_channels.append((name.strip(), url.strip()))
                except:
                    continue

    log(f"提取到 {len(all_channels)} 个频道")
    return all_channels


def parse_m3u_for_group(content, target_group):
    if not content:
        return []
    
    lines = content.splitlines()
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            try:
                if f'group-title="{target_group}"' in line:
                    name_part = line.split(',')[-1].strip()
                    if i + 1 < len(lines):
                        url_line = lines[i + 1].strip()
                        if url_line and not url_line.startswith('#'):
                            channels.append((line, name_part, url_line))
                            i += 1
            except:
                pass
        i += 1
    log(f"提取到 {len(channels)} 个属于 '{target_group}' 的频道")
    return channels


def clean_tw_channel_name(name):
    """清洗 TW 频道名称：去除末尾的「4gTV」、「ofiii」等标记"""
    original = name
    cleaned = name
    
    # 方法1：直接匹配硬编码后缀
    for suffix in TW_NAME_SUFFIXES_TO_REMOVE:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
            break
    
    # 方法2：正则匹配末尾的「xxx」格式
    if cleaned == original:
        cleaned = re.sub(r'[「【(][^」】)]*[」】)]$', '', cleaned)
    
    cleaned = cleaned.strip()
    
    if cleaned != original:
        log(f"清洗名称: '{original}' -> '{cleaned}'")
    
    return cleaned


def should_filter_by_keyword(name):
    if not name:
        return False
    name_lower = name.lower()
    for keyword in FILTER_KEYWORDS:
        if keyword.lower() in name_lower:
            log(f"关键词过滤: {name}")
            return True
    return False


def should_filter_by_url(url):
    if not url:
        return False
    for filter_url in FILTER_URLS:
        if url == filter_url or url.startswith(filter_url):
            log(f"URL过滤: {url}")
            return True
    return False


def is_mostly_english(name):
    if not name:
        return False
    non_chinese = re.sub(r'[\u4e00-\u9fff]', '', name)
    non_chinese_stripped = non_chinese.replace(' ', '')
    if len(non_chinese_stripped) > len(name) / 2:
        if re.search('[a-zA-Z]', non_chinese_stripped):
            log(f"过滤英文频道: {name}")
            return True
    return False


def get_tw_group_weight(name):
    if not name:
        return 7
    name_lower = name.lower()
    if "love nature" in name_lower:
        return 1
    if "中天" in name:
        return 2
    if "民視" in name or "民视" in name:
        return 3
    if "寰宇" in name:
        return 4
    if "中視" in name or "中视" in name:
        return 5
    if "三立" in name:
        return 6
    return 7


def sort_tw_by_groups(channels):
    return sorted(channels, key=lambda x: (get_tw_group_weight(x[1]), x[1]))


def sort_by_custom_order(channels, order_list):
    order_map = {name: i for i, name in enumerate(order_list)}
    def key_func(item):
        name, _ = item
        for idx, order_name in enumerate(order_list):
            if order_name in name:
                return (0, idx)
        return (1, name)
    return sorted(channels, key=key_func)


def deduplicate_channels(channels):
    url_groups = {}
    for name, url in channels:
        url_groups.setdefault(url, []).append(name)
    
    deduped = []
    for url, names in url_groups.items():
        if len(names) == 1:
            deduped.append((names[0], url))
        else:
            log(f"重复URL: {url}")
            selected = names[0]
            for name in names:
                if name in PREFERRED_NAMES:
                    selected = name
                    break
            deduped.append((selected, url))
    return deduped


def is_preferred_name(name):
    return name.lower() in [p.lower() for p in PREFERRED_NAMES]


def clean_channel_name(name):
    name = re.sub(r'\s*[Hh][Dd]\s*1080[pP]?\s*$', '', name)
    name = re.sub(r'\s*1080[pP]\s*$', '', name)
    name = re.sub(r'\s*[Hh][Dd]\s*$', '', name)
    name = re.sub(r'\s*720[pP]\s*$', '', name)
    return name.strip()


def normalize_channel_name(name):
    name_stripped = name.strip()
    for variant, standard in NAME_NORMALIZATION.items():
        if name_stripped == variant or name_stripped.lower() == variant.lower():
            return standard
    return name_stripped


def is_hk_channel(name):
    hk_identifiers = ["凤凰", "Now", "HOY", "翡翠", "明珠", "TVB", "无线", "Viu", "RHK", "CH5", "CH8", "CHU", "CCTV13", "八度空间", "天映"]
    name_lower = name.lower()
    return any(identifier.lower() in name_lower for identifier in hk_identifiers)


# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u ...")
    
    try:
        bb = download(BB_URL, "BB.m3u")
        if not bb:
            sys.exit(1)

        gat_content = download(GAT_URL, "港台大陆源文件") or ""
        tw_source_content = download(TW_SOURCE_URL, "台湾源文件") or ""

        # ===== 处理 HK 频道 =====
        hk_channels = []
        if gat_content:
            try:
                all_source = extract_channels_from_file(gat_content, SOURCE_GROUPS)
                cleaned = [(clean_channel_name(name), url) for name, url in all_source]
                keyword_filtered = [(n, u) for n, u in cleaned if not should_filter_by_keyword(n)]
                url_filtered = [(n, u) for n, u in keyword_filtered if not should_filter_by_url(u)]
                normalized = [(normalize_channel_name(n), u) for n, u in url_filtered]
                deduped = deduplicate_channels(normalized)
                hk_channels = [(n, u) for n, u in deduped if is_hk_channel(n)]
                log(f"HK频道: {len(hk_channels)} 个")
            except Exception as e:
                log(f"HK处理出错: {e}")

        # ===== 处理 TW 频道 =====
        tw_channels = []
        if tw_source_content:
            try:
                tw_raw = parse_m3u_for_group(tw_source_content, TARGET_TW_GROUP)
                
                # 调试：打印原始名称
                log("=== 调试信息：原始频道名称 ===")
                for i, (_, name, _) in enumerate(tw_raw[:5]):
                    log(f"  原始 {i+1}: '{name}'")
                
                tw_processed = []
                for extinf_line, original_name, url in tw_raw:
                    try:
                        # 清洗名称
                        cleaned_name = clean_tw_channel_name(original_name)
                        
                        if is_mostly_english(cleaned_name):
                            continue
                        if should_filter_by_keyword(cleaned_name):
                            continue
                        if should_filter_by_url(url):
                            continue
                        
                        tw_processed.append((extinf_line, cleaned_name, url))
                    except Exception as e:
                        continue
                
                # 调试：打印清洗后的名称
                log("=== 调试信息：清洗后频道名称 ===")
                for i, (_, name, _) in enumerate(tw_processed[:5]):
                    log(f"  清洗后 {i+1}: '{name}'")
                
                tw_channels = tw_processed
                log(f"TW频道: {len(tw_channels)} 个")
            except Exception as e:
                log(f"TW处理出错: {e}")

        # 排序
        sorted_hk = sort_by_custom_order(hk_channels, HK_ORDER)
        sorted_tw = sort_tw_by_groups(tw_channels)

        # ===== 生成输出文件 =====
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
        output += f"# DD.m3u\n# 生成时间: {timestamp}\n\n"

        # 写入 BB
        bb_count = 0
        for line in bb.splitlines():
            if not line.startswith("#EXTM3U"):
                output += line + "\n"
                if line.startswith("#EXTINF"):
                    bb_count += 1

        # 写入 HK
        if sorted_hk:
            output += f"\n# {HK_GROUP}频道 ({len(sorted_hk)})\n"
            for name, url in sorted_hk:
                output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n{url}\n'

        # ===== ⚠️ 修复：写入 TW 分组时，使用清洗后的名称 =====
        if sorted_tw:
            output += f"\n# {TW_GROUP}频道 ({len(sorted_tw)})\n"
            for extinf_line, cleaned_name, url in sorted_tw:
                try:
                    # 步骤1：先替换 group-title
                    modified = re.sub(r'group-title="[^"]*"', f'group-title="{TW_GROUP}"', extinf_line)
                    
                    # 步骤2：再替换末尾的频道名称（最后一个逗号之后的部分）
                    # 原始名称在 extinf_line 中是在最后一个逗号之后
                    parts = modified.rsplit(',', 1)
                    if len(parts) == 2:
                        # 用清洗后的名称替换原始名称
                        modified = parts[0] + ',' + cleaned_name
                    
                    output += modified + "\n" + url + "\n"
                except Exception as e:
                    # 降级处理：如果替换失败，使用简单格式
                    log(f"⚠️ 写入失败，使用降级格式: {cleaned_name}")
                    output += f'#EXTINF:-1 group-title="{TW_GROUP}",{cleaned_name}\n{url}\n'

        # 统计
        total = bb_count + len(sorted_hk) + len(sorted_tw)
        output += f"\n# 统计: BB({bb_count}) + HK({len(sorted_hk)}) + TW({len(sorted_tw)}) = {total}\n"

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log(f"✅ 生成成功！总频道: {total}")

    except Exception as e:
        log(f"❌ 失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
