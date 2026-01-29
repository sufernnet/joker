#!/usr/bin/env python3
"""
DD.m3u合并脚本 - 针对目标源优化版
1. 从指定URL提取“港澳台直播”分组内的所有频道
2. 自动细分为“香港”、“台湾”两个分组
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

# 分组关键词
TARGET_GROUP = "港澳台直播"  # 要提取的目标分组
HK_GROUP_NAME = "香港"
TW_GROUP_NAME = "台湾"

# 香港频道关键词 (用于从“港澳台直播”中二次细分)
HK_KEYWORDS = ["香港", "港", "TVB", "无线", "明珠", "翡翠", "本港台", "凤凰卫视", "NOW", "VIU", "RTHK", "有线"]
# 台湾频道关键词
TW_KEYWORDS = ["台湾", "台", "台视", "中视", "华视", "民视", "三立", "东森", "TVBS", "中天", "寰宇", "非凡", "纬来"]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_content(url, description):
    """下载内容"""
    try:
        log(f"下载 {description}...")
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'}
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        log(f"✅ {description} 下载成功 ({len(response.text)} 字符)")
        return response.text
    except Exception as e:
        log(f"❌ {description} 下载失败: {e}")
        return None

def extract_target_group_channels(content):
    """
    核心功能：从内容中精确提取“港澳台直播”分组下的所有频道
    格式示例：频道名称,http://url
    """
    if not content:
        log("内容为空，无法提取")
        return []
    
    log(f"开始提取分组：{TARGET_GROUP}")
    
    # 查找目标分组开始位置
    target_section_pattern = f"{TARGET_GROUP},#genre#"
    lines = content.split('\n')
    target_channels = []
    in_target_section = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 找到目标分组标题行
        if target_section_pattern in line:
            in_target_section = True
            log(f"✅ 在第{i+1}行找到目标分组: {TARGET_GROUP}")
            continue
        
        # 如果已经在目标分组内
        if in_target_section:
            # 遇到下一个分组标题行（包含“,#genre#”）则停止
            if ",#genre#" in line:
                log(f"到达下一个分组，停止提取")
                break
            
            # 解析频道行（格式：频道名,URL）
            if ',' in line and '://' in line:
                parts = line.split(',', 1)  # 只分割第一个逗号
                if len(parts) == 2:
                    channel_name, channel_url = parts
                    target_channels.append((channel_name.strip(), channel_url.strip()))
    
    log(f"从『{TARGET_GROUP}』分组中提取到 {len(target_channels)} 个频道")
    
    # 显示前几个提取到的频道
    if target_channels:
        log("提取到的频道示例：")
        for idx, (name, url) in enumerate(target_channels[:8]):
            log(f"  {idx+1:2d}. {name[:40]:<40} | URL长度:{len(url)}")
    else:
        log("⚠️  未在目标分组中找到任何频道")
        # 调试：显示目标分组附近的内容
        log("分组附近内容（用于调试）：")
        for i, line in enumerate(lines):
            if TARGET_GROUP in line:
                start = max(0, i-3)
                end = min(len(lines), i+10)
                for j in range(start, end):
                    log(f"  行{j+1}: {lines[j][:80]}")
                break
    
    return target_channels

def classify_channels_by_region(channels):
    """将频道细分为香港和台湾"""
    hk_channels = []
    tw_channels = []
    unclassified_channels = []  # 无法分类的频道
    
    log("开始细分香港/台湾频道...")
    
    for channel_name, channel_url in channels:
        name_lower = channel_name.lower()
        classified = False
        
        # 检查是否为香港频道
        for keyword in HK_KEYWORDS:
            if keyword.lower() in name_lower:
                # 确保频道名称格式正确
                extinf_line = f'#EXTINF:-1,{channel_name}'
                if not any(group_tag in extinf_line for group_tag in ['group-title="', 'tvg-id="']):
                    extinf_line = f'#EXTINF:-1 group-title="{HK_GROUP_NAME}",{channel_name}'
                else:
                    # 替换现有分组
                    extinf_line = re.sub(r'group-title="[^"]*"', f'group-title="{HK_GROUP_NAME}"', extinf_line)
                
                hk_channels.append((extinf_line, channel_url, channel_name))
                classified = True
                break
        
        # 如果不是香港，检查是否为台湾
        if not classified:
            for keyword in TW_KEYWORDS:
                if keyword.lower() in name_lower:
                    extinf_line = f'#EXTINF:-1,{channel_name}'
                    if not any(group_tag in extinf_line for group_tag in ['group-title="', 'tvg-id="']):
                        extinf_line = f'#EXTINF:-1 group-title="{TW_GROUP_NAME}",{channel_name}'
                    else:
                        extinf_line = re.sub(r'group-title="[^"]*"', f'group-title="{TW_GROUP_NAME}"', extinf_line)
                    
                    tw_channels.append((extinf_line, channel_url, channel_name))
                    classified = True
                    break
        
        # 如果无法分类，保留原样（仍属于“港澳台直播”分组）
        if not classified:
            extinf_line = f'#EXTINF:-1,{channel_name}'
            unclassified_channels.append((extinf_line, channel_url, channel_name))
    
    # 输出分类统计
    log(f"✅ 频道细分完成：")
    log(f"   ├─ 香港频道: {len(hk_channels)} 个")
    log(f"   ├─ 台湾频道: {len(tw_channels)} 个")
    log(f"   └─ 未细分频道: {len(unclassified_channels)} 个 (保留在『{TARGET_GROUP}』)")
    
    # 显示分类示例
    if hk_channels:
        log("香港频道示例：")
        for _, _, name in hk_channels[:4]:
            log(f"    • {name}")
    
    if tw_channels:
        log("台湾频道示例：")
        for _, _, name in tw_channels[:4]:
            log(f"    • {name}")
    
    return hk_channels, tw_channels, unclassified_channels

def get_bb_epg(bb_content):
    """从BB.m3u提取EPG信息"""
    if not bb_content:
        return None
    
    epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
    if epg_match:
        return epg_match.group(1)
    
    epg_match = re.search(r'x-tvg-url="([^"]+)"', bb_content)
    if epg_match:
        return epg_match.group(1)
    
    return None

def main():
    """主函数"""
    log("开始生成 DD.m3u (针对目标源优化版)...")
    
    # 1. 下载BB.m3u
    bb_content = download_content(BB_URL, "BB.m3u")
    if not bb_content:
        log("❌ BB.m3u下载失败，无法继续")
        return
    
    # 2. 下载港澳台源
    gat_content = download_content(GAT_URL, "港澳台直播源")
    if not gat_content:
        log("⚠️  港澳台源下载失败，只合并BB.m3u")
        gat_content = ""
    
    # 3. 提取EPG
    epg_url = get_bb_epg(bb_content)
    log(f"EPG源: {epg_url if epg_url else '未找到，使用默认头部'}")
    
    # 4. 处理目标分组频道
    hk_channels, tw_channels, other_gat_channels = [], [], []
    
    if gat_content:
        # 4.1 提取目标分组的所有频道
        target_group_channels = extract_target_group_channels(gat_content)
        
        if target_group_channels:
            # 4.2 将目标分组频道细分为香港和台湾
            hk_channels, tw_channels, other_gat_channels = classify_channels_by_region(target_group_channels)
        else:
            log("⚠️  未找到目标分组频道，跳过港澳台内容")
    else:
        log("⚠️  无港澳台内容，仅使用BB.m3u")
    
    # 5. 构建DD.m3u
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部
    if epg_url:
        m3u_header = f'#EXTM3U url-tvg="{epg_url}"\n'
    else:
        m3u_header = '#EXTM3U\n'
    
    output = m3u_header + f"""# DD.m3u - 港澳台专版 (优化版)
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 17:00 (北京时间)
# BB源: {BB_URL}
# 港澳台源: {GAT_URL}
# 处理逻辑: 提取『{TARGET_GROUP}』分组 → 细分为「香港」「台湾」
# EPG源: {epg_url if epg_url else '沿用BB的EPG'}
# GitHub Actions 自动生成

"""
    
    # 5.1 添加BB内容（跳过第一行）
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
    
    # 5.2 添加香港频道
    if hk_channels:
        output += f"\n# {HK_GROUP_NAME}频道 (共 {len(hk_channels)} 个，从『{TARGET_GROUP}』细分)\n"
        # 按频道名排序
        hk_channels.sort(key=lambda x: x[2])
        for extinf, url, _ in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    else:
        output += f"\n# {HK_GROUP_NAME}频道 (0个 - 未从源中识别到香港频道)\n"
    
    # 5.3 添加台湾频道
    if tw_channels:
        output += f"\n# {TW_GROUP_NAME}频道 (共 {len(tw_channels)} 个，从『{TARGET_GROUP}』细分)\n"
        tw_channels.sort(key=lambda x: x[2])
        for extinf, url, _ in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    else:
        output += f"\n# {TW_GROUP_NAME}频道 (0个 - 未从源中识别到台湾频道)\n"
    
    # 5.4 添加未细分的港澳台频道（如有）
    if other_gat_channels:
        output += f"\n# 其他{TARGET_GROUP}频道 (共 {len(other_gat_channels)} 个，未细分)\n"
        for extinf, url, _ in other_gat_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 5.5 添加统计信息
    total_channels = bb_count + len(hk_channels) + len(tw_channels) + len(other_gat_channels)
output += f"""

# 统计信息
# BB 频道数: {bb_count}
# 香港频道数: {len(hk_channels)} (从『{TARGET_GROUP}』细分)
# 台湾频道数: {len(tw_channels)} (从『{TARGET_GROUP}』细分)
# 其他{target_group}频道数: {len(other_gat_channels)}
# 总频道数: {total_channels}
# 更新时间: {timestamp}
# 更新频率: 每天 06:00 和 17:00 (北京时间)
# 备注: 本文件专为『{GAT_URL}』源优化，确保正确提取并细分港澳台频道
"""
    
    # 6. 保存文件
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        
        log(f"\n🎉 DD.m3u 生成成功！")
        log(f"📁 文件: {OUTPUT_FILE}")
        log(f"📏 大小: {len(output):,} 字符")
        log(f"📺 频道统计: BB({bb_count}) + 香港({len(hk_channels)}) + 台湾({len(tw_channels)}) = {total_channels}")
        
        # 显示文件头部
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            log("文件头部预览:")
            for i, line in enumerate(f.readlines()[:15]):
                if line.strip():
                    log(f"  {i+1:2d}: {line.rstrip()}")
                    
    except Exception as e:
        log(f"❌ 保存文件失败: {e}")

if __name__ == "__main__":
    main()
