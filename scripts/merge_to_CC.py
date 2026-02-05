#!/usr/bin/env python3
"""
CC.m3u 合并脚本
功能：
1. 从 https://stymei.sufern001.workers.dev/ 提取"🔥全网通港澳台"分组
2. 重命名为"全网通港澳台"
3. 与本地 BB.m3u 合并
4. 输出 CC.m3u
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

SOURCE_URL = "https://stymei.sufern001.workers.dev/"
BB_FILE = "BB.m3u"
OUTPUT_FILE = "CC.m3u"

SOURCE_GROUP = "🔥全网通港澳台"
TARGET_GROUP = "全网通港澳台"

# ================== 工具函数 ==================

def log(msg):
    """日志输出"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_source():
    """下载源数据"""
    try:
        log(f"从 {SOURCE_URL} 下载数据...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(SOURCE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        log(f"✅ 下载成功 ({len(response.text)} 字符)")
        return response.text
    except Exception as e:
        log(f"❌ 下载失败: {e}")
        return None

def load_local_m3u():
    """加载本地BB.m3u文件"""
    try:
        log(f"加载本地文件: {BB_FILE}")
        with open(BB_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.splitlines()
        log(f"✅ 本地文件加载成功 ({len(lines)} 行)")
        return lines
    except FileNotFoundError:
        log(f"⚠️  {BB_FILE} 不存在，使用空内容")
        return ["#EXTM3U", "# 本地频道列表"]
    except Exception as e:
        log(f"❌ 加载本地文件失败: {e}")
        return []

def extract_gat_channels(content):
    """提取港澳台分组内容"""
    log(f"正在提取分组: {SOURCE_GROUP}")
    
    lines = content.splitlines()
    channels = []
    in_target_section = False
    
    # 查找目标分组
    target_marker = f"{SOURCE_GROUP},#genre#"
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 找到目标分组
        if target_marker in line:
            log(f"✅ 在第 {i+1} 行找到目标分组")
            in_target_section = True
            continue
        
        # 如果在下个分组开始，停止收集
        if in_target_section and '#genre#' in line and SOURCE_GROUP not in line:
            log("到达下一个分组，停止提取")
            break
        
        # 收集频道行
        if in_target_section and line and ',' in line:
            # 检查是否是有效的频道行（有URL）
            parts = line.split(',')
            if len(parts) >= 2 and ('://' in parts[-1] or parts[-1].startswith('http')):
                channels.append(line)
    
    log(f"提取到 {len(channels)} 个港澳台频道")
    
    # 如果没有找到，显示所有分组供调试
    if not channels:
        log("⚠️  未提取到频道，所有分组如下:")
        for i, line in enumerate(lines):
            if '#genre#' in line:
                log(f"  第{i+1}行: {line}")
    
    return channels

def merge_content(local_lines, gat_channels):
    """合并本地内容和港澳台频道"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output_lines = []
    
    # 添加M3U头
    output_lines.append("#EXTM3U")
    output_lines.append(f"# CC.m3u - 生成时间: {timestamp}")
    output_lines.append(f"# 源URL: {SOURCE_URL}")
    output_lines.append(f"# 提取分组: {SOURCE_GROUP} → {TARGET_GROUP}")
    output_lines.append("")
    
    # 添加本地内容（跳过已存在的EXTM3U头）
    if local_lines:
        log(f"合并本地内容 ({len(local_lines)} 行)")
        extm3u_found = False
        for line in local_lines:
            line_stripped = line.strip()
            if line_stripped == "#EXTM3U" and not extm3u_found:
                extm3u_found = True
                continue
            output_lines.append(line)
        
        # 添加分隔行
        if local_lines and gat_channels:
            output_lines.append("")
            output_lines.append("#" + "=" * 60)
            output_lines.append("# 以下为提取的港澳台频道")
            output_lines.append("#" + "=" * 60)
            output_lines.append("")
    
    # 添加港澳台分组
    if gat_channels:
        log(f"添加港澳台分组 ({len(gat_channels)} 个频道)")
        output_lines.append(f"{TARGET_GROUP},#genre#")
        for channel in gat_channels:
            output_lines.append(channel)
    
    # 添加统计信息
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# 统计信息")
    output_lines.append(f"# 本地频道数: {len([l for l in local_lines if ',' in l and '://' in l])}")
    output_lines.append(f"# 港澳台频道数: {len(gat_channels)}")
    output_lines.append(f"# 生成时间: {timestamp}")
    output_lines.append("#" + "=" * 60)
    
    return output_lines

def save_output(content_lines):
    """保存到文件"""
    try:
        log(f"正在保存到 {OUTPUT_FILE}")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(content_lines))
        
        # 验证文件
        import os
        if os.path.exists(OUTPUT_FILE):
            file_size = os.path.getsize(OUTPUT_FILE)
            log(f"✅ 文件保存成功")
            log(f"   文件路径: {os.path.abspath(OUTPUT_FILE)}")
            log(f"   文件大小: {file_size} 字节")
            log(f"   总行数: {len(content_lines)}")
            
            # 显示文件头
            print("\n📋 文件前10行:")
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"   {i+1}: {line.rstrip()}")
                    else:
                        break
            
            return True
        else:
            log(f"❌ 文件保存失败")
            return False
            
    except Exception as e:
        log(f"❌ 保存失败: {e}")
        return False

# ================== 主流程 ==================

def main():
    log("开始生成 CC.m3u ...")
    print("=" * 70)
    
    # 1. 下载源数据
    source_content = download_source()
    if source_content is None:
        log("❌ 无法获取源数据，停止执行")
        return
    
    # 2. 提取港澳台频道
    gat_channels = extract_gat_channels(source_content)
    
    # 3. 加载本地文件
    local_lines = load_local_m3u()
    
    # 4. 合并内容
    output_lines = merge_content(local_lines, gat_channels)
    
    # 5. 保存文件
    success = save_output(output_lines)
    
    print("\n" + "=" * 70)
    if success:
        log("🎉 CC.m3u 生成成功!")
        log(f"📊 统计: 本地频道 + {len(gat_channels)}个港澳台频道")
    else:
        log("❌ CC.m3u 生成失败")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
