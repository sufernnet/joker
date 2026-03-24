#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
from datetime import datetime

# ===================== 配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/4TV.m3u"
OUTPUT_FILE = "EE.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

# ===================== HK 关键词优先级 =====================

HK_PRIORITY = [
    ["凤凰", "中文"],
    ["凤凰", "资讯"],
    ["凤凰", "香港"],

    ["now"],
    ["viu"],
    ["tvb"],
]

# ===================== 工具 =====================

def download(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text


def normalize(text):
    return text.lower().replace("鳳", "凤").replace("臺", "台")


def contains_keywords(name, keys):
    name = normalize(name)
    return all(k in name for k in keys)


def clean_name(name):
    return re.sub(r'\s*(HD|1080p|720p|4K).*$', '', name, flags=re.I).strip()


def deduplicate(channels):
    seen, result = set(), []
    for name, extinf, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, extinf, url))
    return result


def normalize_group(extinf, group):
    extinf = extinf.strip()
    if 'group-title="' in extinf:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
    return extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"', 1)


def parse_name(extinf):
    return extinf.split(",", 1)[1].strip() if "," in extinf else ""


def parse_m3u(content):
    lines = content.splitlines()
    res, extinf, name = [], None, None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            extinf = line
            name = parse_name(line)

        elif line.startswith("http") and extinf and name:
            res.append((name, extinf, line))

    return res


def append_channel(out, extinf, url, group):
    return out + normalize_group(extinf, group) + "\n" + url.strip() + "\n"


# ===================== HK 排序 =====================

def sort_hk(channels):

    def key(x):
        name = clean_name(x[0])

        for i, keys in enumerate(HK_PRIORITY):
            if contains_keywords(name, keys):
                return (0, i)

        return (1, name)

    return sorted(channels, key=key)


# ===================== TW 分类 =====================

def classify_tw(name):
    name = normalize(name)

    if any(k in name for k in ["新闻", "news"]):
        return "TW-新闻"
    if any(k in name for k in ["体育", "sport"]):
        return "TW-体育"
    if any(k in name for k in ["电影", "影", "movie"]):
        return "TW-电影"
    return "TW-其他"


# ===================== 主程序 =====================

def main():
    print("下载 HK...")
    content = download(SOURCE_URL)

    hk = []
    group = name = extinf = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            extinf = line
            name = parse_name(line)
            group = line.split('group-title="')[1].split('"')[0] if 'group-title="' in line else None

        elif line.startswith("http") and group == HK_SOURCE_GROUP:
            hk.append((name, extinf, line))

    print("下载 TW...")
    tw = parse_m3u(download(TW_M3U_URL))

    hk = sort_hk(deduplicate(hk))
    tw = deduplicate(tw)

    print("HK:", len(hk), "TW:", len(tw))

    out = "#EXTM3U\n\n"
    out += f"# Generated: {datetime.now()}\n\n"

    # ================= BB =================
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            for l in f:
                if not l.startswith("#EXTM3U"):
                    out += l.strip() + "\n"
        out += "\n"
    except:
        print("⚠️ BB.m3u 不存在")

    # ================= HK =================
    out += "# HK\n"
    for n, e, u in hk:
        out = append_channel(out, e, u, "HK")

    # ================= TW（分类） =================
    tw_groups = {}

    for n, e, u in tw:
        g = classify_tw(n)
        tw_groups.setdefault(g, []).append((n, e, u))

    for g, items in tw_groups.items():
        out += f"\n# {g}\n"
        for n, e, u in items:
            out = append_channel(out, e, u, g)

    # 清理多余空行
    out = re.sub(r'\n{3,}', '\n\n', out)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)

    print("✅ 完成:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
