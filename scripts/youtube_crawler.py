#!/usr/bin/env python3
# 台灣新聞 YouTube 直播抓取（官方頻道版）

import requests
import re
import os
import time
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

# =========================
# 官方頻道配置
# =========================
CHANNELS = [
    {
        "name": "中天新聞",
        "tvg_id": "CTITV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7f/CTi_News_Logo.png",
        "channel_id": "@中天電視CtiT",  # 官方頻道
        "keywords": ["直播", "24小時", "LIVE", "live", "Live"]
    },
    {
        "name": "民視新聞",
        "tvg_id": "FTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/1/1e/Formosa_TV_logo.png",
        "channel_id": "@FTV_News",  # 官方頻道
        "keywords": ["新聞直播", "24小時", "LIVE"]
    },
    {
        "name": "民視第壹台",
        "tvg_id": "FTV_ONE",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/1/1e/Formosa_TV_logo.png",
        "channel_id": "@FTV_News",  # 同一頻道
        "keywords": ["第壹台", "第一台", "FTV ONE", "直播"]
    },
    {
        "name": "TVBS 新聞",
        "tvg_id": "TVBS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5d/TVBS_News_Logo.png",
        "channel_id": "@TVBSNEWS01",  # 官方頻道
        "keywords": ["新聞直播", "24小時", "LIVE"]
    },
    {
        "name": "東森新聞",
        "tvg_id": "ETTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/72/ETtoday_logo.png",
        "channel_id": "@newsebc",  # 官方頻道
        "keywords": ["新聞直播", "24小時", "LIVE"]
    },
    {
        "name": "EBC 東森財經新聞",
        "tvg_id": "ETTV_FINANCE",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/72/ETtoday_logo.png",
        "channel_id": "@57ETFN",  # 官方頻道
        "keywords": ["財經", "EBC", "直播", "LIVE"]
    },
    {
        "name": "寰宇新聞",
        "tvg_id": "HUANYU_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/9/9e/Global_News_TW_logo.png",
        "channel_id": "@globalnewstw",  # 官方頻道
        "keywords": ["新聞直播", "寰宇", "LIVE"]
    },
    {
        "name": "寰宇新聞台灣台",
        "tvg_id": "HUANYU_TW",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/9/9e/Global_News_TW_logo.png",
        "channel_id": "@globalnewstw",  # 同一頻道
        "keywords": ["台灣台", "24小時直播", "Taiwan"]
    },
    {
        "name": "三立新聞",
        "tvg_id": "SET_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/8e/SET_iNEWS_logo.png",
        "channel_id": "@setnews",  # 官方頻道
        "keywords": ["新聞直播", "LIVE", "直播"]
    },
    {
        "name": "三立 iNEWS",
        "tvg_id": "SET_INEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/8e/SET_iNEWS_logo.png",
        "channel_id": "@三立iNEWS",  # 官方頻道
        "keywords": ["iNEWS", "直播", "LIVE"]
    },
    {
        "name": "公視新聞",
        "tvg_id": "PTS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5c/PTS_logo.png",
        "channel_id": "@PNNPTS",  # 官方頻道
        "keywords": ["新聞", "直播", "LIVE"]
    },
    {
        "name": "鏡新聞",
        "tvg_id": "MNEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7b/Mirror_News_TW_logo.png",
        "channel_id": "@mnews-tw",  # 官方頻道
        "keywords": ["直播", "LIVE", "24小時"]
    },
    {
        "name": "非凡財經",
        "tvg_id": "UBN_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7e/Unique_Broadcast_News_logo.png",
        "channel_id": "@ustvbiz",  # 官方頻道
        "keywords": ["非凡", "財經", "直播", "LIVE"]
    },
    {
        "name": "台視新聞台",
        "tvg_id": "TTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/6/6c/TTV_logo.png",
        "channel_id": "@TTV_NEWS",  # 官方頻道
        "keywords": ["新聞", "直播", "LIVE", "24小時"]
    },
    {
        "name": "華視新聞",
        "tvg_id": "CTS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/86/CTS_logo.png",
        "channel_id": "@CtsTw",  # 官方頻道
        "keywords": ["新聞", "直播", "LIVE", "華視"]
    },
    {
        "name": "中視新聞",
        "tvg_id": "CTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7f/CTV_logo.png",
        "channel_id": "@chinatvnews",  # 官方頻道
        "keywords": ["新聞", "直播", "LIVE", "中視"]
    },
    {
        "name": "公視台語台",
        "tvg_id": "PTS_TAIYU",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5c/PTS_logo.png",
        "channel_id": "@PNNPTS",  # 同一頻道
        "keywords": ["台語", "Taiwanese", "直播"]
    },
    {
        "name": "客家電視台",
        "tvg_id": "HAKKA_TV",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/2/2a/Hakka_TV_logo.png",
        "channel_id": "@HakkaTV",  # 官方頻道
        "keywords": ["客家", "Hakka", "直播", "LIVE"]
    }
]

def get_channel_videos(channel_id):
    """獲取頻道的最新影片列表"""
    url = f"https://www.youtube.com/{channel_id}/videos"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html = resp.text
        
        # 尋找所有影片ID
        video_patterns = [
            r'"videoId":"([^"]{11})"',  # 標準格式
            r'watch\?v=([^"&]{11})',     # 備用格式
            r'/watch/([^"&]{11})'        # 另一種格式
        ]
        
        video_ids = []
        for pattern in video_patterns:
            matches = re.findall(pattern, html)
            video_ids.extend(matches)
        
        # 去重並返回前20個
        return list(dict.fromkeys(video_ids))[:20]
        
    except Exception as e:
        print(f"   ⚠️ 獲取頻道影片失敗: {e}")
        return []

def check_video_live(video_id):
    """檢查影片是否為直播或首播"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        html = resp.text.lower()
        
        # 檢查是否為直播
        if '"isLive":true' in html or '"livebroadcastdetails"' in html:
            return True
        
        # 檢查標題是否包含直播關鍵字
        title_match = re.search(r'<title>([^<]+)</title>', resp.text)
        if title_match:
            title = title_match.group(1).lower()
            live_keywords = ['直播', 'live', '首播', '24小時', '正在直播']
            if any(keyword in title for keyword in live_keywords):
                return True
        
        # 檢查描述
        if '"shortdescription"' in html:
            desc_start = html.find('"shortdescription"')
            desc_snippet = html[desc_start:desc_start+500]
            if any(keyword in desc_snippet for keyword in ['直播', 'live']):
                return True
                
        return False
        
    except Exception as e:
        print(f"   ⚠️ 檢查影片狀態失敗: {e}")
        return False

def search_channel_live(channel):
    """在指定頻道中搜索直播影片"""
    print(f"🔍 搜索 {channel['name']} ({channel['channel_id']})")
    
    # 獲取頻道影片列表
    video_ids = get_channel_videos(channel['channel_id'])
    
    if not video_ids:
        print(f"  ⚠️ 未找到任何影片")
        return None
    
    print(f"  📺 找到 {len(video_ids)} 個影片")
    
    # 優先檢查最新的5個影片
    for i, video_id in enumerate(video_ids[:5]):
        print(f"  🔄 檢查影片 {i+1}/{len(video_ids[:5])}")
        
        if check_video_live(video_id):
            # 進一步驗證標題是否符合頻道
            url = f"https://www.youtube.com/watch?v={video_id}"
            try:
                resp = requests.get(url, headers=HEADERS, timeout=8)
                title_match = re.search(r'<title>([^<]+)</title>', resp.text)
                if title_match:
                    title = title_match.group(1)
                    
                    # 檢查標題是否包含頻道關鍵字
                    for keyword in channel['keywords']:
                        if keyword.lower() in title.lower():
                            print(f"  ✅ 找到直播: {title[:50]}...")
                            return video_id
                    
                    # 如果沒有關鍵字匹配，但確定是直播，也返回
                    print(f"  ⚠️ 找到直播但標題不符: {title[:50]}...")
                    return video_id
            except:
                # 如果檢查標題失敗，但確定是直播，仍然返回
                print(f"  ✅ 找到直播 (ID: {video_id})")
                return video_id
        
        # 避免請求過快
        time.sleep(0.5)
    
    print(f"  ❌ 未找到直播內容")
    return None

def fetch_all_channels():
    """抓取所有頻道的直播"""
    results = []
    success_count = 0
    
    for ch in CHANNELS:
        video_id = search_channel_live(ch)
        
        if video_id:
            results.append({
                "name": ch["name"],
                "tvg_id": ch["tvg_id"],
                "logo": ch["logo"],
                "video_id": video_id,
                "channel": ch["channel_id"]
            })
            success_count += 1
        else:
            print(f"  ❌ {ch['name']} 未找到直播")
        
        # 頻道間隔
        time.sleep(1)
    
    print(f"\n📊 抓取統計: {success_count}/{len(CHANNELS)} 個頻道成功")
    return results

def generate_m3u(channels):
    """生成M3U播放列表"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines = [
        '#EXTM3U url-tvg="http://epg.51zmt.top:8000/e.xml"',
        '# Generated by Taiwan News YouTube Crawler (Official Channels)',
        f'# 更新時間: {now}',
        f'# 頻道總數: {len(channels)}',
        '# 來源: YouTube官方頻道',
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
    print("🚀 台灣新聞直播抓取開始 (官方頻道版)")
    print("=" * 50)
    print(f"📡 共 {len(CHANNELS)} 個官方頻道")
    print("=" * 50)
    
    channels = fetch_all_channels()
    
    if not channels:
        print("\n❌ 沒有任何頻道抓到直播")
        return
    
    m3u = generate_m3u(channels)
    
    # 確保scripts目錄存在
    os.makedirs("scripts", exist_ok=True)
    
    # 在scripts目錄下生成文件
    output_path = "live.m3u"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(m3u)
    
    print(f"\n✅ 生成完成，共 {len(channels)} 個頻道")
    print(f"📁 輸出文件：{output_path}")
    
    # 顯示生成的頻道列表
    print("\n📡 成功抓取的頻道:")
    print("-" * 40)
    for i, ch in enumerate(channels, 1):
        print(f"{i:2d}. {ch['name']:15} (來源: {ch['channel']})")
    print("-" * 40)
    
    # 顯示失敗的頻道
    success_names = [ch['name'] for ch in channels]
    failed = [ch for ch in CHANNELS if ch['name'] not in success_names]
    
    if failed:
        print("\n❌ 失敗的頻道:")
        for ch in failed:
            print(f"  • {ch['name']}")

if __name__ == "__main__":
    main()
