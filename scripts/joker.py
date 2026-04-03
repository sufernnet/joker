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
- 额外抓取：
  1) 央视频道（世界地理~央视台球，原逻辑不动）
  2) 从指定源直接提取 CHC/淘系/萌宠TV 频道，放入新建 CHC 分组
- 插入到 BB.m3u 的央视分组最后面（仅央视数字频道）
- 输出 joker.m3u（输出到仓库根目录）
- 保留 tvg-id / tvg-name / tvg-logo
"""

import os
import re
import time
import asyncio
import aiohttp
import requests
from datetime import datetime

# ===================== 路径配置 =====================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))   # jokerone/scripts
ROOT_DIR = os.path.dirname(SCRIPT_DIR)                    # jokerone

SOURCE_URL = "https://yang.sufern001.workers.dev/"
TW_M3U_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/TW.m3u"

OUTPUT_FILE = os.path.join(ROOT_DIR, "joker.m3u")
BB_FILE = os.path.join(ROOT_DIR, "BB.m3u")

HK_SOURCE_GROUP = "• Juli 「精選」"

# 单独提取 CHC 的源
CHC_DIRECT_SOURCE = "https://live.45678888.xyz/sub?kbQyhXwA=m3u"

# ===================== 精准剔除 YouTube ID =====================

REMOVE_YT_IDS = [
    "fN9uYWCjQaw",
    "7j92Myu2wzg",
    "f6Kq93wnaZ8",
    "BOy2xDU1LC8",
    "vr3XyVCR4T0",
    "o_-hSMgpAzs",
]

# ===================== 央视频道目标 =====================

TARGET_CCTV = {
    "CCTV世界地理",
    "CCTV兵器科技",
    "CCTV女性时尚",
    "CCTV怀旧剧场",
    "CCTV文化精品",
    "CCTV第一剧场",
    "CCTV风云足球",
    "CCTV风云音乐",
    "CCTV央视台球"
}

TARGET_CCTV_ORDER = [
    "CCTV世界地理",
    "CCTV兵器科技",
    "CCTV女性时尚",
    "CCTV怀旧剧场",
    "CCTV文化精品",
    "CCTV第一剧场",
    "CCTV风云足球",
    "CCTV风云音乐",
    "CCTV央视台球"
]

# ===================== CHC 分组直提目标 =====================

TARGET_DIRECT_CHC_ORDER = [
    "CHC动作电影",
    "CHC高清电影",
    "CHC家庭影院",
    "CHC影迷电影",
    "淘电影",
    "淘剧场",
    "淘娱乐",
    "萌宠TV",
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


def replace_name_in_extinf(extinf_line, new_name):
    """
    替换 #EXTINF 行逗号后的显示名称
    """
    if "," in extinf_line:
        return extinf_line.split(",", 1)[0] + "," + new_name
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

        elif line.startswith(("http://", "https://")):
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


def normalize_name_for_match(name):
    n = (name or "").strip().lower()
    n = n.replace(" ", "").replace("-", "").replace("_", "")
    n = n.replace("（", "(").replace("）", ")")
    n = n.replace("高清", "").replace("标清", "").replace("频道", "")
    n = n.replace("hd", "").replace("sd", "")
    return n


def match_target(name):
    """
    仅用于央视数字频道匹配（原逻辑保留）
    """
    n = normalize_name_for_match(name)

    cctv_alias_map = {
        "CCTV世界地理": ["cctv世界地理", "世界地理", "央视世界地理"],
        "CCTV兵器科技": ["cctv兵器科技", "央视兵器科技", "兵器科技", "cctv兵器", "兵器"],
        "CCTV女性时尚": ["cctv女性时尚", "女性时尚", "央视女性时尚"],
        "CCTV怀旧剧场": ["cctv怀旧剧场", "怀旧剧场", "央视怀旧剧场"],
        "CCTV文化精品": ["cctv文化精品", "文化精品", "央视文化精品"],
        "CCTV第一剧场": ["cctv第一剧场", "第一剧场", "央视第一剧场"],
        "CCTV风云足球": ["cctv风云足球", "风云足球", "央视风云足球"],
        "CCTV风云音乐": ["cctv风云音乐", "风云音乐", "央视风云音乐"],
        "CCTV央视台球": ["cctv央视台球", "央视台球", "台球"],
    }

    for std_name, aliases in cctv_alias_map.items():
        for alias in aliases:
            if normalize_name_for_match(alias) in n:
                return std_name

    return None


def match_direct_chc(name):
    """
    单独用于从 CHC_DIRECT_SOURCE 直接提取 CHC / 淘系 / 萌宠TV
    """
    n = normalize_name_for_match(name)

    alias_map = {
        "CHC动作电影": ["chc动作电影", "动作电影", "chc动作", "动作电影hd", "chc动作电影hd"],
        "CHC高清电影": ["chc高清电影", "高清电影", "chc高清", "高清电影hd", "chc高清电影hd"],
        "CHC家庭影院": ["chc家庭影院", "家庭影院", "家庭影院hd", "chc家庭影院hd"],
        "CHC影迷电影": ["chc影迷电影", "影迷电影", "影迷电影hd", "chc影迷电影hd"],
        "淘电影": ["淘电影"],
        "淘剧场": ["淘剧场"],
        "淘娱乐": ["淘娱乐"],
        "萌宠TV": ["萌宠tv", "萌宠tvhd", "萌宠"],
    }

    for std_name, aliases in alias_map.items():
        for alias in aliases:
            if normalize_name_for_match(alias) in n:
                return std_name

    return None


def is_cctv_group(group_name):
    g = (group_name or "").strip().lower()
    return any(x in g for x in ["央视", "cctv", "央视频道"])


def normalize_cctv_display_name(name):
    """
    把抓取到的频道名转换成标准输出名
    """
    mapping = {
        "CCTV世界地理": "世界地理",
        "CCTV央视台球": "央视台球",
        "CCTV女性时尚": "女性时尚",
        "CCTV怀旧剧场": "怀旧剧场",
        "CCTV文化精品": "文化精品",
        "CCTV第一剧场": "第一剧场",
        "CCTV风云足球": "风云足球",
        "CCTV风云音乐": "风云音乐",
        "CCTV兵器科技": "兵器科技",
    }
    return mapping.get(name, name.replace("CCTV", "").strip())


def normalize_direct_chc_display_name(name):
    mapping = {
        "CHC动作电影": "动作电影",
        "CHC高清电影": "高清电影",
        "CHC家庭影院": "家庭影院",
        "CHC影迷电影": "影迷电影",
        "淘电影": "淘电影",
        "淘剧场": "淘剧场",
        "淘娱乐": "淘娱乐",
        "萌宠TV": "萌宠TV",
    }
    return mapping.get(name, name)


def build_cctv_extinf(name, group_name="央视"):
    std_name = normalize_cctv_display_name(name)
    logo_url = f"https://raw.githubusercontent.com/xiasufern/AA/main/icon/{std_name}.png"
    return (
        f'#EXTINF:-1 '
        f'tvg-id="{std_name}" '
        f'tvg-name="{std_name}" '
        f'tvg-logo="{logo_url}" '
        f'group-title="{group_name}",{std_name}'
    )


def build_direct_chc_extinf(name, old_extinf=None):
    """
    CHC 分组统一标准化输出
    """
    std_name = normalize_direct_chc_display_name(name)
    logo_url = f"https://raw.githubusercontent.com/xiasufern/AA/main/icon/{std_name}.png"

    if old_extinf:
        extinf = normalize_group(old_extinf, "CHC")
        extinf = replace_name_in_extinf(extinf, std_name)

        # 替换或补充 tvg-id / tvg-name / tvg-logo
        if 'tvg-id="' in extinf:
            extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{std_name}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-id="{std_name}"', 1)

        if 'tvg-name="' in extinf:
            extinf = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{std_name}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-name="{std_name}"', 1)

        if 'tvg-logo="' in extinf:
            extinf = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo_url}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{logo_url}"', 1)

        return extinf

    return (
        f'#EXTINF:-1 '
        f'tvg-id="{std_name}" '
        f'tvg-name="{std_name}" '
        f'tvg-logo="{logo_url}" '
        f'group-title="CHC",{std_name}'
    )


# ===================== 抓取与测速逻辑（央视数字频道） =====================

async def test_stream(session, url):
    start = time.time()
    try:
        async with session.get(url, timeout=TEST_TIMEOUT) as r:
            if r.status in (200, 206):
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
    """
    原有 CCTV 世界地理~央视台球 抓取逻辑，不动
    """
    all_valid = []

    for s in CCTV_SOURCES:
        is_m3u = s.endswith((".m3u", ".m3u8")) or "m3u" in s.lower()
        print(f"抓取目标频道源: {s}")
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

    result = []

    for name in TARGET_CCTV_ORDER:
        if name in best_map:
            result.append((name, best_map[name][0]))

    print("已获取到的央视数字频道数量:", len(result))
    return result


# ===================== 直接提取 CHC 分组 =====================

def fetch_direct_chc_channels():
    """
    直接从 CHC_DIRECT_SOURCE 解析目标频道，不测速，不改原央视逻辑
    返回：
    [
      (std_name, extinf, url),
      ...
    ]
    """
    print("直接提取 CHC 分组源:", CHC_DIRECT_SOURCE)
    content = download(CHC_DIRECT_SOURCE)
    channels = parse_m3u_full(content)

    best_map = {}

    for name, extinf, url in channels:
        key = match_direct_chc(name)
        if not key:
            continue

        if key not in best_map:
            best_map[key] = (key, extinf, url)

    result = []
    for name in TARGET_DIRECT_CHC_ORDER:
        if name in best_map:
            result.append(best_map[name])

    print("已直接提取到的 CHC 分组频道数量:", len(result))
    return result


# ===================== 把央视数字频道插入 BB 的央视分组最后 =====================

def append_cctv_channels_to_bb(bb_content, extra_channels):
    """
    extra_channels: [(name, url), ...]
    插入到 BB.m3u 里央视分组的最后面
    """
    if not extra_channels:
        return bb_content

    lines = bb_content.splitlines()
    output_lines = []

    current_group = None
    last_cctv_insert_pos = None
    existing_names = set()

    for line in lines:
        raw = line.rstrip("\n")
        output_lines.append(raw)

        s = raw.strip()
        if s.startswith("#EXTINF"):
            current_group = parse_group_from_extinf(s)
            name = parse_name_from_extinf(s)
            if name:
                existing_names.add(name.strip())

        elif s.startswith("http"):
            if is_cctv_group(current_group):
                last_cctv_insert_pos = len(output_lines)

    insert_lines = []
    existing_std_names = set()

    for n in existing_names:
        existing_std_names.add(n.strip())
        existing_std_names.add(normalize_cctv_display_name(n))

    for name, url in extra_channels:
        std_name = normalize_cctv_display_name(name)

        if name in existing_names or std_name in existing_std_names:
            continue

        insert_lines.append(build_cctv_extinf(name, "央视"))
        insert_lines.append(url)

    if not insert_lines:
        return "\n".join(output_lines) + "\n"

    if last_cctv_insert_pos is not None:
        new_lines = (
            output_lines[:last_cctv_insert_pos] +
            insert_lines +
            output_lines[last_cctv_insert_pos:]
        )
        return "\n".join(new_lines) + "\n"

    if output_lines and output_lines[-1].strip():
        output_lines.append("")
    output_lines.extend(insert_lines)
    return "\n".join(output_lines) + "\n"


# ===================== 主程序 =====================

def main():
    print("当前工作目录:", os.getcwd())
    print("脚本目录:", SCRIPT_DIR)
    print("仓库根目录:", ROOT_DIR)
    print("输出文件:", OUTPUT_FILE)
    print("BB文件:", BB_FILE)

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

    # 抓取央视数字频道（原逻辑）
    extra_cctv_channels = asyncio.run(fetch_best_cctv_channels())

    # 直接提取 CHC 分组
    direct_chc_channels = fetch_direct_chc_channels()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = '#EXTM3U\n\n'
    output += f"# joker.m3u\n# 生成时间: {timestamp}\n\n"

    # 合并 BB，并把央视数字频道插入 BB 的央视分组最后
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            bb_content = f.read()

        bb_content = re.sub(r'^\s*#EXTM3U\s*', '', bb_content, flags=re.I)
        bb_content = append_cctv_channels_to_bb(bb_content, extra_cctv_channels)

        output += bb_content.rstrip() + "\n\n"
        print("已合并 BB.m3u，并插入央视数字频道")
    except Exception as e:
        print("未找到或无法读取 BB.m3u，跳过：", e)

    # 新建 CHC 分组
    if direct_chc_channels:
        output += "# CHC\n"
        for name, extinf, url in direct_chc_channels:
            output += build_direct_chc_extinf(name, extinf) + "\n"
            output += url + "\n"
        output += "\n"

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

    print("文件已写出:", OUTPUT_FILE)
    print("文件是否存在:", os.path.exists(OUTPUT_FILE))
    if os.path.exists(OUTPUT_FILE):
        print("文件大小:", os.path.getsize(OUTPUT_FILE), "bytes")

    print("✅ joker.m3u 生成完成")


if __name__ == "__main__":
    main()
