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

# ---------- JULI 频道（抓 #EXTINF + URL） ----------
juli_lines = ["#EXTM3U"]
juli_url = "https://php.946985.filegear-sg.me/jackTV.m3u"

try:
    scraper = cloudscraper.create_scraper()
    r = scraper.get(juli_url, timeout=30)
    r.raise_for_status()

    lines = r.text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if "JULI" in line.upper():  # 匹配 #EXTINF 行
            juli_lines.append(line)  # 加入 #EXTINF
            if i + 1 < len(lines):
                juli_lines.append(lines[i + 1])  # 加入对应 URL
            i += 2
        else:
            i += 1

    print(f"抓到 {len(juli_lines)//2} JULI 频道（包含播放链接）")
except Exception as e:
    print("抓取 JULI 频道失败:", e)
    juli_lines = ["#EXTM3U"]

# ---------- 合并生成 all-1.m3u ----------
output_path = "all-1.m3u"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")

    # 国内源
    f.write("# ===== 国内 =====\n")
    f.write("\n".join(domestic_lines) + "\n\n")

    # JULI
    if len(juli_lines) > 1:
        f.write("# ===== JULI =====\n")
        f.write("\n".join(juli_lines[1:]))  # 去掉重复 #EXTM3U
        f.write("\n")

print(f"生成 {output_path} 完成！")
