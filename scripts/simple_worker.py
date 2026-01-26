#!/usr/bin/env python3
"""最简单有效的版本"""

import requests
import os

print("=== 开始创建 CC.m3u ===")

# 1. 下载 BB.m3u
try:
    print("下载 BB.m3u...")
    bb_url = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
    response = requests.get(bb_url, timeout=10)
    bb_content = response.text
    print(f"✅ 下载成功: {len(bb_content)} 字符")
except Exception as e:
    print(f"❌ 下载失败: {e}")
    bb_content = "#EXTM3U\n# 备用内容\n\n"

# 2. 创建 CC.m3u
output = f"""#EXTM3U
# 自动生成的 M3U 文件
# 生成时间: 2026-01-26
# GitHub Actions 生成

{bb_content}
"""

# 3. 保存文件
try:
    with open("CC.m3u", "w", encoding="utf-8") as f:
        f.write(output)
    
    # 验证文件
    if os.path.exists("CC.m3u"):
        size = os.path.getsize("CC.m3u")
        print(f"\n🎉 创建成功!")
        print(f"📁 文件: CC.m3u")
        print(f"📏 大小: {size} 字节")
        print(f"📁 路径: {os.path.abspath('CC.m3u')}")
        
        # 显示目录内容
        print(f"\n📂 当前目录:")
        for item in os.listdir('.'):
            print(f"  - {item}")
    else:
        print("❌ 文件创建失败!")
        
except Exception as e:
    print(f"❌ 保存文件失败: {e}")
    import traceback
    traceback.print_exc()
