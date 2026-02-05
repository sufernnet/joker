#!/usr/bin/env python3
"""
CC.m3u 合并脚本 - 标准M3U格式（支持EPG、频道排序、频道过滤）
从 https://stymei.sufern001.workers.dev/ 提取：
1. 🔥全网通港澳台
2. 🔮港澳台直播
将相同频道合并，支持多播放地址，并按指定规则排序、过滤
排序规则：凤凰→NOW直播台→NOW新闻台→NOW财经台→NOW体育台→爆谷台→星影台→TVB→HOY→VIUTV→其他
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
        "http://iptv.4666888.xyz/iptv2A.php?id=45",  # 倒数第二个凤凰中文的链接
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

# 频道排序优先级（新规则：凤凰→NOW直播台→NOW新闻台→NOW财经台→NOW体育台→爆谷台→星影台→TVB→HOY→VIUTV→其他）
CHANNEL_PRIORITY = {
    # 最高优先级：凤凰系列
    "凤凰中文": 1,
    "凤凰资讯": 2,
    "凤凰香港": 3,
    "凤凰卫视": 5,
    
    # 第二优先级：NOW系列（各自独立）
    "NOW直播台": 10,
    "NOW新闻台": 11,
    "NOW财经台": 12,
    "NOW体育台": 13,
    
    # 第三优先级：爆谷台、星影台（排在NOW系列后面）
    "爆谷台": 20,
    "星影台": 21,
    
    # 第四优先级：TVB系列
    "TVB": 30,
    "翡翠台": 31,
    "明珠台": 32,
    "J2": 33,
    "无线新闻": 34,
    "无线财经": 35,
    
    # 第五优先级：HOY系列
    "HOY": 40,
    "HOY TV": 41,
    "HOY资讯台": 42,
    "香港开电视": 43,
    
    # 第六优先级：VIUTV系列
    "VIUTV": 50,
    "VIUTV中文台": 51,
    "VIUTV综艺台": 52,
    
    # 其他凤凰频道
    "凤凰": 6,  # 其他凤凰频道
    
    # 其他NOW频道
    "NOW": 15,  # 其他NOW频道
    
    # 默认优先级
    "其他": 100,
}

# 频道名称标准化（只处理大小写和空格，不合并不同频道）
CHANNEL_NAME_NORMALIZATION = {
    # 大小写标准化
    "now直播台": "NOW直播台",
    "now新闻台": "NOW新闻台", 
    "now财经台": "NOW财经台",
    "now体育台": "NOW体育台",
    "now电影台": "NOW电影台",
    "now娱乐台": "NOW娱乐台",
    # 凤凰系列标准化（保持独立但统一格式）
    "凤凰中文台": "凤凰中文",
    "凤凰卫视中文": "凤凰中文",
    "凤凰卫视中文台": "凤凰中文",
    "凤凰中文频道": "凤凰中文",
    "凤凰中文卫视": "凤凰中文",
    "凤凰卫视": "凤凰中文",  # 如果只是"凤凰卫视"也映射到凤凰中文
    "凤凰资讯台": "凤凰资讯",
    "凤凰卫视资讯": "凤凰资讯",
    "凤凰卫视资讯台": "凤凰资讯",
    "凤凰香港台": "凤凰香港",
    "凤凰卫视香港": "凤凰香港",
    "凤凰卫视香港台": "凤凰香港",
    # 其他频道名称标准化
    "TVB翡翠台": "翡翠台",
    "TVB明珠台": "明珠台",
    "VIUTV中文": "VIUTV中文台",
    "VIUTV综艺": "VIUTV综艺台",
    # 爆谷台、星影台标准化
    "爆谷": "爆谷台",
    "星影": "星影台",
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
    """标准化频道名称（只处理格式，不合并不同频道）"""
    original_name = channel_name
    cleaned_name = channel_name.strip()
    
    # 0. 先检查精确映射
    if cleaned_name in CHANNEL_NAME_NORMALIZATION:
        mapped_name = CHANNEL_NAME_NORMALIZATION[cleaned_name]
        if original_name != mapped_name:
            log(f"  精确映射: {original_name} -> {mapped_name}")
        return mapped_name
    
    # 1. 大小写标准化：所有NOW开头的大写
    if cleaned_name.lower().startswith("now"):
        # 提取NOW后面的部分
        match = re.match(r'(now)(.+)?', cleaned_name, re.IGNORECASE)
        if match:
            prefix = "NOW"  # 统一大写
            suffix = match.group(2) or ""
            normalized = prefix + suffix
            if original_name != normalized:
                log(f"  NOW大小写标准化: {original_name} -> {normalized}")
            return normalized
    
    # 2. 爆谷台、星影台标准化
    if "爆谷" in cleaned_name and "台" not in cleaned_name:
        normalized = "爆谷台"
        if original_name != normalized:
            log(f"  爆谷台标准化: {original_name} -> {normalized}")
        return normalized
    
    if "星影" in cleaned_name and "台" not in cleaned_name:
        normalized = "星影台"
        if original_name != normalized:
            log(f"  星影台标准化: {original_name} -> {normalized}")
        return normalized
    
    # 3. 大小写标准化：凤凰系列
    if "凤凰" in cleaned_name:
        # 保持原样，只处理明显的格式问题
        if cleaned_name.lower() in CHANNEL_NAME_NORMALIZATION:
            mapped_name = CHANNEL_NAME_NORMALIZATION[cleaned_name.lower()]
            if original_name != mapped_name:
                log(f"  凤凰系列标准化: {original_name} -> {mapped_name}")
            return mapped_name
    
    # 4. 移除多余的空格
    final_name = re.sub(r'\s+', ' ', cleaned_name)
    
    if original_name != final_name:
        log(f"  清理空格: {original_name} -> {final_name}")
    
    return final_name

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
    
    # 特殊规则：包含"NOW"但不是已定义的NOW系列
    if "NOW" in channel_name.upper() and channel_name not in ["NOW直播台", "NOW新闻台", "NOW财经台", "NOW体育台"]:
        return 15  # 其他NOW频道放在已定义NOW频道之后
    
    # 特殊规则：爆谷台相关
    if "爆谷" in channel_name:
        return 20
    
    # 特殊规则：星影台相关
    if "星影" in channel_name:
        return 21
    
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
    log(f"频道排序完成，新优先级分布:")
    priority_groups = defaultdict(list)
    for name, _ in sorted_channels:
        priority = get_channel_priority(name)
        priority_groups[priority].append(name)
    
    # 显示主要优先级组（按照新规则）
    priority_mapping = {
        1: "凤凰中文",
        2: "凤凰资讯",
        3: "凤凰香港",
        5: "凤凰卫视",
        6: "其他凤凰频道",
        10: "NOW直播台",
        11: "NOW新闻台",
        12: "NOW财经台", 
        13: "NOW体育台",
        15: "其他NOW频道",
        20: "爆谷台",
        21: "星影台",
        30: "TVB",
        31: "翡翠台",
        32: "明珠台",
        33: "J2",
        34: "无线新闻",
        35: "无线财经",
        40: "HOY",
        41: "HOY TV",
        42: "HOY资讯台",
        43: "香港开电视",
        50: "VIUTV",
        51: "VIUTV中文台",
        52: "VIUTV综艺台",
    }
    
    # 按照新规则顺序显示
    for priority in [1, 2, 3, 5, 6, 10, 11, 12, 13, 15, 20, 21, 30, 31, 32, 33, 34, 35, 40, 41, 42, 43, 50, 51, 52, 100]:
        if priority in priority_groups and priority_groups[priority]:
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
        # NOW系列（各自独立）
        "NOW直播台": "now.live.png",
        "NOW新闻台": "now.news.png",
        "NOW财经台": "now.finance.png",
        "NOW体育台": "now.sports.png",
        # 爆谷台、星影台
        "爆谷台": "popcorn.png",
        "星影台": "starmovie.png",
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
        "VIUTV中文台": "viutv.chinese.png",
        "VIUTV综艺台": "viutv.variety.png",
        # 其他常见频道
        "中天": "cti.png",
        "东森": "ettv.png",
        "三立": "set.png",
        "民视": "ftv.png",
    }
    
    # 1. 精确匹配
    for key, filename in logo_map.items():
        if key == channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}{filename}"
                return logo_url
    
    # 2. 部分匹配
    for key, filename in logo_map.items():
        if key in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}{filename}"
                return logo_url
    
    # 3. NOW系列通用匹配
    if "NOW" in channel_name:
        if "新闻" in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}now.news.png"
                return logo_url
        elif "财经" in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}now.finance.png"
                return logo_url
        elif "体育" in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}now.sports.png"
                return logo_url
        elif "直播" in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}now.live.png"
                return logo_url
        else:
            for source in LOGO_SOURCES:
                logo_url = f"{source}now.png"
                return logo_url
    
    # 4. 关键词匹配
    keywords = {
        "新闻": "news.png",
        "体育": "sports.png",
        "电影": "movie.png",
        "音乐": "music.png",
        "财经": "finance.png",
        "直播": "live.png",
        "爆谷": "popcorn.png",
        "星影": "starmovie.png",
    }
    
    for keyword, filename in keywords.items():
        if keyword in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}{filename}"
                return logo_url
    
    # 5. 返回默认台标
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
    重要：只合并完全相同的频道（大小写标准化后相同），不合并不同NOW频道
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
        'original_names': set(),  # 记录原始名称
        'original_lines': []  # 记录原始行
    })
    
    lines = content.split('\n')
    
    log(f"开始提取并合并分组: {SOURCE_GROUPS}")
    log(f"合并规则: 只合并完全相同的频道（大小写标准化后）")
    log(f"排序规则: 凤凰→NOW直播台→NOW新闻台→NOW财经台→NOW体育台→爆谷台→星影台→TVB→HOY→VIUTV→其他")
    
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
                        # 标准化频道名称（只处理格式，不合并不同频道）
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
                            channel_dict[channel_name]['original_lines'].append(f"{original_name},{url}")
                            group_count += 1
                        
                        # 特别处理：如果这是倒数第二个凤凰中文的链接
                        if original_name == "凤凰中文" and url == "http://iptv.4666888.xyz/iptv2A.php?id=45":
                            log(f"  🔍 找到倒数第二个凤凰中文链接: {url}")
        
        if group_found:
            log(f"  从「{source_group}」提取 {group_count} 个播放源，过滤 {blacklist_count} 个黑名单频道")
        else:
            log(f"⚠️  未找到分组: {source_group}")
    
    # 转换为普通字典
    result = dict(channel_dict)
    
    # 添加特殊链接到凤凰中文
    if "凤凰中文" in result:
        for url in SPECIAL_URLS.get("凤凰中文", []):
            if url not in result["凤凰中文"]['urls']:
                result["凤凰中文"]['urls'].append(url)
                log(f"✅ 为凤凰中文添加特殊链接: {url[:50]}...")
    
    # 统计信息
    total_channels = len(result)
    total_urls = sum(len(ch['urls']) for ch in result.values())
    
    log(f"✅ 合并后得到 {total_channels} 个唯一频道，共 {total_urls} 个播放源")
    
    # 显示凤凰中文合并详情
    if "凤凰中文" in result:
        phoenix_data = result["凤凰中文"]
        log(f"📊 凤凰中文合并详情:")
        log(f"  最终名称: 凤凰中文")
        log(f"  合并相同频道数: {len(phoenix_data['original_names'])} 个")
        log(f"  播放源总数: {len(phoenix_data['urls'])} 个")
        
        # 检查是否包含特定的倒数第二个链接
        target_url = "http://iptv.4666888.xyz/iptv2A.php?id=45"
        if any(target_url in url for url in phoenix_data['urls']):
            log(f"  ✅ 已包含倒数第二个凤凰中文链接")
        else:
            log(f"  ❌ 未找到倒数第二个凤凰中文链接，手动添加")
            phoenix_data['urls'].append(target_url)
    
    # 显示关键频道统计
    key_channels = ["NOW直播台", "NOW新闻台", "NOW财经台", "NOW体育台", "爆谷台", "星影台"]
    for channel in key_channels:
        if channel in result:
            data = result[channel]
            log(f"📊 {channel}: {len(data['urls'])}个播放源")
    
    # 显示过滤统计
    if blacklist_count > 0:
        log(f"✅ 共过滤 {blacklist_count} 个黑名单频道")
    
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
        f"# CC.m3u - 自动生成（EPG+新排序+过滤+精确合并版）",
        f"# 生成时间: {timestamp}",
        f"# 源地址: {SOURCE_URL}",
        f"# EPG地址: {EPG_URL}",
        f"# 提取分组: {', '.join(SOURCE_GROUPS)} → {TARGET_GROUP}",
        f"# 新排序规则: 凤凰→NOW直播台→NOW新闻台→NOW财经台→NOW体育台→爆谷台→星影台→TVB→HOY→VIUTV→其他",
        f"# 合并规则: 只合并完全相同的频道（大小写标准化后相同）",
        f"# 特殊链接: 凤凰中文已添加倒数第二个链接及其他优质链接",
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
        output_lines.append("# 新排序规则：凤凰系列→NOW系列（各自独立）→爆谷台→星影台→TVB系列→HOY系列→VIUTV系列→其他")
        output_lines.append("# 合并规则：只合并名称完全相同的频道（如NOW新闻和Now新闻合并）")
        output_lines.append("# NOW频道：NOW直播台、NOW新闻台、NOW财经台、NOW体育台保持各自独立")
        output_lines.append("# 爆谷台、星影台：排在NOW系列后面、TVB系列前面")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        # 添加分组标题便于识别（按照新规则）
        current_priority = None
        priority_mapping = {
            1: "凤凰中文（已完全合并）",
            2: "凤凰资讯",
            3: "凤凰香港",
            5: "凤凰卫视",
            6: "其他凤凰频道",
            10: "NOW直播台",
            11: "NOW新闻台",
            12: "NOW财经台",
            13: "NOW体育台",
            15: "其他NOW频道",
            20: "爆谷台",
            21: "星影台",
            30: "TVB",
            31: "翡翠台",
            32: "明珠台",
            33: "J2",
            34: "无线新闻",
            35: "无线财经",
            40: "HOY",
            41: "HOY TV",
            42: "HOY资讯台",
            43: "香港开电视",
            50: "VIUTV",
            51: "VIUTV中文台",
            52: "VIUTV综艺台",
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
                
                # 如果是凤凰中文，显示合并信息
                if channel_name == "凤凰中文" and len(data.get('original_names', set())) > 1:
                    originals = list(data['original_names'])
                    if len(originals) > 3:
                        originals = originals[:3] + [f"...等{len(data['original_names'])}个相同名称频道"]
                    output_lines.append(f"# 合并自相同名称: {', '.join(originals)}")
            
            # EXTINF 行
            extinf = f'#EXTINF:-1 tvg-id="{data["tvg_id"]}" tvg-name="{data["tvg_name"]}" tvg-logo="{data["logo"]}" group-title="{TARGET_GROUP}",{channel_name}'
            output_lines.append(extinf)
            
            # 多个播放地址（每个地址一行）
            url_count = 0
            for url in data['urls']:
                output_lines.append(url)
                url_count += 1
                
                # 标记倒数第二个凤凰中文链接
                if channel_name == "凤凰中文" and url == "http://iptv.4666888.xyz/iptv2A.php?id=45":
                    output_lines.append("# ↑ 倒数第二个凤凰中文链接（已合并）")
            
            # 如果是凤凰中文，标记特殊链接
            if channel_name == "凤凰中文" and url_count > 0:
                output_lines.append("# ↑ 凤凰中文特殊优质链接（共{}个源）".format(url_count))
        
        # 移除最后的空行（如果有）
        while output_lines and output_lines[-1] == "":
            output_lines.pop()
    
    # 统计信息
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# 统计信息")
    local_channels = len([l for l in local_content.split('\n') if l.startswith('#EXTINF')])
    total_urls = sum(len(ch['urls']) for ch in channel_dict.values())
    
    # 统计各系列数量（按照新规则）
    series_count = defaultdict(int)
    for channel_name in channel_dict.keys():
        priority = get_channel_priority(channel_name)
        series_mapping = {
            1: "凤凰中文",
            2: "凤凰资讯",
            3: "凤凰香港",
            5: "凤凰卫视",
            6: "其他凤凰",
            10: "NOW直播台",
            11: "NOW新闻台",
            12: "NOW财经台",
            13: "NOW体育台",
            15: "其他NOW",
            20: "爆谷台",
            21: "星影台",
            30: "TVB",
            31: "翡翠台",
            32: "明珠台",
            33: "J2",
            34: "无线新闻",
            35: "无线财经",
            40: "HOY",
            41: "HOY TV",
            42: "HOY资讯台",
            43: "香港开电视",
            50: "VIUTV",
            51: "VIUTV中文台",
            52: "VIUTV综艺台",
        }
        series = series_mapping.get(priority, "其他")
        series_count[series] += 1
    
    # 凤凰中文合并统计
    phoenix_original_count = 0
    if "凤凰中文" in channel_dict:
        phoenix_original_count = len(channel_dict["凤凰中文"].get('original_names', set()))
    
    output_lines.append(f"# 本地频道数: {local_channels}")
    output_lines.append(f"# 港澳台唯一频道数: {len(channel_dict)}")
    output_lines.append(f"# 港澳台播放源总数: {total_urls}")
    
    # 按照新规则顺序显示统计
    if series_count:
        output_lines.append("# 频道系列分布（新排序规则）:")
        
        # 凤凰系列
        phoenix_series = ["凤凰中文", "凤凰资讯", "凤凰香港", "凤凰卫视", "其他凤凰"]
        for series in phoenix_series:
            if series_count.get(series, 0) > 0:
                count_info = f"{series_count[series]}个频道"
                if series == "凤凰中文" and phoenix_original_count > 1:
                    count_info = f"{series_count[series]}个频道 (合并自{phoenix_original_count}个相同名称频道)"
                output_lines.append(f"#   {series}: {count_info}")
        
        # NOW系列
        now_series = ["NOW直播台", "NOW新闻台", "NOW财经台", "NOW体育台", "其他NOW"]
        for series in now_series:
            if series_count.get(series, 0) > 0:
                output_lines.append(f"#   {series}: {series_count[series]}个频道")
        
        # 爆谷台、星影台
        for series in ["爆谷台", "星影台"]:
            if series_count.get(series, 0) > 0:
                output_lines.append(f"#   {series}: {series_count[series]}个频道")
        
        # TVB系列
        tvb_series = ["TVB", "翡翠台", "明珠台", "J2", "无线新闻", "无线财经"]
        for series in tvb_series:
            if series_count.get(series, 0) > 0:
                output_lines.append(f"#   {series}: {series_count[series]}个频道")
        
        # HOY系列
        hoy_series = ["HOY", "HOY TV", "HOY资讯台", "香港开电视"]
        for series in hoy_series:
            if series_count.get(series, 0) > 0:
                output_lines.append(f"#   {series}: {series_count[series]}个频道")
        
        # VIUTV系列
        viutv_series = ["VIUTV", "VIUTV中文台", "VIUTV综艺台"]
        for series in viutv_series:
            if series_count.get(series, 0) > 0:
                output_lines.append(f"#   {series}: {series_count[series]}个频道")
        
        # 其他
        if series_count.get("其他", 0) > 0:
            output_lines.append(f"#   其他: {series_count['其他']}个频道")
    
    output_lines.append(f"# 更新时间: {timestamp}")
    output_lines.append("# EPG节目单: 已集成，播放器会自动加载")
    output_lines.append("# 新排序规则: 凤凰→NOW直播台→NOW新闻台→NOW财经台→NOW体育台→爆谷台→星影台→TVB→HOY→VIUTV→其他")
    output_lines.append("# 倒数第二个凤凰中文链接: 已成功合并")
    output_lines.append("#" + "=" * 60)
    
    return '\n'.join(output_lines)

def main():
    """主函数"""
    print("=" * 70)
    log("开始生成 CC.m3u（新排序规则版）...")
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
        
        # 3. 按新规则排序频道
        log("开始按新规则排序频道...")
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
            log(f"   新排序规则: 凤凰→NOW直播台→NOW新闻台→NOW财经台→NOW体育台→爆谷台→星影台→TVB→HOY→VIUTV→其他")
            
            # 显示关键频道排序结果
            print("\n📋 关键频道排序结果（新规则）:")
            print("-" * 70)
            
            # 关键频道映射
            key_series = {
                1: "凤凰中文",
                10: "NOW直播台",
                11: "NOW新闻台",
                12: "NOW财经台",
                13: "NOW体育台",
                20: "爆谷台",
                21: "星影台",
                30: "TVB",
                31: "翡翠台",
                32: "明珠台",
                40: "HOY",
                41: "HOY TV",
                50: "VIUTV",
                51: "VIUTV中文台",
            }
            
            # 只显示关键频道
            shown_count = 0
            for name, data in sorted_channel_dict.items():
                priority = get_channel_priority(name)
                if priority in key_series or shown_count < 20:
                    series = key_series.get(priority, "其他")
                    source_count = len(data['urls'])
                    original_count = len(data.get('original_names', set()))
                    
                    if original_count > 1:
                        name_display = f"{name} ({original_count}合1)"
                    else:
                        name_display = name
                    
                    # 添加位置标记
                    position_marker = ""
                    if priority == 20:  # 爆谷台
                        position_marker = "← NOW系列结束，爆谷台开始"
                    elif priority == 30:  # TVB
                        position_marker = "← 爆谷/星影台结束，TVB开始"
                    elif priority == 40:  # HOY
                        position_marker = "← TVB结束，HOY开始"
                    elif priority == 50:  # VIUTV
                        position_marker = "← HOY结束，VIUTV开始"
                    
                    print(f"{shown_count+1:2d}. [{series}] {name_display} ({source_count}源) {position_marker}")
                    shown_count += 1
                    
                    if shown_count >= 25:  # 显示前25个
                        break
            
            print("-" * 70)
            
            # 验证新排序规则
            print("\n✅ 新排序规则验证:")
            print("-" * 50)
            
            # 检查关键频道顺序
            channel_order = []
            for name in sorted_channel_dict.keys():
                priority = get_channel_priority(name)
                if priority <= 60:  # 只检查主要系列
                    channel_order.append((priority, name))
            
            # 检查顺序是否符合新规则
            expected_order = [
                (1, "凤凰系列"),
                (10, "NOW直播台"),
                (11, "NOW新闻台"),
                (12, "NOW财经台"),
                (13, "NOW体育台"),
                (20, "爆谷台"),
                (21, "星影台"),
                (30, "TVB系列"),
                (40, "HOY系列"),
                (50, "VIUTV系列"),
            ]
            
            last_priority = 0
            correct_order = True
            for priority, name in channel_order[:15]:  # 检查前15个
                if priority < last_priority:
                    print(f"  ⚠️  顺序错误: {name} (优先级{priority}) 出现在优先级{last_priority}之后")
                    correct_order = False
                last_priority = priority
            
            if correct_order:
                print("  ✅ 频道排序符合新规则")
            else:
                print("  ⚠️  频道排序需要调整")
            
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
