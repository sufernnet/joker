#!/usr/bin/env python3
"""
自动合并 M3U 文件脚本
每天 6:00 和 18:00 自动更新
修复版：处理 403 错误
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

def download_with_retry(url, filename, max_retries=3):
    """下载文件，带重试机制和多种 User-Agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        'curl/7.68.0',
        'python-requests/2.31.0'
    ]
    
    headers_list = [
        {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        } for ua in user_agents
    ]
    
    for attempt in range(max_retries):
        try:
            headers = headers_list[attempt % len(headers_list)]
            
            log_message(f"尝试 {attempt + 1}/{max_retries} 下载 {filename}...")
            
            # 对于第二个URL，可能需要添加referer
            if 'filegear-sg.me' in url:
                headers['Referer'] = 'https://www.google.com/'
                headers['Origin'] = 'https://smart.946985.filegear-sg.me'
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            log_message(f"✅ {filename} 下载成功 ({len(response.text)} 字符)")
            
            # 检查是否是有效的M3U文件
            if filename.endswith('.m3u') and not response.text.strip().startswith('#EXTM3U'):
                log_message(f"⚠️  警告: {filename} 可能不是有效的M3U文件")
                log_message(f"前100字符: {response.text[:100]}")
            
            return response.text
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                log_message(f"❌ 尝试 {attempt + 1} 失败: 403 Forbidden")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                else:
                    raise
            else:
                log_message(f"❌ HTTP错误 {e.response.status_code}: {e}")
                raise
        except requests.exceptions.RequestException as e:
            log_message(f"❌ 网络错误: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise
    
    raise Exception(f"下载失败，已尝试 {max_retries} 次")

def extract_juli_channels(content):
    """从内容中提取所有 JULI 频道"""
    if not content:
        return []
    
    lines = content.split('\n')
    juli_channels = []
    found_channels = []
    
    # 方法1：直接搜索 JULI
    for i in range(len(lines)):
        line = lines[i].strip()
        if line and 'JULI' in line.upper():
            # 查找对应的 #EXTINF 行
            for j in range(max(0, i-5), i+1):
                if j < len(lines) and lines[j].startswith('#EXTINF:'):
                    extinf_line = lines[j]
                    
                    # 查找对应的 URL（从当前行向下找）
                    for k in range(max(i, j)+1, min(len(lines), max(i, j)+6)):
                        url_line = lines[k].strip()
                        if url_line and not url_line.startswith('#') and '://' in url_line:
                            # 避免重复
                            channel_key = f"{extinf_line}|{url_line}"
                            if channel_key not in found_channels:
                                juli_channels.append((extinf_line, url_line))
                                found_channels.append(channel_key)
                            break
                    break
    
    # 方法2：如果方法1没找到，尝试按M3U格式解析
    if not juli_channels:
        for i in range(len(lines)):
            if lines[i].startswith('#EXTINF:'):
                if 'JULI' in lines[i].upper():
                    # 找下一个非#开头的行作为URL
                    for j in range(i+1, min(len(lines), i+4)):
                        if lines[j].strip() and not lines[j].startswith('#'):
                            juli_channels.append((lines[i], lines[j].strip()))
                            break
    
    return juli_channels

def merge_m3u_files():
    """主合并函数"""
    log_message("🚀 开始合并 M3U 文件...")
    
    # 显示当前时间
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message(f"📅 运行时间: {current_time}")
    
    # 1. 下载第一个文件 (BB.m3u)
    try:
        bb_url = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
        log_message(f"🔗 源1: {bb_url}")
        bb_content = download_with_retry(bb_url, "BB_temp.m3u")
    except Exception as e:
        log_message(f"❌ 无法下载BB.m3u: {e}")
        # 如果已有CC.m3u，使用它
        if os.path.exists("CC.m3u"):
            log_message("🔄 使用现有的CC.m3u作为基础")
            with open("CC.m3u", "r", encoding="utf-8") as f:
                return f.read()
        else:
            raise Exception("无法下载BB.m3u且没有现有文件")
    
    # 2. 尝试下载第二个文件（带多种尝试）
    second_content = ""
    second_url = "https://smart.946985.filegear-sg.me/sub.php?user=tg_Thinkoo_bot"
    log_message(f"🔗 源2: {second_url}")
    
    try:
        second_content = download_with_retry(second_url, "second_temp.m3u")
    except Exception as e:
        log_message(f"⚠️  警告: 无法下载第二个源: {e}")
        log_message("🔄 将继续使用仅BB.m3u的内容")
        # 检查是否有旧的second_temp文件
        if os.path.exists("second_temp.m3u"):
            with open("second_temp.m3u", "r", encoding="utf-8") as f:
                second_content = f.read()
                log_message("📂 使用之前保存的第二个源缓存")
    
    # 3. 从第二个文件中提取 JULI 频道
    juli_channels = []
    if second_content:
        log_message("🔍 正在提取 JULI 频道...")
        juli_channels = extract_juli_channels(second_content)
        log_message(f"📊 找到 {len(juli_channels)} 个 JULI 频道")
        
        # 显示找到的频道
        if juli_channels:
            log_message("📋 找到的JULI频道:")
            for extinf, url in juli_channels[:10]:  # 只显示前10个
                if ',' in extinf:
                    channel_name = extinf.split(',', 1)[1].strip()
                    log_message(f"  • {channel_name}")
            if len(juli_channels) > 10:
                log_message(f"  ... 还有 {len(juli_channels) - 10} 个频道")
    else:
        log_message("⚠️  第二个源为空，无法提取JULI频道")
    
    # 4. 计算统计信息
    bb_lines = bb_content.split('\n')
    bb_channels = sum(1 for line in bb_lines if line.startswith('#EXTINF:'))
    
    # 5. 合并内容
    output_content = f"#EXTM3U x-tvg-url=\"\"\n"
    output_content += f"# {'='*60}\n"
    output_content += f"# 自动合并 M3U 文件\n"
    output_content += f"# 生成时间: {current_time}\n"
    output_content += f"# 更新频率: 每天 06:00 和 18:00（北京时间）\n"
    output_content += f"# 源1: {bb_url}\n"
    output_content += f"# 源2: {second_url}\n"
    output_content += f"# BB 频道数: {bb_channels}\n"
    output_content += f"# JULI 频道数: {len(juli_channels)}\n"
    output_content += f"# {'='*60}\n\n"
    
    # 添加 BB.m3u 内容（跳过可能重复的#EXTM3U）
    added_channels = 0
    for line in bb_lines:
        line = line.rstrip()
        if line:
            if line.startswith('#EXTM3U'):
                continue
            output_content += line + '\n'
            if line.startswith('#EXTINF:'):
                added_channels += 1
    
    # 添加 JULI 频道
    if juli_channels:
        output_content += f"\n{'#'*70}\n"
        output_content += f"# JULI 频道区域 ({len(juli_channels)} 个)\n"
        output_content += f"{'#'*70}\n\n"
        
        for extinf, url in juli_channels:
            output_content += extinf + '\n'
            output_content += url + '\n'
            added_channels += 1
    
    # 6. 添加文件尾部信息
    output_content += f"\n{'#'*70}\n"
    output_content += f"# 文件统计\n"
    output_content += f"# 总频道数: {added_channels}\n"
    output_content += f"# 最后更新: {current_time}\n"
    output_content += f"# GitHub Actions 自动生成\n"
    output_content += f"{'#'*70}\n"
    
    # 7. 保存为 CC.m3u
    output_file = "CC.m3u"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    # 8. 保存第二个源的缓存（供下次使用）
    if second_content and len(second_content) > 100:
        with open("second_backup.m3u", 'w', encoding='utf-8') as f:
            f.write(second_content)
    
    # 9. 清理临时文件
    for temp_file in ["BB_temp.m3u", "second_temp.m3u"]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    # 10. 输出最终统计
    log_message(f"\n{'='*60}")
    log_message("🎉 合并完成！")
    log_message(f"📁 输出文件: {output_file}")
    log_message(f"📏 文件大小: {len(output_content):,} 字符")
    log_message(f"📺 原始BB频道: {bb_channels}")
    log_message(f"📺 添加JULI频道: {len(juli_channels)}")
    log_message(f"📺 频道总数: {added_channels}")
    log_message(f"{'='*60}")
    
    # 保存更新记录
    with open("update_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{current_time} | BB:{bb_channels} | JULI:{len(juli_channels)} | TOTAL:{added_channels}\n")
    
    return output_content

def main():
    """主函数"""
    start_time = time.time()
    
    try:
        merge_m3u_files()
        
        # 计算运行时间
        end_time = time.time()
        run_time = end_time - start_time
        log_message(f"⏱️  脚本运行时间: {run_time:.2f} 秒")
        
        sys.exit(0)
        
    except Exception as e:
        log_message(f"❌ 脚本执行失败: {e}")
        
        # 尝试保存错误日志
        try:
            with open("error_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {str(e)}\n")
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
