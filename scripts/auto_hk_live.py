import subprocess
import requests
import yaml
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YML_FILE = os.path.join(BASE_DIR, "channels.yml")
EE_FILE = os.path.join(BASE_DIR, "EE.m3u")
LOG_FILE = os.path.join(BASE_DIR, "generate.log")

def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {msg}\n")

def load_config():
    with open(YML_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def search_hk_live_channels(keyword, max_channels=20):
    """搜索 YouTube 直播频道"""
    url = f"https://www.youtube.com/results?search_query={keyword.replace(' ','+')}&sp=EgJAAQ%3D%3D"
    channels = {}
    try:
        r = requests.get(url, timeout=10)
        html = r.text
        for part in html.split('"'):
            if "channelId" in part:
                parts = part.split("channelId")
                for p in parts[1:]:
                    cid = p.split('"')[2] if len(p.split('"'))>2 else None
                    if cid and cid not in channels:
                        channels[cid] = None
        return list(channels.keys())[:max_channels]
    except Exception as e:
        log(f"搜索失败: {keyword} -> {e}")
        return []

def get_live_m3u8_title_logo(channel_id):
    """获取直播 m3u8、标题、logo，实时检测是否开播"""
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    try:
        # 获取 m3u8
        result = subprocess.run(
            ["yt-dlp", "-g", "-f", "best", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20
        )
        m3u8_url = result.stdout.strip()
        if not m3u8_url.startswith("http"):
            return None, None, None  # 未开播

        # 获取标题
        result_title = subprocess.run(
            ["yt-dlp", "--get-title", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        title = result_title.stdout.strip() or channel_id

        # 获取logo
        result_logo = subprocess.run(
            ["yt-dlp", "--get-thumbnail", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        logo = result_logo.stdout.strip() or ""

        return m3u8_url, title, logo
    except Exception as e:
        log(f"[{channel_id}] 获取 m3u8/title/logo 失败: {e}")
        return None, None, None

def generate_m3u(channel_list, group_name="香港直播"):
    lines = ["#EXTM3U"]
    for ch in channel_list:
        lines.append(f'#EXTINF:-1 tvg-name="{ch["title"]}" tvg-logo="{ch["logo"]}" group-title="{group_name}",{ch["title"]}')
        lines.append(ch["url"])
    with open(EE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"EE.m3u 已更新, 共 {len(channel_list)} 个直播频道")

def main():
    config = load_config()
    keywords = config.get("keywords", [])
    max_channels = config.get("max_channels", 20)
    group_name = config.get("group_name", "香港直播")

    seen_titles = set()
    channel_list = []

    for kw in keywords:
        ids = search_hk_live_channels(kw, max_channels)
        for cid in ids:
            m3u8, title, logo = get_live_m3u8_title_logo(cid)
            if m3u8 and title not in seen_titles:
                channel_list.append({"title": title, "url": m3u8, "logo": logo})
                seen_titles.add(title)
                log(f"[{title}] 添加成功 -> {m3u8}")
            elif not m3u8:
                log(f"[{cid}] 当前未开播，跳过")

    if channel_list:
        generate_m3u(channel_list, group_name)
    else:
        log("未抓取到任何直播频道")

if __name__ == "__main__":
    main()
