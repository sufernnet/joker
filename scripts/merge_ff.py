#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===================== 配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"

# ⭐ MYTV 源
MYTV_URL = "https://php.946985.filegear-sg.me/jackTV.m3u"

OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

MYTV_TARGET = ["Love Nature 4K", "AXN", "PopC", "tvN"]

BAD_KEYWORDS = ["测试", "购物", "广告"]

# ===================== 下载（增强版） =====================

def download(url, retry=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Referer": url
    }

    for i in range(retry):
        try:
            r = requests.get(
                url,
                headers=headers,
                timeout=20,
                allow_redirects=True
            )

            if r.status_code == 200 and "#EXTM3U" in r.text:
                return r.text

        except Exception as e:
            print(f"重试 {i+1} 失败: {url} | {e}")

    print(f"跳过: {url}")
    return ""

# ===================== 解析 =====================

def parse_name(extinf):
    return extinf.split(",", 1)[-1].strip()

def parse_group(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""

def parse_m3u(content):
    content = content.lstrip("\ufeff").strip()

    lines = content.splitlines()
    data, ext = [], None

    for l in lines:
        l = l.strip()
        if l.startswith("#EXTINF"):
            ext = l
        elif l.startswith("http") and ext:
            name = parse_name(ext)
            if not any(x in name for x in BAD_KEYWORDS):
                data.append((name, ext, l))
    return data

# ===================== 匹配增强 =====================

def match_channel(name, target):
    name = name.lower()
    target = target.lower()
    return (
        target in name
        or name in target
        or target.replace(" ", "") in name.replace(" ", "")
    )

# ===================== MYTV 提取 =====================

def load_mytv():
    print("MYTV 源...")
    raw = download(MYTV_URL)
    data = parse_m3u(raw)

    result = {}

    # 调试可打开
    # print("示例频道：", [x[0] for x in data[:20]])

    for n, e, u in data:
        if parse_group(e) != "MYTV":
            continue

        for target in MYTV_TARGET:
            if match_channel(n, target):
                result[target] = u

    return result

# ===================== 工具 =====================

def dedup(data):
    seen, out = set(), []
    for n, e, u in data:
        if u not in seen:
            seen.add(u)
            out.append((n, e, u))
    return out

def set_group(extinf, group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')

# ===================== 主程序 =====================

def main():
    print("主源...")
    main_data = parse_m3u(download(SOURCE_URL))

    print("TW...")
    tw_data = parse_m3u(download(TW_M3U_URL))

    mytv_map = load_mytv()

    hk = dedup([x for x in main_data if HK_SOURCE_GROUP in x[1]])
    tw = dedup(tw_data)

    # ===================== 构造 MYTV 频道 =====================

    mytv_channels = []

    for name in MYTV_TARGET:
        if name in mytv_map:
            url = mytv_map[name]

            ext = (
                f'#EXTINF:-1 tvg-id="{name}" '
                f'tvg-name="{name}" '
                f'tvg-logo="" '
                f'group-title="HK",{name}'
            )

            mytv_channels.append((name, ext, url))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out = "#EXTM3U\n\n"
    out += f"# 更新时间 {now}\n\n"

    try:
        with open(BB_FILE, encoding="utf-8") as f:
            for l in f:
                if not l.startswith("#EXTM3U"):
                    out += l
        out += "\n"
    except:
        pass

    # ===================== HK（插入）=====================

    out += "\n# HK\n"

    inserted = False

    for n, e, u in hk:
        out += set_group(e, "HK") + "\n" + u + "\n"

        if not inserted and "鳳凰衛視·香港" in n:
            for cn, ce, cu in mytv_channels:
                out += ce + "\n" + cu + "\n"
            inserted = True

    # 兜底
    if not inserted:
        for cn, ce, cu in mytv_channels:
            out += ce + "\n" + cu + "\n"

    # ===================== TW =====================

    out += "\n# TW\n"
    for n, e, u in tw:
        out += set_group(e, "TW") + "\n" + u + "\n"

    # ===================== 写入 =====================

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成")

if __name__ == "__main__":
    main()
