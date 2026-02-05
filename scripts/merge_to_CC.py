#!/usr/bin/env python3
"""
CC.m3u 合并脚本 - 标准M3U格式（支持EPG、频道排序、频道过滤）
从 https://stymei.sufern001.workers.dev/ 提取：
1. 🔥全网通港澳台
2. 🔮港澳台直播
将相同频道合并，支持多播放地址，并按指定规则排序、过滤
新增功能：
1. NOW相关频道合并到NOW分组
2. 爆谷、星影台排在OW直播台后面
3. 凤凰中文添加特定链接
"""

import requests
from datetime import datetime
import os
import re
import hashlib
from collections import defaultdict

# ================== 配置区域 ==================
SOURCE_URL = "https://stymei.sufern001.workers.dev/"
BB_FILE = "BB.m3u"
OUTPUT_FILE = "CC.m3u"
EPG_URL = "http://epg.51zmt.top:8000/e.xml"  # EPG节目单地址

# 要提取的源分组（可扩展多个）
SOURCE_GROUPS = [
    "🔥全网通港澳台",
    "🔮港澳台直播"
]
TARGET_GROUP = "全网通港澳台"  # 合并后的统一分组名

# 特殊链接映射（特定频道添加特定链接）
SPECIAL_URLS = {
    "凤凰中文": [
        "http://iptv.4666888.xyz/iptv2A.php?id=45",
        "http://61.184.46.85:85/tsfile/live/1029_1.m3u8?key=txiptv&playlive=1&authid=0",
        "http://r.jdshipin.com/cCCzW"
    ]
}

# 台标源（按优先级排序）
LOGO_SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/logos/",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/",
    "https://raw.githubusercontent.com/lqist/IPTVlogos/main/",
]

# 频道排序优先级（依次为:凤凰→NOW→TVB→HOY→VIUTV→爆谷→星影台→其他）
CHANNEL_PRIORITY = {
    # 最高优先级：凤凰系列
    "凤凰中文": 1,
    "凤凰资讯": 2,
    "凤凰香港": 3,
    "凤凰卫视": 5,
    # 第二优先级：NOW系列（所有NOW相关频道统一为NOW）
    "NOW": 10,
    "NOW直播台": 10,      # 映射到NOW
    "NOW新闻台": 10,      # 映射到NOW
    "NOW财经台": 10,      # 映射到NOW
    "NOW体育台": 10,      # 映射到NOW
    "NOW电影台": 10,      # 映射到NOW
    # 第三优先级：TVB系列
    "TVB": 20,
    "翡翠台": 21,
    "明珠台": 22,
    "J2": 23,
    "无线新闻": 24,
    "无线财经": 25,
    # 第四优先级：HOY系列
    "HOY": 30,
    "HOY TV": 31,
    "HOY资讯台": 32,
    "香港开电视": 33,
    # 第五优先级：VIUTV系列
    "VIUTV": 40,
    "VIUTV中文台": 41,
    "VIUTV综艺台": 42,
    # 第六优先级：爆谷、星影台（排在NOW后面）
    "爆谷台": 50,
    "星影台": 51,
    # 其他频道默认优先级：100
}

# 频道名称映射（合并相似频道）
CHANNEL_NAME_MAPPING = {
    # NOW相关频道统一为NOW
    "NOW直播台": "NOW",
    "NOW新闻台": "NOW",
    "NOW财经台": "NOW",
    "NOW体育台": "NOW",
    "NOW电影台": "NOW",
    "NOW娱乐台": "NOW",
    # 其他可能的NOW变体
    "Now直播台": "NOW",
    "Now新闻台": "NOW",
    "Now财经台": "NOW",
    # 标准化其他频道名称
    "凤凰卫视中文台": "凤凰中文",
    "凤凰卫视资讯台": "凤凰资讯",
    "凤凰卫视香港台": "凤凰香港",
    "TVB翡翠台": "翡翠台",
    "TVB明珠台": "明珠台",
}

# 需要剔除的频道关键词（完全匹配或部分匹配）
BLACKLIST_KEYWORDS = [
    # 原黑名单
    "SPOTV",
    "GOODTV",
    "GOOD2",
    "番薯111",
    "人间卫视",
    "唯心电视",
    "中旺电视",
    "生命电影",
    "唐人卫视",
    "香港卫视",
    "唐NTD",
    "NTDTV",
    "新唐人",
    # 新增剔除频道
    "凤凰电影",
    "C+",
    "MoMoTV",
    "DAZN1",
    "DAZN2",
    "ELEVEN体育1",
    "ELEVEN体育2",
    "爱奇艺",
]

# ================== 工具函数 ==================
def log(msg):
    """日志输出"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def normalize_channel_name(channel_name):
    """标准化频道名称（合并相似频道）"""
    original_name = channel_name
    
    # 1. 检查映射表
    for pattern, mapped_name in CHANNEL_NAME_MAPPING.items():
        if pattern in channel_name:
            log(f"  频道映射: {original_name} -> {mapped_name}")
            return mapped_name
    
    # 2. 特殊规则：包含"NOW"但不是已定义的
    if "NOW" in channel_name.upper() and channel_name not in CHANNEL_PRIORITY:
        log(f"  NOW频道标准化: {channel_name} -> NOW")
        return "NOW"
    
    # 3. 移除多余的空格和特殊字符
    cleaned = re.sub(r'\s+', ' ', channel_name.strip())
    return cleaned

def is_channel_blacklisted(channel_name):
    """检查频道是否在黑名单中"""
    for keyword in BLACKLIST_KEYWORDS:
        if keyword in channel_name:
            return True
    return False

def get_channel_priority(channel_name):
    """获取频道排序优先级"""
    # 检查精确匹配
    for key, priority in CHANNEL_PRIORITY.items():
        if key == channel_name:
            return priority
    
    # 检查部分匹配
    for key, priority in CHANNEL_PRIORITY.items():
        if key in channel_name:
            return priority
    
    # 特殊规则：包含"凤凰"但不是已定义的（不包括"凤凰电影"）
    if "凤凰" in channel_name and channel_name not in CHANNEL_PRIORITY and "凤凰电影" not in channel_name:
        return 6  # 其他凤凰频道放在已定义凤凰频道之后
    
    # 特殊规则：包含"NOW"但不是已定义的
    if "NOW" in channel_name.upper() and channel_name not in CHANNEL_PRIORITY:
        return 10  # 统一归到NOW优先级
    
    # 默认优先级
    return 100

def sort_channels(channel_dict):
    """按指定规则排序频道"""
    # 转换为列表便于排序
    channels_list = [(name, data) for name, data in channel_dict.items()]
    
    # 排序规则：1.优先级 2.频道名称
    def sort_key(item):
        channel_name = item[0]
        priority = get_channel_priority(channel_name)
        return (priority, channel_name)
    
    sorted_channels = sorted(channels_list, key=sort_key)
    
    # 转换回字典
    sorted_dict = {name: data for name, data in sorted_channels}
    
    # 记录排序信息
    log(f"频道排序完成，优先级分布:")
    priority_groups = defaultdict(list)
    for name, _ in sorted_channels:
        priority = get_channel_priority(name)
        priority_groups[priority].append(name)
    
    # 显示主要优先级组
    priority_mapping = {
        1: "凤凰系列",
        2: "凤凰系列",
        3: "凤凰系列",
        5: "凤凰系列",
        6: "凤凰系列",
        10: "NOW系列",
        20: "TVB系列",
        21: "TVB系列",
        22: "TVB系列",
        23: "TVB系列",
        24: "TVB系列",
        25: "TVB系列",
        30: "HOY系列",
        31: "HOY系列",
        32: "HOY系列",
        33: "HOY系列",
        40: "VIUTV系列",
        41: "VIUTV系列",
        42: "VIUTV系列",
        50: "爆谷台",
        51: "星影台",
    }
    
    for priority in sorted(priority_groups.keys()):
        if priority <= 100:  # 显示所有优先级组
            group_name = priority_mapping.get(priority, f"优先级{priority}")
            log(f"  {group_name}: {len(priority_groups[priority])}个频道")
    
    return sorted_dict

def get_channel_logo(channel_name):
    """根据频道名匹配台标"""
    # 频道名映射表（可自行扩展）
    logo_map = {
        # 凤凰系列
        "凤凰中文": "phoenix.chinese.png",
        "凤凰资讯": "phoenix.infonews.png",
        "凤凰香港": "phoenix.hongkong.png",
        "凤凰卫视": "phoenix.tv.png",
        # NOW系列
        "NOW": "now.png",
        # TVB系列
        "翡翠台": "tvb.jade.png",
        "明珠台": "tvb.pearl.png",
        "J2": "tvb.j2.png",
        "TVB": "tvb.png",
        # HOY系列
        "HOY": "hoy.png",
        "HOY TV": "hoy.tv.png",
        "香港开电视": "hoy.tv.png",
        # VIUTV系列
        "VIUTV": "viutv.png",
        # 爆谷、星影台
        "爆谷台": "popcorn.png",
        "星影台": "starmovie.png",
        # 其他常见频道
        "中天": "cti.png",
        "东森": "ettv.png",
        "三立": "set.png",
        "民视": "ftv.png",
    }
    
    # 1. 精确匹配
    for key, filename in logo_map.items():
        if key in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}{filename}"
                return logo_url
    
    # 2. 关键词匹配
    keywords = {
        "新闻": "news.png",
        "体育": "sports.png",
        "电影": "movie.png",
        "音乐": "music.png",
        "财经": "finance.png",
        "直播": "live.png",
    }
    
    for keyword, filename in keywords.items():
        if keyword in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}{filename}"
                return logo_url
    
    # 3. 返回默认台标
    return "https://raw.githubusercontent.com/iptv-org/iptv/master/logos/default.png"

def extract_tvg_info(channel_name):
    """生成频道的tvg信息"""
    # 清理名称生成tvg-id
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
    
    # 使用MD5生成一致的tvg-id，确保相同频道名有相同ID
    tvg_id = f"channel_{hashlib.md5(channel_name.encode()).hexdigest()[:8]}"
    tvg_name = channel_name
    logo_url = get_channel_logo(channel_name)
    
    return tvg_id, tvg_name, logo_url

def download_source():
    """下载源数据"""
    try:
        log(f"正在下载源数据: {SOURCE_URL}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/plain'
        }
        response = requests.get(SOURCE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text
        log(f"✅ 下载成功，{len(content)} 字符")
        return content
    except Exception as e:
        log(f"❌ 下载失败: {e}")
        return None

def extract_and_merge_channels(content):
    """
    从内容中提取指定分组的所有频道，并合并相同频道的多个源
    返回结构: {channel_name: {tvg_id, tvg_name, logo, group, urls: [url1, url2, ...]}}
    """
    if not content:
        return {}
    
    # 使用字典合并相同频道，值是一个包含所有URL的列表
    channel_dict = defaultdict(lambda: {
        'name': '',
        'tvg_id': '',
        'tvg_name': '',
        'logo': '',
        'group': TARGET_GROUP,
        'urls': [],  # 存储多个播放地址
        'source_groups': set(),  # 记录来源分组
        'original_names': set()  # 记录原始名称（用于NOW合并）
    })
    
    lines = content.split('\n')
    
    log(f"开始提取并合并分组: {SOURCE_GROUPS}")
    log(f"频道标准化规则: NOW相关频道统一为NOW")
    log(f"新增排序: 爆谷台、星影台排在NOW后面")
    
    for source_group in SOURCE_GROUPS:
        in_section = False
        group_found = False
        group_count = 0
        blacklist_count = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 查找分组开始
            if f"{source_group},#genre#" in line:
                log(f"✅ 找到分组: {source_group} (第{i+1}行)")
                in_section = True
                group_found = True
                continue
            
            # 如果已在分组中，遇到下一个分组则结束
            if in_section and '#genre#' in line and source_group not in line:
                break
            
            # 提取频道
            if in_section and line and ',' in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    original_name = parts[0].strip()
                    url = ','.join(parts[1:]).strip()
                    
                    # 检查是否在黑名单中
                    if is_channel_blacklisted(original_name):
                        blacklist_count += 1
                        log(f"  过滤黑名单频道: {original_name}")
                        continue
                    
                    if url and ('://' in url or url.startswith('http')):
                        # 标准化频道名称
                        channel_name = normalize_channel_name(original_name)
                        
                        # 如果是首次遇到这个频道，生成tvg信息
                        if channel_name not in channel_dict or not channel_dict[channel_name]['tvg_id']:
                            tvg_id, tvg_name, logo_url = extract_tvg_info(channel_name)
                            channel_dict[channel_name].update({
                                'name': channel_name,
                                'tvg_id': tvg_id,
                                'tvg_name': tvg_name,
                                'logo': logo_url,
                                'group': TARGET_GROUP,
                            })
                        
                        # 添加URL到列表
                        if url not in channel_dict[channel_name]['urls']:
                            channel_dict[channel_name]['urls'].append(url)
                            channel_dict[channel_name]['source_groups'].add(source_group)
                            channel_dict[channel_name]['original_names'].add(original_name)
                            group_count += 1
        
        if group_found:
            log(f"  从「{source_group}」提取 {group_count} 个播放源，过滤 {blacklist_count} 个黑名单频道")
        else:
            log(f"⚠️  未找到分组: {source_group}")
    
    # 转换为普通字典
    result = dict(channel_dict)
    
    # 添加特殊链接
    for channel_name, special_urls in SPECIAL_URLS.items():
        if channel_name in result:
            for url in special_urls:
                if url not in result[channel_name]['urls']:
                    result[channel_name]['urls'].append(url)
                    log(f"✅ 为 {channel_name} 添加特殊链接: {url[:50]}...")
    
    # 统计信息
    total_channels = len(result)
    total_urls = sum(len(ch['urls']) for ch in result.values())
    
    log(f"✅ 合并后得到 {total_channels} 个唯一频道，共 {total_urls} 个播放源")
    
    # 显示NOW合并统计
    now_channels = [name for name in result.keys() if "NOW" in name.upper()]
    if len(now_channels) > 1:
        log(f"✅ NOW频道合并: 将 {len(now_channels)} 个NOW相关频道合并为'NOW'")
        for name in now_channels:
            if name != "NOW":
                log(f"  合并 {name} -> NOW")
    
    # 显示过滤统计
    if blacklist_count > 0:
        log(f"✅ 共过滤 {blacklist_count} 个黑名单频道")
    
    # 显示合并示例
    if result:
        log("频道合并示例:")
        for name, data in list(result.items())[:5]:
            original_count = len(data['original_names'])
            if original_count > 1:
                log(f"  {name}: {len(data['urls'])}个播放源 (合并自: {', '.join(list(data['original_names'])[:3])}...)")
            else:
                log(f"  {name}: {len(data['urls'])}个播放源")
    
    return result

def load_local_m3u():
    """加载本地BB.m3u文件"""
    try:
        if not os.path.exists(BB_FILE):
            log(f"⚠️  {BB_FILE} 不存在，创建默认文件")
            default_content = f"""#EXTM3U
#EXTINF:-1 tvg-id="" tvg-name="本地测试1" tvg-logo="" group-title="本地",本地测试1
http://example.com/local1
#EXTINF:-1 tvg-id="" tvg-name="本地测试2" tvg-logo="" group-title="本地",本地测试2
http://example.com/local2"""
            with open(BB_FILE, 'w', encoding='utf-8') as f:
                f.write(default_content)
            return default_content
        
        with open(BB_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        log(f"✅ 加载本地文件成功，{len(content.splitlines())} 行")
        return content
    except Exception as e:
        log(f"❌ 加载本地文件失败: {e}")
        return "#EXTM3U\n"

def generate_m3u_content(local_content, channel_dict):
    """生成最终的M3U内容（支持多播放地址）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output_lines = [
        f'#EXTM3U url-tvg="{EPG_URL}"',
        f"# CC.m3u - 自动生成（EPG+排序+过滤+合并版）",
        f"# 生成时间: {timestamp}",
        f"# 源地址: {SOURCE_URL}",
        f"# EPG地址: {EPG_URL}",
        f"# 提取分组: {', '.join(SOURCE_GROUPS)} → {TARGET_GROUP}",
        f"# 排序规则: 凤凰→NOW→TVB→HOY→VIUTV→爆谷→星影台→其他",
        f"# 频道合并: NOW相关频道统一为NOW，凤凰中文添加特殊链接",
        f"# 过滤频道: 共{len(BLACKLIST_KEYWORDS)}个关键词",
        f"# 唯一频道数: {len(channel_dict)}",
        f"# 自动运行: 北京时间 06:00, 17:30",
        f"# GitHub Actions 自动生成",
        ""
    ]
    
    # 添加本地内容
    if local_content and local_content.strip():
        output_lines.append("#" + "=" * 60)
        output_lines.append("# 本地频道")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        local_lines = local_content.split('\n')
        for line in local_lines:
            if line.strip() == "#EXTM3U" and len(output_lines) > 8:
                continue
            output_lines.append(line)
        
        output_lines.append("")
    
    # 添加港澳台频道（支持多播放地址）
    if channel_dict:
        output_lines.append("#" + "=" * 60)
        output_lines.append(f"# {TARGET_GROUP} (合并自: {', '.join(SOURCE_GROUPS)})")
        output_lines.append("# 说明：每个频道可能包含多个播放地址，播放器会自动选择可用源")
        output_lines.append("# 排序：凤凰系列→NOW系列→TVB系列→HOY系列→VIUTV系列→爆谷台→星影台→其他")
        output_lines.append("# 合并：NOW直播台、NOW新闻台等统一合并为NOW频道")
        output_lines.append("# 链接：凤凰中文已添加特殊优质链接")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        # 添加分组标题便于识别
        current_priority = None
        priority_mapping = {
            1: "凤凰系列",
            2: "凤凰系列",
            3: "凤凰系列",
            5: "凤凰系列",
            6: "凤凰系列",
            10: "NOW系列（合并所有NOW相关频道）",
            20: "TVB系列",
            21: "TVB系列",
            22: "TVB系列",
            23: "TVB系列",
            24: "TVB系列",
            25: "TVB系列",
            30: "HOY系列",
            31: "HOY系列",
            32: "HOY系列",
            33: "HOY系列",
            40: "VIUTV系列",
            41: "VIUTV系列",
            42: "VIUTV系列",
            50: "爆谷台",
            51: "星影台",
        }
        
        for i, (channel_name, data) in enumerate(channel_dict.items(), 1):
            priority = get_channel_priority(channel_name)
            
            # 添加分组分隔
            if current_priority != priority:
                current_priority = priority
                group_name = priority_mapping.get(priority, "其他频道")
                
                if i > 1:  # 不是第一个频道才添加空行
                    output_lines.append("")
                output_lines.append(f"# --- {group_name} ---")
                
                # 如果是NOW系列，显示合并信息
                if priority == 10 and len(data.get('original_names', set())) > 1:
                    originals = list(data['original_names'])
                    if len(originals) > 3:
                        originals = originals[:3] + [f"...等{len(data['original_names'])}个频道"]
                    output_lines.append(f"# 合并自: {', '.join(originals)}")
            
            # EXTINF 行
            extinf = f'#EXTINF:-1 tvg-id="{data["tvg_id"]}" tvg-name="{data["tvg_name"]}" tvg-logo="{data["logo"]}" group-title="{TARGET_GROUP}",{channel_name}'
            output_lines.append(extinf)
            
            # 多个播放地址（每个地址一行）
            for url in data['urls']:
                output_lines.append(url)
            
            # 如果是凤凰中文，标记特殊链接
            if channel_name == "凤凰中文":
                output_lines.append("# ↑ 以上为凤凰中文特殊优质链接")
        
        # 移除最后的空行（如果有）
        while output_lines and output_lines[-1] == "":
            output_lines.pop()
    
    # 统计信息
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# 统计信息")
    local_channels = len([l for l in local_content.split('\n') if l.startswith('#EXTINF')])
    total_urls = sum(len(ch['urls']) for ch in channel_dict.values())
    
    # 统计各系列数量
    series_count = defaultdict(int)
    for channel_name in channel_dict.keys():
        priority = get_channel_priority(channel_name)
        series_mapping = {
            1: "凤凰", 2: "凤凰", 3: "凤凰", 5: "凤凰", 6: "凤凰",
            10: "NOW",
            20: "TVB", 21: "TVB", 22: "TVB", 23: "TVB", 24: "TVB", 25: "TVB",
            30: "HOY", 31: "HOY", 32: "HOY", 33: "HOY",
            40: "VIUTV", 41: "VIUTV", 42: "VIUTV",
            50: "爆谷台",
            51: "星影台",
        }
        series = series_mapping.get(priority, "其他")
        series_count[series] += 1
    
    # NOW合并统计
    now_original_count = 0
    for channel_name, data in channel_dict.items():
        if channel_name == "NOW":
            now_original_count = len(data.get('original_names', set()))
    
    output_lines.append(f"# 本地频道数: {local_channels}")
    output_lines.append(f"# 港澳台唯一频道数: {len(channel_dict)}")
    output_lines.append(f"# 港澳台播放源总数: {total_urls}")
    
    if series_count:
        output_lines.append("# 频道系列分布:")
        for series in ["凤凰", "NOW", "TVB", "HOY", "VIUTV", "爆谷台", "星影台", "其他"]:
            if series_count.get(series, 0) > 0:
                count_info = f"{series_count[series]}个频道"
                if series == "NOW" and now_original_count > 1:
                    count_info = f"{series_count[series]}个频道 (合并自{now_original_count}个相关频道)"
                output_lines.append(f"#   {series}: {count_info}")
    
    output_lines.append(f"# 更新时间: {timestamp}")
    output_lines.append("# EPG节目单: 已集成，播放器会自动加载")
    output_lines.append("# 特殊功能: NOW频道合并、凤凰中文特殊链接、爆谷/星影台排序")
    output_lines.append("#" + "=" * 60)
    
    return '\n'.join(output_lines)

def main():
    """主函数"""
    print("=" * 70)
    log("开始生成 CC.m3u（NOW合并+特殊排序版）...")
    print("=" * 70)
    
    try:
        # 1. 下载源数据
        source_content = download_source()
        if not source_content:
            log("❌ 无法获取源数据，退出")
            return
        
        # 2. 提取并合并频道
        channel_dict = extract_and_merge_channels(source_content)
        
        if not channel_dict:
            log("⚠️  未提取到任何频道，检查源数据格式")
            # 显示前5个分组供调试
            lines = source_content.split('\n')
            log("源数据中的分组:")
            count = 0
            for line in lines:
                if '#genre#' in line and count < 5:
                    log(f"  - {line}")
                    count += 1
        
        # 3. 按规则排序频道
        log("开始按规则排序频道...")
        sorted_channel_dict = sort_channels(channel_dict)
        
        # 4. 加载本地文件
        local_content = load_local_m3u()
        
        # 5. 生成内容
        m3u_content = generate_m3u_content(local_content, sorted_channel_dict)
        
        # 6. 保存文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
            f.write(m3u_content)
        
        # 7. 验证结果
        if os.path.exists(OUTPUT_FILE):
            file_size = os.path.getsize(OUTPUT_FILE)
            line_count = m3u_content.count('\n') + 1
            
            print("\n" + "=" * 70)
            log("✅ CC.m3u 生成成功!")
            log(f"   文件位置: {os.path.abspath(OUTPUT_FILE)}")
            log(f"   文件大小: {file_size} 字节")
            log(f"   总行数: {line_count}")
            log(f"   唯一频道数: {len(sorted_channel_dict)}")
            log(f"   EPG地址: {EPG_URL}")
            
            # 显示NOW合并详情
            print("\n📋 NOW频道合并详情:")
            print("-" * 70)
            for name, data in sorted_channel_dict.items():
                if name == "NOW" and len(data.get('original_names', set())) > 1:
                    print(f"✅ NOW频道合并完成:")
                    print(f"   合并后名称: NOW")
                    print(f"   合并频道数: {len(data['original_names'])} 个")
                    print(f"   播放源数量: {len(data['urls'])} 个")
                    print(f"   原始频道: {', '.join(list(data['original_names'])[:5])}")
                    if len(data['original_names']) > 5:
                        print(f"            ... 等{len(data['original_names'])}个频道")
            
            # 显示凤凰中文特殊链接
            print("\n📋 凤凰中文特殊链接:")
            print("-" * 70)
            if "凤凰中文" in sorted_channel_dict:
                phoenix_data = sorted_channel_dict["凤凰中文"]
                print(f"频道: 凤凰中文")
                print(f"总链接数: {len(phoenix_data['urls'])} 个")
                print("特殊链接:")
                for url in SPECIAL_URLS.get("凤凰中文", []):
                    if url in phoenix_data['urls']:
                        print(f"  ✓ {url[:80]}..." if len(url) > 80 else f"  ✓ {url}")
            
            # 显示排序结果
            print("\n📋 频道排序结果（按新规则）:")
            print("-" * 70)
            
            # 系列映射
            series_mapping = {
                1: "凤凰", 2: "凤凰", 3: "凤凰", 5: "凤凰", 6: "凤凰",
                10: "NOW",
                20: "TVB", 21: "TVB", 22: "TVB", 23: "TVB", 24: "TVB", 25: "TVB",
                30: "HOY", 31: "HOY", 32: "HOY", 33: "HOY",
                40: "VIUTV", 41: "VIUTV", 42: "VIUTV",
                50: "爆谷台",
                51: "星影台",
            }
            
            for i, (name, data) in enumerate(list(sorted_channel_dict.items())[:15]):
                priority = get_channel_priority(name)
                series = series_mapping.get(priority, "其他")
                source_count = len(data['urls'])
                if name == "NOW" and len(data.get('original_names', set())) > 1:
                    name_display = f"{name} ({len(data['original_names'])}合1)"
                else:
                    name_display = name
                print(f"{i+1:2d}. [{series}] {name_display} ({source_count}源)")
            print("-" * 70)
            
            # 显示文件头
            print("\n📄 生成文件头部:")
            print("-" * 50)
            lines = m3u_content.split('\n')
            for line in lines[:20]:
                print(line)
            print("-" * 50)
            
        else:
            log("❌ 文件保存失败")
    
    except Exception as e:
        log(f"❌ 执行错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)
    log("执行完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
