#!/usr/bin/env python3
"""
从 Cloudflare 代理页面提取并合并 M3U
代理地址: https://smt-proxy.sufern001.workers.dev/
JULI分组已改为HK分组
"""

import requests
import re
import os
from datetime import datetime

# 配置
PROXY_URL = "https://smt-proxy.sufern001.workers.dev/"
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_bb_m3u():
    """下载BB.m3u"""
    try:
        log("下载 BB.m3u...")
        response = requests.get(BB_URL, timeout=10)
        response.raise_for_status()
        log(f"✅ BB.m3u 下载成功 ({len(response.text)} 字符)")
        return response.text
    except Exception as e:
        log(f"❌ BB.m3u 下载失败: {e}")
        return ""

def extract_m3u_from_proxy():
    """从代理页面提取M3U内容"""
    log("从代理页面提取内容...")
    
    try:
        # 获取代理页面
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(PROXY_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        html_content = response.text
        log(f"代理页面获取成功 ({len(html_content)} 字符)")
        
        # 方法1：直接查找M3U链接
        m3u_links = re.findall(r'https?://[^\s"\']+\.m3u(?:\?[^\s"\']*)?', html_content, re.IGNORECASE)
        
        if m3u_links:
            log(f"找到 {len(m3u_links)} 个M3U链接")
            # 尝试下载第一个M3U链接
            try:
                m3u_response = requests.get(m3u_links[0], timeout=10)
                if m3u_response.status_code == 200:
                    log(f"✅ 成功下载M3U文件 ({len(m3u_response.text)} 字符)")
                    return m3u_response.text
            except Exception as e:
                log(f"下载M3U链接失败: {e}")
        
        # 方法2：查找可能包含M3U内容的区域
        log("尝试直接提取M3U内容...")
        
        patterns = [
            r'(#EXTM3U.*?)(?:</pre>|</code>|</textarea>|$)',
            r'<pre[^>]*>(.*?#EXTM3U.*?)</pre>',
            r'<code[^>]*>(.*?#EXTM3U.*?)</code>',
            r'<textarea[^>]*>(.*?#EXTM3U.*?)</textarea>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            if matches:
                log(f"找到模式匹配: {len(matches)} 处")
                for match in matches:
                    content = match.strip()
                    if content.startswith('#EXTM3U'):
                        log(f"✅ 找到有效的M3U内容 ({len(content)} 字符)")
                        return content
        
        # 方法3：如果页面是纯文本格式的M3U
        if html_content.startswith('#EXTM3U'):
            log(f"✅ 页面本身就是M3U文件 ({len(html_content)} 字符)")
            return html_content
        
        # 方法4：提取所有可能包含频道信息的行
        log("尝试提取频道信息行...")
        lines = html_content.split('\n')
        m3u_content = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:') or ('://' in line and not line.startswith('<')):
                m3u_content.append(line)
        
        if m3u_content:
            log(f"✅ 提取到 {len(m3u_content)} 行频道信息")
            return '#EXTM3U\n' + '\n'.join(m3u_content)
        
        log("❌ 无法从页面提取M3U内容")
        # 保存HTML供调试
        with open("proxy_debug.html", "w", encoding="utf-8") as f:
            f.write(html_content[:2000])
        
        return ""
        
    except Exception as e:
        log(f"❌ 从代理提取失败: {e}")
        return ""

def extract_hk_channels(m3u_content):
    """从M3U内容中提取JULI频道并改为HK分组"""
    if not m3u_content:
        return []
    
    log("提取JULI频道并改为HK分组...")
    lines = m3u_content.split('\n')
    channels = []
    seen_channels = set()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 寻找包含JULI的行（不区分大小写）
        if 'JULI' in line.upper():
            # 向前找EXTINF行
            extinf_line = None
            for j in range(max(0, i-3), i+1):
                if lines[j].strip().startswith('#EXTINF:'):
                    extinf_line = lines[j].strip()
                    break
            
            # 向后找URL行
            url_line = None
            if extinf_line:
                for k in range(i+1, min(len(lines), i+4)):
                    test_line = lines[k].strip()
                    if test_line and not test_line.startswith('#') and '://' in test_line:
                        url_line = test_line
                        break
            
            # 如果找到了EXTINF和URL
            if extinf_line and url_line:
                # 修改频道名称：把JULI改成HK
                new_extinf = extinf_line
                if 'JULI' in new_extinf.upper():
                    # 使用正则替换所有JULI为HK
                    new_extinf = re.sub(r'JULI', 'HK', new_extinf, flags=re.IGNORECASE)
                
                # 创建频道唯一标识（用于去重）
                channel_id = f"{new_extinf}|{url_line}"
                
                if channel_id not in seen_channels:
                    seen_channels.add(channel_id)
                    channels.append((new_extinf, url_line))
        
        i += 1
    
    log(f"✅ 提取到 {len(channels)} 个HK频道（原JULI频道）")
    
    # 显示前几个频道
    if channels:
        log("部分HK频道:")
        for idx, (extinf, url) in enumerate(channels[:3]):
            if ',' in extinf:
                name = extinf.split(',', 1)[1]
                log(f"  {idx+1}. {name[:60]}{'...' if len(name) > 60 else ''}")
    
    return channels

def main():
    """主函数"""
    log("开始合并M3U文件...")
    
    # 1. 下载BB.m3u
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从代理获取内容
    proxy_content = extract_m3u_from_proxy()
    if not proxy_content:
        log("⚠️  无法从代理获取内容，只使用BB.m3u")
        hk_channels = []
    else:
        # 3. 提取HK频道（原JULI频道）
        hk_channels = extract_hk_channels(proxy_content)
    
    # 4. 合并内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output = f"""#EXTM3U
# 自动合并 M3U 文件
# 生成时间: {timestamp}
# 代理源: {PROXY_URL}
# JULI分组已改为HK分组
# GitHub Actions 自动生成

"""
    
    # 添加BB内容（跳过开头的#EXTM3U）
    bb_lines = bb_content.split('\n')
    bb_count = 0
    for line in bb_lines:
        if line.strip() and not line.startswith('#EXTM3U'):
            output += line + '\n'
            if line.startswith('#EXTINF:'):
                bb_count += 1
    
    # 添加HK频道（原JULI频道）
    if hk_channels:
        output += f"\n# HK 频道 (原JULI频道，从代理提取)\n"
        for extinf, url in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)} (原JULI频道)
# 总频道数: {bb_count + len(hk_channels)}
# 更新时间: {timestamp}
"""
    
    # 5. 保存文件
    output_file = "CC.m3u"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: {output_file}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 HK频道: {len(hk_channels)} (原JULI)")
    log(f"📺 总计: {bb_count + len(hk_channels)}")

if __name__ == "__main__":
    main()
