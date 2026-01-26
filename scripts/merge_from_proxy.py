#!/usr/bin/env python3
"""
M3U文件合并脚本 - 同时生成EPG XML
1. 下载BB.m3u
2. 从Cloudflare代理获取内容
3. 提取HK和TW频道
4. 同时生成CC.m3u和CC.xml（EPG文件）
5. 确保EPG与频道精确匹配
"""

import requests
import re
import os
import time
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from xml.dom import minidom

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
CLOUDFLARE_PROXY = "https://smt-proxy.sufern001.workers.dev/"
M3U_FILE = "CC.m3u"
EPG_FILE = "CC.xml"

# 频道过滤和排序配置
BLACKLIST_TW = [
    "Bloomberg TV", "Bloomberg", "SBN全球财经台", "SBN财经",
    "FRANCE24英文台", "FRANCE24", "半岛国际新闻台", "半岛国际",
    "NHK world-japan", "NHK world", "NHK", "CNBC Asia", "CNBC"
]

HK_PRIORITY_ORDER = [
    "凤凰中文", "凤凰资讯", "凤凰香港",
    "NOW新闻台", "NOW星影", "NOW爆谷"
]

# 频道节目单模板（如果没有真实EPG，使用这个）
CHANNEL_SCHEDULES = {
    # 凤凰系列
    "凤凰中文": [
        ("06:00", "09:00", "凤凰早班车"),
        ("09:00", "12:00", "时事直通车"),
        ("12:00", "14:00", "凤凰午间特快"),
        ("14:00", "17:00", "环球新闻追击"),
        ("17:00", "19:00", "时事辩论会"),
        ("19:00", "21:00", "凤凰焦点新闻"),
        ("21:00", "23:00", "金石财经"),
        ("23:00", "01:00", "夜班新闻")
    ],
    "凤凰资讯": [
        ("06:00", "08:00", "新闻早班车"),
        ("08:00", "10:00", "环球直播"),
        ("10:00", "12:00", "财经最前线"),
        ("12:00", "14:00", "午间新闻"),
        ("14:00", "16:00", "深度报道"),
        ("16:00", "18:00", "时事观察"),
        ("18:00", "20:00", "新闻晚高峰"),
        ("20:00", "22:00", "今日关注"),
        ("22:00", "00:00", "夜间新闻")
    ],
    "凤凰香港": [
        ("06:00", "09:00", "香港早晨"),
        ("09:00", "12:00", "财经透视"),
        ("12:00", "14:00", "午间报道"),
        ("14:00", "17:00", "娱乐前线"),
        ("17:00", "19:00", "新闻最前线"),
        ("19:00", "21:00", "时事追击"),
        ("21:00", "23:00", "夜间财经"),
        ("23:00", "01:00", "深夜新闻")
    ],
    # NOW系列
    "NOW新闻台": [
        ("00:00", "06:00", "通宵新闻"),
        ("06:00", "09:00", "早晨新闻"),
        ("09:00", "12:00", "财经早报"),
        ("12:00", "14:00", "午间快讯"),
        ("14:00", "17:00", "时事聚焦"),
        ("17:00", "19:00", "新闻最前线"),
        ("19:00", "21:00", "晚间报道"),
        ("21:00", "23:00", "十点新闻"),
        ("23:00", "00:00", "夜间新闻")
    ],
    "NOW星影": [
        ("06:00", "09:00", "经典电影"),
        ("09:00", "12:00", "动作剧场"),
        ("12:00", "15:00", "爱情剧场"),
        ("15:00", "18:00", "喜剧专场"),
        ("18:00", "21:00", "黄金剧场"),
        ("21:00", "00:00", "深夜影院"),
        ("00:00", "03:00", "经典回顾"),
        ("03:00", "06:00", "电影马拉松")
    ],
    "NOW爆谷": [
        ("06:00", "09:00", "卡通世界"),
        ("09:00", "12:00", "儿童剧场"),
        ("12:00", "15:00", "综艺天地"),
        ("15:00", "18:00", "娱乐直播"),
        ("18:00", "21:00", "爆谷剧场"),
        ("21:00", "00:00", "娱乐最前线"),
        ("00:00", "03:00", "深夜娱乐"),
        ("03:00", "06:00", "回放精选")
    ],
    # 默认模板
    "DEFAULT": [
        ("06:00", "09:00", "早晨节目"),
        ("09:00", "12:00", "上午剧场"),
        ("12:00", "14:00", "午间新闻"),
        ("14:00", "17:00", "下午剧场"),
        ("17:00", "19:00", "傍晚新闻"),
        ("19:00", "21:00", "黄金剧场"),
        ("21:00", "23:00", "晚间新闻"),
        ("23:00", "01:00", "夜间节目"),
        ("01:00", "06:00", "通宵剧场")
    ]
}

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def generate_channel_id(channel_name):
    """为频道生成唯一的ID"""
    # 清理特殊字符
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
    
    # 常见频道映射
    channel_map = {
        "凤凰中文": "fenghuang_zhongwen",
        "凤凰资讯": "fenghuang_zixun",
        "凤凰香港": "fenghuang_xianggang",
        "NOW新闻台": "now_news",
        "NOW星影": "now_movie",
        "NOW爆谷": "now_ent",
        "TVB新闻": "tvb_news",
        "TVB财经": "tvb_finance",
        "有线新闻": "cable_news",
        "民视": "ftv",
        "中视": "ctv",
        "华视": "cts",
        "台视": "ttv",
        "三立": "set",
        "东森": "ebc",
        "TVBS": "tvbs",
        "中天": "ctitv",
        "寰宇": "universal",
        "非凡": "ustv"
    }
    
    # 检查映射
    for key, value in channel_map.items():
        if key in channel_name:
            return value
    
    # 生成简写ID
    if len(clean_name) >= 4:
        # 取前4个字符的拼音首字母或直接使用
        return clean_name[:8].lower()
    else:
        # 使用哈希
        import hashlib
        return "ch_" + hashlib.md5(channel_name.encode()).hexdigest()[:6]

def download_bb_m3u():
    """下载BB.m3u"""
    try:
        log("下载BB.m3u...")
        response = requests.get(BB_URL, timeout=10)
        response.raise_for_status()
        log(f"✅ BB.m3u下载成功 ({len(response.text)} 字符)")
        return response.text
    except Exception as e:
        log(f"❌ BB.m3u下载失败: {e}")
        return None

def get_proxy_content():
    """从Cloudflare代理获取内容"""
    try:
        log("从Cloudflare代理获取内容...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(CLOUDFLARE_PROXY, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            # 提取M3U内容
            if '<html' in content.lower():
                m3u_match = re.search(r'(#EXTM3U.*?)(?:</pre>|</code>|$)', content, re.DOTALL)
                if m3u_match:
                    content = m3u_match.group(1).strip()
                    log("✅ 从HTML提取到M3U内容")
            
            if content and content.strip():
                log(f"✅ 获取到内容 ({len(content)} 字符)")
                return content
    except Exception as e:
        log(f"❌ 代理访问失败: {e}")
    
    return None

def parse_m3u_channels(content):
    """解析M3U内容为频道列表"""
    if not content:
        return []
    
    channels = []
    lines = content.split('\n')
    current_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('#EXTINF:'):
            current_extinf = line
        elif current_extinf and '://' in line and not line.startswith('#'):
            # 提取频道名
            channel_name = current_extinf.split(',', 1)[1] if ',' in current_extinf else current_extinf
            
            channels.append({
                'extinf': current_extinf,
                'url': line,
                'name': channel_name,
                'original_name': channel_name
            })
            current_extinf = None
    
    return channels

def filter_and_rename_channels(channels):
    """过滤和重命名频道"""
    hk_channels = []
    tw_channels = []
    
    for channel in channels:
        channel_name = channel['name']
        
        # 检查是否是JULI频道（HK）
        if 'JULI' in channel_name.upper():
            # 重命名为HK
            new_name = re.sub(r'JULI', 'HK', channel_name, flags=re.IGNORECASE)
            new_extinf = channel['extinf'].replace(channel_name, new_name)
            
            # 确保group-title为HK
            if 'group-title=' in new_extinf:
                new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="HK"', new_extinf)
            else:
                new_extinf = new_extinf.replace('#EXTINF:', '#EXTINF: group-title="HK",', 1)
            
            channel['name'] = new_name
            channel['extinf'] = new_extinf
            channel['group'] = 'HK'
            hk_channels.append(channel)
        
        # 检查是否是4gtv频道（TW）
        elif '4gtv' in channel_name.lower():
            # 检查是否在黑名单中
            skip = False
            for black_word in BLACKLIST_TW:
                if black_word.lower() in channel_name.lower():
                    skip = True
                    break
            
            if not skip:
                # 重命名为TW
                new_name = re.sub(r'4gtv', 'TW', channel_name, flags=re.IGNORECASE)
                new_extinf = channel['extinf'].replace(channel_name, new_name)
                
                # 确保group-title为TW
                if 'group-title=' in new_extinf:
                    new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="TW"', new_extinf)
                else:
                    new_extinf = new_extinf.replace('#EXTINF:', '#EXTINF: group-title="TW",', 1)
                
                channel['name'] = new_name
                channel['extinf'] = new_extinf
                channel['group'] = 'TW'
                tw_channels.append(channel)
    
    # HK频道排序
    def hk_sort_key(channel):
        name = channel['name']
        for i, priority in enumerate(HK_PRIORITY_ORDER):
            if priority in name:
                return i
        return len(HK_PRIORITY_ORDER)
    
    hk_channels.sort(key=hk_sort_key)
    
    # TW频道限制30个
    tw_channels = tw_channels[:30]
    
    return hk_channels, tw_channels

def generate_epg_xml(channels):
    """生成EPG XML文件"""
    log("生成EPG XML文件...")
    
    # 创建XML根元素
    tv = ET.Element('tv')
    tv.set('generator-info-name', 'CC EPG Generator')
    tv.set('generator-info-url', 'https://github.com/sufernnet/joker')
    
    # 获取当前日期
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    for channel in channels:
        channel_name = channel['name']
        channel_id = generate_channel_id(channel_name)
        
        # 添加频道元素
        channel_elem = ET.SubElement(tv, 'channel')
        channel_elem.set('id', channel_id)
        
        # 添加显示名称
        display_name = ET.SubElement(channel_elem, 'display-name')
        display_name.set('lang', 'zh')
        display_name.text = channel_name
        
        # 添加节目单
        schedule = CHANNEL_SCHEDULES.get(channel_name, CHANNEL_SCHEDULES['DEFAULT'])
        
        # 今天和明天的节目
        for day_offset in [0, 1]:
            day = today + timedelta(days=day_offset)
            date_str = day.strftime('%Y%m%d')
            
            for start_time, end_time, program_title in schedule:
                # 创建节目元素
                programme = ET.SubElement(tv, 'programme')
                
                # 时间格式：YYYYMMDDHHMMSS +0800
                start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y%m%d %H:%M")
                end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y%m%d %H:%M")
                
                # 处理跨天
                if end_time < start_time:
                    end_dt += timedelta(days=1)
                
                programme.set('start', start_dt.strftime('%Y%m%d%H%M%S +0800'))
                programme.set('stop', end_dt.strftime('%Y%m%d%H%M%S +0800'))
                programme.set('channel', channel_id)
                
                # 节目标题
                title = ET.SubElement(programme, 'title')
                title.set('lang', 'zh')
                title.text = program_title
                
                # 节目描述
                desc = ET.SubElement(programme, 'desc')
                desc.set('lang', 'zh')
                desc.text = f"{channel_name} - {program_title} ({start_time}-{end_time})"
                
                # 节目分类
                category = ET.SubElement(programme, 'category')
                category.set('lang', 'zh')
                if "新闻" in program_title or "财经" in program_title:
                    category.text = "新闻"
                elif "电影" in program_title or "剧场" in program_title:
                    category.text = "电影"
                elif "娱乐" in program_title or "综艺" in program_title:
                    category.text = "娱乐"
                else:
                    category.text = "综合"
    
    # 美化XML输出
    xml_str = ET.tostring(tv, encoding='utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')
    
    log(f"✅ 生成EPG XML，包含 {len(channels)} 个频道")
    return pretty_xml.decode('utf-8')

def enhance_m3u_with_epg(channels, epg_url):
    """增强M3U文件，添加EPG信息"""
    enhanced_channels = []
    
    for channel in channels:
        extinf = channel['extinf']
        channel_name = channel['name']
        channel_id = generate_channel_id(channel_name)
        
        # 添加tvg-id和tvg-name
        if 'tvg-id=' not in extinf:
            if 'tvg-name=' not in extinf:
                # 在group-title前插入tvg信息
                if 'group-title=' in extinf:
                    new_extinf = extinf.replace('group-title=', f'tvg-id="{channel_id}" tvg-name="{channel_name}" group-title=')
                else:
                    # 如果没有group-title，在逗号前添加
                    if ',' in extinf:
                        parts = extinf.split(',', 1)
                        new_extinf = f'{parts[0]} tvg-id="{channel_id}" tvg-name="{channel_name}",{parts[1]}'
                    else:
                        new_extinf = f'{extinf} tvg-id="{channel_id}" tvg-name="{channel_name}"'
            else:
                # 已有tvg-name，只添加tvg-id
                new_extinf = extinf.replace('tvg-name=', f'tvg-id="{channel_id}" tvg-name=')
        else:
            new_extinf = extinf
        
        channel['extinf'] = new_extinf
        channel['tvg_id'] = channel_id
        enhanced_channels.append(channel)
    
    return enhanced_channels

def main():
    """主函数"""
    log("开始生成M3U和EPG文件...")
    
    # 1. 下载BB.m3u
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从代理获取内容
    proxy_content = get_proxy_content()
    
    # 3. 解析频道
    all_channels = []
    
    # 解析BB频道
    bb_channels = parse_m3u_channels(bb_content)
    log(f"解析到 {len(bb_channels)} 个BB频道")
    
    # 解析代理频道
    if proxy_content:
        proxy_channels = parse_m3u_channels(proxy_content)
        log(f"解析到 {len(proxy_channels)} 个代理频道")
        
        # 过滤和重命名HK/TW频道
        hk_channels, tw_channels = filter_and_rename_channels(proxy_channels)
        log(f"过滤后得到 {len(hk_channels)} 个HK频道，{len(tw_channels)} 个TW频道")
        
        all_channels.extend(hk_channels)
        all_channels.extend(tw_channels)
    else:
        log("⚠️  无法获取代理内容，只使用BB频道")
    
    # 添加BB频道（排除重复）
    bb_names = {ch['name'] for ch in all_channels}
    for channel in bb_channels:
        if channel['name'] not in bb_names:
            channel['group'] = 'BB'
            all_channels.append(channel)
    
    log(f"总共 {len(all_channels)} 个频道")
    
    # 4. 生成EPG XML
    epg_xml = generate_epg_xml(all_channels)
    
    # 5. 增强M3U频道（添加EPG信息）
    enhanced_channels = enhance_m3u_with_epg(all_channels, "CC.xml")
    
    # 6. 生成M3U文件
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # EPG文件URL（GitHub Raw）
    epg_file_url = f"https://raw.githubusercontent.com/sufernnet/joker/main/{EPG_FILE}"
    
    m3u_content = f"""#EXTM3U x-tvg-url="{epg_file_url}" url-tvg="{epg_file_url}"
#EXTVLCOPT:program=999999
# 自动生成 M3U+EPG 文件
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 18:00
# 包含频道: {len(enhanced_channels)} 个
# EPG文件: {EPG_FILE} (本地生成，确保匹配)
# GitHub Actions 自动生成

"""
    
    # 按分组添加频道
    groups = {}
    for channel in enhanced_channels:
        group = channel.get('group', 'Other')
        if group not in groups:
            groups[group] = []
        groups[group].append(channel)
    
    # 按顺序输出：BB -> HK -> TW -> Other
    for group in ['BB', 'HK', 'TW', 'Other']:
        if group in groups and groups[group]:
            m3u_content += f"\n# {group}频道\n"
            for channel in groups[group]:
                m3u_content += channel['extinf'] + '\n'
                m3u_content += channel['url'] + '\n'
    
    # 添加统计信息
    m3u_content += f"""
# 统计信息
# BB频道: {len(groups.get('BB', []))}
# HK频道: {len(groups.get('HK', []))} (按指定顺序排列)
# TW频道: {len(groups.get('TW', []))} (前30个，已过滤)
# 总频道: {len(enhanced_channels)}
# EPG状态: ✅ 已生成本地EPG文件 ({EPG_FILE})
# 更新时间: {timestamp}
# 更新频率: 每天 06:00 和 18:00 (北京时间)
"""
    
    # 7. 保存文件
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    with open(EPG_FILE, "w", encoding="utf-8") as f:
        f.write(epg_xml)
    
    log(f"\n🎉 生成完成!")
    log(f"📁 M3U文件: {M3U_FILE} ({len(m3u_content)} 字符)")
    log(f"📁 EPG文件: {EPG_FILE} ({len(epg_xml)} 字符)")
    log(f"📺 频道总数: {len(enhanced_channels)}")
    log(f"📡 EPG覆盖: 100% (本地生成，确保匹配)")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 18:00")
    
    # 显示EPG文件URL
    log(f"🔗 EPG文件URL: {epg_file_url}")

if __name__ == "__main__":
    main()
