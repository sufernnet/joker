#!/usr/bin/env python3
"""
DD.m3u 合并脚本（港澳台直提 + 凤凰/NOW 精确排序）

功能：
1. 提取“🔮[三网]港澳台直播”分组
2. 重命名为“港澳台”
3. 港澳台分组内排序：
   凤凰中文 → 凤凰资讯 → 凤凰香港 → 凤凰电影 → NOW → 其他
4. 合并 BB.m3u
5. 使用固定 EPG

北京时间每天 06:00 / 17:00 自动运行
"""

import requests
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
OUTPUT_FILE = "DD.m3u"

# 修改为新的分组名称
SOURCE_GROUP = "🔮[三网]港澳台直播"
TARGET_GROUP = "港澳台"

EPG_URL = "http://epg.51zmt.top:8000/e.xml"

# ================== 工具 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download(url, desc):
    try:
        log(f"下载 {desc}...")
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        log(f"✅ {desc} 下载成功 ({len(r.text)} 字符)")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return None


def extract_gat_channels(content):
    lines = content.splitlines()
    channels = []
    in_section = False
    marker = f"{SOURCE_GROUP},#genre#"

    log(f"开始提取分组：{SOURCE_GROUP}")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if marker in line:
            in_section = True
            log(f"✅ 在第 {i+1} 行找到目标分组")
            continue

        if in_section:
            if ",#genre#" in line:
                log("到达下一个分组，停止提取")
                break

            if "," in line and "://" in line:
                name, url = line.split(",", 1)
                channels.append((name.strip(), url.strip()))

    log(f"提取到 {len(channels)} 个频道")
    return channels


def sort_gat_channels(channels):
    """
    排序权重（越小越靠前）：
    0 凤凰中文
    1 凤凰资讯
    2 凤凰香港
    3 凤凰电影
    4 NOW
    5 其他
    """
    def weight(name):
        if "凤凰电影" in name:
            return (3, name)
        if "凤凰卫视中文" in name or "凤凰中文" in name:
            return (0, name)
        if "凤凰卫视资讯" in name or "凤凰资讯" in name:
            return (1, name)
        if "凤凰卫视香港" in name or "凤凰香港" in name:
            return (2, name)
        if "凤凰" in name:
            return (2, name)  # 兜底：其他凤凰靠前但在电影前
        if "NOW" in name:
            return (4, name)
        return (5, name)

    return sorted(channels, key=lambda x: weight(x[0]))


# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    gat = download(GAT_URL, "港澳台直播源") or ""
    gat_channels = extract_gat_channels(gat) if gat else []
    gat_channels = sort_gat_channels(gat_channels)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===== M3U 头 =====
    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# DD.m3u
# 生成时间: {timestamp}
# 更新频率: 每天 06:00 / 17:00
# EPG: {EPG_URL}
# GitHub Actions 自动生成

"""

    # ===== BB =====
    bb_count = 0
    for line in bb.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        output += line + "\n"
        if line.startswith("#EXTINF"):
            bb_count += 1

    # ===== 港澳台 =====
    if gat_channels:
        output += f"\n# {TARGET_GROUP}频道 ({len(gat_channels)})\n"
        for name, url in gat_channels:
            output += f'#EXTINF:-1 group-title="{TARGET_GROUP}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(gat_channels)

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {TARGET_GROUP}频道数: {len(gat_channels)}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 DD.m3u 生成成功")
        log(f"📺 BB({bb_count}) + 港澳台({len(gat_channels)}) = {total}")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
