#!/usr/bin/env python3
"""
只做两件事：
1. 合并重复的NOW新闻台（只保留一个）
2. 體育世界中NOW频道排最前
其他保持原样
"""

import requests
import re
import os
import sys
from datetime import datetime

SOURCE_URL = "https://raw.githubusercontent.com/yihad168/tv/refs/heads/main/tv.m3u"
EPG_URL = "http://epg.51zmt.top:8000/e.xml"

def main():
    print("开始处理...")
    
    # 1. 下载源文件
    response = requests.get(SOURCE_URL, timeout=30)
    content = response.text
    
    # 2. 按行分割
    lines = content.split('\n')
    
    # 3. 准备存储
    all_channels = []
    now_news_count = 0
    current_section = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("#EXTINF"):
            # 检查分组
            if 'group-title="港澳頻道"' in line or 'group-title="體育世界"' in line:
                # 找到对应的URL
                j = i + 1
                while j < len(lines):
                    url_line = lines[j].strip()
                    if url_line and not url_line.startswith('#'):
                        break
                    j += 1
                
                if j < len(lines):
                    url = lines[j].strip()
                    
                    # 只对NOW新闻台去重
                    if 'NOW新闻台' in line or 'NOW新聞台' in line:
                        now_news_count += 1
                        if now_news_count == 1:  # 只保留第一个
                            all_channels.append((line, url))
                            print(f"保留NOW新闻台")
                        else:
                            print(f"跳过重复的NOW新闻台")
                    else:
                        all_channels.append((line, url))
                    
                    i = j  # 跳过URL行
        i += 1
    
    print(f"总共找到 {len(all_channels)} 个频道")
    print(f"NOW新闻台: {now_news_count} 个（只保留第一个）")
    
    # 4. 分离體育世界中的NOW频道
    hk_channels = []
    sports_now_channels = []
    sports_other_channels = []
    
    for extinf, url in all_channels:
        if 'group-title="港澳頻道"' in extinf:
            hk_channels.append((extinf, url))
        elif 'group-title="體育世界"' in extinf:
            if 'NOW' in extinf.upper():
                sports_now_channels.append((extinf, url))
            else:
                sports_other_channels.append((extinf, url))
    
    print(f"港澳頻道: {len(hk_channels)} 个")
    print(f"體育世界-NOW频道: {len(sports_now_channels)} 个")
    print(f"體育世界-其他频道: {len(sports_other_channels)} 个")
    
    # 5. 构建输出
    output_lines = []
    
    # 文件头
    output_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    output_lines.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append(f"# 源地址: {SOURCE_URL}")
    output_lines.append(f"# EPG源: {EPG_URL}")
    output_lines.append("# 修改: 1.NOW新闻台去重 2.體育世界NOW优先")
    output_lines.append("")
    
    # 读取BB.m3u（如果有）
    if os.path.exists("../BB.m3u"):
        with open("../BB.m3u", 'r', encoding='utf-8') as f:
            bb_content = f.read()
        bb_lines = bb_content.split('\n')
        for line in bb_lines:
            if line.strip() and not line.strip().startswith("#EXTM3U"):
                output_lines.append(line.rstrip())
        output_lines.append("")
        print("已合并BB.m3u")
    
    # 添加港澳頻道（保持原顺序）
    if hk_channels:
        output_lines.append("# 港澳頻道")
        for extinf, url in hk_channels:
            output_lines.append(extinf)
            output_lines.append(url)
        output_lines.append("")
    
    # 添加體育世界（NOW频道在前）
    if sports_now_channels or sports_other_channels:
        output_lines.append("# 體育世界")
        
        # NOW频道在前
        if sports_now_channels:
            for extinf, url in sports_now_channels:
                output_lines.append(extinf)
                output_lines.append(url)
        
        # 其他频道在后
        if sports_other_channels:
            if sports_now_channels:
                output_lines.append("")  # 空行分隔
            for extinf, url in sports_other_channels:
                output_lines.append(extinf)
                output_lines.append(url)
    
    # 6. 保存文件
    output_path = "../EE.m3u"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    # 7. 验证
    with open(output_path, 'r', encoding='utf-8') as f:
        final_content = f.read()
    
    final_now_news = final_content.count("NOW新闻台") + final_content.count("NOW新聞台")
    print(f"\n✅ 处理完成")
    print(f"文件保存到: {output_path}")
    print(f"文件大小: {len(final_content)} 字节")
    print(f"频道总数: {final_content.count('#EXTINF')}")
    print(f"NOW新闻台数量: {final_now_news}（应=1）")
    
    if final_now_news > 1:
        print("警告: NOW新闻台可能重复！")
        sys.exit(1)

if __name__ == "__main__":
    main()
