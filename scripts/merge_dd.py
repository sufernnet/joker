#!/usr/bin/env python3
"""
DD.m3u合并脚本 - 针对目标源优化版
1. 从指定URL提取“港澳台直播”分组内的所有频道
2. 自动细分为“香港”、“台湾”两个分组
3. 与BB.m3u合并
4. 输出DD.m3u
北京时间每天6:00、17:00自动运行
"""

import requests
import re
from datetime import datetime

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
OUTPUT_FILE = "DD.m3u"

# 分组关键词
TARGET_GROUP = "港澳台直播"
HK_GROUP_NAME = "香港"
TW_GROUP_NAME = "台湾"

# 香港频道关键词
HK_KEYWORDS = ["香港", "港", "TVB", "无线", "明珠", "翡翠", "本港台", "凤凰卫视", "NOW", "VIU", "RTHK", "有线"]
# 台湾频道关键词
TW_KEYWORDS = ["台湾", "台", "台视", "中视", "华视", "民视", "三立", "东森", "TVBS", "中天", "寰宇", "非凡", "纬来"]


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def download_content(url, description):
    try:
        log(f"下载 {description}...")
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        log(f"✅ {description} 下载成功 ({len(r.text)} 字符)")
        return r.text
    except Exception as e:
        log(f"❌ {description} 下载失败: {e}")
        return None


def extract_target_group_channels(content):
    if not content:
        return []

    log(f"开始提取分组：{TARGET_GROUP}")
    lines = content.splitlines()
    target_channels = []
    in_section = False
    pattern = f"{TARGET_GROUP},#genre#"

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        if pattern in line:
            in_section = True
            log(f"✅ 在第 {i+1} 行找到目标分组")
            continue

        if in_section:
            if ",#genre#" in line:
                log("到达下一个分组，停止提取")
                break

            if "," in line and "://" in line:
                name, url = line.split(",", 1)
                target_channels.append((name.strip(), url.strip()))

    log(f"从『{TARGET_GROUP}』分组中提取到 {len(target_channels)} 个频道")
    return target_channels


def classify_channels_by_region(channels):
    hk, tw, other = [], [], []
    log("开始细分香港 / 台湾频道...")

    for name, url in channels:
        lname = name.lower()
        matched = False

        for k in HK_KEYWORDS:
            if k.lower() in lname:
                hk.append((f'#EXTINF:-1 group-title="{HK_GROUP_NAME}",{name}', url, name))
                matched = True
                break

        if not matched:
            for k in TW_KEYWORDS:
                if k.lower() in lname:
                    tw.append((f'#EXTINF:-1 group-title="{TW_GROUP_NAME}",{name}', url, name))
                    matched = True
                    break

        if not matched:
            other.append((f"#EXTINF:-1,{name}", url, name))

    log(f"   ├─ 香港频道: {len(hk)}")
    log(f"   ├─ 台湾频道: {len(tw)}")
    log(f"   └─ 未细分频道: {len(other)}")

    return hk, tw, other


def get_bb_epg(content):
    if not content:
        return None
    m = re.search(r'url-tvg="([^"]+)"', content)
    return m.group(1) if m else None


def main():
    log("开始生成 DD.m3u ...")

    bb_content = download_content(BB_URL, "BB.m3u")
    if not bb_content:
        return

    gat_content = download_content(GAT_URL, "港澳台直播源") or ""

    epg_url = get_bb_epg(bb_content)
    log(f"EPG源: {epg_url}")

    hk, tw, other = [], [], []
    if gat_content:
        all_channels = extract_target_group_channels(gat_content)
        hk, tw, other = classify_channels_by_region(all_channels)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f'#EXTM3U url-tvg="{epg_url}"\n\n'

    output += f"""# DD.m3u
# 生成时间: {timestamp}
# 更新频率: 每天 06:00 / 17:00
# 目标分组: {TARGET_GROUP}

"""

    bb_count = 0
    for line in bb_content.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        output += line + "\n"
        if line.startswith("#EXTINF"):
            bb_count += 1

    if hk:
        output += f"\n# 香港频道 ({len(hk)})\n"
        for e, u, _ in sorted(hk, key=lambda x: x[2]):
            output += f"{e}\n{u}\n"

    if tw:
        output += f"\n# 台湾频道 ({len(tw)})\n"
        for e, u, _ in sorted(tw, key=lambda x: x[2]):
            output += f"{e}\n{u}\n"

    if other:
        output += f"\n# 其他{TARGET_GROUP}频道 ({len(other)})\n"
        for e, u, _ in other:
            output += f"{e}\n{u}\n"

    total = bb_count + len(hk) + len(tw) + len(other)
    output += f"""
# 统计
# BB: {bb_count}
# 香港: {len(hk)}
# 台湾: {len(tw)}
# 其他{TARGET_GROUP}: {len(other)}
# 总数: {total}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 DD.m3u 生成成功")
    except Exception as e:
        log(f"❌ 保存失败: {e}")


if __name__ == "__main__":
    main()
