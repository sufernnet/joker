#!/usr/bin/env python3
"""
CC.m3u 合并脚本 - 标准M3U格式（带公开台标）
从 https://stymei.sufern001.workers.dev/ 提取：
1. 🔥全网通港澳台
2. 🔮港澳台直播
合并为「全网通港澳台」分组，并与本地 BB.m3u 合并输出 CC.m3u
"""

import requests
from datetime import datetime
import os
import re
import hashlib

# ================== 配置区域 ==================
SOURCE_URL = "https://stymei.sufern001.workers.dev/"
BB_FILE = "BB.m3u"
OUTPUT_FILE = "CC.m3u"

# 要提取的源分组（可扩展多个）
SOURCE_GROUPS = [
    "🔥全网通港澳台",
    "🔮港澳台直播"
]
TARGET_GROUP = "全网通港澳台"  # 合并后的统一分组名

# 台标源（按优先级排序）
LOGO_SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/logos/",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/",
    "https://raw.githubusercontent.com/lqist/IPTVlogos/main/",
]

# ================== 工具函数 ==================
def log(msg):
    """日志输出"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def get_channel_logo(channel_name):
    """根据频道名匹配台标"""
    # 频道名映射表（可自行扩展）
    logo_map = {
        # 凤凰系列
        "凤凰卫视": "phoenix.tv.png",
        "凤凰中文": "phoenix.chinese.png",
        "凤凰资讯": "phoenix.infonews.png",
        "凤凰香港": "phoenix.hongkong.png",
        # TVB系列
        "翡翠台": "tvb.jade.png",
        "明珠台": "tvb.pearl.png",
        "J2": "tvb.j2.png",
        # 其他常见频道
        "TVBS": "tvbs.png",
        "中天": "cti.png",
        "东森": "ettv.png",
        "三立": "set.png",
        "民视": "ftv.png",
        "HBO": "hbo.png",
        "CNN": "cnn.png",
        "BBC": "bbc.png",
        "Discovery": "discovery.png",
        "National Geographic": "natgeo.png",
        "ESPN": "espn.png",
        "FOX": "fox.png",
    }
    
    # 1. 精确匹配
    for key, filename in logo_map.items():
        if key in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}{filename}"
                # 这里不实际验证URL，由播放器处理
                return logo_url
    
    # 2. 关键词匹配
    keywords = {
        "新闻": "news.png",
        "体育": "sports.png",
        "电影": "movie.png",
        "音乐": "music.png",
        "儿童": "kids.png",
        "卡通": "cartoon.png",
        "财经": "finance.png",
        "教育": "education.png",
    }
    
    for keyword, filename in keywords.items():
        if keyword in channel_name:
            for source in LOGO_SOURCES:
                logo_url = f"{source}{filename}"
                return logo_url
    
    # 3. 生成基于名称的猜测
    clean_name = re.sub(r'[^\w]', '', channel_name)
    for source in LOGO_SOURCES:
        logo_url = f"{source}{clean_name.lower()}.png"
        return logo_url  # 返回第一个猜测

def extract_tvg_info(channel_name):
    """生成频道的tvg信息"""
    # 清理名称生成tvg-id
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
    
    if re.search(r'[\u4e00-\u9fff]', channel_name):
        # 中文名称使用MD5哈希
        tvg_id = f"channel_{hashlib.md5(channel_name.encode()).hexdigest()[:8]}"
    else:
        tvg_id = clean_name
    
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

def extract_channels(content):
    """从内容中提取指定分组的所有频道"""
    if not content:
        return []
    
    channels = []
    lines = content.split('\n')
    
    log(f"开始提取分组: {SOURCE_GROUPS}")
    
    for source_group in SOURCE_GROUPS:
        in_section = False
        group_found = False
        group_count = 0
        
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
                    channel_name = parts[0].strip()
                    url = ','.join(parts[1:]).strip()
                    
                    if url and ('://' in url or url.startswith('http')):
                        tvg_id, tvg_name, logo_url = extract_tvg_info(channel_name)
                        channels.append({
                            'name': channel_name,
                            'url': url,
                            'tvg_id': tvg_id,
                            'tvg_name': tvg_name,
                            'logo': logo_url,
                            'group': TARGET_GROUP,
                            'source_group': source_group  # 记录原始分组
                        })
                        group_count += 1
        
        if group_found:
            log(f"  从「{source_group}」提取 {group_count} 个频道")
        else:
            log(f"⚠️  未找到分组: {source_group}")
    
    log(f"✅ 总计提取 {len(channels)} 个频道")
    
    # 去重（基于频道名称）
    unique_channels = []
    seen_names = set()
    for ch in channels:
        if ch['name'] not in seen_names:
            seen_names.add(ch['name'])
            unique_channels.append(ch)
    
    if len(unique_channels) < len(channels):
        log(f"✅ 去重后剩余 {len(unique_channels)} 个唯一频道")
    
    return unique_channels

def load_local_m3u():
    """加载本地BB.m3u文件"""
    try:
        if not os.path.exists(BB_FILE):
            log(f"⚠️  {BB_FILE} 不存在，创建默认文件")
            default_content = """#EXTM3U
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

def generate_m3u_content(local_content, channels):
    """生成最终的M3U内容"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output_lines = [
        "#EXTM3U",
        f"# CC.m3u - 自动生成",
        f"# 生成时间: {timestamp}",
        f"# 源地址: {SOURCE_URL}",
        f"# 提取分组: {', '.join(SOURCE_GROUPS)} → {TARGET_GROUP}",
        f"# 港澳台频道数: {len(channels)}",
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
    
    # 添加港澳台频道
    if channels:
        output_lines.append("#" + "=" * 60)
        output_lines.append(f"# {TARGET_GROUP} (合并自: {', '.join(SOURCE_GROUPS)})")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        for i, channel in enumerate(channels, 1):
            # EXTINF 行
            extinf = f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}" tvg-name="{channel["tvg_name"]}" tvg-logo="{channel["logo"]}" group-title="{TARGET_GROUP}",{channel["name"]}'
            output_lines.append(extinf)
            # URL 行
            output_lines.append(channel["url"])
            # 每5个频道加一个空行（美观）
            if i % 5 == 0 and i < len(channels):
                output_lines.append("")
    
    # 统计信息
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# 统计信息")
    local_channels = len([l for l in local_content.split('\n') if l.startswith('#EXTINF')])
    output_lines.append(f"# 本地频道数: {local_channels}")
    output_lines.append(f"# 港澳台频道数: {len(channels)}")
    output_lines.append(f"# 总频道数: {local_channels + len(channels)}")
    output_lines.append(f"# 更新时间: {timestamp}")
    output_lines.append("#" + "=" * 60)
    
    return '\n'.join(output_lines)

def main():
    """主函数"""
    print("=" * 70)
    log("开始生成 CC.m3u ...")
    print("=" * 70)
    
    try:
        # 1. 下载源数据
        source_content = download_source()
        if not source_content:
            log("❌ 无法获取源数据，退出")
            return
        
        # 2. 提取频道
        channels = extract_channels(source_content)
        
        if not channels:
            log("⚠️  未提取到任何频道，检查源数据格式")
            # 显示前5个分组供调试
            lines = source_content.split('\n')
            log("源数据中的分组:")
            count = 0
            for line in lines:
                if '#genre#' in line and count < 5:
                    log(f"  - {line}")
                    count += 1
        
        # 3. 加载本地文件
        local_content = load_local_m3u()
        
        # 4. 生成内容
        m3u_content = generate_m3u_content(local_content, channels)
        
        # 5. 保存文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
            f.write(m3u_content)
        
        # 6. 验证结果
        if os.path.exists(OUTPUT_FILE):
            file_size = os.path.getsize(OUTPUT_FILE)
            line_count = m3u_content.count('\n') + 1
            
            print("\n" + "=" * 70)
            log("✅ CC.m3u 生成成功!")
            log(f"   文件位置: {os.path.abspath(OUTPUT_FILE)}")
            log(f"   文件大小: {file_size} 字节")
            log(f"   总行数: {line_count}")
            log(f"   港澳台频道: {len(channels)} 个")
            
            # 显示示例
            print("\n📋 生成示例 (前3个频道):")
            print("-" * 70)
            lines = m3u_content.split('\n')
            extinf_count = 0
            for line in lines:
                if line.startswith('#EXTINF'):
                    print(line[:100] + "..." if len(line) > 100 else line)
                    extinf_count += 1
                    if extinf_count >= 3:
                        break
            print("-" * 70)
            
            # 显示实际文件位置
            print(f"\n📁 文件已保存至: {os.path.abspath(OUTPUT_FILE)}")
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
