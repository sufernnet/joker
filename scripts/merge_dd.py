#!/usr/bin/env python3
"""
DD.m3u合并脚本
1. 从指定URL提取港澳台直播
2. 自动按香港、台湾分组
3. 与BB.m3u合并
4. 输出DD.m3u
北京时间每天6:00、17:00自动运行
"""

import requests
import re
import os
from datetime import datetime

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
OUTPUT_FILE = "DD.m3u"

# 香港频道关键词
HK_KEYWORDS = [
    "香港", "港台", "TVB", "无线", "有线", "凤凰", "NOW", "VIU", "RTHK",
    "明珠", "翡翠", "本港", "国际", "财经", "新闻", "卫视", "亚洲"
]

# 台湾频道关键词
TW_KEYWORDS = [
    "台湾", "台视", "中视", "华视", "民视", "三立", "东森", "TVBS",
    "中天", "寰宇", "非凡", "卫视", "电影", "戏剧", "新闻", "财经"
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_content(url, description):
    """下载内容"""
    try:
        log(f"下载 {description}...")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        content = response.text
        log(f"✅ {description} 下载成功 ({len(content)} 字符)")
        return content
        
    except Exception as e:
        log(f"❌ {description} 下载失败: {e}")
        return None

def extract_channels(content):
    """从内容中提取频道"""
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
            channels.append((current_extinf, line))
            current_extinf = None
    
    return channels

def classify_channels(channels):
    """分类频道为香港和台湾"""
    hk_channels = []
    tw_channels = []
    
    for extinf, url in channels:
        channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
        
        # 检查香港关键词
        is_hk = False
        for keyword in HK_KEYWORDS:
            if keyword in channel_name:
                # 添加香港分组
                if 'group-title=' in extinf:
                    new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="香港"', extinf)
                else:
                    new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="香港",', 1)
                
                hk_channels.append((new_extinf, url, channel_name))
                is_hk = True
                break
        
        # 如果还不是香港，检查台湾
        if not is_hk:
            for keyword in TW_KEYWORDS:
                if keyword in channel_name:
                    # 添加台湾分组
                    if 'group-title=' in extinf:
                        new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="台湾"', extinf)
                    else:
                        new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="台湾",', 1)
                    
                    tw_channels.append((new_extinf, url, channel_name))
                    break
    
    return hk_channels, tw_channels

def get_epg_url(content):
    """提取EPG URL"""
    if not content:
        return None
    
    # 查找url-tvg
    match = re.search(r'url-tvg="([^"]+)"', content)
    if match:
        return match.group(1)
    
    # 查找x-tvg-url
    match = re.search(r'x-tvg-url="([^"]+)"', content)
    if match:
        return match.group(1)
    
    return None

def main():
    """主函数"""
    log("开始生成 DD.m3u...")
    
    # 1. 下载BB.m3u
    bb_content = download_content(BB_URL, "BB.m3u")
    if not bb_content:
        log("❌ BB.m3u下载失败，无法继续")
        return
    
    # 2. 下载港澳台源
    gat_content = download_content(GAT_URL, "港澳台直播源")
    
    # 3. 提取EPG
    epg_url = get_epg_url(bb_content)
    if epg_url:
        log(f"✅ 使用EPG: {epg_url}")
    
    # 4. 提取和分类频道
    all_channels = []
    
    # BB频道
    bb_channels = extract_channels(bb_content)
    log(f"从BB提取到 {len(bb_channels)} 个频道")
    
    # 港澳台频道
    hk_channels = []
    tw_channels = []
    if gat_content:
        gat_channels = extract_channels(gat_content)
        log(f"从港澳台源提取到 {len(gat_channels)} 个频道")
        
        hk_channels, tw_channels = classify_channels(gat_channels)
        log(f"分类结果: 香港 {len(hk_channels)} 个, 台湾 {len(tw_channels)} 个")
    else:
        log("⚠️  港澳台源下载失败，只使用BB频道")
    
    # 5. 构建M3U内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部
    if epg_url:
        m3u_header = f'#EXTM3U url-tvg="{epg_url}"\n'
    else:
        m3u_header = '#EXTM3U\n'
    
    output = m3u_header + f"""# DD.m3u - 港澳台专版
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 17:00 (北京时间)
# BB源: {BB_URL}
# 港澳台源: {GAT_URL}
# EPG源: {epg_url if epg_url else '沿用BB的EPG'}
# GitHub Actions 自动生成

"""
    
    # 添加BB频道（跳过第一行）
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
    
    # 添加香港频道
    if hk_channels:
        output += f"\n# 香港频道 ({len(hk_channels)}个)\n"
        for extinf, url, name in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加台湾频道
    if tw_channels:
        output += f"\n# 台湾频道 ({len(tw_channels)}个)\n"
        for extinf, url, name in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# 香港频道数: {len(hk_channels)}
# 台湾频道数: {len(tw_channels)}
# 总频道数: {bb_count + len(hk_channels) + len(tw_channels)}
# 更新时间: {timestamp}
# 更新频率: 每天 06:00 和 17:00 (北京时间)
"""
    
    # 6. 保存文件
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        
        # 验证文件
        if os.path.exists(OUTPUT_FILE):
            file_size = os.path.getsize(OUTPUT_FILE)
            log(f"✅ DD.m3u 生成成功")
            log(f"📁 文件: {OUTPUT_FILE}")
            log(f"📏 大小: {file_size} 字节")
            log(f"📺 总频道: {bb_count + len(hk_channels) + len(tw_channels)}")
        else:
            log(f"❌ 文件保存失败")
            
    except Exception as e:
        log(f"❌ 保存文件错误: {e}")

if __name__ == "__main__":
    main()
