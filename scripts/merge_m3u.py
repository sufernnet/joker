#!/usr/bin/env python3
"""
自动合并 M3U 文件脚本
每天 6:00 和 18:00 自动更新
"""

import requests
import os
import sys
import time
from datetime import datetime

def log_message(message):
    """添加时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def download_file(url, filename):
    """下载文件并保存"""
    try:
        log_message(f"正在下载 {filename}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        log_message(f"✅ {filename} 下载成功 ({len(response.text)} 字符)")
        return response.text
    except Exception as e:
        log_message(f"❌ 下载 {filename} 失败：{e}")
        raise

def extract_juli_channels(content):
    """从内容中提取所有 JULI 频道"""
    lines = content.split('\n')
    juli_channels = []
    found_channels = []
    
    # 寻找所有包含 JULI 的频道
    for i in range(len(lines)):
        if 'JULI' in lines[i].upper():
            # 向前查找 #EXTINF 行
            for j in range(max(0, i-3), i+1):
                if j < len(lines) and lines[j].startswith('#EXTINF:'):
                    # 提取频道名称
                    channel_info = lines[j]
                    if ',' in channel_info:
                        channel_name = channel_info.split(',', 1)[1].strip()
                        
                        # 查找对应的 URL
                        for k in range(j+1, min(len(lines), j+6)):
                            if k < len(lines) and lines[k].strip() and not lines[k].startswith('#'):
                                url = lines[k].strip()
                                
                                # 避免重复
                                if channel_name not in found_channels:
                                    juli_channels.append((channel_info, url))
                                    found_channels.append(channel_name)
                                break
                    break
    
    return juli_channels

def merge_m3u_files():
    """主合并函数"""
    log_message("🚀 开始合并 M3U 文件...")
    
    # 显示当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message(f"📅 运行时间: {current_time}")
    
    try:
        # 1. 下载第一个文件 (BB.m3u)
        bb_url = "https://raw.githubusercontent.com/sufernnet/joker/blob/main/BB.m3u"
        # 使用原始文件链接
        bb_url = bb_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        bb_content = download_file(bb_url, "BB_temp.m3u")
        
        # 2. 下载第二个文件
        second_url = "https://smart.946985.filegear-sg.me/sub.php?user=tg_Thinkoo_bot"
        second_content = download_file(second_url, "second_temp.m3u")
        
    except Exception as e:
        log_message(f"❌ 下载源文件失败，使用备用方案...")
        # 备用方案：如果有旧的 CC.m3u，复制它
        if os.path.exists("CC.m3u"):
            with open("CC.m3u", "r", encoding="utf-8") as f:
                return f.read()
        else:
            raise
    
    # 3. 从第二个文件中提取 JULI 频道
    log_message("🔍 正在提取 JULI 频道...")
    juli_channels = extract_juli_channels(second_content)
    
    log_message(f"📊 找到 {len(juli_channels)} 个 JULI 频道")
    
    # 4. 合并内容
    output_content = f"#EXTM3U x-tvg-url=\"\"\n"
    output_content += f"# 自动合并 M3U 文件\n"
    output_content += f"# 生成时间: {current_time}\n"
    output_content += f"# 更新频率: 每天 06:00 和 18:00（北京时间）\n"
    output_content += f"# 源1: {bb_url}\n"
    output_content += f"# 源2: {second_url}\n"
    output_content += f"# 包含 JULI 频道: {len(juli_channels)} 个\n\n"
    
    # 添加 BB.m3u 内容（跳过开头的 #EXTM3U 如果存在）
    bb_lines = bb_content.split('\n')
    added_bb = 0
    for line in bb_lines:
        if line.strip():
            if line.startswith('#EXTM3U'):
                continue
            output_content += line + '\n'
            if line.startswith('#EXTINF:'):
                added_bb += 1
    
    # 添加 JULI 频道
    if juli_channels:
        output_content += f"\n# {'='*50}\n"
        output_content += f"# JULI 频道 ({len(juli_channels)} 个)\n"
        output_content += f"# {'='*50}\n\n"
        
        for extinf, url in juli_channels:
            output_content += extinf + '\n'
            output_content += url + '\n'
    
    # 5. 保存为 CC.m3u
    output_file = "CC.m3u"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    # 6. 清理临时文件
    for temp_file in ["BB_temp.m3u", "second_temp.m3u"]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    # 7. 输出统计信息
    log_message(f"\n🎉 合并完成！")
    log_message(f"📁 生成文件: {output_file}")
    log_message(f"📏 文件大小: {len(output_content)} 字符")
    log_message(f"📺 BB 频道数: {added_bb}")
    log_message(f"📺 JULI 频道数: {len(juli_channels)}")
    log_message(f"📺 总频道数: {added_bb + len(juli_channels)}")
    
    # 显示 JULI 频道名称
    if juli_channels:
        log_message("\n📋 JULI 频道列表:")
        for extinf, url in juli_channels:
            if ',' in extinf:
                channel_name = extinf.split(',', 1)[1].strip()
                log_message(f"  • {channel_name}")
    
    return output_content

def main():
    """主函数"""
    start_time = time.time()
    
    try:
        merge_m3u_files()
        
        # 计算运行时间
        end_time = time.time()
        run_time = end_time - start_time
        log_message(f"⏱️ 脚本运行时间: {run_time:.2f} 秒")
        
        # 写入状态文件
        with open("last_update.txt", "w", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        sys.exit(0)
        
    except Exception as e:
        log_message(f"❌ 脚本执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
