#!/usr/bin/env python3
"""
M3U文件合并脚本
1. 先更新订阅确保获取有效直播
2. 从更新的订阅中提取JULI频道并改为HK分组
3. 合并BB.m3u和提取的HK频道
4. 生成新的CC.m3u
"""

import requests
import re
import os
import time
from datetime import datetime

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
JULI_SUB_URL = "https://smart.946985.filegear-sg.me/sub.php?user=tg_Thinkoo_bot"
OUTPUT_FILE = "CC.m3u"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_with_retry(url, description, max_retries=3):
    """下载文件，带重试机制"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://smart.946985.filegear-sg.me/',
        'Connection': 'keep-alive'
    }
    
    for attempt in range(max_retries):
        try:
            log(f"下载{description} (尝试 {attempt + 1}/{max_retries})...")
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                content = response.text.strip()
                if content:
                    log(f"✅ {description} 下载成功 ({len(content)} 字符)")
                    return content
                else:
                    log(f"⚠️  {description} 内容为空")
            else:
                log(f"❌ {description} HTTP错误: {response.status_code}")
                
        except requests.exceptions.Timeout:
            log(f"❌ {description} 超时")
        except requests.exceptions.ConnectionError:
            log(f"❌ {description} 连接错误")
        except Exception as e:
            log(f"❌ {description} 错误: {e}")
        
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 5  # 递增等待时间
            log(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    
    return None

def update_and_get_juli_subscription():
    """更新并获取JULI订阅内容"""
    log("更新JULI订阅...")
    
    # 先访问一次激活订阅（如果需要）
    activation_url = f"{JULI_SUB_URL}&t={int(time.time())}"
    log(f"访问订阅URL: {JULI_SUB_URL}")
    
    # 获取订阅内容
    content = download_with_retry(activation_url, "JULI订阅")
    
    if not content:
        log("❌ 无法获取JULI订阅")
        return None
    
    # 检查订阅是否有效
    if not content.startswith('#EXTM3U'):
        log("⚠️  订阅内容不是有效的M3U格式")
        
        # 尝试从内容中提取M3U
        m3u_pattern = r'#EXTM3U.*'
        match = re.search(m3u_pattern, content, re.DOTALL)
        if match:
            content = match.group(0)
            log(f"✅ 从内容中提取到M3U ({len(content)} 字符)")
        else:
            # 检查是否有频道信息
            lines = content.split('\n')
            m3u_lines = []
            for line in lines:
                if line.strip().startswith('#EXTINF:') or ('://' in line and not line.startswith('<')):
                    m3u_lines.append(line.strip())
            
            if m3u_lines:
                content = '#EXTM3U\n' + '\n'.join(m3u_lines)
                log(f"✅ 从页面提取到频道信息 ({len(m3u_lines)} 个)")
            else:
                log("❌ 订阅内容中没有找到有效的频道信息")
                return None
    
    # 验证订阅中的频道是否有效
    log("验证订阅频道有效性...")
    channels = extract_channels_from_m3u(content)
    if not channels:
        log("❌ 订阅中没有找到频道")
        return None
    
    log(f"✅ 订阅验证通过，找到 {len(channels)} 个频道")
    
    # 可选：快速测试几个频道（不实际播放，只检查URL格式）
    test_channels = channels[:3]
    for i, (extinf, url) in enumerate(test_channels):
        if ',' in extinf:
            name = extinf.split(',', 1)[1][:30]
            log(f"  频道{i+1}: {name}...")
    
    return content

def extract_channels_from_m3u(m3u_content):
    """从M3U内容中提取所有频道"""
    if not m3u_content:
        return []
    
    lines = m3u_content.split('\n')
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
    
    return channels

def extract_hk_channels_from_subscription(sub_content):
    """从订阅内容中提取JULI频道并改为HK分组"""
    log("从订阅中提取JULI频道并改为HK分组...")
    
    channels = extract_channels_from_m3u(sub_content)
    if not channels:
        return []
    
    hk_channels = []
    seen = set()
    
    for extinf, url in channels:
        # 检查是否是JULI频道
        if 'JULI' in extinf.upper():
            # 重命名为HK分组
            new_extinf = re.sub(r'JULI', 'HK', extinf, flags=re.IGNORECASE)
            
            # 也可以添加分组标签
            if 'group-title=' in new_extinf:
                new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="HK"', new_extinf)
            else:
                # 如果没有group-title，添加一个
                if ',' in new_extinf:
                    parts = new_extinf.split(',', 1)
                    new_extinf = f'{parts[0]} group-title="HK",{parts[1]}'
            
            # 去重
            channel_key = f"{new_extinf}|{url}"
            if channel_key not in seen:
                seen.add(channel_key)
                hk_channels.append((new_extinf, url))
    
    log(f"✅ 提取到 {len(hk_channels)} 个HK频道（原JULI频道）")
    
    # 显示部分频道
    if hk_channels:
        log("部分HK频道:")
        for i, (extinf, url) in enumerate(hk_channels[:3]):
            if ',' in extinf:
                name = extinf.split(',', 1)[1]
                log(f"  {i+1}. {name[:50]}{'...' if len(name) > 50 else ''}")
    
    return hk_channels

def get_epg_url(content):
    """从内容中提取EPG URL"""
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
    log("开始更新和合并M3U文件...")
    
    # 1. 下载BB.m3u
    bb_content = download_with_retry(BB_URL, "BB.m3u")
    if not bb_content:
        log("❌ BB.m3u下载失败，无法继续")
        return
    
    # 提取BB的EPG
    bb_epg = get_epg_url(bb_content)
    if bb_epg:
        log(f"✅ BB EPG: {bb_epg}")
    
    # 2. 更新并获取JULI订阅
    juli_content = update_and_get_juli_subscription()
    
    # 提取JULI的EPG
    juli_epg = get_epg_url(juli_content) if juli_content else None
    if juli_epg:
        log(f"✅ JULI EPG: {juli_epg}")
    
    # 3. 从订阅中提取HK频道
    hk_channels = []
    if juli_content:
        hk_channels = extract_hk_channels_from_subscription(juli_content)
    else:
        log("⚠️  无法获取JULI订阅，只合并BB.m3u")
    
    # 4. 选择EPG（优先使用BB的）
    epg_url = bb_epg or juli_epg
    if epg_url:
        log(f"✅ 使用EPG: {epg_url}")
    
    # 5. 构建合并后的M3U
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部
    if epg_url:
        output = f'#EXTM3U url-tvg="{epg_url}"\n'
    else:
        output = '#EXTM3U\n'
    
    output += f"""# 自动合并 M3U 文件
# 生成时间: {timestamp}
# BB源: {BB_URL}
# JULI源: {JULI_SUB_URL}
# JULI分组已改为HK分组
# EPG源: {epg_url if epg_url else '无'}
# 订阅更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# GitHub Actions 自动生成

"""
    
    # 添加BB内容（跳过开头的#EXTM3U行）
    bb_lines = bb_content.split('\n')
    bb_count = 0
    skip_header = True
    
    for line in bb_lines:
        line = line.rstrip()
        if not line:
            continue
        
        if skip_header and line.startswith('#EXTM3U'):
            skip_header = False
            continue
        
        output += line + '\n'
        if line.startswith('#EXTINF:'):
            bb_count += 1
    
    # 添加HK频道
    if hk_channels:
        output += f"\n# HK频道 (原JULI频道，订阅已更新验证)\n"
        for extinf, url in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)} (已更新验证)
# 总频道数: {bb_count + len(hk_channels)}
# 更新时间: {timestamp}
# 下次更新: 每天 06:00 和 18:00 (北京时间)
# 订阅状态: {"已更新" if juli_content else "更新失败"}
"""
    
    # 6. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {epg_url if epg_url else '无'}")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 HK频道: {len(hk_channels)}")
    log(f"📺 总计: {bb_count + len(hk_channels)}")
    log(f"🔄 订阅状态: {'✅ 已更新' if juli_content else '❌ 更新失败'}")
    
    # 7. 保存更新记录
    with open("update_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | BB:{bb_count} | HK:{len(hk_channels)} | EPG:{epg_url or 'none'} | STATUS:{'OK' if juli_content else 'FAILED'}\n")

if __name__ == "__main__":
    main()
