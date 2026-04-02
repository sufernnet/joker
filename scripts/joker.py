#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gather IPTV Generator
功能：
- 下载源 M3U
- 提取 HK
- 合并远程 TW.m3u
- 剔除指定 YouTube 源
- 去重
- 合并 BB.m3u
- 额外抓取 8 个央视频道，插入到 BB.m3u 的央视分组最后面
- 输出 joker.m3u
- 保留 tvg-id / tvg-name / tvg-logo
"""

import requests
import re
import asyncio
import aiohttp
import time
from datetime import datetime

# ===================== 基础配置 =====================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"
OUTPUT_FILE = "joker.m3u"
BB_FILE = "BB.m3u"

HK_SOURCE_GROUP = "• Juli 「精選」"

# ===================== 精准剔除 YouTube ID =====================

REMOVE_YT_IDS = [
    "fN9uYWCjQaw",
    "7j92Myu2wzg",
    "f6Kq93wnaZ8",
    "BOy2xDU1LC8",
    "vr3XyVCR4T0",
    "o_-hSMgpAzs",
]

# ===================== 仅保留的 8 个 CCTV 频道 =====================

TARGET_CCTV = {
    "CCTV世界地理",
    "CCTV央视台球",
    "CCTV女性时尚",
    "CCTV怀旧剧场",
    "CCTV文化精品",
    "CCTV第一剧场",
    "CCTV风云足球",
    "CCTV兵器科技"
}

CCTV_SOURCES = [
    "https://tzdr.com/iptv.txt",
    "https://live.kilvn.com/iptv.m3u",
    "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "http://175.178.251.183:6689/live.m3u",
    "https://m3u.ibert.me/ycl_iptv.m3u"
]

TEST_TIMEOUT = 10

# ===================== 工具函数 =====================

def download(url):
    r = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    r.raise_for_status()
    return r.text


def is_bad_youtube(url):
    for yt_id in REMOVE_YT_IDS:
        if yt_id in url:
            return True
    return False


def deduplicate(channels):
    """
    channels: [(name, extinf, url), ...]
    按 url 去重
    """
    seen = set()
    result = []
    for name, extinf, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, extinf, url))
    return result


def normalize_group(extinf_line, new_group):
    """
    把 #EXTINF 行里的 group-title 改成指定分组
    若没有 group-title，则补上
    """
    if 'group-title="' in extinf_line:
        extinf_line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group}"', extinf_line)
    else:
        if extinf_line.startswith("#EXTINF:-1 "):
            extinf_line = extinf_line.replace("#EXTINF:-1 ", f'#EXTINF:-1 group-title="{new_group}" ', 1)
        elif extinf_line.startswith("#EXTINF:-1"):
            extinf_line = extinf_line.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{new_group}"', 1)
    return extinf_line


def parse_name_from_extinf(extinf_line):
    if "," in extinf_line:
        return extinf_line.split(",", 1)[1].strip()
    return ""


def parse_group_from_extinf(extinf_line):
    m = re.search(r'group-title="([^"]*)"', extinf_line)
    return m.group(1).strip() if m else ""


def parse_m3u_full(content):
    """
    返回:
    [
        (name, extinf, url),
        ...
    ]
    """
    lines = content.splitlines()
    channels = []

    current_extinf = None
    current_name = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_extinf = line
            current_name = parse_name_from_extinf(line)

        elif line.startswith("http"):
            if current_extinf and current_name:
                channels.append((current_name, current_extinf, line))

    return channels


def contains_date(text):
    return re.search(r"\d{4}-\d{2}-\d{2}", text or "") is not None


def extract_urls_from_txt(content):
    urls = []
    for line in content.splitlines():
        line = line.strip()
        if line and ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                urls.append((parts[0].strip(), parts[1].strip()))
    return urls


def extract_urls_from_m3u(content):
    urls = []
    lines = content.splitlines()
    channel = "Unknown"

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            parts = line.split(',', 1)
            channel = parts[1].strip() if len(parts) > 1 else "Unknown"
        elif line.startswith(('http://', 'https://')):
            urls.append((channel, line))
    return urls


def match_target(name):
    for k in TARGET_CCTV:
        if k in name:
            return k
    return None


def is_cctv_group(group_name):
    g = (group_name or "").strip().lower()
    return any(x in g for x in ["央视", "cctv", "央视频道"])


# ===================== 8 个央视频道抓取逻辑 =====================

async def test_stream(session, url):
    start = time.time()
    try:
        async with session.get(url, timeout=TEST_TIMEOUT) as r:
            if r.status == 200:
                return True, time.time() - start
    except:
        pass
    return False, None


async def read_and_test_file(url, is_m3u):
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as r:
                content = await r.text()

            entries = extract_urls_from_m3u(content) if is_m3u else extract_urls_from_txt(content)

            tasks = [test_stream(session, u) for _, u in entries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid = []
            for result, (ch, u) in zip(results, entries):
                if isinstance(result, Exception):
                    continue
                ok, t = result
                if ok:
                    valid.append((ch, u, t))

            return valid
    except:
        return []


async def fetch_best_cctv_channels():
    all_valid = []

    for s in CCTV_SOURCES:
        is_m3u = s.endswith((".m3u", ".m3u8"))
        print(f"抓取8个央视频道源: {s}")
        data = await read_and_test_file(s, is_m3u)
        all_valid.extend(data)

    best_map = {}

    for ch, url, latency in all_valid:
        if contains_date(ch) or contains_date(url):
            continue

        key = match_target(ch)
        if not key:
            continue

        if key not in best_map or latency < best_map[key][1]:
            best_map[key] = (url, latency)

    # 固定顺序输出
    order = [
        "CCTV世界地理",
        "CCTV央视台球",
        "CCTV女性时尚",
        "CCTV怀旧剧场",
        "CCTV文化精品",
        "CCTV第一剧场",
        "CCTV风云足球",
        "CCTV兵器科技"
    ]

    result = []
    for name in order:
        if name in best_map:
            result.append((name, best_map[name][0]))

    print("已获取到的8个央视频道数量:", len(result))
    return result


# ===================== 把 8 个频道插入 BB 的央视分组最后 =====================

def append_cctv_channels_to_bb(bb_content, extra_channels):
    """
    extra_channels: [(name, url), ...]
    插入到 BB.m3u 里央视分组的最后面
    """
    if not extra_channels:
        return bb_content

    lines = bb_content.splitlines()
    output_lines = []

    current_extinf = None
    current_group = None
    last_cctv_insert_pos = None
    detected_cctv_group_name = "央视频道"

    existing_names = set()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        output_lines.append(line)

        if line.strip().startswith("#EXTINF"):
            current_extinf = line.strip()
            current_group = parse_group_from_extinf(current_extinf)
            name = parse_name_from_extinf(current_extinf)
            if name:
                existing_names.add(name)

        elif line.strip().startswith("http"):
            if is_cctv_group(current_group):
                last_cctv_insert_pos = len(output_lines)
                if current_group:
                    detected_cctv_group_name = current_group

        i += 1

    # 构造要插入的频道
    insert_lines = []
    for name, url in extra_channels:
        if name in existing_names:
            continue
        insert_lines.append(f'#EXTINF:-1 group-title="{detected_cctv_group_name}",{name}')
        insert_lines.append(url)

    if not insert_lines:
        return "\n".join(output_lines) + "\n"

    # 如果找到了央视分组最后一个频道，就插入那里后面
    if last_cctv_insert_pos is not None:
        new_lines = (
            output_lines[:last_cctv_insert_pos] +
            insert_lines +
            output_lines[last_cctv_insert_pos:]
        )
        return "\n".join(new_lines) + "\n"

    # 如果 BB.m3u 里压根没找到央视分组，就追加到末尾
    if output_lines and output_lines[-1].strip():
        output_lines.append("")
    output_lines.extend(insert_lines)
    return "\n".join(output_lines) + "\n"


# ===================== 主程序 =====================

def main():
    print("下载源...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    hk_channels = []
    current_group = None
    current_name = None
    current_extinf = None

    # 解析 HK
    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_extinf = line

            if 'group-title="' in line:
                current_group = line.split('group-title="')[1].split('"')[0]
            else:
                current_group = None

            current_name = parse_name_from_extinf(line)

        elif line.startswith("http"):
            url = line.strip()

            if not current_group or not current_name or not current_extinf:
                continue

            if current_group == HK_SOURCE_GROUP:
                if is_bad_youtube(url):
                    continue
                hk_channels.append((current_name, current_extinf, url))

    # 解析 TW
    print("下载 TW.m3u...")
    tw_content = download(TW_M3U_URL)
    tw_channels = parse_m3u_full(tw_content)

    # 去重
    hk_channels = deduplicate(hk_channels)
    tw_channels = deduplicate(tw_channels)

    print("HK:", len(hk_channels))
    print("TW:", len(tw_channels))

    # 抓取 8 个央视频道
    extra_cctv_channels = asyncio.run(fetch_best_cctv_channels())

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = '#EXTM3U\n\n'
    output += f"# joker.m3u\n# 生成时间: {timestamp}\n\n"

    # 合并 BB，并把 8 个央视频道插入 BB 的央视分组最后
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            bb_content = f.read()

        bb_content = re.sub(r'^\s*#EXTM3U\s*', '', bb_content, flags=re.I)
        bb_content = append_cctv_channels_to_bb(bb_content, extra_cctv_channels)

        output += bb_content.rstrip() + "\n\n"
        print("已合并 BB.m3u，并插入8个央视频道")
    except:
        print("未找到 BB.m3u，跳过")

    # HK
    if hk_channels:
        output += "# HK\n"
        for name, extinf, url in hk_channels:
            output += normalize_group(extinf, "HK") + "\n"
            output += url + "\n"

    # TW
    if tw_channels:
        output += "\n# TW\n"
        for name, extinf, url in tw_channels:
            output += normalize_group(extinf, "TW") + "\n"
            output += url + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ joker.m3u 生成完成")


if __name__ == "__main__":
    main()
