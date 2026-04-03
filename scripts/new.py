#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import asyncio
import aiohttp
from urllib.parse import urljoin
from datetime import datetime

OUTPUT_FILE = "new.m3u"
TEST_TIMEOUT = 10
PLAYLIST_TIMEOUT = 8
SEGMENT_TIMEOUT = 8
LOGO_BASE = "https://raw.githubusercontent.com/xiasufern/AA/main/icon/"
SAT_LOGO_BASE = "http://epg.51zmt.top:8000/tb1/ws/"
BLOCKED_SOURCE_KEYWORDS = ["iptv.catvod.com"]

SOURCES = [
    "https://tzdr.com/iptv.txt",
    "https://live.kilvn.com/iptv.m3u",
    "https://cdn.jsdelivr.net/gh/Guovin/iptv-api@gd/output/result.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "http://175.178.251.183:6689/live.m3u",
    "https://m3u.ibert.me/ycl_iptv.m3u"
]

CCTV_ORDER = [
    "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7",
    "CCTV8", "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13",
    "CCTV14", "CCTV15", "CCTV16", "CCTV17"
]
SAT_ORDER = [
    "北京卫视", "天津卫视", "河北卫视", "山西卫视", "内蒙古卫视", "辽宁卫视", "吉林卫视",
    "黑龙江卫视", "东方卫视", "江苏卫视", "浙江卫视", "安徽卫视", "东南卫视", "江西卫视",
    "山东卫视", "河南卫视", "湖北卫视", "湖南卫视", "广东卫视", "深圳卫视", "广西卫视",
    "海南卫视", "重庆卫视", "四川卫视", "贵州卫视", "云南卫视", "西藏卫视", "陕西卫视",
    "甘肃卫视", "青海卫视", "宁夏卫视", "新疆卫视", "兵团卫视"
]
FOURK_ORDER = ["浙江卫视4K","江苏卫视4K","深圳卫视4K","东方卫视4K","四川卫视4K","湖南卫视4K","广东卫视4K","山东卫视4K","北京卫视4K"]
CHC_ORDER = ["动作电影","高清电影","家庭电影","家庭影院","影迷电影"]
DIGITAL_ORDER = ["世界地理","第一剧场","怀旧剧场","风云足球","风云音乐","风云剧场","央视台球","女性时尚","文化精品","兵器科技"]
HK_ORDER = ["凤凰中文","凤凰资讯","凤凰香港"]

OUTPUT_ORDER = CCTV_ORDER + SAT_ORDER + FOURK_ORDER + CHC_ORDER + DIGITAL_ORDER + HK_ORDER
MATCH_ORDER = FOURK_ORDER + CCTV_ORDER[::-1] + CHC_ORDER + DIGITAL_ORDER + HK_ORDER + SAT_ORDER

CHANNEL_SPECS = {
    "CCTV1":{"group":"央视","aliases":["cctv1","cctv-1","央视1","中央1","中央一台","央视综合"]},
    "CCTV2":{"group":"央视","aliases":["cctv2","cctv-2","央视2","中央2","央视财经"]},
    "CCTV3":{"group":"央视","aliases":["cctv3","cctv-3","央视3","中央3","央视综艺"]},
    "CCTV4":{"group":"央视","aliases":["cctv4","cctv-4","央视4","中央4","中文国际"]},
    "CCTV5":{"group":"央视","aliases":["cctv5","cctv-5","央视5","中央5","央视体育"]},
    "CCTV5+":{"group":"央视","aliases":["cctv5+","cctv-5+","cctv5plus","央视5+","体育赛事","央视体育赛事"]},
    "CCTV6":{"group":"央视","aliases":["cctv6","cctv-6","央视6","中央6","央视电影","电影频道"]},
    "CCTV7":{"group":"央视","aliases":["cctv7","cctv-7","央视7","中央7","国防军事","军事农业"]},
    "CCTV8":{"group":"央视","aliases":["cctv8","cctv-8","央视8","中央8","央视电视剧"]},
    "CCTV9":{"group":"央视","aliases":["cctv9","cctv-9","央视9","中央9","纪录频道"]},
    "CCTV10":{"group":"央视","aliases":["cctv10","cctv-10","央视10","中央10","科教频道"]},
    "CCTV11":{"group":"央视","aliases":["cctv11","cctv-11","央视11","中央11","戏曲频道"]},
    "CCTV12":{"group":"央视","aliases":["cctv12","cctv-12","央视12","中央12","社会与法"]},
    "CCTV13":{"group":"央视","aliases":["cctv13","cctv-13","央视13","中央13","央视新闻","新闻频道"]},
    "CCTV14":{"group":"央视","aliases":["cctv14","cctv-14","央视14","中央14","少儿频道"]},
    "CCTV15":{"group":"央视","aliases":["cctv15","cctv-15","央视15","中央15","音乐频道"]},
    "CCTV16":{"group":"央视","aliases":["cctv16","cctv-16","央视16","中央16","奥林匹克"]},
    "CCTV17":{"group":"央视","aliases":["cctv17","cctv-17","央视17","中央17","农业农村"]},

    "北京卫视":{"group":"卫视","aliases":["北京卫视"]},
    "天津卫视":{"group":"卫视","aliases":["天津卫视"]},
    "河北卫视":{"group":"卫视","aliases":["河北卫视"]},
    "山西卫视":{"group":"卫视","aliases":["山西卫视"]},
    "内蒙古卫视":{"group":"卫视","aliases":["内蒙古卫视","nmg卫视"]},
    "辽宁卫视":{"group":"卫视","aliases":["辽宁卫视"]},
    "吉林卫视":{"group":"卫视","aliases":["吉林卫视"]},
    "黑龙江卫视":{"group":"卫视","aliases":["黑龙江卫视"]},
    "东方卫视":{"group":"卫视","aliases":["东方卫视","上海东方卫视"]},
    "江苏卫视":{"group":"卫视","aliases":["江苏卫视"]},
    "浙江卫视":{"group":"卫视","aliases":["浙江卫视"]},
    "安徽卫视":{"group":"卫视","aliases":["安徽卫视"]},
    "东南卫视":{"group":"卫视","aliases":["东南卫视","福建东南卫视"]},
    "江西卫视":{"group":"卫视","aliases":["江西卫视"]},
    "山东卫视":{"group":"卫视","aliases":["山东卫视"]},
    "河南卫视":{"group":"卫视","aliases":["河南卫视"]},
    "湖北卫视":{"group":"卫视","aliases":["湖北卫视"]},
    "湖南卫视":{"group":"卫视","aliases":["湖南卫视"]},
    "广东卫视":{"group":"卫视","aliases":["广东卫视"]},
    "深圳卫视":{"group":"卫视","aliases":["深圳卫视"]},
    "广西卫视":{"group":"卫视","aliases":["广西卫视"]},
    "海南卫视":{"group":"卫视","aliases":["海南卫视"]},
    "重庆卫视":{"group":"卫视","aliases":["重庆卫视"]},
    "四川卫视":{"group":"卫视","aliases":["四川卫视"]},
    "贵州卫视":{"group":"卫视","aliases":["贵州卫视"]},
    "云南卫视":{"group":"卫视","aliases":["云南卫视"]},
    "西藏卫视":{"group":"卫视","aliases":["西藏卫视"]},
    "陕西卫视":{"group":"卫视","aliases":["陕西卫视"]},
    "甘肃卫视":{"group":"卫视","aliases":["甘肃卫视"]},
    "青海卫视":{"group":"卫视","aliases":["青海卫视"]},
    "宁夏卫视":{"group":"卫视","aliases":["宁夏卫视"]},
    "新疆卫视":{"group":"卫视","aliases":["新疆卫视"]},
    "兵团卫视":{"group":"卫视","aliases":["兵团卫视"]},

    "浙江卫视4K":{"group":"4K","aliases":["浙江卫视4k","浙江4k"]},
    "江苏卫视4K":{"group":"4K","aliases":["江苏卫视4k","江苏4k"]},
    "深圳卫视4K":{"group":"4K","aliases":["深圳卫视4k","深圳4k"]},
    "东方卫视4K":{"group":"4K","aliases":["东方卫视4k","东方4k","上海东方卫视4k"]},
    "四川卫视4K":{"group":"4K","aliases":["四川卫视4k","四川4k"]},
    "湖南卫视4K":{"group":"4K","aliases":["湖南卫视4k","湖南4k"]},
    "广东卫视4K":{"group":"4K","aliases":["广东卫视4k","广东4k"]},
    "山东卫视4K":{"group":"4K","aliases":["山东卫视4k","山东4k"]},
    "北京卫视4K":{"group":"4K","aliases":["北京卫视4k","北京4k"]},

    "动作电影":{"group":"电影","aliases":["chc动作电影","动作电影","chc动作"]},
    "高清电影":{"group":"电影","aliases":["chc高清电影","高清电影","chc高清"]},
    "家庭电影":{"group":"电影","aliases":["chc家庭电影","家庭电影"]},
    "家庭影院":{"group":"电影","aliases":["chc家庭影院","家庭影院"]},
    "影迷电影":{"group":"电影","aliases":["chc影迷电影","影迷电影"]},

    "世界地理":{"group":"数字","aliases":["cctv世界地理","世界地理","央视世界地理"]},
    "第一剧场":{"group":"数字","aliases":["cctv第一剧场","第一剧场","央视第一剧场"]},
    "怀旧剧场":{"group":"数字","aliases":["cctv怀旧剧场","怀旧剧场","央视怀旧剧场"]},
    "风云足球":{"group":"数字","aliases":["cctv风云足球","风云足球","央视风云足球"]},
    "风云音乐":{"group":"数字","aliases":["cctv风云音乐","风云音乐","央视风云音乐"]},
    "风云剧场":{"group":"数字","aliases":["cctv风云剧场","风云剧场","央视风云剧场"]},
    "央视台球":{"group":"数字","aliases":["cctv央视台球","央视台球","台球"]},
    "女性时尚":{"group":"数字","aliases":["cctv女性时尚","女性时尚","央视女性时尚"]},
    "文化精品":{"group":"数字","aliases":["cctv文化精品","文化精品","央视文化精品"]},
    "兵器科技":{"group":"数字","aliases":["cctv兵器科技","央视兵器科技","兵器科技","cctv兵器"]},

    "凤凰中文":{"group":"HK","aliases":["凤凰中文"]},
    "凤凰资讯":{"group":"HK","aliases":["凤凰资讯"]},
    "凤凰香港":{"group":"HK","aliases":["凤凰香港"]},
}

SAT_LOGO_MAP = {
    "北京卫视":"beijing.png","天津卫视":"tianjin.png","河北卫视":"hebei.png","山西卫视":"shanxi.png",
    "内蒙古卫视":"neimenggu.png","辽宁卫视":"liaoning.png","吉林卫视":"jilin.png","黑龙江卫视":"heilongjiang.png",
    "东方卫视":"dongfang.png","江苏卫视":"jiangsu.png","浙江卫视":"zhejiang.png","安徽卫视":"anhui.png",
    "东南卫视":"dongnan.png","江西卫视":"jiangxi.png","山东卫视":"shandong.png","河南卫视":"henan.png",
    "湖北卫视":"hubei.png","湖南卫视":"hunan.png","广东卫视":"guangdong.png","深圳卫视":"shenzhen.png",
    "广西卫视":"guangxi.png","海南卫视":"hainan.png","重庆卫视":"chongqing.png","四川卫视":"sichuan.png",
    "贵州卫视":"guizhou.png","云南卫视":"yunnan.png","西藏卫视":"xizang.png","陕西卫视":"shaanxi.png",
    "甘肃卫视":"gansu.png","青海卫视":"qinghai.png","宁夏卫视":"ningxia.png","新疆卫视":"xinjiang.png",
    "兵团卫视":"bingtuan.png"
}
FOURK_LOGO_MAP = {
    "北京卫视4K":"BJ4K.png","湖南卫视4K":"HN4K.png","江苏卫视4K":"JS4K.png","浙江卫视4K":"ZJ4K.png",
    "深圳卫视4K":"SZ4K.png","东方卫视4K":"DF4K.png","四川卫视4K":"SC4K.png","广东卫视4K":"GD4K.png",
    "山东卫视4K":"SD4K.png"
}

def normalize_text(text):
    if not text:
        return ""
    text = text.strip().lower()
    text = (text.replace("臺", "台").replace("鳳", "凤").replace("資訊", "资讯")
                .replace("衛視", "卫视").replace("頻道", "频道")
                .replace("＋", "+").replace("４ｋ", "4k").replace("4Ｋ", "4k"))
    return text.replace(" ", "").replace("-", "").replace("_", "")

def is_alias_match(norm_name, alias):
    a = normalize_text(alias)
    if re.fullmatch(r"cctv\d+", a):
        return re.search(rf"{re.escape(a)}(?!\d)", norm_name) is not None
    return a in norm_name

def is_hk_name_valid(std_name, raw_name):
    n = normalize_text(raw_name)
    if "凤凰" not in n and "phoenix" not in n:
        return False
    if std_name == "凤凰中文":
        return ("中文" in n) and ("资讯" not in n) and ("香港" not in n)
    if std_name == "凤凰资讯":
        return ("资讯" in n) and ("中文" not in n) and ("香港" not in n)
    if std_name == "凤凰香港":
        return ("香港" in n) and ("中文" not in n) and ("资讯" not in n)
    return True

def match_target(name):
    norm_name = normalize_text(name)
    for std_name in MATCH_ORDER:
        for alias in CHANNEL_SPECS.get(std_name, {}).get("aliases", []):
            if is_alias_match(norm_name, alias):
                if std_name in HK_ORDER and not is_hk_name_valid(std_name, name):
                    continue
                return std_name
    return None

def get_logo_url(std_name):
    group = CHANNEL_SPECS[std_name]["group"]
    if group == "卫视":
        f = SAT_LOGO_MAP.get(std_name)
        if f:
            return SAT_LOGO_BASE + f
    if group == "4K":
        f = FOURK_LOGO_MAP.get(std_name)
        if f:
            return LOGO_BASE + f
    return f"{LOGO_BASE}{std_name}.png"

def build_extinf(std_name):
    return (
        f'#EXTINF:-1 tvg-id="{std_name}" tvg-name="{std_name}" '
        f'tvg-logo="{get_logo_url(std_name)}" '
        f'group-title="{CHANNEL_SPECS[std_name]["group"]}",{std_name}'
    )

def is_blocked_source(url):
    u = (url or "").lower()
    return any(k in u for k in BLOCKED_SOURCE_KEYWORDS)

def contains_date(text):
    return re.search(r"\d{4}-\d{2}-\d{2}", text or "") is not None

def extract_urls_from_txt(content):
    res = []
    for line in content.splitlines():
        line = line.strip()
        if line and "," in line:
            a = line.split(",", 1)
            if len(a) == 2:
                res.append((a[0].strip(), a[1].strip()))
    return res

def extract_urls_from_m3u(content):
    res, ch = [], "Unknown"
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            p = line.split(",", 1)
            ch = p[1].strip() if len(p) > 1 else "Unknown"
        elif line.startswith(("http://", "https://")):
            res.append((ch, line))
    return res

async def fetch_text(session, url, timeout=PLAYLIST_TIMEOUT):
    try:
        async with session.get(url, timeout=timeout, allow_redirects=True) as r:
            if r.status != 200:
                return None
            return await r.text(errors="ignore")
    except:
        return None

async def fetch_head_bytes(session, url, timeout=SEGMENT_TIMEOUT):
    try:
        async with session.get(url, timeout=timeout, headers={"Range": "bytes=0-1023"}, allow_redirects=True) as r:
            if r.status not in (200, 206):
                return False
            return len(await r.read()) > 0
    except:
        return False

async def probe_http_alive(session, url, timeout=SEGMENT_TIMEOUT):
    try:
        async with session.get(url, timeout=timeout, headers={"Range": "bytes=0-255"}, allow_redirects=True) as r:
            if r.status not in (200, 206):
                return False
            return len(await r.read()) > 0
    except:
        return False

def parse_m3u8_lines(text):
    return [x.strip() for x in (text or "").splitlines() if x.strip()]

def first_non_comment_uri(lines):
    for x in lines:
        if not x.startswith("#"):
            return x
    return None

async def sniff_m3u8_playable(session, url):
    text = await fetch_text(session, url)
    if not text or "#EXTM3U" not in text:
        return False
    lines = parse_m3u8_lines(text)

    if any("#EXT-X-STREAM-INF" in x for x in lines):
        child = first_non_comment_uri(lines)
        if not child:
            return False
        child_url = urljoin(url, child)
        text2 = await fetch_text(session, child_url)
        if not text2 or "#EXTM3U" not in text2:
            return False
        seg = first_non_comment_uri(parse_m3u8_lines(text2))
        if not seg:
            return False
        return await fetch_head_bytes(session, urljoin(child_url, seg))

    seg = first_non_comment_uri(lines)
    if not seg:
        return False
    return await fetch_head_bytes(session, urljoin(url, seg))

async def sniff_stream_strict(session, url):
    if ".m3u8" in url.lower():
        return await sniff_m3u8_playable(session, url)
    return await fetch_head_bytes(session, url)

async def sniff_stream_fallback(session, url):
    return await probe_http_alive(session, url)

async def test_stream(session, url):
    start = time.time()
    try:
        if await sniff_stream_strict(session, url):
            return True, True, time.time() - start
    except:
        pass
    try:
        if await sniff_stream_fallback(session, url):
            return False, True, time.time() - start
    except:
        pass
    return False, False, None

async def read_and_test_file(url, is_m3u):
    try:
        if is_blocked_source(url):
            print(f"跳过屏蔽源: {url}")
            return []

        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as r:
                content = await r.text()

            entries = extract_urls_from_m3u(content) if is_m3u else extract_urls_from_txt(content)

            filtered = []
            for ch, u in entries:
                if contains_date(ch) or contains_date(u):
                    continue
                if is_blocked_source(u):
                    continue
                std = match_target(ch)
                if std:
                    filtered.append((std, u))

            tasks = [test_stream(session, u) for _, u in filtered]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid = []
            for result, (std, u) in zip(results, filtered):
                if isinstance(result, Exception):
                    continue
                strict_ok, fallback_ok, latency = result
                if fallback_ok:
                    valid.append((std, u, latency, strict_ok))
            return valid
    except:
        return []

async def fetch_best_channels():
    all_valid = []
    for s in SOURCES:
        if is_blocked_source(s):
            print(f"跳过屏蔽源: {s}")
            continue
        is_m3u = s.endswith((".m3u", ".m3u8"))
        print(f"抓取频道源: {s}")
        all_valid.extend(await read_and_test_file(s, is_m3u))

    best_strict, best_fallback = {}, {}
    for std, url, latency, strict_ok in all_valid:
        if latency is None:
            continue
        if strict_ok and (std not in best_strict or latency < best_strict[std][1]):
            best_strict[std] = (url, latency)
        if std not in best_fallback or latency < best_fallback[std][1]:
            best_fallback[std] = (url, latency)

    result = []
    strict_count = fallback_count = 0
    for std in OUTPUT_ORDER:
        if std in best_strict:
            result.append((std, best_strict[std][0]))
            strict_count += 1
        elif std in best_fallback:
            result.append((std, best_fallback[std][0]))
            fallback_count += 1

    print("已获取频道总数:", len(result))
    print("其中严格可播:", strict_count)
    print("其中兜底保留:", fallback_count)
    return result

def generate_output(channels, filename):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "w", encoding="utf-8") as out:
        out.write("#EXTM3U\n\n")
        out.write(f"# new.m3u\n# 生成时间: {ts}\n\n")
        for std, url in channels:
            out.write(build_extinf(std) + "\n")
            out.write(url + "\n")
    print(f"✅ {filename} 生成完成")

def main():
    print("开始抓取目标频道...")
    print("输出文件:", OUTPUT_FILE)
    print("已启用：HK严格校验 + 可播优先 + 兜底保留")
    print("已启用：屏蔽 iptv.catvod.com（源与播放地址）")
    channels = asyncio.run(fetch_best_channels())
    generate_output(channels, OUTPUT_FILE)

if __name__ == "__main__":
    main()
