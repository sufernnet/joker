#!/usr/bin/env python3
"""
CC.m3u 合并脚本 - 标准M3U格式（支持频道源合并）
从 https://stymei.sufern001.workers.dev/ 提取：
1. 🔥全网通港澳台
2. 🔮港澳台直播
将相同频道合并，支持多播放地址，并与本地 BB.m3u 合并输出 CC.m3u
"""

import requests
from datetime import datetime
import os
import re
import hashlib
from collections import defaultdict

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
        "凤凰中文": "phoenix.chinese.png",
        "凤凰资讯": "phoenix.infonews.png",
        "凤凰香港": "phoenix.hongkong.png",
        "凤凰卫视": "phoenix.tv.png",
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
    
    # 3. 返回默认台标
    return "https://raw.githubusercontent.com/iptv-org/iptv/master/logos/default.png"

def extract_tvg_info(channel_name):
    """生成频道的tvg信息"""
    # 清理名称生成tvg-id
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
    
    # 使用MD5生成一致的tvg-id，确保相同频道名有相同ID
    tvg_id = f"channel_{hashlib.md5(channel_name.encode()).hexdigest()[:8]}"
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

def extract_and_merge_channels(content):
    """
    从内容中提取指定分组的所有频道，并合并相同频道的多个源
    返回结构: {channel_name: {tvg_id, tvg_name, logo, group, urls: [url1, url2, ...]}}
    """
    if not content:
        return {}
    
    # 使用字典合并相同频道，值是一个包含所有URL的列表
    channel_dict = defaultdict(lambda: {
        'name': '',
        'tvg_id': '',
        'tvg_name': '',
        'logo': '',
        'group': TARGET_GROUP,
        'urls': [],  # 存储多个播放地址
        'source_groups': set()  # 记录来源分组
    })
    
    lines = content.split('\n')
    
    log(f"开始提取并合并分组: {SOURCE_GROUPS}")
    
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
                        # 如果是首次遇到这个频道，生成tvg信息
                        if channel_name not in channel_dict or not channel_dict[channel_name]['tvg_id']:
                            tvg_id, tvg_name, logo_url = extract_tvg_info(channel_name)
                            channel_dict[channel_name].update({
                                'name': channel_name,
                                'tvg_id': tvg_id,
                                'tvg_name': tvg_name,
                                'logo': logo_url,
                                'group': TARGET_GROUP,
                            })
                        
                        # 添加URL到列表
                        if url not in channel_dict[channel_name]['urls']:
                            channel_dict[channel_name]['urls'].append(url)
                            channel_dict[channel_name]['source_groups'].add(source_group)
                            group_count += 1
        
        if group_found:
            log(f"  从「{source_group}」提取 {group_count} 个播放源")
        else:
            log(f"⚠️  未找到分组: {source_group}")
    
    # 转换为普通字典并统计
    result = dict(channel_dict)
    total_channels = len(result)
    total_urls = sum(len(ch['urls']) for ch in result.values())
    
    log(f"✅ 合并后得到 {total_channels} 个唯一频道，共 {total_urls} 个播放源")
    
    # 显示合并示例
    if result:
        log("频道合并示例:")
        for name, data in list(result.items())[:3]:
            log(f"  {name}: {len(data['urls'])} 个播放源 (来自: {', '.join(data['source_groups'])})")
    
    return result

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

def generate_m3u_content(local_content, channel_dict):
    """生成最终的M3U内容（支持多播放地址）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output_lines = [
        "#EXTM3U",
        f"# CC.m3u - 自动生成（频道源合并版）",
        f"# 生成时间: {timestamp}",
        f"# 源地址: {SOURCE_URL}",
        f"# 提取分组: {', '.join(SOURCE_GROUPS)} → {TARGET_GROUP}",
        f"# 唯一频道数: {len(channel_dict)}",
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
    
    # 添加港澳台频道（支持多播放地址）
    if channel_dict:
        output_lines.append("#" + "=" * 60)
        output_lines.append(f"# {TARGET_GROUP} (合并自: {', '.join(SOURCE_GROUPS)})")
        output_lines.append("# 说明：每个频道可能包含多个播放地址，播放器会自动选择可用源")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        for i, (channel_name, data) in enumerate(channel_dict.items(), 1):
            # EXTINF 行
            extinf = f'#EXTINF:-1 tvg-id="{data["tvg_id"]}" tvg-name="{data["tvg_name"]}" tvg-logo="{data["logo"]}" group-title="{TARGET_GROUP}",{channel_name}'
            output_lines.append(extinf)
            
            # 多个播放地址（每个地址一行）
            for url in data['urls']:
                output_lines.append(url)
            
            # 每3个频道加一个空行（美观）
            if i % 3 == 0 and i < len(channel_dict):
                output_lines.append("")
        
        # 移除最后的空行（如果有）
        while output_lines and output_lines[-1] == "":
            output_lines.pop()
    
    # 统计信息
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# 统计信息")
    local_channels = len([l for l in local_content.split('\n') if l.startswith('#EXTINF')])
    total_urls = sum(len(ch['urls']) for ch in channel_dict.values())
    output_lines.append(f"# 本地频道数: {local_channels}")
    output_lines.append(f"# 港澳台唯一频道数: {len(channel_dict)}")
    output_lines.append(f"# 港澳台播放源总数: {total_urls}")
    output_lines.append(f"# 更新时间: {timestamp}")
    output_lines.append("# 说明：相同频道的多个播放地址已合并，播放器会尝试所有地址直到成功")
    output_lines.append("#" + "=" * 60)
    
    return '\n'.join(output_lines)

def main():
    """主函数"""
    print("=" * 70)
    log("开始生成 CC.m3u（频道源合并版）...")
    print("=" * 70)
    
    try:
        # 1. 下载源数据
        source_content = download_source()
        if not source_content:
            log("❌ 无法获取源数据，退出")
            return
        
        # 2. 提取并合并频道
        channel_dict = extract_and_merge_channels(source_content)
        
        if not channel_dict:
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
        m3u_content = generate_m3u_content(local_content, channel_dict)
        
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
            log(f"   唯一频道数: {len(channel_dict)}")
            
            # 显示合并示例
            print("\n📋 频道合并示例:")
            print("-" * 70)
            for name, data in list(channel_dict.items())[:2]:
                print(f'{data["tvg_name"]} ({len(data["urls"])}个播放源):')
                for url in data['urls'][:2]:  # 只显示前2个URL
                    print(f"  {url[:80]}..." if len(url) > 80 else f"  {url}")
                if len(data['urls']) > 2:
                    print(f"  ... 还有{len(data['urls'])-2}个播放源")
                print()
            print("-" * 70)
            
            # 显示实际文件内容示例
            print("\n📄 生成文件格式示例:")
            print("-" * 50)
            lines = m3u_content.split('\n')
            # 找到第一个多源频道的部分
            for i, line in enumerate(lines):
                if line.startswith('#EXTINF') and i+1 < len(lines) and lines[i+1].startswith('http'):
                    if i+2 < len(lines) and lines[i+2].startswith('http'):
                        # 这是一个多源频道
                        print(lines[i])
                        print(lines[i+1])
                        print(lines[i+2])
                        if i+3 < len(lines) and lines[i+3].startswith('http'):
                            print(lines[i+3])
                        print("...")
                        break
            print("-" * 50)
            
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
