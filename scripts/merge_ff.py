#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
from datetime import datetime

# ===================== 配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"
MYTV_URL = "https://php.946985.filegear-sg.me/jackTV.m3u"

OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

MYTV_TARGET = ["Love Nature 4K", "AXN", "PopC", "tvN"]

BAD_KEYWORDS = ["测试", "购物", "广告"]

# ===================== 下载（增强稳定） =====================

def download(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": url
    }

    try:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        return r.text
    except Exception as e:
        print("下载失败:", url, e)
        return ""

# ===================== M3U解析（保留KODIPROP） =====================

def parse_m3u(content):
    if not content:
        return []

    content = content.lstrip("\ufeff").strip()

    lines = content.splitlines()

    data = []
    ext = None
    props = []

    for l in lines:
        l = l.strip()

        if l.startswith("#EXTINF"):
            ext = l
            props = []

        elif l.startswith("#KODIPROP"):
            props.append(l)

        elif l.startswith("http") and ext:
            name = ext.split(",", 1)[-1].strip()

            if any(b in name for b in BAD_KEYWORDS):
                continue

            full_ext = "\n".join([ext] + props) if props else ext

            data.append((name, full_ext, l))

            ext = None
            props = []

    return data

# ===================== MYTV增强解析（核心） =====================

def normalize(s):
    return s.lower().replace(" ", "").replace("-", "")

def load_mytv():
    print("\n========== MYTV 调试开始 ==========")

    raw = download(MYTV_URL)

    if not raw:
        print("❌ MYTV 未获取到内容")
        return {}

    print("✔ MYTV 已下载")

    data = parse_m3u(raw)

    print("✔ 解析条数:", len(data))

    # 打印前30个频道用于确认真实结构
    print("\n--- 前30个频道 ---")
    for i, (n, _, _) in enumerate(data[:30]):
        print(i+1, n)

    result = {}

    for n, e, u in data:

        nn = normalize(n)

        for t in MYTV_TARGET:
            if normalize(t) in nn:
                result[t] = u
                print(f"✔ 命中: {t} -> {n}")

    print("\n========== MYTV 命中结果 ==========")
    print(result)

    return result

# ===================== 工具 =====================

def set_group(extinf, group):
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')

def dedup(data):
    seen, out = set(), []
    for n, e, u in data:
        if u not in seen:
            seen.add(u)
            out.append((n, e, u))
    return out

# ===================== 主程序 =====================

def main():

    print("\n========== 主源 ==========")
    main_data = parse_m3u(download(SOURCE_URL))

    print("\n========== TW ==========")
    tw_data = parse_m3u(download(TW_M3U_URL))

    print("\n========== MYTV ==========")
    mytv_map = load_mytv()

    # ===================== HK =====================

    hk = dedup([x for x in main_data if HK_SOURCE_GROUP in x[1]])
    tw = dedup(tw_data)

    mytv_channels = []

    for name in MYTV_TARGET:
        if name in mytv_map:
            url = mytv_map[name]

            ext = f'#EXTINF:-1 tvg-id="{name}" tvg-name="{name}" group-title="HK",{name}'
            mytv_channels.append((name, ext, url))

    # ===================== 输出 =====================

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out = "#EXTM3U\n\n"
    out += f"# 更新时间 {now}\n\n"

    # ===================== HK插入 =====================

    out += "\n# HK\n"

    inserted = False

    for n, e, u in hk:
        out += set_group(e, "HK") + "\n" + u + "\n"

        if not inserted and "鳳凰衛視·香港" in n:
            for _, ce, cu in mytv_channels:
                out += ce + "\n" + cu + "\n"
            inserted = True

    if not inserted:
        print("⚠ 未找到插入点，追加 MYTV")
        for _, ce, cu in mytv_channels:
            out += ce + "\n" + cu + "\n"

    # ===================== TW =====================

    out += "\n# TW\n"
    for n, e, u in tw:
        out += set_group(e, "TW") + "\n" + u + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("\n✅ 完成")

if __name__ == "__main__":
    main()
