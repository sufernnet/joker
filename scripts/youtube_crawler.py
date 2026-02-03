#!/usr/bin/env python3
# 台灣新聞 YouTube 直播抓取（多頻道版）

import requests
import re
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept-Language': 'zh-TW,zh;q=0.9',
}

# =========================
# 頻道配置（重點在這）
# =========================
CHANNELS = [
    {
        "name": "中天新聞",
        "tvg_id": "CTITV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7f/CTi_News_Logo.png",
        "keywords": [
            "中天新聞 直播",
            "CTI News LIVE",
            "中天新聞台 24小時直播"
        ]
    },
    {
        "name": "民視新聞",
        "tvg_id": "FTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/1/1e/Formosa_TV_logo.png",
        "keywords": [
            "民視新聞 直播",
            "FTV News LIVE",
            "民視新聞台 24小時"
        ]
    },
    {
        "name": "TVBS 新聞",
        "tvg_id": "TVBS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5d/TVBS_News_Logo.png",
        "keywords": [
            "TVBS 新聞 直播",
            "TVBS NEWS LIVE"
        ]
    },
    {
        "name": "東森新聞",
        "tvg_id": "ETTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/72/ETtoday_logo.png",
        "keywords": [
            "東森新聞 直播",
            "ETtoday News LIVE"
        ]
    },
    {
        "name": "寰宇新聞",
        "tvg_id": "HUANYU_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/9/9e/Global_News_TW_logo.png",
        "keywords": [
            "寰宇新聞 直播",
            "寰宇新聞台 LIVE"
        ]
    },
    {
        "name": "三立新聞",
        "tvg_id": "SET_INEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/8e/SET_iNEWS_logo.png",
        "keywords": [
            "三立新聞 直播",
            "SET News LIVE"
        ]
    },
    {
        "name": "壹電視",
        "tvg_id": "NEXTTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/4/4b/Next_TV_logo.png",
        "keywords": [
            "壹電視新聞 直播",
            "Next TV News LIVE"
        ]
    },
    {
        "name": "公視新聞",
        "tvg_id": "PTS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5c/PTS_logo.png",
        "keywords": [
            "公視新聞 直播",
            "PTS News LIVE"
        ]
    },
    {
        "name": "東森財經新聞",
        "tvg_id": "ETTV_FINANCE",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/72/ETtoday_logo.png",
        "keywords": [
            "東森財經新聞 直播",
            "ETtoday Finance LIVE"
        ]
    },
    {
        "name": "鏡新聞",
        "tvg_id": "MNEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7b/Mirror_News_TW_logo.png",
        "keywords": [
            "鏡新聞 直播",
            "Mirror News LIVE"
        ]
    },
    {
        "name": "年代新聞",
        "tvg_id": "ERA_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/1/1e/ERA_News_logo.png",
        "keywords": [
            "年代新聞 直播",
            "ERA News LIVE"
        ]
    },
    {
        "name": "民視第壹台",
        "tvg_id": "FTV_ONE",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/1/1e/Formosa_TV_logo.png",
        "keywords": [
            "民視第壹台 直播",
            "FTV One LIVE"
        ]
    },
    {
        "name": "台視新聞",
        "tvg_id": "TTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/6/6c/TTV_logo.png",
        "keywords": [
            "台視新聞 直播",
            "TTV News LIVE"
        ]
    },
    {
        "name": "華視新聞",
        "tvg_id": "CTS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/86/CTS_logo.png",
        "keywords": [
            "華視新聞 直播",
            "CTS News LIVE"
        ]
    },
    {
        "name": "寰宇新聞台灣",
        "tvg_id": "HUANYU_TW",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/9/9e/Global_News_TW_logo.png",
        "keywords": [
            "寰宇新聞台灣 直播",
            "Global News Taiwan LIVE"
        ]
    },
    {
        "name": "艾爾達娛樂台",
        "tvg_id": "ELTA_ENT",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/8d/ELTA_TV_logo.png",
        "keywords": [
            "艾爾達娛樂台 直播",
            "ELTA Entertainment LIVE"
        ]
    },
    {
        "name": "非凡新聞",
        "tvg_id": "UBN_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7e/Unique_Broadcast_News_logo.png",
        "keywords": [
            "非凡新聞 直播",
            "UBN News LIVE"
        ]
    },
    {
        "name": "三立 iNEWS",
        "tvg_id": "SET_INEWS2",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/8e/SET_iNEWS_logo.png",
        "keywords": [
            "三立 iNEWS 直播",
            "SET iNEWS LIVE"
        ]
    },
    {
        "name": "中視新聞",
        "tvg_id": "CTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7f/CTV_logo.png",
        "keywords": [
            "中視新聞 直播",
            "CTV News LIVE"
        ]
    },
    {
        "name": "非凡商業台",
        "tvg_id": "UBN_BUSINESS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7e/Unique_Broadcast_News_logo.png",
        "keywords": [
            "非凡商業台 直播",
            "UBN Business LIVE"
        ]
    },
    {
        "name": "公視台語台",
        "tvg_id": "PTS_TAIYU",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5c/PTS_logo.png",
        "keywords": [
            "公視台語台 直播",
            "PTS Taigi LIVE"
        ]
    },
    {
        "name": "客家電視台",
        "tvg_id": "HAKKA_TV",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/2/2a/Hakka_TV_logo.png",
        "keywords": [
            "客家電視 直播",
            "Hakka TV LIVE"
        ]
    }
]


def search_live_video(keyword):
    url = "https://www.youtube.com/results"
    params = {
        'search_query': keyword,
        'sp': 'EgJAAQ%253D%253D'  # 篩選直播
    }

    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    match = re.search(r'"videoId":"([^"]{11})"', resp.text)
    return match.group(1) if match else None


def fetch_all_channels():
    results = []

    for ch in CHANNELS:
        print(f"\n🔍 抓取 {ch['name']}")

        video_id = None
        for kw in ch["keywords"]:
            video_id = search_live_video(kw)
            if video_id:
                print(f"  ✅ 命中關鍵字：{kw}")
                break

        if video_id:
            results.append({
                "name": ch["name"],
                "tvg_id": ch["tvg_id"],
                "logo": ch["logo"],
                "video_id": video_id
            })
        else:
            print("  ❌ 未找到直播")

    return results


def generate_m3u(channels):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lines = [
        '#EXTM3U url-tvg="http://epg.51zmt.top:8000/e.xml"',
        f"# Generated at {now}",
        ""
    ]

    for ch in channels:
        lines.append(
            f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" '
            f'tvg-name="{ch["name"]}" '
            f'tvg-logo="{ch["logo"]}" '
            f'group-title="TW",{ch["name"]}'
        )
        lines.append(f'https://www.youtube.com/watch?v={ch["video_id"]}')
        lines.append("")

    return "\n".join(lines)


def main():
    print("🚀 台灣新聞直播抓取開始")
    channels = fetch_all_channels()

    if not channels:
        print("\n❌ 沒有任何頻道抓到直播")
        return

    m3u = generate_m3u(channels)

    with open("live.m3u", "w", encoding="utf-8") as f:
        f.write(m3u)

    print(f"\n✅ 生成完成，共 {len(channels)} 個頻道")
    print("📁 輸出文件：live.m3u")


if __name__ == "__main__":
    main()
