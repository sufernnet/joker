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

源地址：https://xnkl.sufern001.workers.dev/
输出文件：xnkl.m3u (放在仓库根目录)
"""

import requests
import re
import os
from datetime import datetime

# ================== 配置区域 ==================

# 原始直播源URL - 已更新为你指定的地址
SOURCE_URL = "https://xnkl.sufern001.workers.dev/"

# 输出文件名（将生成在仓库根目录）
OUTPUT_FILE = "xnkl.m3u"

# EPG 地址
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 分类规则 (关键词 => 类别标签)
CATEGORY_RULES = {
    'HK': [
        'TVB', '明珠', '翡翠', '無線', '無綫', '互動新聞', 'J2', '星河', 
        '鳳凰', '凤凰', 'Now', 'HOY', 'ViuTV', '無線新聞', '無線財經'
    ],
    'TW': [
        '中視', '華視', '民視', '公視', '台視', 'TVBS', '緯來', '龍華', 
        '八大', '東森', '三立', '非凡', '年代', '壹電視', '中天'
    ],
    'SPORTS': [
        '體育', 'SPORTS', '運動', '緯來體育', 'ELTA', '博斯', 'Eleven', 
        '愛爾達', '福斯體育'
    ],
    'NATURE': [
        '探索', '國家地理', 'NATURE', 'DISCOVERY', '動物星球', '歷史頻道',
        '知識', '紀實'
    ],
    'NEWS': [
        '新聞', '新闻', 'NEWS', '资讯', '財經', '天下', 'CNN', 'BBC',
        'CNA', '寰宇新聞'
    ],
    'ENT': [
        '娛樂', '综合', '電影', '影視', 'DRAMA', '戲劇', '綜藝', '星衛',
        'HBO', 'CINEMAX', 'FOX'
    ],
}

# 频道名称标准化映射（用于去重）
NAME_NORMALIZATION = {
    "NOW新闻台": "Now新闻",
    "NOW新闻台 ": "Now新闻",
    "Now新闻台": "Now新闻",
    "now新闻台": "Now新闻",
    "NOW 新闻台": "Now新闻",
    "Now 新闻台": "Now新闻",
    "TVB無線新聞台": "TVB無線新聞",
    "TVB無線財經台": "TVB無線財經",
}

# 需要优先保留的名称模式（不区分大小写）
PREFERRED_NAMES = [
    "Now新闻",
    "Now体育",
    "Now财经", 
    "Now直播",
    "TVB無線新聞",
    "TVB無線財經",
]

# ================== 工具函数 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download_source(url, desc):
    """下载源文件，增加对 workers.dev 的特殊处理"""
    try:
        log(f"📥 下载 {desc}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/plain,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        # 对于 workers.dev 可能需要禁用 SSL 验证或增加超时
        r = requests.get(url, timeout=30, headers=headers)
        r.encoding = 'utf-8'
        r.raise_for_status()
        
        # 检查返回内容是否有效
        content = r.text
        if len(content.strip()) == 0:
            log(f"⚠️ {desc} 返回内容为空")
            return None
            
        log(f"✅ {desc} 下载成功 ({len(content)} 字符)")
        return content
        
    except requests.exceptions.SSLError as e:
        log(f"❌ {desc} SSL错误: {e}")
        return None
    except requests.exceptions.Timeout:
        log(f"❌ {desc} 下载超时")
        return None
    except requests.exceptions.RequestException as e:
        log(f"❌ {desc} 下载失败: {e}")
        return None
    except Exception as e:
        log(f"❌ {desc} 未知错误: {e}")
        return None


def clean_channel_name(name):
    """去除频道名称末尾的分辨率标记"""
    original = name
    # 去除各种分辨率标记
    name = re.sub(r'\s*[Hh][Dd]\s*1080[pP]?\s*$', '', name)
    name = re.sub(r'\s*1080[pP]\s*$', '', name)
    name = re.sub(r'\s*[Hh][Dd]\s*$', '', name)
    name = re.sub(r'\s*[0-9]+p\s*$', '', name)
    name = re.sub(r'\s*[0-9]+P\s*$', '', name)
    name = re.sub(r'\s*FHD\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*4K\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*UHD\s*$', '', name, flags=re.IGNORECASE)
    name = name.strip()
    if name != original:
        log(f"  清洗名称: '{original}' -> '{name}'")
    return name


def normalize_channel_name(name):
    """标准化频道名称（用于去重）"""
    name_stripped = name.strip()
    
    for variant, standard in NAME_NORMALIZATION.items():
        if name_stripped == variant or name_stripped.lower() == variant.lower():
            log(f"  标准化: '{name}' -> '{standard}'")
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
    """根据频道名称分类"""
    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if re.search(keyword, channel_name, re.IGNORECASE):
                return category
    return 'OTHER'


def deduplicate_channels(channels):
    """去重处理：相同URL的频道，优先保留标准名称"""
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
            log(f"  发现重复URL: {url[:50]}...")
            for name in names:
                log(f"    - 名称变体: {name}")
            
            selected = None
            for name in names:
                if is_preferred_name(name):
                    selected = name
                    log(f"    ✅ 选择优先名称: {name}")
                    break
            
            if not selected:
                sorted_names = sorted(names, key=len)
                selected = sorted_names[0]
                log(f"    ⚠️ 选择最短名称: {selected}")
            
            deduped.append((selected, url))
    
    log(f"  去重前: {len(channels)}，去重后: {len(deduped)}")
    return deduped


def parse_m3u(content):
    """解析M3U内容，提取频道信息"""
    channels = []
    lines = content.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 兼容处理：有些文件可能以 #EXTINF 开头，有些可能直接是 "频道名,URL" 格式
        if line.startswith('#EXTINF:'):
            info_line = line
            if i + 1 < len(lines):
                url_line = lines[i + 1].strip()
                if url_line and (url_line.startswith('http://') or url_line.startswith('https://')):
                    channel_name_match = re.search(r',([^,]+)$', info_line)
                    if channel_name_match:
                        channel_name = channel_name_match.group(1).strip()
                    else:
                        channel_name = info_line
                    channels.append((channel_name, url_line))
                    i += 1
        elif ',' in line and '://' in line:
            # 处理 "频道名,URL" 格式
            parts = line.split(',', 1)
            if len(parts) == 2 and (parts[1].startswith('http://') or parts[1].startswith('https://')):
                channels.append((parts[0].strip(), parts[1].strip()))
        
        i += 1
    
    log(f"📊 解析到 {len(channels)} 个频道")
    return channels


def get_category_priority(category):
    """获取分类的显示优先级"""
    priority_order = ['HK', 'TW', 'SPORTS', 'NATURE', 'NEWS', 'ENT', 'OTHER']
    try:
        return priority_order.index(category)
    except ValueError:
        return len(priority_order)


def write_output(categorized, output_path, timestamp):
    """写入分类后的M3U文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n\n')
            f.write(f"""# xnkl.m3u
# 生成时间: {timestamp}
# 原始来源: {SOURCE_URL}
# EPG: {EPG_URL}
# GitHub Actions 自动生成

""")

            total_channels = 0
            for category in sorted(categorized.keys(), key=get_category_priority):
                channels = categorized[category]
                if channels:
                    channels.sort(key=lambda x: x[0])
                    total_channels += len(channels)
                    f.write(f"\n# 分类: {category} (共 {len(channels)} 台)\n")
                    for name, url in channels:
                        f.write(f'#EXTINF:-1 group-title="{category}",{name}\n')
                        f.write(f"{url}\n")

            f.write(f"""
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
""")
        
        return total_channels
    except Exception as e:
        log(f"❌ 写入文件失败: {e}")
        return None


def main():
    """主函数"""
    log("="*60)
    log(f"🚀 开始生成 {OUTPUT_FILE}")
    log("="*60)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    output_path = os.path.join(repo_root, OUTPUT_FILE)
    
    log(f"📁 脚本目录: {script_dir}")
    log(f"📁 仓库根目录: {repo_root}")
    log(f"📄 输出文件: {output_path}")
    log(f"🌐 源地址: {SOURCE_URL}")

    content = download_source(SOURCE_URL, "xnkl.txt")
    if not content:
        log("❌ 下载失败，程序退出")
        return 1

    raw_channels = parse_m3u(content)
    if not raw_channels:
        log("❌ 没有解析到任何频道，程序退出")
        return 1
    
    log(f"📊 原始频道数: {len(raw_channels)}")
    
    log("🔄 清洗频道名称...")
    cleaned_channels = [(clean_channel_name(name), url) for name, url in raw_channels]
    
    log("🔄 标准化频道名称...")
    normalized_channels = [(normalize_channel_name(name), url) for name, url in cleaned_channels]
    
    log("🔄 去重处理...")
    deduped_channels = deduplicate_channels(normalized_channels)
    
    log("🏷️ 分类频道...")
    channels_with_cats = []
    for name, url in deduped_channels:
        category = categorize_channel(name)
        channels_with_cats.append((name, category, url))
        log(f"  {name} -> {category}")
    
    categorized = {}
    for name, category, url in channels_with_cats:
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((name, url))
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = write_output(categorized, output_path, timestamp)
    
    if total:
        log("="*60)
        log(f"🎉 成功！{OUTPUT_FILE} 生成成功")
        log(f"📺 总频道数: {total}")
        for category in sorted(categorized.keys(), key=get_category_priority):
            count = len(categorized.get(category, []))
            if count > 0:
                log(f"   {category}: {count} 个频道")
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            log(f"💾 文件大小: {file_size} 字节")
            log(f"📍 文件位置: {output_path}")
        
        log("="*60)
        return 0
    else:
        log("❌ 生成失败")
        return 1


if __name__ == "__main__":
    exit(main())
