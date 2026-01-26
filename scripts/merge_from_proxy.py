#!/usr/bin/env python3
"""
M3U文件合并脚本 - 使用BB的EPG
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取JULI内容
3. 提取JULI频道并改为HK分组
4. 合并生成CC.m3u，使用BB的EPG
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
        
        # 提取EPG信息（BB的XML地址）
        epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
        epg_url = epg_match.group(1) if epg_match else None
        
        if epg_url:
            log(f"✅ 使用BB的EPG: {epg_url}")
        else:
            log("⚠️  未找到EPG信息")
        
        return bb_content, epg_url
        
    except Exception as e:
        log(f"❌ BB.m3u下载失败: {e}")
        return None, None

def get_juli_from_proxy():
    """从Cloudflare代理获取JULI内容"""
    try:
        log("从Cloudflare代理获取JULI内容...")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*'
        }
        
        response = requests.get(CLOUDFLARE_PROXY, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            # 如果是HTML，尝试提取内容
            if '<html' in content.lower():
                # 查找M3U内容
                m3u_match = re.search(r'(#EXTM3U.*?)(?:</pre>|</code>|$)', content, re.DOTALL)
                if m3u_match:
                    content = m3u_match.group(1).strip()
                else:
                    # 提取频道行
                    lines = content.split('\n')
                    m3u_lines = [l.strip() for l in lines if l.strip().startswith('#EXTINF:') or ('://' in l and not l.startswith('<'))]
                    if m3u_lines:
                        content = '#EXTM3U\n' + '\n'.join(m3u_lines)
            
            if content.strip():
                log(f"✅ 从代理获取到内容 ({len(content)} 字符)")
                return content
            else:
                log("⚠️  代理返回空内容")
        else:
            log(f"❌ 代理返回错误: {response.status_code}")
            
    except Exception as e:
        log(f"❌ 代理访问失败: {e}")
    
    return None

def extract_hk_channels(content):
    """提取JULI频道并改为HK"""
    if not content:
        return []
    
    log("提取JULI频道并改为HK分组...")
    
    # 简单解析M3U
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
    
    # 过滤和重命名JULI频道
    hk_channels = []
    seen = set()
    
    for extinf, url in channels:
        if 'JULI' in extinf.upper():
            # 重命名为HK
            new_extinf = re.sub(r'JULI', 'HK', extinf, flags=re.IGNORECASE)
            
            # 确保有group-title
            if 'group-title=' not in new_extinf:
                if ',' in new_extinf:
                    parts = new_extinf.split(',', 1)
                    new_extinf = f'{parts[0]} group-title="HK",{parts[1]}'
            
            # 去重
            key = f"{new_extinf}|{url}"
            if key not in seen:
                seen.add(key)
                hk_channels.append((new_extinf, url))
    
    log(f"✅ 提取到 {len(hk_channels)} 个HK频道")
    
    if hk_channels:
        log("部分HK频道:")
        for i, (extinf, url) in enumerate(hk_channels[:3]):
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
    
    # 2. 从代理获取JULI内容
    juli_content = get_juli_from_proxy()
    
    # 3. 提取HK频道
    hk_channels = []
    if juli_content:
        hk_channels = extract_hk_channels(juli_content)
    else:
        log("⚠️  无法从代理获取JULI内容，只合并BB")
    
    # 4. 构建M3U内容
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
# JULI分组已改为HK分组
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
    
    # 添加HK频道
    if hk_channels:
        output += f"\n# HK频道 (原JULI频道)\n"
        for extinf, url in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)}
# 总频道数: {bb_count + len(hk_channels)}
# 更新时间: {timestamp}
# 更新频率: 每天 06:00 和 18:00
"""
    
    # 5. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {epg_url}")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 HK频道: {len(hk_channels)}")
    log(f"📺 总计: {bb_count + len(hk_channels)}")

if __name__ == "__main__":
    main()
