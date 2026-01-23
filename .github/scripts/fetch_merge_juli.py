import cloudscraper
import requests

# ---------- 国内 ----------
domestic_url = "https://raw.githubusercontent.com/xiasufern/AA/main/BB.m3u"
domestic = []

try:
    r = requests.get(domestic_url, timeout=15)
    r.raise_for_status()
    domestic = r.text.splitlines()
except:
    pass

# ---------- 斯玛特（排除 加拿大 / Xumo / 整合 / 印度） ----------
iptv_url = "https://www.go-iptv.ggff.net/sub.php?user=PpFQ2ws-1nOoHZWF2d0Jo68g"

INCLUDE_KEYS = ["smart", "smt", "斯玛特"]

EXCLUDE_KEYS = [
    "canada", "加拿大",
    "xumo",
    "整合", "推流", "integration", "合集",
    "india", "indian", "印度",
    "hindi", "tamil", "telugu", "malayalam",
    "in-"
]

smt = []

scraper = cloudscraper.create_scraper()
r = scraper.get(iptv_url, timeout=30)
r.raise_for_status()

lines = r.text.splitlines()
i = 0

while i < len(lines) - 1:
    extinf = lines[i]
    url = lines[i + 1]

    if extinf.startswith("#EXTINF"):
        text = (extinf + url).lower()

        # 必须是斯玛特
        if not any(k in text for k in INCLUDE_KEYS):
            i += 1
            continue

        # 命中排除关键词直接丢弃
        if any(k in text for k in EXCLUDE_KEYS):
            i += 2
            continue

        smt.append(extinf)
        smt.append(url)
        i += 2
        continue

    i += 1

# ---------- 输出 ----------
with open("all-1.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")

    f.write("# ===== 国内 =====\n")
    f.write("\n".join(domestic) + "\n\n")

    f.write("# ===== SMT =====\n")
    f.write("\n".join(smt))

print(f"完成：SMT 频道数 {len(smt)//2}")
