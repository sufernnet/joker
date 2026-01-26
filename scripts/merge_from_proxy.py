#!/usr/bin/env python3
"""
M3U文件合并脚本
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取内容
3. 提取4gtv前30个直播，分组改为TW
4. 提取JULI频道，分组改为HK
5. 合并生成CC.m3u
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
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*'
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

def extract_4gtv_channels(content, limit=30):
    """提取4gtv频道（前30个），分组改为TW"""
    if not content:
        return []
    
    log(f"提取4gtv前{limit}个直播，分组改为TW...")
    
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
    
    # 只取前limit个
    if len(filtered_channels) > limit:
        filtered_channels = filtered_channels[:limit]
        log(f"只取前 {limit} 个4gtv频道")
    
    # 重命名为TW分组
    tw_channels = []
    seen = set()
    
    for extinf, url in filtered_channels:
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
    
    log(f"✅ 提取到 {len(tw_channels)} 个TW频道（原4gtv）")
    
    if tw_channels:
        log("TW频道示例:")
        for i, (extinf, url) in enumerate(tw_channels[:5]):
            name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i+1}. {name[:50]}...")
    
    return tw_channels

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
        log("HK频道示例:")
        for i, (extinf, url) in enumerate(hk_channels[:5]):
            name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i+1}. {name[:50]}...")
    
    return hk_channels

def main():
    """主函数"""
    log("开始合并M3U文件...")
    
    # 1. 下载BB.m3u并获取EPG
    bb_content, epg_url = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从代理获取内容
    proxy_content = get_content_from_proxy()
    
    # 3. 提取TW频道（4gtv前30个）
    tw_channels = []
    if proxy_content:
        tw_channels = extract_4gtv_channels(proxy_content, limit=30)
    else:
        log("⚠️  无法从代理获取内容，跳过TW频道")
    
    # 4. 提取HK频道（JULI）
    hk_channels = []
    if proxy_content:
        hk_channels = extract_hk_channels(proxy_content)
    else:
        log("⚠️  无法从代理获取内容，跳过HK频道")
    
    # 5. 构建M3U内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部（使用BB的EPG）
    if epg_url:
        m3u_header = f'#EXTM3U url-tvg="{epg_url}"\n'
    else:
        m3u_header = '#EXTM3U\n'
    
    output = m3u_header + f"""# 自动合并 M3U 文件
# 生成时间: {timestamp}
# BB源: {BB_URL}
# 代理源: {CLOUDFLARE_PROXY}
# 4gtv分组已改为TW（前30个）
# JULI分组已改为HK
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
    
    # 添加TW频道（4gtv）
    if tw_channels:
        output += f"\n# TW频道 (原4gtv，前30个)\n"
        for extinf, url in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加HK频道（JULI）
    if hk_channels:
        output += f"\n# HK频道 (原JULI)\n"
        for extinf, url in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# TW 频道数: {len(tw_channels)} (原4gtv前30个)
# HK 频道数: {len(hk_channels)} (原JULI)
# 总频道数: {bb_count + len(tw_channels) + len(hk_channels)}
# 更新时间: {timestamp}
# 更新频率: 每天 06:00 和 18:00
"""
    
    # 6. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {epg_url}")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 TW频道: {len(tw_channels)} (4gtv前30个)")
    log(f"📺 HK频道: {len(hk_channels)} (JULI)")
    log(f"📺 总计: {bb_count + len(tw_channels) + len(hk_channels)}")

if __name__ == "__main__":
    main()
