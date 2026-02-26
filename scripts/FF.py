#!/usr/bin/env python3
"""
FF.m3u 生成脚本

功能：
1. 从 iptvpro.txt 提取 🇭🇰 🇹🇼 ⛹️‍体育
2. 分组重命名为 HK / TW / Sports
3. 仅过滤带 720p 字样频道
4. 输出 FF.m3u
"""

import requests
from datetime import datetime

# ================= 配置 =================

SOURCE_URL = "https://ghfast.top/https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/iptvpro.txt"
OUTPUT_FILE = "FF.m3u"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

GROUP_MAP = {
    "🇭🇰": "HK",
    "🇹🇼": "TW",
    "⛹️": "Sports",
}

# ================= 工具 =================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url):
    log("下载 iptvpro.txt ...")
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    log(f"下载成功 ({len(r.text)} 字符)")
    return r.text

def should_keep(name):
    """只过滤 720p"""
    return "720p" not in name.lower()

# ================= 主逻辑 =================

def main():
    log("开始生成 FF.m3u ...")

    content = download(SOURCE_URL)
    lines = content.splitlines()

    groups = {
        "HK": [],
        "TW": [],
        "Sports": []
    }

    current_group = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 判断分组
        for flag, group_name in GROUP_MAP.items():
            if flag in line:
                current_group = group_name
                break

        # 提取频道
        if current_group and "," in line and "http" in line:
            name, url = line.split(",", 1)
            name = name.strip()
            url = url.strip()

            if should_keep(name):
                groups[current_group].append((name, url))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# FF.m3u
# 生成时间: {timestamp}
# 数据源: iptvpro.txt
# GitHub Actions 自动生成

"""

    total_count = 0

    for group_name, channels in groups.items():
        if channels:
            output += f"\n# {group_name} ({len(channels)})\n"
            for name, url in channels:
                output += f'#EXTINF:-1 group-title="{group_name}",{name}\n'
                output += f"{url}\n"
            total_count += len(channels)

    output += f"""
# 统计信息
# 总频道数: {total_count}
# 更新时间: {timestamp}
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    log(f"🎉 FF.m3u 生成完成，共 {total_count} 个频道")


if __name__ == "__main__":
    main()
