#!/usr/bin/env python3
"""
M3U文件合并脚本 - 从GitHub直接抓取全网通港澳台直播源
1. 下载BB.m3u（包含EPG信息）
2. 从GitHub直接抓取"全网通港澳台"直播源
3. 与BB合并生成CC.m3u
北京时间每天6:00、18:00自动运行
"""

import requests
import re
import os
import time
from datetime import datetime

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/main/Jsnzkpg1"
KEYWORD = "全网通港澳台"
OUTPUT_FILE = "CC.m3u"

# 备选EPG源（如果主要EPG失效）
BACKUP_EPG_URLS = [
    "https://epg.112114.xyz/pp.xml",  # BB的EPG
    "https://epg.946985.filegear-sg.me/t.xml.gz",
    "http://epg.51zmt.top:8000/e.xml"
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def test_epg_url(epg_url):
    """测试EPG URL是否可访问"""
    try:
        log(f"测试EPG: {epg_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*'
        }
        
        # 只下载前1KB检查
        response = requests.get(epg_url, headers=headers, timeout=10, stream=True)
        
        if response.status_code == 200:
            # 读取前1KB检查
            chunk = response.raw.read(1024)
            text = chunk.decode('utf-8', errors='ignore')
            
            # 检查是否是XML格式
            if '<?xml' in text or '<tv' in text or '<programme' in text:
                log(f"✅ EPG可用: {epg_url}")
                return True
            else:
                log(f"⚠️  EPG不是XML格式: {epg_url}")
                return False
        else:
            log(f"❌ EPG不可访问: {epg_url} (状态码: {response.status_code})")
            return False
            
    except Exception as e:
        log(f"❌ EPG测试失败 {epg_url}: {e}")
        return False

def get_best_epg_url(epg_urls):
    """获取最佳的EPG URL"""
    log("寻找最佳EPG源...")
    
    # 测试所有EPG
    working_epgs = []
    for epg_url in epg_urls:
        if test_epg_url(epg_url):
            working_epgs.append(epg_url)
    
    if working_epgs:
        # 优先使用第一个可用的
        best_epg = working_epgs[0]
        log(f"✅ 选择EPG: {best_epg}")
        log(f"   其他可用EPG: {len(working_epgs)-1}个")
        return best_epg
    else:
        log("⚠️  没有可用的EPG源")
        return None

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

def get_gangaotai_channels():
    """从GitHub直接抓取包含"全网通港澳台"的频道"""
    try:
        log(f"从GitHub直接抓取包含'{KEYWORD}'的频道...")
        log(f"地址: {GITHUB_RAW_URL}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        response = requests.get(GITHUB_RAW_URL, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            if content and content.strip():
                log(f"✅ 下载成功 ({len(content)} 字符)")
                
                # 检查内容格式
                if content.startswith('#EXTM3U'):
                    log("✅ 内容为有效的M3U格式")
                else:
                    log("⚠️  内容不是标准M3U格式，但仍尝试解析")
                
                # 检查是否包含关键词
                if KEYWORD in content:
                    log(f"✅ 找到'{KEYWORD}'相关内容")
                    
                    # 提取所有包含关键词的频道
                    channels = extract_channels_by_keyword(content, KEYWORD)
                    
                    if channels:
                        log(f"✅ 提取到 {len(channels)//2} 个包含'{KEYWORD}'的频道")
                        
                        # 显示前几个频道名称用于验证
                        log("前5个频道:")
                        for i in range(0, min(5*2, len(channels)), 2):
                            if i+1 < len(channels):
                                extinf = channels[i]
                                # 提取频道名
                                channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
                                log(f"  {i//2+1}. {channel_name[:60]}")
                        
                        m3u_content = "#EXTM3U\n" + "\n".join(channels)
                        return m3u_content
                    else:
                        log(f"❌ 找到关键词但未能提取到频道，尝试调试...")
                        
                        # 调试：显示内容结构
                        debug_content_structure(content)
                        
                else:
                    log(f"❌ 没有找到'{KEYWORD}'相关内容")
                    
                    # 显示内容前500字符查看格式
                    log(f"内容前500字符:")
                    log(content[:500])
                    
                    # 尝试查找其他可能的分组名
                    find_all_groups(content)
                    
                    return None
            else:
                log("⚠️  内容为空")
        else:
            log(f"❌ 下载失败: HTTP {response.status_code}")
            
    except Exception as e:
        log(f"❌ 抓取失败: {e}")
    
    return None

def extract_channels_by_keyword(content, keyword):
    """提取所有包含关键词的频道"""
    channels = []
    lines = content.split('\n')
    current_extinf = None
    
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
            
        if line.startswith('#EXTINF:'):
            # 检查是否包含关键词
            if keyword in line:
                current_extinf = line
            else:
                current_extinf = None
                
        elif current_extinf and '://' in line and not line.startswith('#'):
            # 这是一个频道URL，添加到结果中
            channels.append(current_extinf)
            channels.append(line)
            current_extinf = None
    
    return channels

def debug_content_structure(content):
    """调试内容结构"""
    log("调试内容结构...")
    lines = content.split('\n')
    
    # 统计总行数
    log(f"总行数: {len(lines)}")
    
    # 查找所有包含关键词的行
    keyword_lines = [line for line in lines if KEYWORD in line]
    log(f"包含'{KEYWORD}'的行数: {len(keyword_lines)}")
    
    if keyword_lines:
        log(f"前5个包含'{KEYWORD}'的行:")
        for i, line in enumerate(keyword_lines[:5], 1):
            log(f"  {i}: {line[:100]}...")
    
    # 统计EXTINF行数
    extinf_lines = [line for line in lines if line.startswith('#EXTINF:')]
    log(f"#EXTINF行数: {len(extinf_lines)}")
    
    # 统计URL行数
    url_lines = [line for line in lines if '://' in line and not line.startswith('#')]
    log(f"URL行数: {len(url_lines)}")

def find_all_groups(content):
    """查找内容中的所有分组"""
    log("查找所有分组...")
    
    # 查找所有分组
    groups = re.findall(r'group-title="([^"]+)"', content)
    if groups:
        unique_groups = list(set(groups))
        log(f"发现 {len(unique_groups)} 个唯一分组")
        
        # 按频道数排序
        group_counts = {}
        for group in groups:
            group_counts[group] = group_counts.get(group, 0) + 1
        
        # 显示前20个分组
        log("分组列表（按频道数排序）:")
        sorted_groups = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
        for i, (group, count) in enumerate(sorted_groups[:20], 1):
            log(f"  {i:2d}. {group} ({count}个频道)")
            
            # 检查是否包含"港澳台"相关关键词
            if "港澳台" in group or "HK" in group or "TW" in group or "Hongkong" in group or "Taiwan" in group:
                log(f"       ⚠️  可能是目标分组")
    
    # 查找可能的EPG信息
    epg_patterns = [
        (r'url-tvg="([^"]+)"', 'url-tvg'),
        (r'x-tvg-url="([^"]+)"', 'x-tvg-url'),
    ]
    
    for pattern, name in epg_patterns:
        matches = re.findall(pattern, content)
        if matches:
            log(f"找到 {len(matches)} 个{name} EPG:")
            for match in matches[:3]:  # 只显示前3个
                log(f"  - {match}")

def extract_epg_urls(content):
    """从内容中提取EPG URL"""
    epg_urls = []
    
    if not content:
        return epg_urls
    
    patterns = [
        r'url-tvg="([^"]+)"',
        r'x-tvg-url="([^"]+)"',
        r'tvg-url="([^"]+)"',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if 'http' in match and match not in epg_urls:
                epg_urls.append(match)
    
    return epg_urls

def main():
    """主函数"""
    log("开始合并M3U文件...")
    
    current_time = datetime.now()
    log(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"下次运行: 北京时间 06:00 和 18:00")
    log(f"GitHub地址: {GITHUB_RAW_URL}")
    log(f"搜索关键词: {KEYWORD}")
    
    # 1. 下载BB.m3u
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从GitHub抓取包含"全网通港澳台"的频道
    gangaotai_content = get_gangaotai_channels()
    
    # 3. 收集所有EPG源
    epg_urls = []
    
    # 从BB.m3u提取EPG
    bb_epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
    if bb_epg_match:
        epg_urls.append(bb_epg_match.group(1))
        log(f"✅ 找到BB EPG: {bb_epg_match.group(1)}")
    
    # 从港澳台内容提取EPG
    if gangaotai_content:
        new_epgs = extract_epg_urls(gangaotai_content)
        for epg in new_epgs:
            if epg not in epg_urls:
                epg_urls.append(epg)
                log(f"✅ 找到新EPG: {epg}")
    
    # 添加备选EPG
    for backup_epg in BACKUP_EPG_URLS:
        if backup_epg not in epg_urls:
            epg_urls.append(backup_epg)
    
    log(f"总共找到 {len(epg_urls)} 个EPG源")
    
    # 4. 获取最佳EPG
    best_epg = get_best_epg_url(epg_urls)
    
    # 5. 解析港澳台频道内容
    gangaotai_count = 0
    gangaotai_channels_content = ""
    
    if gangaotai_content:
        lines = gangaotai_content.split('\n')
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            if line.startswith('#EXTM3U'):
                continue
            
            gangaotai_channels_content += line + '\n'
            if line.startswith('#EXTINF:'):
                gangaotai_count += 1
    
    # 6. 构建M3U内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部（使用最佳EPG）
    if best_epg:
        m3u_header = f'#EXTM3U url-tvg="{best_epg}"\n'
        log(f"✅ 使用EPG: {best_epg}")
    else:
        m3u_header = '#EXTM3U\n'
        log("⚠️  未找到可用EPG")
    
    output = m3u_header + f"""# 自动合并 M3U 文件
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 18:00 (北京时间)
# BB源: {BB_URL}
# GitHub源: {GITHUB_RAW_URL}
# 搜索关键词: {KEYWORD}
# EPG源: {best_epg if best_epg else '无可用EPG'}
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
    
    # 添加港澳台频道
    if gangaotai_channels_content:
        output += f"\n# {KEYWORD}频道\n"
        output += f"# 来自: {GITHUB_RAW_URL}\n"
        output += gangaotai_channels_content
        
        # 添加频道统计
        output += f"\n# {KEYWORD}频道统计\n"
        output += f"# 共提取到 {gangaotai_count} 个频道\n"
    else:
        log("⚠️  没有找到港澳台相关频道")
        output += f"\n# 注意：未找到包含'{KEYWORD}'的频道\n"
        output += f"# GitHub源: {GITHUB_RAW_URL}\n"
    
    # 添加EPG信息说明
    if epg_urls:
        output += f"""
# EPG信息
# 使用EPG: {best_epg if best_epg else '无'}
# 测试的EPG源 ({len(epg_urls)}个):"""
        for i, epg in enumerate(epg_urls, 1):
            status = "✅" if epg == best_epg else "  "
            output += f"\n#   {status} {epg}"
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {KEYWORD} 频道数: {gangaotai_count}
# 总频道数: {bb_count + gangaotai_count}
# EPG状态: {'✅ 正常' if best_epg else '❌ 无可用EPG'}
# 更新时间: {timestamp} (北京时间)
# 更新频率: 每天 06:00 和 18:00 (北京时间)
"""
    
    # 7. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {best_epg if best_epg else '无可用EPG'}")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 {KEYWORD}频道: {gangaotai_count}")
    log(f"📺 总计: {bb_count + gangaotai_count}")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 18:00")

if __name__ == "__main__":
    main()
