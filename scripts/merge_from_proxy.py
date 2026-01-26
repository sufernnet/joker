# scripts/merge_from_proxy.py
#!/usr/bin/env python3
"""
从 Cloudflare 代理页面提取并合并 M3U
代理地址: https://smt-proxy.sufern001.workers.dev/
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
        
        # 方法1：直接查找M3U链接（如果页面有直接链接）
        m3u_links = re.findall(r'https?://[^\s"\']+\.m3u(?:\?[^\s"\']*)?', html_content, re.IGNORECASE)
        
        if m3u_links:
            log(f"找到 {len(m3u_links)} 个M3U链接")
            for link in m3u_links:
                log(f"  - {link}")
            
            # 尝试下载第一个M3U链接
            try:
                m3u_response = requests.get(m3u_links[0], timeout=10)
                if m3u_response.status_code == 200:
                    log(f"✅ 成功下载M3U文件 ({len(m3u_response.text)} 字符)")
                    return m3u_response.text
            except Exception as e:
                log(f"下载M3U链接失败: {e}")
        
        # 方法2：如果页面直接包含M3U内容（可能在<pre>标签或文本中）
        log("尝试直接提取M3U内容...")
        
        # 查找可能包含M3U内容的区域
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
                for i, match in enumerate(matches[:2]):
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
        log("页面开头1000字符:")
        print(html_content[:1000])
        
        # 保存HTML供调试
        with open("proxy_debug.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return ""
        
    except Exception as e:
        log(f"❌ 从代理提取失败: {e}")
        return ""

def extract_juli_channels(m3u_content):
    """从M3U内容中提取JULI频道"""
    if not m3u_content:
        return []
    
    log("提取JULI频道...")
    lines = m3u_content.split('\n')
    channels = []
    current_extinf = None
    
    for i in range(len(lines)):
        line = lines[i].strip()
        
        # 寻找JULI频道
        if 'JULI' in line.upper():
            # 如果是EXTINF行
            if line.startswith('#EXTINF:'):
                current_extinf = line
                # 查找对应的URL
                for j in range(i+1, min(i+3, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and '://' in next_line and not next_line.startswith('#'):
                        channels.append((current_extinf, next_line))
                        break
            
            # 如果在其他行找到JULI，向前找EXTINF
            elif i > 0:
                for j in range(max(0, i-3), i):
                    if lines[j].startswith('#EXTINF:'):
                        current_extinf = lines[j]
                        # 查找URL
                        for k in range(i, min(i+3, len(lines))):
                            url_line = lines[k].strip()
                            if url_line and '://' in url_line and not url_line.startswith('#'):
                                channels.append((current_extinf, url_line))
                                break
                        break
    
    # 去重
    unique_channels = []
    seen = set()
    for extinf, url in channels:
        key = f"{extinf}|{url}"
        if key not in seen:
            seen.add(key)
            unique_channels.append((extinf, url))
    
    log(f"✅ 提取到 {len(unique_channels)} 个JULI频道")
    
    # 显示部分频道
    for i, (extinf, url) in enumerate(unique_channels[:5]):
        channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
        log(f"  {i+1}. {channel_name[:50]}...")
    
    return unique_channels

def main():
    """主函数"""
    log("开始合并M3U文件...")
    
    # 1. 下载BB.m3u
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从代理获取JULI内容
    proxy_content = extract_m3u_from_proxy()
    if not proxy_content:
        log("⚠️  无法从代理获取内容，只使用BB.m3u")
        juli_channels = []
    else:
        # 3. 提取JULI频道
        juli_channels = extract_juli_channels(proxy_content)
    
    # 4. 合并内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output = f"""#EXTM3U
# 自动合并 M3U 文件
# 生成时间: {timestamp}
# 代理源: {PROXY_URL}
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
    
    # 添加JULI频道
    if juli_channels:
        output += f"\n# JULI 频道 (从代理提取)\n"
        for extinf, url in juli_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计信息
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# JULI 频道数: {len(juli_channels)}
# 总频道数: {bb_count + len(juli_channels)}
# 更新时间: {timestamp}
"""
    
    # 5. 保存文件
    with open("CC.m3u", "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: CC.m3u")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 JULI频道: {len(juli_channels)}")
    log(f"📺 总计: {bb_count + len(juli_channels)}")

if __name__ == "__main__":
    main()
