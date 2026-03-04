#!/usr/bin/env python3
"""
DD.m3u 合并脚本（香港 + 台湾限制 双分组版）

功能：
1. 提取香港频道（从原港澳台源）
2. 提取台湾「限制」频道（从 CF Workers）
3. 去重处理（按URL）
4. 分组输出：
   - 香港
   - 台湾限制
5. 合并 BB.m3u
6. 固定 EPG

每天 06:00 / 17:00 自动运行
"""

import requests
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
HK_SOURCE_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
TW_SOURCE_URL = "https://yang.sufern001.workers.dev/"

OUTPUT_FILE = "DD.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

HK_GROUP_NAME = "香港"
TW_GROUP_NAME = "台湾限制"

# ================== 工具 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url, desc):
    try:
        log(f"下载 {desc} ...")
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        log(f"✅ {desc} 下载成功")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return ""

# ================== 提取逻辑 ==================

def extract_hk_channels(content):
    """
    从港澳台源中提取香港频道
    """
    lines = content.splitlines()
    channels = []
    in_section = False
    marker = "🔮[三网]港澳台直播,#genre#"

    HK_KEYWORDS = [
        "香港", "凤凰", "Now", "TVB",
        "HOY", "RHK", "Viu", "有线"
    ]

    log("开始提取香港频道")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if marker in line:
            in_section = True
            continue

        if in_section:
            if ",#genre#" in line:
                break

            if "," in line and "://" in line:
                name, url = line.split(",", 1)

                # 只保留香港相关
                if any(k.lower() in name.lower() for k in HK_KEYWORDS):
                    channels.append((name.strip(), url.strip()))

    log(f"香港频道数: {len(channels)}")
    return channels


def extract_tw_limited(content):
    """
    提取台湾「限制」分组
    """
    lines = content.splitlines()
    channels = []
    in_section = False
    marker = "•台湾「限制」,#genre#"

    log("开始提取台湾「限制」频道")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if marker in line:
            in_section = True
            continue

        if in_section:
            if ",#genre#" in line:
                break

            if "," in line and "://" in line:
                name, url = line.split(",", 1)
                channels.append((name.strip(), url.strip()))

    log(f"台湾限制频道数: {len(channels)}")
    return channels


# ================== 去重 ==================

def deduplicate(channels):
    """
    按 URL 去重
    """
    seen = {}
    for name, url in channels:
        if url not in seen:
            seen[url] = name

    result = [(name, url) for url, name in seen.items()]
    log(f"去重后频道数: {len(result)}")
    return result


# ================== 排序 ==================

def sort_channels(channels):
    """
    简单字母排序
    """
    return sorted(channels, key=lambda x: x[0].lower())


# ================== 主流程 ==================

def main():
    log("开始生成 DD.m3u")

    bb_content = download(BB_URL, "BB.m3u")
    hk_source = download(HK_SOURCE_URL, "香港源")
    tw_source = download(TW_SOURCE_URL, "台湾源")

    hk_channels = extract_hk_channels(hk_source)
    tw_channels = extract_tw_limited(tw_source)

    hk_channels = deduplicate(hk_channels)
    tw_channels = deduplicate(tw_channels)

    hk_channels = sort_channels(hk_channels)
    tw_channels = sort_channels(tw_channels)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# DD.m3u
# 生成时间: {timestamp}
# 香港 + 台湾限制 双分组版
# EPG: {EPG_URL}

"""

    # ===== BB =====
    bb_count = 0
    for line in bb_content.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        output += line + "\n"
        if line.startswith("#EXTINF"):
            bb_count += 1

    # ===== 香港 =====
    if hk_channels:
        output += f"\n# {HK_GROUP_NAME}频道 ({len(hk_channels)})\n"
        for name, url in hk_channels:
            output += f'#EXTINF:-1 group-title="{HK_GROUP_NAME}",{name}\n'
            output += f"{url}\n"

    # ===== 台湾限制 =====
    if tw_channels:
        output += f"\n# {TW_GROUP_NAME}频道 ({len(tw_channels)})\n"
        for name, url in tw_channels:
            output += f'#EXTINF:-1 group-title="{TW_GROUP_NAME}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(hk_channels) + len(tw_channels)

    output += f"""

# 统计
# BB频道数: {bb_count}
# 香港频道数: {len(hk_channels)}
# 台湾限制频道数: {len(tw_channels)}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 DD.m3u 生成成功")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
