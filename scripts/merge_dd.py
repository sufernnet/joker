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
import time
from datetime import datetime

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
OUTPUT_FILE = "DD.m3u"

# 香港频道关键词
HK_KEYWORDS = [
    "香港", "港台", "TVB", "无线", "有线", "凤凰", "NOW", "VIU", "RTHK",
    "明珠", "翡翠", "本港", "国际", "财经", "新闻", "卫视", "亚洲",
    "中文", "资讯", "电影", "娱乐", "体育", "儿童", "粤语"
]

# 台湾频道关键词
TW_KEYWORDS = [
    "台湾", "台视", "中视", "华视", "民视", "三立", "东森", "TVBS",
    "中天", "寰宇", "非凡", "卫视", "电影", "戏剧", "新闻", "财经",
    "娱乐", "综合", "体育", "客家", "原民", "公视", "纬来", "龙祥"
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_content(url, description):
    """下载内容"""
    try:
        log(f"下载{description}...")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        content = response.text
        log(f"✅ {description}下载成功 ({len(content)} 字符)")
        return content
        
    except Exception as e:
        log(f"❌ {description}下载失败: {e}")
        return None

def extract_gat_channels(content):
    """从内容中提取港澳台频道"""
    if not content:
        return [], []
    
    log("提取港澳台频道...")
    
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
    
    log(f"找到 {len(channels)} 个频道")
    
    # 分类频道
    hk_channels = []
    tw_channels = []
    other_channels = []
    
    for extinf, url in channels:
        channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
        
        # 判断是否为港澳台频道
        is_gat = False
        
        # 检查香港关键词
        for keyword in HK_KEYWORDS:
            if keyword in channel_name:
                # 增强EXTINF，添加group-title
                if 'group-title=' not in extinf:
                    new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="香港",', 1)
                else:
                    new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="香港"', extinf)
                
                hk_channels.append((new_extinf, url, channel_name))
                is_gat = True
                break
        
        # 检查台湾关键词（如果还不是港澳台频道）
        if not is_gat:
            for keyword in TW_KEYWORDS:
                if keyword in channel_name:
                    if 'group-title=' not in extinf:
                        new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="台湾",', 1)
                    else:
                        new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="台湾"', extinf)
                    
                    tw_channels.append((new_extinf, url, channel_name))
                    is_gat = True
                    break
        
        # 如果不是港澳台频道，检查其他特征
        if not is_gat:
            # 检查URL中是否包含相关关键词
            url_lower = url.lower()
            if 'hongkong' in url_lower or 'hk' in url_lower or 'tw' in url_lower or 'taiwan' in url_lower:
                # 根据URL判断
                if 'hk' in url_lower or 'hongkong' in url_lower:
                    new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="香港",', 1)
                    hk_channels.append((new_extinf, url, channel_name))
                elif 'tw' in url_lower or 'taiwan' in url_lower:
                    new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="台湾",', 1)
                    tw_channels.append((new_extinf, url, channel_name))
                else:
                    other_channels.append((extinf, url, channel_name))
            else:
                other_channels.append((extinf, url, channel_name))
    
    log(f"✅ 分类完成:")
    log(f"   香港频道: {len(hk_channels)} 个")
    log(f"   台湾频道: {len(tw_channels)} 个")
    log(f"   其他频道: {len(other_channels)} 个")
    
    # 显示部分频道
    if hk_channels:
        log("香港频道示例:")
        for i, (extinf, url, name) in enumerate(hk_channels[:5]):
            log(f"   {i+1}. {name[:40]}...")
    
    if tw_channels:
        log("台湾频道示例:")
        for i, (extinf, url, name) in enumerate(tw_channels[:5]):
            log(f"   {i+1}. {name[:40]}...")
    
    return hk_channels, tw_channels

def get_bb_epg(bb_content):
    """从BB.m3u提取EPG信息"""
    if not bb_content:
        return None
    
    # 查找EPG URL
    epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
    if epg_match:
        return epg_match.group(1)
    
    # 尝试其他格式
    epg_match = re.search(r'x-tvg-url="([^"]+)"', bb_content)
    if epg_match:
        return epg_match.group(1)
    
    return None

def main():
    """主函数"""
    log("开始生成DD.m3u文件...")
    
    # 显示时间信息
    current_time = datetime.now()
    log(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    log(f"下次运行: 北京时间 06:00 和 17:00")
    log(f"港澳台源: {GAT_URL}")
    
    # 1. 下载BB.m3u
    bb_content = download_content(BB_URL, "BB.m3u")
    if not bb_content:
        log("❌ BB.m3u下载失败，无法继续")
        return
    
    # 提取BB的EPG
    epg_url = get_bb_epg(bb_content)
    if epg_url:
        log(f"✅ 使用EPG: {epg_url}")
    else:
        log("⚠️  未找到EPG信息")
    
    # 2. 下载港澳台直播源
    gat_content = download_content(GAT_URL, "港澳台直播源")
    
    # 3. 提取并分类港澳台频道
    hk_channels, tw_channels = [], []
    if gat_content:
        hk_channels, tw_channels = extract_gat_channels(gat_content)
    else:
        log("⚠️  无法获取港澳台内容，只合并BB.m3u")
    
    # 4. 构建DD.m3u内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部（使用BB的EPG）
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
# 自动分类: 香港频道、台湾频道
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
    
    # 添加香港频道
    if hk_channels:
        output += f"\n# 香港频道 ({len(hk_channels)}个)\n"
        
        # 按频道名排序
        hk_channels.sort(key=lambda x: x[2])
        
        for extinf, url, name in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加台湾频道
    if tw_channels:
        output += f"\n# 台湾频道 ({len(tw_channels)}个)\n"
        
        # 按频道名排序
        tw_channels.sort(key=lambda x: x[2])
        
        for extinf, url, name in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计和说明
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# 香港频道数: {len(hk_channels)} (自动分类)
# 台湾频道数: {len(tw_channels)} (自动分类)
# 总频道数: {bb_count + len(hk_channels) + len(tw_channels)}
# 更新时间: {timestamp}
# 更新频率: 每天 06:00 和 17:00 (北京时间)
# 分类规则:
#   香港: {', '.join(HK_KEYWORDS[:10])}...
#   台湾: {', '.join(TW_KEYWORDS[:10])}...
# EPG说明: 沿用BB.m3u的EPG源，确保节目单显示
"""
    
    # 5. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 DD.m3u生成完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {epg_url if epg_url else '沿用BB'}")
    log(f"📺 BB频道: {bb_count}")
    log(f"🎯 香港频道: {len(hk_channels)} (自动分类)")
    log(f"🎯 台湾频道: {len(tw_channels)} (自动分类)")
    log(f"📺 总计: {bb_count + len(hk_channels) + len(tw_channels)}")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 17:00")

if __name__ == "__main__":
    main()
