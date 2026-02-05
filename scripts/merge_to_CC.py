#!/usr/bin/env python3
"""
CC.m3u 合并脚本 - 标准M3U格式（带公开台标）
从 https://stymei.sufern001.workers.dev/ 提取"🔥全网通港澳台"分组
生成标准M3U格式：#EXTINF标签 + group-title属性 + 公开台标
"""

import requests
from datetime import datetime
import os
import re
import urllib.parse

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def get_channel_logo_public(channel_name):
    """使用公开台标库获取台标URL"""
    
    # 主要台标库（按优先级）
    logo_sources = [
        # 1. IPTV-org 官方台标库（最全）
        "https://raw.githubusercontent.com/iptv-org/iptv/master/logos/",
        
        # 2. 中文台标库
        "https://raw.githubusercontent.com/fanmingming/live/main/tv/",
        
        # 3. 另一个中文台标库
        "https://raw.githubusercontent.com/lqist/IPTVlogos/main/",
        
        # 4. 备用台标库
        "https://raw.githubusercontent.com/ChengShide/IPTVlogos/main/",
    ]
    
    # 常见港澳台频道名到标准名的映射
    name_mapping = {
        # 凤凰系列
        '凤凰卫视': ['凤凰卫视', '凤凰电视', '凤凰台', 'Phoenix'],
        '凤凰中文': ['凤凰中文', '凤凰卫视中文台', 'Phoenix Chinese'],
        '凤凰资讯': ['凤凰资讯', '凤凰卫视资讯台', 'Phoenix Info'],
        '凤凰香港': ['凤凰香港', '凤凰卫视香港台', 'Phoenix Hong Kong'],
        '凤凰电影': ['凤凰电影', 'Phoenix Movies'],
        
        # TVB系列
        'TVB': ['TVB', '无线电视'],
        '翡翠台': ['翡翠台', 'TVB Jade'],
        '明珠台': ['明珠台', 'TVB Pearl'],
        'J2': ['J2'],
        
        # 港台电视台
        '香港开电视': ['香港开电视', 'HOY TV'],
        '香港国际': ['香港国际', 'RTHK'],
        '港台电视': ['港台电视', 'RTHK TV'],
        '有线新闻': ['有线新闻', 'Cable News'],
        
        # 澳门
        '澳门卫视': ['澳门卫视', 'Macau Satellite'],
        '澳视澳门': ['澳视澳门', 'TDM Macau'],
        '澳视体育': ['澳视体育', 'TDM Sports'],
        
        # 台湾
        '中视': ['中视', 'CTV'],
        '中天': ['中天', 'CTi'],
        '东森': ['东森', 'ETTV'],
        '三立': ['三立', 'SET'],
        '民视': ['民视', 'FTV'],
        'TVBS': ['TVBS'],
        '八大': ['八大', 'GTV'],
        '纬来': ['纬来', 'VL'],
        '台视': ['台视', 'TTV'],
        '华视': ['华视', 'CTS'],
        '公视': ['公视', 'PTS'],
        
        # 国际频道（港澳台常见）
        'CNN': ['CNN'],
        'BBC': ['BBC'],
        'HBO': ['HBO'],
        'Discovery': ['Discovery'],
        'National Geographic': ['国家地理', 'Nat Geo', 'National Geographic'],
        'ESPN': ['ESPN'],
        'FOX': ['FOX'],
        'CCTV4': ['CCTV4', '央视四套'],
        '湖南卫视': ['湖南卫视', 'Hunan TV'],
        '浙江卫视': ['浙江卫视', 'Zhejiang TV'],
    }
    
    # 首先检查是否有标准映射
    standard_name = None
    for std_name, variants in name_mapping.items():
        for variant in variants:
            if variant.lower() in channel_name.lower():
                standard_name = std_name
                break
        if standard_name:
            break
    
    # 如果没有找到映射，使用原始名称
    if not standard_name:
        standard_name = channel_name
    
    # 清理名称用于URL
    def clean_for_url(name):
        # 移除特殊字符，保留字母数字
        cleaned = re.sub(r'[^\w\s]', '', name)
        # 替换空格为下划线或连字符
        cleaned = cleaned.replace(' ', '_')
        # 转换为小写
        return cleaned.lower()
    
    cleaned_name = clean_for_url(standard_name)
    
    # 尝试从不同源获取台标
    test_sources = []
    
    # 源1: iptv-org格式（channel_name.png）
    test_sources.append(f"{logo_sources[0]}{cleaned_name}.png")
    test_sources.append(f"{logo_sources[0]}{cleaned_name}.jpg")
    test_sources.append(f"{logo_sources[0]}{cleaned_name}.webp")
    
    # 源2: fanmingming格式（channel_name.png）
    test_sources.append(f"{logo_sources[1]}{cleaned_name}.png")
    
    # 源3: lqist格式（channel_name.png）
    test_sources.append(f"{logo_sources[2]}{cleaned_name}.png")
    
    # 源4: ChengShide格式（channel_name.png）
    test_sources.append(f"{logo_sources[3]}{cleaned_name}.png")
    
    # 特殊：一些频道可能有特定格式
    if '凤凰' in channel_name:
        test_sources.append("https://raw.githubusercontent.com/iptv-org/iptv/master/logos/phoenix.tv.png")
        test_sources.append("https://raw.githubusercontent.com/fanmingming/live/main/tv/phoenix.png")
    
    if 'TVB' in channel_name or '翡翠' in channel_name or '明珠' in channel_name:
        test_sources.append("https://raw.githubusercontent.com/iptv-org/iptv/master/logos/tvb.png")
        test_sources.append("https://raw.githubusercontent.com/fanmingming/live/main/tv/tvb.png")
    
    if '中天' in channel_name:
        test_sources.append("https://raw.githubusercontent.com/iptv-org/iptv/master/logos/cti.tv.png")
    
    if '东森' in channel_name:
        test_sources.append("https://raw.githubusercontent.com/iptv-org/iptv/master/logos/ettv.png")
    
    # 默认台标（如果所有源都不可用）
    default_logos = [
        "https://raw.githubusercontent.com/iptv-org/iptv/master/logos/default.png",
        "https://raw.githubusercontent.com/fanmingming/live/main/tv/default.png",
        "https://via.placeholder.com/128x72.png?text=TV"
    ]
    
    # 添加到测试列表
    test_sources.extend(default_logos)
    
    # 返回第一个有效的URL（实际使用时客户端会去获取）
    # 注意：这里不实际测试URL有效性，因为GitHub Actions中可能无法访问
    # 直接返回一个最有可能的URL，让播放器去处理
    primary_logo = test_sources[0]
    
    log(f"  台标匹配: {channel_name} -> {standard_name}")
    log(f"  使用台标URL: {primary_logo}")
    
    return primary_logo

def extract_tvg_info(channel_name):
    """从频道名提取tvg-id、tvg-name和台标"""
    # 清理名称
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
    
    # 生成tvg-id
    if re.search(r'[\u4e00-\u9fff]', channel_name):
        # 中文频道：使用拼音首字母或hash
        import hashlib
        tvg_id = f"channel_{hashlib.md5(channel_name.encode()).hexdigest()[:8]}"
        tvg_name = channel_name
    else:
        # 英文频道：直接使用清理后的名称
        tvg_id = clean_name
        tvg_name = channel_name
    
    # 获取台标
    logo_url = get_channel_logo_public(channel_name)
    
    return tvg_id, tvg_name, logo_url

def download_source():
    """下载源数据"""
    try:
        url = "https://stymei.sufern001.workers.dev/"
        log(f"正在下载源数据: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/plain'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        log(f"✅ 下载成功，{len(content)} 字符")
        return content
        
    except Exception as e:
        log(f"❌ 下载失败: {e}")
        return None

def extract_channels(content):
    """从源数据提取港澳台频道"""
    source_group = "🔥全网通港澳台"
    target_group = "全网通港澳台"
    
    log(f"正在提取分组: {source_group}")
    
    if not content:
        log("❌ 源数据为空")
        return []
    
    lines = content.split('\n')
    channels = []
    in_target_group = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 查找目标分组
        if f"{source_group},#genre#" in line:
            log(f"✅ 在第 {i+1} 行找到目标分组")
            in_target_group = True
            continue
        
        # 如果开始下一个分组，停止
        if in_target_group and '#genre#' in line and source_group not in line:
            log("到达下一个分组，停止提取")
            break
        
        # 收集频道行 (格式: 频道名,URL)
        if in_target_group and line and ',' in line:
            parts = line.split(',')
            if len(parts) >= 2:
                channel_name = parts[0].strip()
                url = ','.join(parts[1:]).strip()
                
                # 验证URL
                if url and ('://' in url or url.startswith('http')):
                    # 提取tvg信息和台标
                    tvg_id, tvg_name, logo_url = extract_tvg_info(channel_name)
                    channels.append({
                        'name': channel_name,
                        'url': url,
                        'tvg_id': tvg_id,
                        'tvg_name': tvg_name,
                        'logo': logo_url,
                        'group': target_group
                    })
    
    log(f"✅ 提取到 {len(channels)} 个港澳台频道")
    
    # 显示台标匹配情况
    if channels:
        log("台标匹配情况（前5个频道）:")
        for i, ch in enumerate(channels[:5]):
            log(f"  {i+1}. {ch['name']} -> {ch['logo']}")
    
    return channels

def load_local_bb():
    """加载本地BB.m3u文件"""
    bb_file = "BB.m3u"
    
    try:
        if not os.path.exists(bb_file):
            log(f"⚠️  {bb_file} 不存在，创建默认文件")
            # 创建标准M3U格式的默认文件（带台标）
            default_content = '''#EXTM3U
#EXTINF:-1 tvg-id="local1" tvg-name="本地频道1" tvg-logo="https://raw.githubusercontent.com/iptv-org/iptv/master/logos/default.png" group-title="本地",本地频道1
http://example.com/channel1

#EXTINF:-1 tvg-id="local2" tvg-name="本地频道2" tvg-logo="https://raw.githubusercontent.com/iptv-org/iptv/master/logos/default.png" group-title="本地",本地频道2
http://example.com/channel2'''
            
            with open(bb_file, 'w', encoding='utf-8') as f:
                f.write(default_content)
            
            content = default_content
        else:
            log(f"正在加载本地文件: {bb_file}")
            with open(bb_file, 'r', encoding='utf-8') as f:
                content = f.read()
        
        lines = content.split('\n')
        log(f"✅ 加载本地文件成功，{len(lines)} 行")
        
        return content
        
    except Exception as e:
        log(f"❌ 加载本地文件失败: {e}")
        return "#EXTM3U\n"

def generate_cc_m3u(local_content, hk_channels):
    """生成标准M3U格式的CC.m3u（带台标）"""
    output_file = "CC.m3u"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log(f"正在生成标准M3U格式文件（带台标）: {output_file}")
    
    output_lines = []
    
    # 1. M3U头部信息
    output_lines.append("#EXTM3U")
    output_lines.append(f"# CC.m3u - 标准M3U格式（带台标）")
    output_lines.append(f"# 生成时间: {timestamp}")
    output_lines.append(f"# 源URL: https://stymei.sufern001.workers.dev/")
    output_lines.append(f"# 提取分组: 🔥全网通港澳台 -> 全网通港澳台")
    output_lines.append(f"# 港澳台频道数: {len(hk_channels)}")
    output_lines.append(f"# 台标源: iptv-org/logos, fanmingming/live")
    output_lines.append("")
    
    # 2. 添加本地内容（保持原样）
    if local_content and local_content.strip():
        output_lines.append("#" + "=" * 60)
        output_lines.append("# 本地频道")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        local_lines = local_content.split('\n')
        for line in local_lines:
            if line.strip() == "#EXTM3U" and len(output_lines) > 1:
                continue
            output_lines.append(line)
        
        output_lines.append("")
    
    # 3. 添加港澳台频道（带台标的标准M3U格式）
    if hk_channels:
        output_lines.append("#" + "=" * 60)
        output_lines.append("# 全网通港澳台频道（带台标）")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        for channel in hk_channels:
            # 生成#EXTINF行，包含台标
            extinf_line = f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}" tvg-name="{channel["tvg_name"]}" tvg-logo="{channel["logo"]}" group-title="{channel["group"]}",{channel["name"]}'
            output_lines.append(extinf_line)
            
            # URL行
            output_lines.append(channel["url"])
            
            # 可选：添加空行分隔
            output_lines.append("")
        
        # 移除最后一个空行
        if output_lines[-1] == "":
            output_lines.pop()
    
    # 4. 添加统计信息
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# 统计信息")
    output_lines.append(f"# 港澳台频道数: {len(hk_channels)}")
    if hk_channels:
        output_lines.append("# 台标库: https://github.com/iptv-org/iptv/tree/master/logos")
        output_lines.append("# 备用台标库: https://github.com/fanmingming/live")
    output_lines.append(f"# 更新时间: {timestamp}")
    output_lines.append("# GitHub Actions 自动生成")
    output_lines.append("#" + "=" * 60)
    
    return '\n'.join(output_lines)

def main():
    log("开始生成带台标的CC.m3u ...")
    print("=" * 70)
    
    try:
        # 1. 下载源数据
        source_content = download_source()
        if not source_content:
            log("❌ 无法获取源数据，退出")
            return
        
        # 2. 提取港澳台频道
        hk_channels = extract_channels(source_content)
        
        if not hk_channels:
            log("⚠️  未提取到港澳台频道，检查源数据格式")
            lines = source_content.split('\n')
            log("源数据中的分组:")
            for line in lines:
                if '#genre#' in line:
                    log(f"  - {line}")
        
        # 3. 加载本地BB.m3u
        local_content = load_local_bb()
        
        # 4. 生成CC.m3u内容
        cc_content = generate_cc_m3u(local_content, hk_channels)
        
        # 5. 保存文件
        output_file = "CC.m3u"
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(cc_content)
        
        # 验证文件
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            line_count = cc_content.count('\n') + 1
            
            log(f"✅ CC.m3u 生成成功!")
            log(f"   文件位置: {os.path.abspath(output_file)}")
            log(f"   文件大小: {file_size} 字节")
            log(f"   总行数: {line_count}")
            log(f"   港澳台频道数: {len(hk_channels)}")
            
            # 显示生成的文件格式示例
            print("\n📋 生成的EXTINF格式示例（带台标）:")
            print("=" * 70)
            for i, channel in enumerate(hk_channels[:3]):  # 显示前3个
                print(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}" tvg-name="{channel["tvg_name"]}" tvg-logo="{channel["logo"]}" group-title="{channel["group"]}",{channel["name"]}')
                print(channel["url"])
                print()
            print("=" * 70)
            
            # 显示实际文件内容（前20行）
            print("\n📄 文件内容预览（前20行）:")
            print("-" * 70)
            lines = cc_content.split('\n')
            for i, line in enumerate(lines[:20]):
                print(line)
            print("..." if len(lines) > 20 else "")
            print("-" * 70)
            
        else:
            log("❌ 文件保存失败")
            
    except Exception as e:
        log(f"❌ 执行过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)
    log("执行完成")

if __name__ == "__main__":
    main()
