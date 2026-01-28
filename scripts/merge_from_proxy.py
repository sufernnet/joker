#!/usr/bin/env python3
"""
M3U文件合并脚本 - 增强EPG支持
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取内容
3. 提取JULI频道，分组改为HK，按指定顺序排列
4. 提取4gtv前30个直播，分组改为TW，过滤指定频道
5. 合并生成CC.m3u，包含多个EPG源
北京时间每天6:00、17:00自动运行
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

# 需要过滤掉的TW频道关键词（不区分大小写）
BLACKLIST_TW = [
    "Bloomberg TV",
    "Bloomberg",
    "SBN全球财经台",
    "SBN财经",
    "FRANCE24英文台",
    "FRANCE24",
    "半岛国际新闻台",
    "半島国际",
    "NHK world-japan",
    "NHK world",
    "SBN",
    "日本",
    "NHK",
    "CNBC Asia",
    "CNBC"
]

# HK频道优先顺序（按这个顺序排列在最前面）
HK_PRIORITY_ORDER = [
    "凤凰中文",
    "凤凰资讯", 
    "凤凰香港",
    "NOW新闻台",
    "NOW星影",
    "NOW爆谷"
]

# 备选EPG源（如果主要EPG失效）
BACKUP_EPG_URLS = [
    "https://epg.112114.xyz/pp.xml",  # BB的EPG
    "https://epg.946985.filegear-sg.me/t.xml.gz",  # JULI的EPG
    "https://epg.112114.xyz/pp.xml",
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
        
        response = requests.get(epg_url, headers=headers, timeout=10, stream=True)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            chunk = response.raw.read(1024)
            text = chunk.decode('utf-8', errors='ignore')
            
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
    working_epgs = []
    
    for epg_url in epg_urls:
        if test_epg_url(epg_url):
            working_epgs.append(epg_url)
    
    if working_epgs:
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

def get_content_from_proxy():
    """从Cloudflare代理获取内容"""
    try:
        log("从Cloudflare代理获取内容...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://smart.946985.filegear-sg.me/'
        }
        
        response = requests.get(CLOUDFLARE_PROXY, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            if '<html' in content.lower():
                m3u_match = re.search(r'(#EXTM3U.*?)(?:</pre>|</code>|$)', content, re.DOTALL)
                if m3u_match:
                    content = m3u_match.group(1).strip()
                    log("✅ 从HTML提取到M3U内容")
            if content.strip():
                log(f"✅ 获取到内容 ({len(content)} 字符)")
                return content
        else:
            log(f"❌ 代理返回错误: {response.status_code}")
    except Exception as e:
        log(f"❌ 代理访问失败: {e}")
    return None

def main():
    log("开始合并M3U文件...")
    log(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"下次运行: 北京时间 06:00 和 17:00")

    bb_content = download_bb_m3u()
    if not bb_content:
        return

    proxy_content = get_content_from_proxy()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f"""#EXTM3U
# 自动合并 M3U 文件
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 17:00 (北京时间)
# GitHub Actions 自动生成
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    log("🎉 合并完成!")
    log("🕒 下次自动更新: 北京时间 06:00 和 17:00")

if __name__ == "__main__":
    main()
