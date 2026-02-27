#!/usr/bin/env python3
"""
xnkl.m3u 直播源分类脚本

功能：
1. 从指定URL获取直播源
2. 按关键词分类：HK（香港）、TW（台湾）、SPORTS（体育）、NATURE（自然）、NEWS（新闻）、ENT（娱乐）、OTHER（其他）
3. 清洗频道名称，去除分辨率标记
4. 去重处理
5. 按分类和优先级排序
6. 生成分类清晰的 M3U 文件

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

SOURCE_URL = "https://feer-cdn-bp.xpnb.qzz.io/xnkl.txt"
OUTPUT_FILE = "xnkl.m3u"

# EPG 配置
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 分类规则 (关键词 => 类别标签)
CATEGORY_RULES = {
    'HK': ['TVB', '明珠', '翡翠', '無線', '無綫', '互動新聞', 'J2', '星河', '鳳凰', '凤凰', 'Now', 'HOY', 'ViuTV'],
    'TW': ['中視', '華視', '民視', '公視', '台視', 'TVBS', '緯來', '龍華', '八大', '東森', '三立'],
    'SPORTS': ['體育', 'SPORTS', '運動', '緯來體育', 'ELTA', '博斯'],
    'NATURE': ['探索', '國家地理', 'NATURE', 'DISCOVERY', '動物星球', '歷史頻道'],
    'NEWS': ['新聞', '新闻', 'NEWS', '资讯', '財經', '天下'],
    'ENT': ['娛樂', '综合', '電影', '影視', 'DRAMA', '戲劇', '綜藝'],
}

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

# ================== 工具 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download(url, desc):
    try:
        log(f"下载 {desc}...")
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = 'utf-8'
        r.raise_for_status()
        log(f"✅ {desc} 下载成功 ({len(r.text)} 字符)")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return None


def clean_channel_name(name):
    """去除频道名称末尾的分辨率标记如 'HD 1080p', '1080p' 等"""
    original = name
    # 去除末尾常见的分辨率标记
    name = re.sub(r'\s*[Hh][Dd]\s*1080[pP]?\s*$', '', name)
    name = re.sub(r'\s*1080[pP]\s*$', '', name)
    name = re.sub(r'\s*[Hh][Dd]\s*$', '', name)
    name = re.sub(r'\s*[0-9]+p\s*$', '', name)  # 如 720p, 480p 等
    name = re.sub(r'\s*[0-9]+P\s*$', '', name)
    # 去除可能留下的空格
    name = name.strip()
    if name != original:
        log(f"清洗名称: '{original}' -> '{name}'")
    return name


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


def categorize_channel(channel_name):
    """
    根据频道名称，通过关键词匹配返回对应的分类标签
    """
    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if re.search(keyword, channel_name, re.IGNORECASE):
                return category
    return 'OTHER'


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
                # 选择最短的名称（通常是不带"台"的标准名称）
                sorted_names = sorted(names, key=len)
                selected = sorted_names[0]
                log(f"  ⚠️ 无优先名称，选择最短的: {selected}")
            
            deduped.append((selected, url))
    
    log(f"去重前频道数: {len(channels)}，去重后: {len(deduped)}")
    return deduped


def parse_m3u(content):
    """
    解析M3U内容，提取频道信息
    """
    channels = []
    lines = content.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF:'):
            info_line = line
            if i + 1 < len(lines):
                url_line = lines[i + 1].strip()
                
                if url_line and (url_line.startswith('http://') or url_line.startswith('https://')):
                    # 提取频道名称
                    channel_name_match = re.search(r',([^,]+)$', info_line)
                    if channel_name_match:
                        channel_name = channel_name_match.group(1).strip()
                    else:
                        channel_name = info_line
                    
                    channels.append((channel_name, url_line))
                    i += 1  # 跳过已处理的URL行
            i += 1
        else:
            i += 1
    
    log(f"解析到 {len(channels)} 个频道")
    return channels


def get_category_priority(category):
    """
    获取分类的显示优先级
    """
    priority_order = ['HK', 'TW', 'SPORTS', 'NATURE', 'NEWS', 'ENT', 'OTHER']
    try:
        return priority_order.index(category)
    except ValueError:
        return len(priority_order)


def sort_channels_by_category(channels_with_cats):
    """
    按分类和名称排序频道
    """
    def sort_key(item):
        channel, category = item
        cat_priority = get_category_priority(category)
        return (cat_priority, channel)
    
    return sorted(channels_with_cats, key=sort_key)


# ================== 主流程 ==================

def main():
    log("开始生成 xnkl.m3u ...")

    # 下载源文件
    content = download(SOURCE_URL, "xnkl.txt")
    if not content:
        log("❌ 下载失败，程序退出")
        return

    # 解析频道
    raw_channels = parse_m3u(content)
    if not raw_channels:
        log("❌ 没有解析到任何频道，程序退出")
        return
    
    log(f"原始频道数: {len(raw_channels)}")
    
    # 清洗名称：去除分辨率标记
    cleaned_channels = [(clean_channel_name(name), url) for name, url in raw_channels]
    log(f"清洗后频道数: {len(cleaned_channels)}")
    
    # 标准化名称（用于去重）
    normalized_channels = [(normalize_channel_name(name), url) for name, url in cleaned_channels]
    
    # 去重处理
    deduped_channels = deduplicate_channels(normalized_channels)
    
    # 分类
    channels_with_cats = [(name, categorize_channel(name), url) for name, url in deduped_channels]
    
    # 按分类分组
    categorized = {}
    for name, category, url in channels_with_cats:
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((name, url))
    
    # 对每个分类内的频道进行排序
    for category in categorized:
        categorized[category].sort(key=lambda x: x[0])  # 按名称排序
    
    # 全局排序（按分类优先级）
    sorted_items = sort_channels_by_category([(name, cat) for name, cat, _ in channels_with_cats])
    sorted_channels_dict = {name: url for name, url in deduped_channels}
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 生成输出文件
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# xnkl.m3u
# 生成时间: {timestamp}
# 原始来源: {SOURCE_URL}
# EPG: {EPG_URL}
# GitHub Actions 自动生成

"""

    # 按分类写入频道
    total_channels = 0
    for category in sorted(categorized.keys(), key=get_category_priority):
        channels = categorized[category]
        if channels:
            total_channels += len(channels)
            output += f"\n# 分类: {category} (共 {len(channels)} 台)\n"
            for name, url in channels:
                output += f'#EXTINF:-1 group-title="{category}",{name}\n'
                output += f"{url}\n"

    # 添加统计信息
    output += f"""
# 统计信息
# 香港(HK)频道数: {len(categorized.get('HK', []))}
# 台湾(TW)频道数: {len(categorized.get('TW', []))}
# 体育(SPORTS)频道数: {len(categorized.get('SPORTS', []))}
# 自然(NATURE)频道数: {len(categorized.get('NATURE', []))}
# 新闻(NEWS)频道数: {len(categorized.get('NEWS', []))}
# 娱乐(ENT)频道数: {len(categorized.get('ENT', []))}
# 其他(OTHER)频道数: {len(categorized.get('OTHER', []))}
# 总频道数: {total_channels}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 xnkl.m3u 生成成功")
        log(f"📺 总频道数: {total_channels}")
        for category in sorted(categorized.keys(), key=get_category_priority):
            count = len(categorized.get(category, []))
            if count > 0:
                log(f"   {category}: {count} 个频道")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
