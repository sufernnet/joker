import cloudscraper
import requests

# ---------- 国内 ----------
domestic_url = "https://raw.githubusercontent.com/xiasufern/AA/main/BB.m3u"
domestic = []

try:
    r = requests.get(domestic_url, timeout=15)
    r.raise_for_status()
    domestic = r.text.splitlines()
    print(f"国内源行数: {len(domestic)}")
except Exception as e:
    print("国内源失败:", e)

# ---------- 斯玛特源（更稳的匹配方式） ----------
smart_url = "https://php.946985.filegear-sg.me/jackTV.m3u"
smt = []

KEYWORDS = ["smart", "smt", "斯玛特"]

try:
    s = cloudscraper.create_scraper()
    r = s.get(smart_url, timeout=30)
    r.raise_for_status()

    lines = r.text.splitlines()
    i = 0
    while i < len(lines) - 1:
        extinf = lines[i]
        url = lines[i + 1]

        if extinf.startswith("#EXTINF"):
            text = (extinf + url).lower()
            if any(k in text for k in KEYWORDS):
                smt.append(extinf)
                smt.append(url)
                i += 2
                continue
        i += 1

    print(f"斯玛特频道数: {len(smt)//2}")
except Exception as e:
    print("斯玛特抓取失败:", e)

# ---------- 输出 ----------
with open("all-1.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")

    f.write("# ===== 国内 =====\n")
    f.write("\n".join(domestic) + "\n\n")

    if smt:
        f.write("# ===== SMT =====\n")
        f.write("\n".join(smt) + "\n")

print("完成：斯玛特源已正确提取并归类到 SMT")
