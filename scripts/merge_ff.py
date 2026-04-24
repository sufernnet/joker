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

EXTRA_URLS = [
    "https://tzdr.com/iptv.txt",
    "https://live.kilvn.com/iptv.m3u",
    "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "http://175.178.251.183:6689/live.m3u",
    "https://m3u.ibert.me/ycl_iptv.m3u",
    "https://codeberg.org/Jsnzkpg/Jsnzkpg/raw/Jsnzkpg/Jsnzkpg1.m3u",
    "https://2026.xymm.ccwu.cc",
    "https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u",
    "https://iptv.catvod.com/list.php?token=e222e4d00c9d1945c3387a6c63b434577afbefd92f01f3fa39da76f154997133"
]

OUTPUT_FILE = "Gather.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

CCTV_TARGET = [
    "世界地理","兵器科技","怀旧剧场","第一剧场",
    "女性时尚","风云足球","风云音乐","央视台球"
]

# ✅ 修复 HC
CHC_TARGET = [
    "CHC影迷电影","CHC家庭影院","CHC动作电影"
]

BAD_KEYWORDS = ["测试", "购物", "广告"]

# ===================== 台标修复 =====================

LOGO_MAP = {
    "CHC影迷电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC影迷电影.png",
    "CHC家庭影院": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC家庭影院.png",
    "CHC动作电影": "https://raw.githubusercontent.com/xiasufern/AA/main/icon/CHC动作电影.png"
}

def fix_logo(name, extinf):
    if name in LOGO_MAP:
        logo = LOGO_MAP[name]
        if 'tvg-logo="' in extinf:
            extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{logo}"')
    return extinf

# ===================== 下载 =====================

def download(url, retry=2):
    headers = {"User-Agent": "Mozilla/5.0"}
    for i in range(retry):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.text
        except:
            print(f"重试 {i+1} 失败: {url}")
    print(f"跳过: {url}")
    return ""

# ===================== 解析 =====================

def parse_name(extinf):
    return extinf.split(",", 1)[-1].strip()

def parse_group(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""

def parse_m3u(content):
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

def parse_txt(content):
    data = []
    for l in content.splitlines():
        if "," in l and "http" in l:
            name, url = l.split(",", 1)
            if not any(x in name for x in BAD_KEYWORDS):
                ext = f'#EXTINF:-1 group-title="未知",{name.strip()}'
                data.append((name.strip(), ext, url.strip()))
    return data

def load_extra():
    all_data = []
    for url in EXTRA_URLS:
        print("抓取:", url)
        raw = download(url)
        if not raw:
            continue
        try:
            if "#EXTINF" in raw:
                all_data += parse_m3u(raw)
            else:
                all_data += parse_txt(raw)
        except:
            print("解析失败:", url)
    return all_data

# ===================== ⭐ CHC 专用（新增） =====================

def load_chc_from_shanghai():
    url = "https://github.chenc.dev/raw.githubusercontent.com/CKL1211/eric/refs/heads/master/MyIPTV.m3u"
    raw = download(url)
    data = parse_m3u(raw)

    result = []

    for n, e, u in data:
        if parse_group(e) != "上海":
            continue

        m = re.search(r'tvg-name="([^"]+)"', e)
        if not m:
            continue

        tvg_name = m.group(1).strip()

        if tvg_name in CHC_TARGET:
            result.append((tvg_name, e, u))

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
    if extinf is None:
        return ""  # 如果 extinf 是 None，则返回一个空字符串
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"')

# ===================== 并发测速 =====================

def check(url):
    try:
        start = time.time()
        r = requests.get(url, timeout=5, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return url, time.time() - start
    except:
        pass
    return url, 999

def pick_best(urls):
    best_url, best_time = None, 999
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check, u) for u in urls]
        for f in as_completed(futures):
            url, t = f.result()
            if t < best_time:
                best_time, best_url = t, url
    return best_url

# ===================== 主程序 =====================

def main():
    print("主源...")
    main_data = parse_m3u(download(SOURCE_URL))

    print("TW...")
    tw_data = parse_m3u(download(TW_M3U_URL))

    print("扩展源...")
    extra_data = load_extra()

    hk = dedup([x for x in main_data if HK_SOURCE_GROUP in x[1]])
    tw = dedup(tw_data)

    # 央视
    cctv_map = {}
    for n, e, u in extra_data:
        if n in CCTV_TARGET:
            cctv_map.setdefault(n, []).append((e, u))

    cctv = []
    for name in CCTV_TARGET:
        if name in cctv_map:
            best = pick_best([u for _, u in cctv_map[name]])
            ext = cctv_map[name][0][0]
            cctv.append((name, ext, best))

    # ⭐ CHC（只从上海源）
    chc_raw = load_chc_from_shanghai()

    chc_map = {}
    for n, e, u in chc_raw:
        chc_map.setdefault(n, []).append((e, u))

    chc = []
    for name in CHC_TARGET:
        if name in chc_map:
            best = pick_best([u for _, u in chc_map[name]])
            ext = chc_map[name][0][0]
            chc.append((name, ext, best))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out = "#EXTM3U\n\n"
    out += f"# 更新时间 {now}\n\n"

    # 读取BB.m3u并去除末尾多余空行
    try:
        with open(BB_FILE, encoding="utf-8") as f:
            bb_lines = f.readlines()
            # 跳过第一行 #EXTM3U
            for i, l in enumerate(bb_lines):
                if not l.startswith("#EXTM3U"):
                    out += l
            # 去除末尾连续的空行
            out = out.rstrip('\n')
            out += '\n'
    except:
        pass

    out += "# 数字\n"
    for n, e, u in cctv:
        out += (set_group(e, "数字") or "") + "\n" + (u or "") + "\n"

    out += "\n# CHC\n"
    for n, e, u in chc:
        e = fix_logo(n, e)
        out += (set_group(e, "CHC") or "") + "\n" + (u or "") + "\n"

    out += "\n# HK\n"
    for n, e, u in hk:
        out += (set_group(e, "HK") or "") + "\n" + (u or "") + "\n"

    out += "\n# TW\n"
    for n, e, u in tw:
        out += (set_group(e, "TW") or "") + "\n" + (u or "") + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成")

if __name__ == "__main__":
    main()
