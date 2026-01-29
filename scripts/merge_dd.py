#!/usr/bin/env python3
"""
DD.m3u 合并脚本
仅提取【港澳台直播】分组 → 拆分为【香港 / 台湾】
"""

import requests
import re
from datetime import datetime

# ================= 配置 =================
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
OUTPUT_FILE = "DD.m3u"

TARGET_GROUP = "港澳台直播"

# =======================================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url, desc):
    log(f"下载 {desc} ...")
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text

def extract_target_group(content):
    """
    只提取 group-title="港澳台直播" 的频道
    """
    lines = content.splitlines()
    results = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#EXTINF") and f'group-title="{TARGET_GROUP}"' in line:
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith("#"):
                    results.append((line, url))
            i += 2
        else:
            i += 1

    log(f"提取到【{TARGET_GROUP}】频道 {len(results)} 个")
    return results

def split_hk_tw(channels):
    hk_kw = ["香港", "HK", "TVB", "翡翠", "明珠", "凤凰", "有线", "NOW", "VIU", "港"]
    tw_kw = ["台湾", "台视", "中视", "华视", "民视", "三立", "东森", "TVBS"]

    hk, tw = [], []

    for extinf, url in channels:
        name = extinf.split(",", 1)[-1].lower()

        if any(k.lower() in name for k in hk_kw):
            new_extinf = re.sub(
                r'group-title="[^"]*"',
                'group-title="香港"',
                extinf
            )
            hk.append((new_extinf, url))

        elif any(k.lower() in name for k in tw_kw):
            new_extinf = re.sub(
                r'group-title="[^"]*"',
                'group-title="台湾"',
                extinf
            )
            tw.append((new_extinf, url))

    log(f"香港频道 {len(hk)} 个，台湾频道 {len(tw)} 个")
    return hk, tw

def main():
    log("=== 开始生成 DD.m3u ===")

    bb = download(BB_URL, "BB.m3u")
    gat = download(GAT_URL, "港澳台订阅")

    # 提取 EPG
    epg = None
    m = re.search(r'url-tvg="([^"]+)"', bb)
    if m:
        epg = m.group(1)

    # 只取【港澳台直播】
    target_channels = extract_target_group(gat)

    # 分香港 / 台湾
    hk, tw = split_hk_tw(target_channels)

    # 构建输出
    out = "#EXTM3U"
    if epg:
        out += f' url-tvg="{epg}"'
    out += "\n"
    out += f"""# DD.m3u
# 仅提取：港澳台直播
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""

    # 原 BB 内容（跳过头）
    for line in bb.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        out += line + "\n"

    # 香港
    out += f"\n# 香港频道 ({len(hk)} 个)\n"
    for e, u in hk:
        out += e + "\n" + u + "\n"

    # 台湾
    out += f"\n# 台湾频道 ({len(tw)} 个)\n"
    for e, u in tw:
        out += e + "\n" + u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    log("✅ DD.m3u 生成完成")
    log(f"香港 {len(hk)} | 台湾 {len(tw)}")

if __name__ == "__main__":
    main()
