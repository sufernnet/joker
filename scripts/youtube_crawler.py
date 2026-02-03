#!/usr/bin/env python3
# 台灣新聞 YouTube 直播抓取（多頻道版） - 僅限1080P直播

import requests
import re
import os
import json
from datetime import datetime
from urllib.parse import quote

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
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
        ],
        "specific_channel": "@中天電視CtiT"  # 指定中天新聞頻道
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


def search_live_video(channel_info, keyword):
    """搜索直播视频，并检查分辨率"""
    
    # 如果是中天新闻，直接搜索指定频道
    if channel_info.get("specific_channel"):
        channel_name = channel_info["specific_channel"]
        search_query = f"{channel_name} live"
    else:
        search_query = keyword
    
    url = "https://www.youtube.com/results"
    params = {
        'search_query': search_query,
        'sp': 'EgJAAQ%253D%253D'  # 篩選直播
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        
        # 查找所有视频ID
        video_ids = re.findall(r'"videoId":"([^"]{11})"', resp.text)
        
        # 优先检查前5个结果
        for video_id in video_ids[:5]:
            # 检查视频质量和频道
            quality_ok, channel_match = check_video_quality_and_channel(video_id, channel_info)
            
            if quality_ok and channel_match:
                return video_id
        
        return None
        
    except Exception as e:
        print(f"   ⚠️ 搜索失敗: {e}")
        return None


def check_video_quality_and_channel(video_id, channel_info):
    """检查视频是否为1080P并且来自正确的频道"""
    
    try:
        # 获取视频信息页面
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(video_url, headers=HEADERS, timeout=10)
        
        # 检查是否为1080P
        if '"height":1080' not in response.text:
            return False, False
        
        # 检查频道信息
        if channel_info.get("specific_channel"):
            # 对于中天新闻，检查是否为指定频道
            channel_pattern = r'"channelHandle":"@[^"]+"'
            channel_match = re.search(channel_pattern, response.text)
            if channel_match:
                channel_handle = channel_match.group(0)
                if "@中天電視CtiT" in channel_handle:
                    return True, True
            return False, False
        
        # 对于其他频道，只要1080P就接受
        return True, True
        
    except Exception as e:
        print(f"   ⚠️ 檢查視頻質量失敗: {e}")
        return False, False


def get_video_details(video_id):
    """获取视频详细信息"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(video_url, headers=HEADERS, timeout=10)
        
        # 尝试提取视频标题
        title_match = re.search(r'"title":"([^"]+)"', response.text)
        title = title_match.group(1) if title_match else "未知標題"
        
        # 尝试提取频道信息
        channel_match = re.search(r'"channelHandle":"(@[^"]+)"', response.text)
        channel = channel_match.group(1) if channel_match else "未知頻道"
        
        # 检查分辨率
        is_1080p = '"height":1080' in response.text
        is_720p = '"height":720' in response.text
        
        resolution = "1080P" if is_1080p else "720P" if is_720p else "其他"
        
        return {
            "title": title,
            "channel": channel,
            "resolution": resolution,
            "is_1080p": is_1080p
        }
    except:
        return {
            "title": "無法獲取",
            "channel": "無法獲取",
            "resolution": "未知",
            "is_1080p": False
        }


def fetch_all_channels():
    results = []
    success_count = 0
    skipped_count = 0

    print("🔍 開始抓取台灣新聞直播 (僅限1080P)")
    print("=" * 60)

    for ch in CHANNELS:
        print(f"\n📺 處理頻道: {ch['name']}")
        
        if ch.get("specific_channel"):
            print(f"   ⭐ 指定頻道: {ch['specific_channel']}")

        video_id = None
        details = None
        
        # 尝试所有关键词
        for kw in ch["keywords"]:
            video_id = search_live_video(ch, kw)
            if video_id:
                details = get_video_details(video_id)
                print(f"   ✅ 找到直播: {details['title'][:50]}...")
                print(f"     頻道: {details['channel']}")
                print(f"     分辨率: {details['resolution']}")
                
                if details['is_1080p']:
                    print(f"     🎯 符合1080P要求")
                    break
                else:
                    print(f"     ⚠️ 分辨率不符，繼續搜索...")
                    video_id = None
        
        if video_id and details and details['is_1080p']:
            results.append({
                "name": ch["name"],
                "tvg_id": ch["tvg_id"],
                "logo": ch["logo"],
                "video_id": video_id,
                "details": details
            })
            success_count += 1
        else:
            print(f"   ❌ 未找到符合條件的1080P直播")
            skipped_count += 1

    print(f"\n📊 抓取統計:")
    print(f"   ✅ 成功: {success_count} 個頻道")
    print(f"   ❌ 跳過: {skipped_count} 個頻道 (非1080P或未找到)")
    print(f"   📺 總數: {len(CHANNELS)} 個頻道")
    
    return results


def generate_m3u(channels):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    lines = [
        '#EXTM3U url-tvg="http://epg.51zmt.top:8000/e.xml"',
        '# Generated by Taiwan News YouTube Crawler',
        '# 要求: 僅包含1080P直播源',
        f'# 更新時間: {now}',
        f'# 符合條件頻道數: {len(channels)}',
        ""
    ]

    for ch in channels:
        details = ch.get("details", {})
        channel_info = f" ({details.get('channel', '')})" if details.get('channel') else ""
        
        lines.append(
            f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" '
            f'tvg-name="{ch["name"]}" '
            f'tvg-logo="{ch["logo"]}" '
            f'group-title="TW",{ch["name"]}{channel_info}'
        )
        lines.append(f'https://www.youtube.com/watch?v={ch["video_id"]}')
        lines.append("")

    return "\n".join(lines)


def main():
    print("🚀 台灣新聞直播抓取開始 - 僅限1080P")
    print("=" * 60)
    print("📋 要求:")
    print("   1. 中天新聞必須來自 @中天電視CtiT")
    print("   2. 所有直播必須為1080P分辨率")
    print("=" * 60)
    
    channels = fetch_all_channels()

    if not channels:
        print("\n❌ 沒有任何頻道符合1080P條件")
        return

    m3u = generate_m3u(channels)
    
    # 在scripts目录下生成文件
    output_path = "live.m3u"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(m3u)

    print(f"\n✅ 生成完成，共 {len(channels)} 個符合條件的頻道")
    print(f"📁 輸出文件：{output_path}")
    
    # 顯示生成的頻道列表
    print("\n🎯 符合1080P條件的頻道:")
    print("-" * 50)
    for i, ch in enumerate(channels, 1):
        details = ch.get("details", {})
        resolution = details.get("resolution", "未知")
        channel = details.get("channel", "未知")
        print(f"{i:2d}. {ch['name']:15} | {resolution:6} | {channel}")
    print("-" * 50)


if __name__ == "__main__":
    main()
