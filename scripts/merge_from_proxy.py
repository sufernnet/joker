#!/usr/bin/env python3
"""
M3U文件合并脚本 - 从新地址抓取全网通港澳台直播源
1. 下载BB.m3u（包含EPG信息）
2. 从新地址抓取"全网通港澳台"直播源
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
NEW_SOURCE_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
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
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            
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

def get_quanwangtong_gangaotai():
    """从新地址抓取"全网通港澳台"直播源"""
    try:
        log("从新地址抓取全网通港澳台直播源...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://github.com/'
        }
        
        response = requests.get(NEW_SOURCE_URL, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            if content and content.strip():
                log(f"✅ 获取到内容 ({len(content)} 字符)")
                
                # 查找"全网通港澳台"分组
                if "全网通港澳台" in content:
                    log("✅ 找到'全网通港澳台'分组")
                    
                    # 提取该分组的内容
                    lines = content.split('\n')
                    in_target_group = False
                    extracted_lines = []
                    
                    for line in lines:
                        line = line.rstrip()
                        
                        # 检查是否进入目标分组
                        if 'group-title="全网通港澳台"' in line or 'group-title=".*全网通港澳台.*"' in line:
                            in_target_group = True
                        
                        # 如果在目标分组中，收集内容直到遇到其他分组
                        if in_target_group:
                            # 检查是否遇到其他分组（但不是同一分组）
                            if line.startswith('#EXTINF:') and 'group-title=' in line:
                                # 如果遇到新的分组但不是全网通港澳台，则停止
                                if '全网通港澳台' not in line:
                                    break
                            
                            extracted_lines.append(line)
                    
                    # 确保包含M3U头
                    if extracted_lines and not extracted_lines[0].startswith('#EXTM3U'):
                        extracted_lines.insert(0, '#EXTM3U')
                    
                    extracted_content = '\n'.join(extracted_lines)
                    log(f"✅ 提取到全网通港澳台内容 ({len(extracted_content)} 字符)")
                    return extracted_content
                else:
                    log("⚠️  未找到'全网通港澳台'分组")
                    # 如果没有找到，返回全部内容
                    return content
            else:
                log("⚠️  内容为空")
        else:
            log(f"❌ 新地址返回错误: {response.status_code}")
            
    except Exception as e:
        log(f"❌ 从新地址抓取失败: {e}")
    
    return None

def extract_epg_urls(content):
    """从内容中提取EPG URL"""
    epg_urls = []
    
    if not content:
        return epg_urls
    
    # 查找所有可能的EPG URL模式
    patterns = [
        r'url-tvg="([^"]+)"',
        r'x-tvg-url="([^"]+)"',
        r'epg-url="([^"]+)"',
        r'#EXTM3U.*?http[^"\s]+',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if 'http' in match and match not in epg_urls:
                epg_urls.append(match)
                log(f"找到EPG: {match}")
    
    return epg_urls

def main():
    """主函数"""
    log("开始合并M3U文件...")
    
    # 显示当前时间（用于调试定时任务）
    current_time = datetime.now()
    log(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"下次运行: 北京时间 06:00 和 18:00")
    log(f"新源地址: {NEW_SOURCE_URL}")
    
    # 1. 下载BB.m3u
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从新地址抓取"全网通港澳台"直播源
    new_source_content = get_quanwangtong_gangaotai()
    
    # 3. 收集所有EPG源
    epg_urls = []
    
    # 从BB.m3u提取EPG
    bb_epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
    if bb_epg_match:
        epg_urls.append(bb_epg_match.group(1))
        log(f"✅ 找到BB EPG: {bb_epg_match.group(1)}")
    
    # 从新源内容提取EPG
    if new_source_content:
        new_epgs = extract_epg_urls(new_source_content)
        for epg in new_epgs:
            if epg not in epg_urls:
                epg_urls.append(epg)
    
    # 添加备选EPG
    for backup_epg in BACKUP_EPG_URLS:
        if backup_epg not in epg_urls:
            epg_urls.append(backup_epg)
    
    log(f"找到 {len(epg_urls)} 个EPG源")
    
    # 4. 获取最佳EPG
    best_epg = get_best_epg_url(epg_urls)
    
    # 5. 解析新源内容（全网通港澳台）
    new_channels_count = 0
    new_channels_content = ""
    
    if new_source_content:
        lines = new_source_content.split('\n')
        in_m3u = False
        collecting = False
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            if line.startswith('#EXTM3U'):
                in_m3u = True
                # 跳过M3U头，我们会在后面添加自己的
                continue
            
            if in_m3u:
                # 检查是否是"全网通港澳台"分组
                if line.startswith('#EXTINF:'):
                    if '全网通港澳台' in line:
                        collecting = True
                    else:
                        collecting = False
                
                if collecting:
                    new_channels_content += line + '\n'
                    if line.startswith('#EXTINF:'):
                        new_channels_count += 1
    
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
# 新源地址: {NEW_SOURCE_URL}
# 抓取分组: 全网通港澳台
# EPG源: {best_epg if best_epg else '无可用EPG'}
# 测试的EPG源: {len(epg_urls)} 个
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
    
    # 添加全网通港澳台频道
    if new_channels_content:
        output += f"\n# 全网通港澳台频道\n"
        output += f"# 来自: {NEW_SOURCE_URL}\n"
        output += new_channels_content
    
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
# 全网通港澳台 频道数: {new_channels_count}
# 总频道数: {bb_count + new_channels_count}
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
    log(f"📺 全网通港澳台频道: {new_channels_count}")
    log(f"📺 总计: {bb_count + new_channels_count}")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 18:00")

if __name__ == "__main__":
    main()
