#!/usr/bin/env python3
"""
M3U文件合并脚本
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取内容
3. 提取JULI频道，分组改为HK（排在前面）
4. 提取4gtv前30个直播，分组改为TW（排在后面），过滤指定频道
5. 合并生成CC.m3u
北京时间每天6:00、18:00自动运行
"""

import requests
import re
import os
import time
from datetime import datetime

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
CLOUDFLARE_PROXY = "https://smt-proxy.sufern001.workers.dev/"
OUTPUT_FILE = "CC.m3u"

# 需要过滤掉的TW频道关键词（不区分大小写）
BLACKLIST_TW = [
    "Bloomberg TV",
    "Bloomberg",
    "SBN全球财经台",
    "SBN财经",
    "FRANCE24英文台",
    "FRANCE24",
    "半岛国际新闻台",
    "半岛国际",
    "半島",
    "日本",
    "SBN",
    "NHK world-japan",
    "NHK world",
    "NHK",
    "CNBC Asia",
    "CNBC"
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_bb_m3u():
    """下载BB.m3u并提取EPG"""
    try:
        log("下载BB.m3u...")
        response = requests.get(BB_URL, timeout=10)
        response.raise_for_status()
        
        bb_content = response.text
        log(f"✅ BB.m3u下载成功 ({len(bb_content)} 字符)")
        
        # 提取EPG信息
        epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
        epg_url = epg_match.group(1) if epg_match else None
        
        if epg_url:
            log(f"✅ 使用BB的EPG: {epg_url}")
        
        return bb_content, epg_url
        
    except Exception as e:
        log(f"❌ BB.m3u下载失败: {e}")
        return None, None

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

def extract_hk_channels(content):
    """提取JULI频道，分组改为HK"""
    if not content:
        return []
    
    log("提取JULI频道，分组改为HK...")
    
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
    
    # 过滤JULI频道
    hk_channels = []
    seen = set()
    
    for extinf, url in channels:
        if 'JULI' in extinf.upper():
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
                hk_channels.append((new_extinf, url))
    
    log(f"✅ 提取到 {len(hk_channels)} 个HK频道（原JULI）")
    
    if hk_channels:
        log("HK频道示例（排在TW之前）:")
        for i, (extinf, url) in enumerate(hk_channels[:5]):
            name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i+1}. {name[:50]}...")
    
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
    
    # 显示过滤掉的频道统计
    filtered_count = len(filtered_channels) - len(tw_channels)
    if filtered_count > 0:
        log(f"⛔ 过滤掉了 {filtered_count} 个TW频道")
    
    if tw_channels:
        log("TW频道示例（已过滤指定频道）:")
        for i, (extinf, url) in enumerate(tw_channels[:5]):
            name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i+1}. {name[:50]}...")
    
    return tw_channels

def main():
    """主函数"""
    log("开始合并M3U文件...")
    
    # 显示当前时间（用于调试定时任务）
    current_time = datetime.now()
    log(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"下次运行: 北京时间 06:00 和 18:00")
    log(f"TW频道过滤列表: {', '.join(BLACKLIST_TW)}")
    
    # 1. 下载BB.m3u并获取EPG
    bb_content, epg_url = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从代理获取内容
    proxy_content = get_content_from_proxy()
    
    # 3. 先提取HK频道（JULI）- 排在前面
    hk_channels = []
    if proxy_content:
        hk_channels = extract_hk_channels(proxy_content)
    else:
        log("⚠️  无法从代理获取内容，跳过HK频道")
    
    # 4. 再提取TW频道（4gtv前30个，过滤指定频道）- 排在后面
    tw_channels = []
    if proxy_content:
        tw_channels = extract_filtered_4gtv_channels(proxy_content, limit=30)
    else:
        log("⚠️  无法从代理获取内容，跳过TW频道")
    
    # 5. 构建M3U内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部（使用BB的EPG）
    if epg_url:
        m3u_header = f'#EXTM3U url-tvg="{epg_url}"\n'
    else:
        m3u_header = '#EXTM3U\n'
    
    output = m3u_header + f"""# 自动合并 M3U 文件
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 18:00 (北京时间)
# BB源: {BB_URL}
# 代理源: {CLOUDFLARE_PROXY}
# JULI分组已改为HK (排在前面)
# 4gtv分组已改为TW (前30个，排在后面，已过滤指定频道)
# 过滤频道: {', '.join(BLACKLIST_TW)}
# EPG: {epg_url if epg_url else 'BB的XML'}
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
    
    # 添加HK频道（JULI）- 排在前面
    if hk_channels:
        output += f"\n# HK频道 (原JULI，排在TW之前)\n"
        for extinf, url in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加TW频道（4gtv）- 排在后面（已过滤）
    if tw_channels:
        output += f"\n# TW频道 (原4gtv，前30个，已过滤指定频道，排在HK之后)\n"
        output += f"# 已过滤: {', '.join(BLACKLIST_TW)}\n"
        for extinf, url in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)} (原JULI，排在前)
# TW 频道数: {len(tw_channels)} (原4gtv前30个，已过滤，排在后)
# 过滤频道: {len(BLACKLIST_TW)} 个
# 总频道数: {bb_count + len(hk_channels) + len(tw_channels)}
# 更新时间: {timestamp} (北京时间)
# 更新频率: 每天 06:00 和 18:00 (北京时间)
# 排序规则: BB → HK → TW
"""
    
    # 6. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {epg_url}")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 HK频道: {len(hk_channels)} (JULI，排在前)")
    log(f"📺 TW频道: {len(tw_channels)} (4gtv前30个，已过滤{len(BLACKLIST_TW)}个频道，排在后)")
    log(f"📺 总计: {bb_count + len(hk_channels) + len(tw_channels)}")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 18:00")
    log(f"⛔ TW过滤列表: {', '.join(BLACKLIST_TW)}")

if __name__ == "__main__":
    main()
