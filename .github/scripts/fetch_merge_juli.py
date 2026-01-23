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

# ---------- JULI（只抓 JULI，但分组叫“香港”） ----------
juli_url = "https://php.946985.filegear-sg.me/jackTV.m3u"
hk = []

try:
    s = cloudscraper.create_scraper()
    r = s.get(juli_url, timeout=30)
    r.raise_for_status()

    lines = r.text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and "JULI" in lines[i].upper():
            hk.append(lines[i])
            if i + 1 < len(lines):
                hk.append(lines[i + 1])
            i += 2
        else:
            i += 1
except:
    pass

# ---------- 输出 ----------
with open("all-1.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")

    f.write("# ===== 国内 =====\n")
    f.write("\n".join(domestic) + "\n\n")

    if hk:
        f.write("# ===== 香港 =====\n")
        f.write("\n".join(hk) + "\n")

print("完成：JULI 已归类到【香港】")
