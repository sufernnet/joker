#!/usr/bin/env python3
import requests
from datetime import datetime
import re

# ================== 基础配置 ==================

SOURCE_URL = "https://yang.sufern001.workers.dev/"
BB_FILE = "BB.m3u"
OUTPUT_FILE = "Gather.m3u"
EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

HK_SOURCE_GROUP = "• Juli 「精選」"
TW_SOURCE_GROUP = "•台湾「限制」"

HK_GROUP = "HK"
TW_GROUP = "TW"

# ================== TW 剔除关键词 ==================

REMOVE_TW_KEYWORDS = [

    "大愛電視","好消息","國會頻道","東森購物","新唐人","人間衛視",
    "幸福空間","車迷","金光布袋戲","原住民族電視","客家電視",
    "LiveABC","ELTA生活英語","Smart知識","達文西","滾動力",
    "INULTRA","Global Trekker","LUXE TV","TV5MONDE","TRACE",
    "GINX","DreamWorks","精選動漫","經典卡通","MOMO親子",
    "Nick Jr","尼克兒童","Pet Club",

    "KMTV","Lifetime","fun探索","HITS","ROCK",
    "豬哥亮","采昌","CLASSICA","Mezzo","CMusic",
    "FashionTV","倪珍播新聞","半島國際","DW德國之聲",
    "FRANCE24","NHK 新聞","CNBC Asia","SBN 全球財經",
    "Bloomberg","DayStar","第1商業","amc電影",
    "MCE 我的歐洲電影","影迷數位電影",
    "影迷數位紀實","CinemaWorld"
]

# ================== 工具函数 ==================

def download(url):
    r = requests.get(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0"
    })
    r.raise_for_status()
    return r.text


def clean_tw_name(name):
    name = re.sub(r'「4gTV」', '', name, flags=re.IGNORECASE)
    name = re.sub(r'「ofiii」', '', name, flags=re.IGNORECASE)
    return name.strip()


def should_remove_tw(name):
    for keyword in REMOVE_TW_KEYWORDS:
        if keyword.lower() in name.lower():
            return True
    return False


def deduplicate(channels):
    seen = set()
    result = []
    for name, url in channels:
        if url not in seen:
            seen.add(url)
            result.append((name, url))
    return result


# ================== TW 分层排序 ==================

def sort_tw_channels(tw_channels):

    priority_top = ["Love Nature", "歷史頻道", "亞洲旅遊"]

    def get_priority(name):

        # 固定前三
        for i, keyword in enumerate(priority_top):
            if keyword in name:
                return (0, i)

        if "中天" in name:
            return (1, name)

        if "民视" in name or "民視" in name:
            return (2, name)

        if "寰宇" in name:
            return (3, name)

        if "鏡電視" in name or "鏡新聞" in name:
            return (4, name)

        if "龍華" in name or "龙华" in name:
            return (5, name)

        return (6, name)

    return sorted(tw_channels, key=lambda x: get_priority(x[0]))


# ================== 主程序 ==================

def main():

    print("下载源文件...")
    content = download(SOURCE_URL)
    lines = content.splitlines()

    hk = []
    tw = []

    current_group = None
    current_name = None

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):

            if 'group-title="' in line:
                current_group = line.split('group-title="')[1].split('"')[0]
            else:
                current_group = None

            if "," in line:
                current_name = line.split(",")[-1].strip()
            else:
                current_name = None

        elif line.startswith("http"):

            url = line.strip()

            if not current_group or not current_name:
                continue

            name_lower = current_name.lower()

            # HK
            if current_group == HK_SOURCE_GROUP:
                hk.append((current_name, url))

            # TW
            elif current_group == TW_SOURCE_GROUP:
                if (
                    "4gtv" in name_lower
                    or "ofiii" in name_lower
                    or "龍華" in current_name
                    or "龙华" in current_name
                ):
                    clean_name = clean_tw_name(current_name)
                    if not should_remove_tw(clean_name):
                        tw.append((clean_name, url))

    # 去重
    hk = deduplicate(hk)
    tw = deduplicate(tw)

    # 排序 TW
    tw = sort_tw_channels(tw)

    print("HK:", len(hk))
    print("TW:", len(tw))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ================== 输出 ==================

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"# Gather.m3u\n# 生成时间: {timestamp}\n\n"

    # 合并 BB
    try:
        with open(BB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("#EXTM3U"):
                    output += line
        print("BB.m3u 已合并")
    except:
        print("未找到 BB.m3u，跳过")

    # 写 HK
    if hk:
        output += f"\n# {HK_GROUP}\n"
        for name, url in hk:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n'
            output += f"{url}\n"

    # 写 TW
    if tw:
        output += f"\n# {TW_GROUP}\n"
        for name, url in tw:
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{name}\n'
            output += f"{url}\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print("🎉 Gather.m3u 生成完成")


if __name__ == "__main__":
    main()
