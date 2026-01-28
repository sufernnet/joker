#!/usr/bin/env python3
"""
M3U文件合并脚本 - 增强EPG支持
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取内容
3. 提取JULI频道，分组改为HK，按指定顺序排列
4. 提取4gtv前30个直播，分组改为TW，过滤指定频道
5. 合并生成CC.m3u，包含多个EPG源
6. 下载并合并多个EPG源，生成新的EPG文件
北京时间每天6:00、17:00自动运行
"""

import requests
import re
import os
import time
import gzip
import io
from datetime import datetime
import xml.etree.ElementTree as ET
from collections import defaultdict

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
CLOUDFLARE_PROXY = "https://smt-proxy.sufern001.workers.dev/"
OUTPUT_FILE = "CC.m3u"
EPG_OUTPUT_FILE = "merged_epg.xml"
EPG_SOURCES = [
    "https://epg.112114.xyz/pp.xml",
    "https://epg.946985.filegear-sg.me/t.xml.gz",
    "http://epg.51zmt.top:8000/e.xml"
]

# 需要过滤掉的TW频道关键词（不区分大小写）
BLACKLIST_TW = [
    "Bloomberg TV",
    "Bloomberg",
    "SBN全球财经台",
    "SBN财经",
    "FRANCE24英文台",
    "FRANCE24",
    "半岛国际新闻台",
    "半島国际",
    "NHK world-japan",
    "NHK world",
    "SBN",
    "日本",
    "NHK",
    "CNBC Asia",
    "CNBC"
]

# HK频道优先顺序（按这个顺序排列在最前面）
HK_PRIORITY_ORDER = [
    "凤凰中文",
    "凤凰资讯", 
    "凤凰香港",
    "NOW新闻台",
    "NOW星影",
    "NOW爆谷"
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_epg_source(url):
    """下载EPG源"""
    try:
        log(f"下载EPG源: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate'
        }
        
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        
        if response.status_code == 200:
            # 检查是否为gzip压缩
            content_type = response.headers.get('content-type', '').lower()
            content_encoding = response.headers.get('content-encoding', '').lower()
            
            if url.endswith('.gz') or 'gzip' in content_encoding or 'application/gzip' in content_type:
                # 解压gzip内容
                log(f"  检测到gzip压缩，正在解压...")
                with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz_file:
                    content = gz_file.read().decode('utf-8', errors='ignore')
            else:
                content = response.text
            
            if content and len(content) > 100:  # 确保有足够的内容
                log(f"  ✅ 下载成功 ({len(content)} 字符)")
                return content
            else:
                log(f"  ⚠️  内容过短或为空")
                return None
        else:
            log(f"  ❌ 下载失败 (状态码: {response.status_code})")
            return None
            
    except Exception as e:
        log(f"  ❌ 下载失败: {e}")
        return None

def merge_epg_sources():
    """合并多个EPG源"""
    log(f"开始合并EPG源，共 {len(EPG_SOURCES)} 个")
    
    all_channels = defaultdict(list)  # channel_id -> [programmes]
    channel_info = {}  # channel_id -> channel_info
    
    for i, epg_url in enumerate(EPG_SOURCES, 1):
        log(f"\n处理EPG源 {i}/{len(EPG_SOURCES)}: {epg_url}")
        content = download_epg_source(epg_url)
        
        if not content:
            continue
        
        try:
            # 清理XML，移除无效字符
            content_clean = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
            
            # 尝试解析XML
            root = ET.fromstring(content_clean)
            
            # 提取频道信息
            channels = 0
            programmes = 0
            
            for element in root:
                if element.tag == 'channel':
                    # 提取频道信息
                    channel_id = element.get('id')
                    if channel_id:
                        channel_info[channel_id] = ET.tostring(element, encoding='unicode')
                        channels += 1
                
                elif element.tag == 'programme':
                    # 提取节目信息
                    channel_id = element.get('channel')
                    if channel_id:
                        all_channels[channel_id].append(ET.tostring(element, encoding='unicode'))
                        programmes += 1
            
            log(f"  解析成功: {channels} 个频道, {programmes} 个节目")
            
        except ET.ParseError as e:
            log(f"  ⚠️  XML解析失败: {e}")
            # 尝试修复常见问题
            try:
                # 移除无效的XML声明
                content_fixed = re.sub(r'<\?xml[^>]*\?>', '', content_clean)
                content_fixed = f'<?xml version="1.0" encoding="UTF-8"?><tv>{content_fixed}</tv>'
                
                root = ET.fromstring(content_fixed)
                channels = 0
                programmes = 0
                
                for element in root:
                    if element.tag == 'channel':
                        channel_id = element.get('id')
                        if channel_id:
                            channel_info[channel_id] = ET.tostring(element, encoding='unicode')
                            channels += 1
                    
                    elif element.tag == 'programme':
                        channel_id = element.get('channel')
                        if channel_id:
                            all_channels[channel_id].append(ET.tostring(element, encoding='unicode'))
                            programmes += 1
                
                log(f"  修复后解析成功: {channels} 个频道, {programmes} 个节目")
                
            except Exception as e2:
                log(f"  ❌ 修复后仍然解析失败: {e2}")
                continue
    
    # 生成合并后的EPG
    log(f"\n生成合并后的EPG...")
    
    # 统计信息
    total_channels = len(channel_info)
    total_programmes = sum(len(progs) for progs in all_channels.values())
    
    # 创建XML头部
    merged_epg = '''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="Merged EPG" generator-info-url="https://github.com/your-repo">
<!-- 
  合并EPG源信息:
  • https://epg.112114.xyz/pp.xml
  • https://epg.946985.filegear-sg.me/t.xml.gz
  • http://epg.51zmt.top:8000/e.xml
  
  生成时间: {timestamp} (北京时间)
  更新频率: 每天 06:00 和 17:00 (北京时间)
  频道总数: {channels}
  节目总数: {programmes}
-->
'''.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        channels=total_channels,
        programmes=total_programmes
    )
    
    # 添加频道信息
    if channel_info:
        merged_epg += "\n<!-- 频道信息 -->\n"
        for channel_id, channel_xml in sorted(channel_info.items()):
            merged_epg += channel_xml + "\n"
    
    # 添加节目信息
    if all_channels:
        merged_epg += "\n<!-- 节目信息 -->\n"
        for channel_id in sorted(all_channels.keys()):
            for programme_xml in all_channels[channel_id]:
                merged_epg += programme_xml + "\n"
    
    # 关闭XML标签
    merged_epg += "</tv>"
    
    # 保存合并后的EPG文件
    with open(EPG_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(merged_epg)
    
    log(f"✅ EPG合并完成: {EPG_OUTPUT_FILE}")
    log(f"   频道数: {total_channels}")
    log(f"   节目数: {total_programmes}")
    log(f"   文件大小: {len(merged_epg)} 字符")
    
    # 返回可访问的URL（假设部署在GitHub Pages或同一目录下）
    return EPG_OUTPUT_FILE

def download_bb_m3u():
    """下载BB.m3u并提取EPG"""
    try:
        log("下载BB.m3u...")
        response = requests.get(BB_URL, timeout=10)
        response.raise_for_status()
        
        bb_content = response.text
        log(f"✅ BB.m3u下载成功 ({len(bb_content)} 字符)")
        
        return bb_content
        
    except Exception as e:
        log(f"❌ BB.m3u下载失败: {e}")
        return None

def get_content_from_proxy():
    """从Cloudflare代理获取内容"""
    try:
        log("从Cloudflare代理获取内容...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://smart.946985.filegear-sg.me/'
        }
        
        response = requests.get(CLOUDFLARE_PROXY, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            # 如果是HTML，尝试提取M3U内容
            if '<html' in content.lower():
                # 查找M3U内容
                m3u_match = re.search(r'(#EXTM3U.*?)(?:</pre>|</code>|$)', content, re.DOTALL)
                if m3u_match:
                    content = m3u_match.group(1).strip()
                    log("✅ 从HTML提取到M3U内容")
                else:
                    # 提取所有可能的频道行
                    lines = content.split('\n')
                    m3u_lines = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith('#EXTINF:') or ('://' in line and not line.startswith('<')):
                            m3u_lines.append(line)
                    
                    if m3u_lines:
                        content = '#EXTM3U\n' + '\n'.join(m3u_lines)
                        log(f"✅ 从HTML提取到 {len(m3u_lines)} 个频道行")
            
            if content and content.strip():
                log(f"✅ 获取到内容 ({len(content)} 字符)")
                return content
            else:
                log("⚠️  内容为空")
        else:
            log(f"❌ 代理返回错误: {response.status_code}")
            
    except Exception as e:
        log(f"❌ 代理访问失败: {e}")
    
    return None

def get_channel_priority(channel_name):
    """获取频道的优先级（越小越靠前）"""
    channel_name_lower = channel_name.lower()
    
    for i, priority_channel in enumerate(HK_PRIORITY_ORDER):
        if priority_channel.lower() in channel_name_lower:
            return i  # 返回优先级索引，越小越靠前
    
    return len(HK_PRIORITY_ORDER)  # 非优先频道排在最后

def extract_and_sort_hk_channels(content):
    """提取JULI频道，分组改为HK，按指定顺序排列"""
    if not content:
        return []
    
    log("提取JULI频道，分组改为HK，按指定顺序排列...")
    log(f"HK优先顺序: {', '.join(HK_PRIORITY_ORDER)}")
    
    # 解析M3U内容
    lines = content.split('\n')
    channels = []
    current_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('#EXTINF:'):
            current_extinf = line
        elif current_extinf and '://' in line and not line.startswith('#'):
            channels.append((current_extinf, line))
            current_extinf = None
    
    # 过滤JULI频道并重命名
    hk_channels_with_priority = []
    seen = set()
    
    for extinf, url in channels:
        if 'JULI' in extinf.upper():
            # 提取原始频道名
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            
            # 重命名为HK分组
            new_extinf = re.sub(r'JULI', 'HK', extinf, flags=re.IGNORECASE)
            
            # 确保group-title为HK
            if 'group-title=' in new_extinf:
                new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="HK"', new_extinf)
            else:
                # 添加group-title
                if ',' in new_extinf:
                    parts = new_extinf.split(',', 1)
                    new_extinf = f'{parts[0]} group-title="HK",{parts[1]}'
            
            # 去重
            key = f"{new_extinf}|{url}"
            if key not in seen:
                seen.add(key)
                # 计算优先级
                priority = get_channel_priority(channel_name)
                hk_channels_with_priority.append((priority, new_extinf, url, channel_name))
    
    # 按优先级排序
    hk_channels_with_priority.sort(key=lambda x: x[0])
    
    # 提取排序后的频道
    hk_channels = [(extinf, url) for _, extinf, url, _ in hk_channels_with_priority]
    
    log(f"✅ 提取到 {len(hk_channels)} 个HK频道（原JULI）")
    
    return hk_channels

def should_skip_channel(channel_name):
    """检查频道是否应该被过滤"""
    channel_name_lower = channel_name.lower()
    
    # 检查是否在黑名单中
    for black_word in BLACKLIST_TW:
        if black_word.lower() in channel_name_lower:
            log(f"  过滤掉: {channel_name} (包含: {black_word})")
            return True
    
    return False

def extract_filtered_4gtv_channels(content, limit=30):
    """提取4gtv频道（前30个），分组改为TW，过滤指定频道"""
    if not content:
        return []
    
    log(f"提取4gtv前{limit}个直播，分组改为TW，过滤指定频道...")
    log(f"过滤列表: {', '.join(BLACKLIST_TW)}")
    
    # 解析M3U内容
    lines = content.split('\n')
    channels = []
    current_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('#EXTINF:'):
            current_extinf = line
        elif current_extinf and '://' in line and not line.startswith('#'):
            channels.append((current_extinf, line))
            current_extinf = None
    
    # 过滤4gtv频道（不区分大小写）
    filtered_channels = []
    for extinf, url in channels:
        if '4gtv' in extinf.lower():
            filtered_channels.append((extinf, url))
    
    log(f"找到 {len(filtered_channels)} 个4gtv频道")
    
    # 过滤黑名单频道
    filtered_by_blacklist = []
    for extinf, url in filtered_channels:
        # 提取频道名
        channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
        
        # 检查是否应该跳过
        if not should_skip_channel(channel_name):
            filtered_by_blacklist.append((extinf, url))
        else:
            log(f"  ⛔ 过滤: {channel_name}")
    
    log(f"过滤后剩余 {len(filtered_by_blacklist)} 个4gtv频道")
    
    # 只取前limit个
    if len(filtered_by_blacklist) > limit:
        filtered_by_blacklist = filtered_by_blacklist[:limit]
        log(f"只取前 {limit} 个过滤后的4gtv频道")
    
    # 重命名为TW分组
    tw_channels = []
    seen = set()
    
    for extinf, url in filtered_by_blacklist:
        # 替换分组为TW
        new_extinf = extinf
        
        # 替换4gtv为TW（在频道名中）
        if '4gtv' in new_extinf.lower():
            new_extinf = re.sub(r'4gtv', 'TW', new_extinf, flags=re.IGNORECASE)
        
        # 确保group-title为TW
        if 'group-title=' in new_extinf:
            new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="TW"', new_extinf)
        else:
            # 添加group-title
            if ',' in new_extinf:
                parts = new_extinf.split(',', 1)
                new_extinf = f'{parts[0]} group-title="TW",{parts[1]}'
        
        # 去重
        key = f"{new_extinf}|{url}"
        if key not in seen:
            seen.add(key)
            tw_channels.append((new_extinf, url))
    
    log(f"✅ 提取到 {len(tw_channels)} 个TW频道（原4gtv，已过滤）")
    
    return tw_channels

def main():
    """主函数"""
    log("开始合并M3U文件...")
    
    # 显示当前时间（用于调试定时任务）
    current_time = datetime.now()
    log(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"下次运行: 北京时间 06:00 和 17:00")
    log(f"HK优先顺序: {', '.join(HK_PRIORITY_ORDER)}")
    log(f"TW频道过滤列表: {', '.join(BLACKLIST_TW)}")
    log(f"EPG源列表: {', '.join(EPG_SOURCES)}")
    
    # 1. 下载并合并EPG源
    log("\n" + "="*50)
    log("步骤1: 合并EPG源")
    merged_epg_url = merge_epg_sources()
    
    # 2. 下载BB.m3u
    log("\n" + "="*50)
    log("步骤2: 下载BB.m3u")
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 3. 从代理获取内容
    log("\n" + "="*50)
    log("步骤3: 从代理获取内容")
    proxy_content = get_content_from_proxy()
    
    # 4. 先提取HK频道（JULI）- 按指定顺序排列在最前面
    log("\n" + "="*50)
    log("步骤4: 提取HK频道")
    hk_channels = []
    if proxy_content:
        hk_channels = extract_and_sort_hk_channels(proxy_content)
    else:
        log("⚠️  无法从代理获取内容，跳过HK频道")
    
    # 5. 再提取TW频道（4gtv前30个，过滤指定频道）- 排在后面
    log("\n" + "="*50)
    log("步骤5: 提取TW频道")
    tw_channels = []
    if proxy_content:
        tw_channels = extract_filtered_4gtv_channels(proxy_content, limit=30)
    else:
        log("⚠️  无法从代理获取内容，跳过TW频道")
    
    # 6. 构建M3U内容
    log("\n" + "="*50)
    log("步骤6: 构建M3U文件")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部（使用合并后的EPG）
    m3u_header = f'#EXTM3U url-tvg="{merged_epg_url}"\n'
    log(f"✅ 使用合并后的EPG: {merged_epg_url}")
    
    output = m3u_header + f"""# 自动合并 M3U 文件
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 17:00 (北京时间)
# BB源: {BB_URL}
# 代理源: {CLOUDFLARE_PROXY}
# JULI分组已改为HK (按指定顺序排列在最前面)
# HK优先顺序: {', '.join(HK_PRIORITY_ORDER)}
# 4gtv分组已改为TW (前30个，排在后面，已过滤指定频道)
# 过滤频道: {', '.join(BLACKLIST_TW)}
# EPG源: {merged_epg_url}
# 合并的EPG源: {len(EPG_SOURCES)} 个
#      {EPG_SOURCES[0]}
#      {EPG_SOURCES[1]}
#      {EPG_SOURCES[2]}
# GitHub Actions 自动生成

"""
    
    # 添加BB内容（跳过第一行）
    bb_lines = bb_content.split('\n')
    bb_count = 0
    skip_first = True
    
    for line in bb_lines:
        line = line.rstrip()
        if not line:
            continue
        
        if skip_first and line.startswith('#EXTM3U'):
            skip_first = False
            continue
        
        output += line + '\n'
        if line.startswith('#EXTINF:'):
            bb_count += 1
    
    # 添加HK频道（JULI）- 按指定顺序排列在最前面
    if hk_channels:
        output += f"\n# HK频道 (原JULI，按指定顺序排列在最前面)\n"
        output += f"# 优先顺序: {', '.join(HK_PRIORITY_ORDER)}\n"
        
        # 显示优先频道
        priority_added = False
        for channel_type in HK_PRIORITY_ORDER:
            type_channels = [(extinf, url) for extinf, url in hk_channels if channel_type.lower() in extinf.lower()]
            if type_channels:
                if not priority_added:
                    output += f"# --- 优先频道 ---\n"
                    priority_added = True
                
                for extinf, url in type_channels:
                    output += extinf + '\n'
                    output += url + '\n'
        
        # 显示其他HK频道
        other_hk_channels = [(extinf, url) for extinf, url in hk_channels 
                           if not any(channel_type.lower() in extinf.lower() for channel_type in HK_PRIORITY_ORDER)]
        
        if other_hk_channels:
            output += f"# --- 其他HK频道 ---\n"
            for extinf, url in other_hk_channels:
                output += extinf + '\n'
                output += url + '\n'
    
    # 添加TW频道（4gtv）- 排在后面（已过滤）
    if tw_channels:
        output += f"\n# TW频道 (原4gtv，前30个，已过滤指定频道，排在HK之后)\n"
        output += f"# 已过滤: {', '.join(BLACKLIST_TW)}\n"
        for extinf, url in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加EPG信息说明
    output += f"""
# EPG信息
# 使用合并后的EPG: {merged_epg_url}
# 合并的EPG源 ({len(EPG_SOURCES)}个):"""
    for i, epg in enumerate(EPG_SOURCES, 1):
        output += f"\n#      {epg}"
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)} (原JULI，按指定顺序排列)
# TW 频道数: {len(tw_channels)} (原4gtv前30个，已过滤，排在后)
# 过滤频道: {len(BLACKLIST_TW)} 个
# 总频道数: {bb_count + len(hk_channels) + len(tw_channels)}
# EPG状态: ✅ 合并 {len(EPG_SOURCES)} 个EPG源
# 更新时间: {timestamp} (北京时间)
# 更新频率: 每天 06:00 和 17:00 (北京时间)
# 排序规则: BB → HK(凤凰/NOW优先) → TW(已过滤)
"""
    
    # 7. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n" + "="*50)
    log("🎉 合并完成!")
    log(f"📁 M3U文件: {OUTPUT_FILE}")
    log(f"📏 M3U大小: {len(output)} 字符")
    log(f"📁 EPG文件: {EPG_OUTPUT_FILE}")
    log(f"📡 EPG状态: ✅ 合并 {len(EPG_SOURCES)} 个EPG源")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 HK频道: {len(hk_channels)} (按指定顺序排列)")
    log(f"📺 TW频道: {len(tw_channels)} (已过滤指定频道)")
    log(f"📺 总计: {bb_count + len(hk_channels) + len(tw_channels)}")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 17:00")
    
    # 检查文件是否存在
    if os.path.exists(EPG_OUTPUT_FILE):
        epg_size = os.path.getsize(EPG_OUTPUT_FILE)
        log(f"📊 EPG文件大小: {epg_size} 字节 ({epg_size/1024:.1f} KB)")
    else:
        log(f"⚠️  EPG文件未生成")

if __name__ == "__main__":
    main()
