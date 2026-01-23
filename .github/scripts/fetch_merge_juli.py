import cloudscraper
import requests

# ---------- 国内 ----------
domestic_url = "https://raw.githubusercontent.com/xiasufern/AA/main/BB.m3u"
domestic_lines = []

try:
    r = requests.get(domestic_url, timeout=15)
    r.raise_for_status()
    domestic_lines = r.text.splitlines()
except:
    pass

# ---------- 斯玛特源 ----------
smart_url = "https://php.946985.filegear-sg.me/jackTV.m3u"
smt_lines = []

try:
    scraper = cloudscraper.create_scraper()
    r = scraper.get(smart_url, timeout=30)
    r.raise_for_status()

    lines = r.text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF") and any(
            k in lines[i].lower() for k in ["斯玛特", "smart"]
        ):
            smt_lines.append(lines[i])
            if i + 1 < len(lines):
                smt_lines.append(lines[i + 1])
            i += 2
        else:
            i += 1
except:
    pass

# ---------- 输出 ----------
with open("all-1.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")

    f.write("# ===== 国内 =====\n")
    f.write("\n".join(domestic_lines) + "\n\n")

    if smt_lines:
        f.write("# ===== SMT =====\n")
        f.write("\n".join(smt_lines) + "\n")

print("完成：斯玛特源已归类到 SMT")
