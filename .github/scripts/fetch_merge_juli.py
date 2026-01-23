import cloudscraper
import requests

# ---------- 国内源 ----------
domestic_lines = []
github_url = "https://raw.githubusercontent.com/xiasufern/AA/main/BB.m3u"
try:
    r = requests.get(github_url, timeout=15)
    r.raise_for_status()
    domestic_lines = r.text.splitlines()
    print(f"国内源共 {len(domestic_lines)} 行")
except Exception as e:
    print("抓取国内源失败:", e)

# ---------- JULI 频道 ----------
juli_lines = ["#EXTM3U"]
juli_url = "https://php.946985.filegear-sg.me/jackTV.m3u"

try:
    scraper = cloudscraper.create_scraper()
    r = scraper.get(juli_url, timeout=30)
    r.raise_for_status()
    
    for line in r.text.splitlines():
        if "JULI" in line.upper():  # 忽略大小写
            juli_lines.append(line)
    
    print(f"JULI 频道数量: {len(juli_lines)-1}")
except Exception as e:
    print("抓取 JULI 频道失败:", e)
    juli_lines = ["#EXTM3U"]

# ---------- 合并生成 all-1.m3u ----------
with open("all-1.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")
    
    # 国内源
    f.write("# ===== 国内 =====\n")
    f.write("\n".join(domestic_lines) + "\n\n")
    
    # JULI
    if len(juli_lines) > 1:
        f.write("# ===== JULI =====\n")
        f.write("\n".join(juli_lines[1:]))  # 去掉重复 #EXTM3U
        f.write("\n")

print("生成 all-1.m3u 完成！")
