#!/usr/bin/env python3
"""
M3U文件合并脚本 - 使用Cloudflare代理
1. 通过代理更新并获取JULI订阅
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
CLOUDFLARE_PROXY = "https://smt-proxy.sufern001.workers.dev/"
OUTPUT_FILE = "CC.m3u"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_with_retry(url, description, max_retries=3):
    """下载文件，带重试机制"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    for attempt in range(max_retries):
        try:
            log(f"下载{description} (尝试 {attempt + 1}/{max_retries})...")
            
            # 如果是Cloudflare代理，可能需要特殊处理
            if 'workers.dev' in url:
                headers['Referer'] = 'https://smart.946985.filegear-sg.me/'
                headers['Origin'] = 'https://smart.946985.filegear-sg.me'
            
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
            wait_time = (attempt + 1) * 5
            log(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    
    return None

def get_juli_content_from_proxy():
    """从Cloudflare代理获取JULI内容"""
    log("从Cloudflare代理获取JULI内容...")
    
    # 尝试不同的访问方式
    test_urls = [
        CLOUDFLARE_PROXY,
        f"{CLOUDFLARE_PROXY}?url=https://smart.946985.filegear-sg.me/sub.php?user=tg_Thinkoo_bot",
        f"{CLOUDFLARE_PROXY}?target=https://smart.946985.filegear-sg.me/sub.php?user=tg_Thinkoo_bot",
        f"{CLOUDFLARE_PROXY}get-juli",
        f"{CLOUDFLARE_PROXY}juli",
        f"{CLOUDFLARE_PROXY}proxy",
    ]
    
    for url in test_urls:
        log(f"尝试URL: {url}")
        content = download_with_retry(url, f"代理 {url}")
        
        if content:
            # 检查是否是有效的M3U内容
            if content.startswith('#EXTM3U'):
                log(f"✅ 找到有效的M3U内容")
                return content
            elif 'JULI' in content.upper():
                log(f"✅ 找到包含JULI的内容")
                return content
            elif '<html' in content.lower():
                # 如果是HTML页面，尝试提取M3U链接
                log("尝试从HTML页面提取...")
                m3u_content = extract_m3u_from_html(content)
                if m3u_content:
                    return m3u_content
    
    log("❌ 无法从代理获取JULI内容")
    return None

def extract_m3u_from_html(html_content):
    """从HTML页面中提取M3U内容"""
    # 方法1：查找#EXTM3U开头的文本
    pattern = r'(#EXTM3U.*?)(?:</pre>|</code>|</textarea>|</script>|$)'
    match = re.search(pattern, html_content, re.DOTALL)
    
    if match:
        content = match.group(1).strip()
        log(f"✅ 从HTML提取到M3U内容 ({len(content)} 字符)")
        return content
    
    # 方法2：查找频道行
    lines = html_content.split('\n')
    m3u_lines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:') or ('://' in line and not line.startswith('<')):
            m3u_lines.append(line)
    
    if m3u_lines:
        content = '#EXTM3U\n' + '\n'.join(m3u_lines)
        log(f"✅ 从HTML提取到 {len(m3u_lines)} 个频道")
        return content
    
    # 方法3：查找M3U链接并下载
    m3u_links = re.findall(r'https?://[^\s"\']+\.m3u(?:\?[^\s"\']*)?', html_content, re.IGNORECASE)
    
    if m3u_links:
        log(f"找到 {len(m3u_links)} 个M3U链接")
        for link in m3u_links[:2]:  # 只尝试前2个
            try:
                content = download_with_retry(link, f"M3U链接 {link}")
                if content and content.startswith('#EXTM3U'):
                    return content
            except:
                continue
    
    return None

def extract_hk_channels_from_content(content):
    """从内容中提取JULI频道并改为HK分组"""
    if not content:
        return []
    
    log("从内容中提取JULI频道并改为HK分组...")
    
    # 先提取所有频道
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
    
    # 过滤并重命名JULI频道
    hk_channels = []
    seen = set()
    
    for extinf, url in channels:
        # 检查是否是JULI频道
        if 'JULI' in extinf.upper():
            # 重命名为HK分组
            new_extinf = re.sub(r'JULI', 'HK', extinf, flags=re.IGNORECASE)
            
            # 添加或修改group-title
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

def get_existing_hk_channels():
    """从现有的CC.m3u中获取HK频道（备用方案）"""
    if not os.path.exists(OUTPUT_FILE):
        return []
    
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找HK频道区域
        lines = content.split('\n')
        hk_channels = []
        in_hk_section = False
        current_extinf = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if '# HK频道' in line or '# HK 频道' in line:
                in_hk_section = True
                continue
            
            if in_hk_section and line.startswith('#EXTINF:'):
                current_extinf = line
            elif in_hk_section and current_extinf and '://' in line and not line.startswith('#'):
                if 'HK' in current_extinf.upper():
                    hk_channels.append((current_extinf, line))
                current_extinf = None
        
        if hk_channels:
            log(f"✅ 从现有文件找到 {len(hk_channels)} 个HK频道")
        return hk_channels
        
    except Exception as e:
        log(f"❌ 读取现有文件失败: {e}")
        return []

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
    
    # 2. 从Cloudflare代理获取JULI内容
    juli_content = get_juli_content_from_proxy()
    
    # 提取HK频道
    hk_channels = []
    if juli_content:
        hk_channels = extract_hk_channels_from_content(juli_content)
    
    # 3. 如果没提取到，使用现有的HK频道
    if not hk_channels:
        log("⚠️  无法从代理提取HK频道，使用现有文件中的HK频道")
        hk_channels = get_existing_hk_channels()
    
    # 提取JULI的EPG
    juli_epg = get_epg_url(juli_content) if juli_content else None
    if juli_epg:
        log(f"✅ JULI EPG: {juli_epg}")
    
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
# 代理源: {CLOUDFLARE_PROXY}
# JULI分组已改为HK分组
# EPG源: {epg_url if epg_url else '无'}
# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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
        output += f"\n# HK频道 (原JULI频道，通过Cloudflare代理更新)\n"
        for extinf, url in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    else:
        log("⚠️  没有找到HK频道")
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)}
# 总频道数: {bb_count + len(hk_channels)}
# 更新时间: {timestamp}
# 下次更新: 每天 06:00 和 18:00 (北京时间)
# 代理状态: {"✅ 正常" if juli_content else "⚠️  使用缓存"}
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
    log(f"🌐 代理状态: {'✅ 通过代理更新' if juli_content else '⚠️  使用现有频道'}")
    
    # 7. 保存更新记录
    with open("update_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | BB:{bb_count} | HK:{len(hk_channels)} | EPG:{epg_url or 'none'} | PROXY:{'OK' if juli_content else 'CACHE'}\n")

if __name__ == "__main__":
    main()
