#!/usr/bin/env python3
# 台灣新聞 YouTube 直播抓取（官方頻道專用版）

import requests
import re
import os
import time
import sys
from datetime import datetime

# 設置請求頭
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# =========================
# 官方頻道配置（使用您提供的官方地址）
# =========================
CHANNELS = [
    {
        "name": "中天新聞",
        "tvg_id": "CTITV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7f/CTi_News_Logo.png",
        "channel_id": "@中天電視CtiT",  # 官方頻道
        "search_keywords": ["直播", "24小時", "LIVE", "線上直播"],
        "fallback_keywords": ["中天新聞 直播", "CTI News LIVE"]
    },
    {
        "name": "民視新聞",
        "tvg_id": "FTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/1/1e/Formosa_TV_logo.png",
        "channel_id": "@FTV_News",  # 官方頻道
        "search_keywords": ["新聞直播", "24小時", "LIVE", "線上"],
        "fallback_keywords": ["民視新聞 直播", "FTV News LIVE"]
    },
    {
        "name": "民視第壹台",
        "tvg_id": "FTV_ONE",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/1/1e/Formosa_TV_logo.png",
        "channel_id": "@FTV_News",  # 同一頻道
        "search_keywords": ["第壹台", "FTV ONE", "直播", "線上"],
        "fallback_keywords": ["民視第壹台 直播", "FTV One LIVE"]
    },
    {
        "name": "TVBS 新聞",
        "tvg_id": "TVBS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5d/TVBS_News_Logo.png",
        "channel_id": "@TVBSNEWS01",  # 官方頻道
        "search_keywords": ["新聞直播", "24小時", "LIVE", "線上"],
        "fallback_keywords": ["TVBS 新聞 直播", "TVBS NEWS LIVE"]
    },
    {
        "name": "東森新聞",
        "tvg_id": "ETTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/72/ETtoday_logo.png",
        "channel_id": "@newsebc",  # 官方頻道
        "search_keywords": ["新聞直播", "24小時", "LIVE", "線上"],
        "fallback_keywords": ["東森新聞 直播", "ETtoday News LIVE"]
    },
    {
        "name": "EBC 東森財經新聞",
        "tvg_id": "ETTV_FINANCE",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/72/ETtoday_logo.png",
        "channel_id": "@57ETFN",  # 官方頻道
        "search_keywords": ["財經直播", "EBC", "LIVE", "線上"],
        "fallback_keywords": ["東森財經新聞 直播", "ETtoday Finance LIVE"]
    },
    {
        "name": "寰宇新聞",
        "tvg_id": "HUANYU_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/9/9e/Global_News_TW_logo.png",
        "channel_id": "@globalnewstw",  # 官方頻道
        "search_keywords": ["新聞直播", "寰宇", "LIVE", "24小時"],
        "fallback_keywords": ["寰宇新聞 直播", "Global News LIVE"]
    },
    {
        "name": "寰宇新聞台灣台",
        "tvg_id": "HUANYU_TW",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/9/9e/Global_News_TW_logo.png",
        "channel_id": "@globalnewstw",  # 同一頻道
        "search_keywords": ["台灣台", "24小時直播", "Taiwan", "LIVE"],
        "fallback_keywords": ["寰宇新聞台灣台 直播", "Global News Taiwan LIVE"]
    },
    {
        "name": "三立新聞",
        "tvg_id": "SET_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/8e/SET_iNEWS_logo.png",
        "channel_id": "@setnews",  # 官方頻道
        "search_keywords": ["新聞直播", "三立", "LIVE", "線上"],
        "fallback_keywords": ["三立新聞 直播", "SET News LIVE"]
    },
    {
        "name": "三立 iNEWS",
        "tvg_id": "SET_INEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/8e/SET_iNEWS_logo.png",
        "channel_id": "@三立iNEWS",  # 官方頻道
        "search_keywords": ["iNEWS", "直播", "LIVE", "線上"],
        "fallback_keywords": ["三立 iNEWS 直播", "SET iNEWS LIVE"]
    },
    {
        "name": "公視新聞",
        "tvg_id": "PTS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/5/5c/PTS_logo.png",
        "channel_id": "@PNNPTS",  # 官方頻道
        "search_keywords": ["新聞直播", "公視", "LIVE", "線上"],
        "fallback_keywords": ["公視新聞 直播", "PTS News LIVE"]
    },
    {
        "name": "鏡新聞",
        "tvg_id": "MNEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7b/Mirror_News_TW_logo.png",
        "channel_id": "@mnews-tw",  # 官方頻道
        "search_keywords": ["直播", "LIVE", "24小時", "鏡新聞"],
        "fallback_keywords": ["鏡新聞 直播", "Mirror News LIVE"]
    },
    {
        "name": "非凡財經",
        "tvg_id": "UBN_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7e/Unique_Broadcast_News_logo.png",
        "channel_id": "@ustvbiz",  # 官方頻道
        "search_keywords": ["非凡", "財經", "直播", "LIVE"],
        "fallback_keywords": ["非凡新聞 直播", "UBN News LIVE"]
    },
    {
        "name": "台視新聞台",
        "tvg_id": "TTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/6/6c/TTV_logo.png",
        "channel_id": "@TTV_NEWS",  # 官方頻道
        "search_keywords": ["新聞直播", "台視", "LIVE", "24小時"],
        "fallback_keywords": ["台視新聞 直播", "TTV News LIVE"]
    },
    {
        "name": "華視新聞",
        "tvg_id": "CTS_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/8/86/CTS_logo.png",
        "channel_id": "@CtsTw",  # 官方頻道
        "search_keywords": ["新聞直播", "華視", "LIVE", "線上"],
        "fallback_keywords": ["華視新聞 直播", "CTS News LIVE"]
    },
    {
        "name": "中視新聞",
        "tvg_id": "CTV_NEWS",
        "logo": "https://upload.wikimedia.org/wikipedia/zh/7/7f/CTV_logo.png",
        "channel_id": "@chinatvnews",  # 官方頻道
        "search_keywords": ["新聞直播", "中視", "LIVE", "線上"],
        "fallback_keywords": ["中視新聞 直播", "CTV News LIVE"]
    }
]

def log_message(message, level="INFO"):
    """統一日誌輸出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def get_channel_videos(channel_id):
    """從官方頻道獲取影片列表"""
    url = f"https://www.youtube.com/{channel_id}/videos"
    
    try:
        log_message(f"獲取頻道影片: {channel_id}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            log_message(f"請求失敗，狀態碼: {response.status_code}", "WARNING")
            return []
        
        html_content = response.text
        
        # 多種方式提取videoId
        video_patterns = [
            r'"videoId":"([a-zA-Z0-9_-]{11})"',
            r'watch\?v=([a-zA-Z0-9_-]{11})',
            r'/watch/([a-zA-Z0-9_-]{11})',
            r'embed/([a-zA-Z0-9_-]{11})'
        ]
        
        video_ids = []
        for pattern in video_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if match not in video_ids:
                    video_ids.append(match)
        
        # 去重並返回
        unique_ids = list(dict.fromkeys(video_ids))
        log_message(f"找到 {len(unique_ids)} 個影片", "SUCCESS")
        return unique_ids[:10]  # 只檢查前10個
        
    except Exception as e:
        log_message(f"獲取影片失敗: {str(e)}", "ERROR")
        return []

def is_live_stream(video_id):
    """檢查影片是否為直播"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        html_content = response.text
        
        # 檢查直播標誌
        live_indicators = [
            '"isLive":true',
            '"isLiveBroadcast":true',
            '"liveBroadcastDetails"',
            '"liveStreamability"',
            '\\"liveNow\\":true',
            'ytInitialPlayerResponse.*"isLive":true'
        ]
        
        for indicator in live_indicators:
            if indicator in html_content:
                return True
        
        # 檢查標題中的直播關鍵字
        title_match = re.search(r'<title>([^<]+)</title>', html_content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).lower()
            live_keywords = [
                '直播', 'live', '首播', '24小時', '正在直播', 
                'live stream', '實況', '線上直播', '24h'
            ]
            if any(keyword in title for keyword in live_keywords):
                return True
        
        # 檢查meta描述
        meta_match = re.search(r'<meta name="description" content="([^"]+)"', html_content, re.IGNORECASE)
        if meta_match:
            description = meta_match.group(1).lower()
            if any(keyword in description for keyword in ['直播', 'live']):
                return True
                
        return False
        
    except Exception as e:
        log_message(f"檢查直播狀態失敗: {str(e)}", "ERROR")
        return False

def get_video_title(video_id):
    """獲取影片標題"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        html_content = response.text
        
        title_match = re.search(r'<title>([^<]+)</title>', html_content)
        if title_match:
            title = title_match.group(1)
            # 清理標題
            title = title.replace(' - YouTube', '').strip()
            return title
    except:
        pass
    
    return f"影片 {video_id}"

def search_youtube_live(keyword):
    """備用方法：搜索YouTube直播"""
    search_url = "https://www.youtube.com/results"
    params = {
        'search_query': keyword,
        'sp': 'EgJAAQ%253D%253D'  # 篩選直播
    }
    
    try:
        response = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        html_content = response.text
        
        # 提取第一個直播影片ID
        video_match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html_content)
        if video_match:
            video_id = video_match.group(1)
            log_message(f"通過搜索找到影片: {video_id}", "INFO")
            return video_id
            
    except Exception as e:
        log_message(f"搜索失敗: {str(e)}", "ERROR")
    
    return None

def find_channel_live(channel_info):
    """查找頻道的直播影片"""
    channel_name = channel_info["name"]
    channel_id = channel_info["channel_id"]
    
    log_message(f"開始查找: {channel_name}", "INFO")
    
    # 方法1: 從官方頻道獲取
    video_ids = get_channel_videos(channel_id)
    
    for video_id in video_ids:
        if is_live_stream(video_id):
            title = get_video_title(video_id)
            log_message(f"找到官方頻道直播: {title[:50]}...", "SUCCESS")
            return video_id
        
        # 避免請求過快
        time.sleep(0.3)
    
    # 方法2: 使用搜索關鍵字
    log_message(f"官方頻道未找到直播，嘗試搜索...", "INFO")
    
    # 嘗試多個關鍵字
    search_queries = []
    
    # 優先使用search_keywords
    for keyword in channel_info["search_keywords"]:
        search_queries.append(f"{channel_name} {keyword}")
    
    # 再嘗試fallback_keywords
    for keyword in channel_info.get("fallback_keywords", []):
        search_queries.append(keyword)
    
    # 去重
    search_queries = list(dict.fromkeys(search_queries))
    
    for query in search_queries:
        video_id = search_youtube_live(query)
        if video_id:
            title = get_video_title(video_id)
            log_message(f"通過搜索找到直播: {title[:50]}...", "SUCCESS")
            return video_id
        time.sleep(0.5)
    
    log_message(f"未找到直播", "WARNING")
    return None

def fetch_all_channels():
    """抓取所有頻道"""
    results = []
    success_count = 0
    
    log_message(f"開始抓取 {len(CHANNELS)} 個頻道", "INFO")
    
    for index, channel in enumerate(CHANNELS, 1):
        log_message(f"處理頻道 {index}/{len(CHANNELS)}: {channel['name']}", "INFO")
        
        video_id = find_channel_live(channel)
        
        if video_id:
            results.append({
                "name": channel["name"],
                "tvg_id": channel["tvg_id"],
                "logo": channel["logo"],
                "video_id": video_id,
                "title": get_video_title(video_id)
            })
            success_count += 1
            log_message(f"✓ {channel['name']} 成功", "SUCCESS")
        else:
            log_message(f"✗ {channel['name']} 失敗", "ERROR")
        
        # 頻道間隔
        if index < len(CHANNELS):
            time.sleep(1)
    
    log_message(f"抓取完成: {success_count}/{len(CHANNELS)} 成功", "SUMMARY")
    return results

def generate_m3u(channels):
    """生成M3U播放列表"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines = [
        '#EXTM3U url-tvg="http://epg.51zmt.top:8000/e.xml"',
        '# ==========================================',
        '# 台灣新聞 YouTube 直播源',
        '# 來源: YouTube官方頻道',
        f'# 更新時間: {now}',
        f'# 頻道總數: {len(channels)}',
        '# 生成工具: youtube_crawler.py',
        '# ==========================================',
        ''
    ]
    
    for ch in channels:
        lines.append(
            f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" '
            f'tvg-name="{ch["name"]}" '
            f'tvg-logo="{ch["logo"]}" '
            f'group-title="台灣新聞",{ch["name"]}'
        )
        lines.append(f'https://www.youtube.com/watch?v={ch["video_id"]}')
        lines.append('')
    
    return '\n'.join(lines)

def save_m3u_file(content, filename="live.m3u"):
    """保存M3U文件"""
    try:
        # 獲取當前腳本所在目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 在scripts目錄下創建文件
        filepath = os.path.join(script_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        log_message(f"M3U文件已保存到: {filepath}", "SUCCESS")
        
        # 同時嘗試在當前工作目錄也保存一份（用於GitHub Actions）
        try:
            work_dir = os.getcwd()
            if work_dir != script_dir:
                alt_path = os.path.join(work_dir, filename)
                with open(alt_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                log_message(f"備份保存到工作目錄: {alt_path}", "INFO")
        except:
            pass
        
        return filepath
        
    except Exception as e:
        log_message(f"保存文件失敗: {str(e)}", "ERROR")
        return None

def main():
    """主函數"""
    print("\n" + "="*60)
    print("🚀 台灣新聞 YouTube 直播抓取系統")
    print("="*60)
    
    # 顯示基本信息
    print(f"📡 頻道數量: {len(CHANNELS)} 個")
    print(f"🕐 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60)
    
    # 抓取頻道
    channels = fetch_all_channels()
    
    if not channels:
        print("\n❌ 錯誤: 沒有找到任何直播頻道")
        # 創建空的M3U文件
        empty_content = "#EXTM3U\n# 未找到直播頻道\n"
        save_m3u_file(empty_content)
        return
    
    # 生成M3U內容
    m3u_content = generate_m3u(channels)
    
    # 保存文件
    saved_path = save_m3u_file(m3u_content)
    
    if saved_path and os.path.exists(saved_path):
        # 顯示統計信息
        print("\n" + "="*60)
        print("📊 生成結果統計")
        print("="*60)
        print(f"✅ 成功頻道: {len(channels)} 個")
        print(f"📁 文件路徑: {saved_path}")
        print(f"📄 文件大小: {os.path.getsize(saved_path)} 字節")
        
        # 顯示頻道列表
        print("\n📺 成功抓取的頻道:")
        print("-"*40)
        for i, ch in enumerate(channels, 1):
            print(f"{i:2d}. {ch['name']:15} - {ch['title'][:40]}...")
        print("-"*40)
        
        # 顯示文件示例
        print("\n📄 M3U文件示例:")
        print("-"*40)
        lines = m3u_content.split('\n')[:15]
        for line in lines:
            print(line)
        if len(m3u_content.split('\n')) > 15:
            print("...")
        print("-"*40)
        
        print(f"\n✨ 任務完成! 文件已生成。")
    else:
        print("\n❌ 錯誤: 無法保存M3U文件")

if __name__ == "__main__":
    main()
