#!/usr/bin/env python3
"""
从TV源中提取"港澳頻道"和"體育世界"并与BB.m3u合并，保存为EE.m3u
优化版本：提高运行速度
"""

import requests
import re
import os
import sys
from datetime import datetime
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
SOURCE_URL = "https://raw.githubusercontent.com/yihad168/tv/refs/heads/main/tv.m3u"
EPG_URL = "http://epg.51zmt.top:8000/e.xml"
BB_FILE = "BB.m3u"
OUTPUT_FILE = "../EE.m3u"

def fetch_m3u_content():
    """获取原始M3U文件内容"""
    try:
        logger.info(f"正在从 {SOURCE_URL} 下载M3U文件...")
        start_time = time.time()
        response = requests.get(SOURCE_URL, timeout=60)  # 增加超时时间
        response.raise_for_status()
        elapsed = time.time() - start_time
        logger.info(f"下载成功，耗时: {elapsed:.2f}秒，大小: {len(response.text)} 字符")
        return response.text
    except requests.RequestException as e:
        logger.error(f"下载M3U文件失败: {e}")
        return None

def read_bb_file():
    """读取BB.m3u文件内容"""
    try:
        bb_path = "../BB.m3u"
        if os.path.exists(bb_path):
            with open(bb_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"读取BB.m3u成功，大小: {len(content)} 字符")
            return content
        else:
            logger.warning(f"BB.m3u文件不存在: {bb_path}")
            return None
    except Exception as e:
        logger.error(f"读取BB.m3u失败: {e}")
        return None

def extract_and_sort_channels_fast(content):
    """快速提取和排序频道"""
    if not content:
        return None
    
    logger.info("开始快速提取指定分组频道...")
    start_time = time.time()
    
    # 预编译正则表达式，提高速度
    group_pattern = re.compile(r'group-title="([^"]+)"')
    channel_name_pattern = re.compile(r',([^,]+)$')
    
    # 目标分组
    target_groups = {"港澳頻道", "體育世界"}
    
    # 存储频道
    categories = {
        'phoenix': [],      # 凤凰频道
        'now_hk': [],       # NOW港澳频道（去重）
        'other_hk': [],     # 其他港澳频道
        'now_sports': [],   # NOW体育频道
        'other_sports': []  # 其他体育频道
    }
    
    # 用于去重的集合
    seen_now_hk = set()     # NOW港澳频道名称去重
    seen_urls = set()       # URL去重（防止完全相同的频道）
    
    # 快速分割行
    lines = content.split('\n')
    total_lines = len(lines)
    logger.info(f"开始处理 {total_lines} 行数据...")
    
    i = 0
    processed_count = 0
    
    while i < total_lines:
        line = lines[i].strip()
        
        if line and line.startswith("#EXTINF"):
            # 快速检查是否包含目标分组
            if any(f'group-title="{group}"' in line for group in target_groups):
                processed_count += 1
                
                # 提取分组信息
                group_match = group_pattern.search(line)
                if not group_match:
                    i += 1
                    continue
                    
                group_name = group_match.group(1)
                
                # 查找URL行
                url_line = ""
                j = i + 1
                while j < total_lines:
                    temp_line = lines[j].strip()
                    if temp_line and not temp_line.startswith("#"):
                        url_line = temp_line
                        break
                    j += 1
                
                if url_line:
                    # URL去重
                    if url_line in seen_urls:
                        i = j
                        continue
                    seen_urls.add(url_line)
                    
                    # 提取频道名称
                    name_match = channel_name_pattern.search(line)
                    channel_name = name_match.group(1).strip() if name_match else ""
                    
                    # 港澳頻道处理
                    if group_name == "港澳頻道":
                        line_upper = line.upper()
                        
                        # 检查凤凰频道
                        if '凤凰' in line or '鳳凰' in line or 'PHOENIX' in line_upper:
                            categories['phoenix'].append((line, url_line, channel_name))
                        
                        # 检查NOW频道（需要去重）
                        elif 'NOW' in line_upper:
                            # 标准化NOW新闻台名称
                            if 'NOW新闻台' in channel_name or 'NOW新聞台' in channel_name:
                                std_name = 'NOW新闻台'
                            else:
                                std_name = channel_name
                            
                            # NOW频道去重
                            if std_name not in seen_now_hk:
                                seen_now_hk.add(std_name)
                                categories['now_hk'].append((line, url_line, channel_name))
                        
                        # 其他港澳频道
                        else:
                            categories['other_hk'].append((line, url_line, channel_name))
                    
                    # 體育世界处理
                    elif group_name == "體育世界":
                        if 'NOW' in line.upper():
                            categories['now_sports'].append((line, url_line, channel_name))
                        else:
                            categories['other_sports'].append((line, url_line, channel_name))
                    
                    i = j  # 跳过URL行
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1
    
    elapsed = time.time() - start_time
    logger.info(f"处理完成，耗时: {elapsed:.2f}秒")
    logger.info(f"处理了 {processed_count} 个频道条目")
    
    # 统计
    logger.info("=== 提取统计 ===")
    for cat_name, cat_list in categories.items():
        logger.info(f"{cat_name}: {len(cat_list)} 个")
    
    total_channels = sum(len(cat) for cat in categories.values())
    logger.info(f"总计提取: {total_channels} 个频道")
    
    if total_channels == 0:
        return None
    
    # 构建输出内容
    result_lines = [f'#EXTM3U url-tvg="{EPG_URL}"']
    result_lines.append("# 排序规则: 港澳頻道(凤凰→NOW去重→其他) | 體育世界(NOW→其他)")
    result_lines.append("")
    
    # 添加港澳頻道
    if any(len(categories[cat]) > 0 for cat in ['phoenix', 'now_hk', 'other_hk']):
        result_lines.append("#" + "=" * 50)
        result_lines.append("# 港澳頻道")
        result_lines.append("#" + "=" * 50)
        
        # 凤凰频道
        if categories['phoenix']:
            result_lines.append("## 凤凰频道")
            for extinf, url, name in categories['phoenix']:
                result_lines.append(extinf)
                result_lines.append(url)
        
        # NOW港澳频道
        if categories['now_hk']:
            result_lines.append("## NOW频道")
            for extinf, url, name in categories['now_hk']:
                result_lines.append(extinf)
                result_lines.append(url)
        
        # 其他港澳频道
        if categories['other_hk']:
            result_lines.append("## 其他港澳频道")
            for extinf, url, name in categories['other_hk']:
                result_lines.append(extinf)
                result_lines.append(url)
        
        result_lines.append("")
    
    # 添加體育世界
    if any(len(categories[cat]) > 0 for cat in ['now_sports', 'other_sports']):
        result_lines.append("#" + "=" * 50)
        result_lines.append("# 體育世界")
        result_lines.append("#" + "=" * 50)
        
        # NOW体育频道
        if categories['now_sports']:
            result_lines.append("## NOW体育频道")
            for extinf, url, name in categories['now_sports']:
                result_lines.append(extinf)
                result_lines.append(url)
        
        # 其他体育频道
        if categories['other_sports']:
            result_lines.append("## 其他体育频道")
            for extinf, url, name in categories['other_sports']:
                result_lines.append(extinf)
                result_lines.append(url)
    
    return '\n'.join(result_lines)

def merge_with_bb_fast(tv_content, bb_content):
    """快速合并内容"""
    result_lines = []
    
    # 头部信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    result_lines.append(f"# 生成时间: {timestamp}")
    result_lines.append(f"# 源地址: {SOURCE_URL}")
    result_lines.append(f"# EPG源: {EPG_URL}")
    result_lines.append("# 包含: BB.m3u + 港澳頻道 + 體育世界")
    result_lines.append("# 排序: 港澳頻道(凤凰→NOW去重→其他) | 體育世界(NOW→其他)")
    result_lines.append("")
    
    # 添加BB内容
    if bb_content:
        bb_lines = bb_content.split('\n')
        bb_count = 0
        for line in bb_lines:
            line = line.strip()
            if line:
                if line.startswith("#EXTM3U"):
                    continue
                if line.startswith("#EXTINF"):
                    bb_count += 1
                result_lines.append(line)
        
        if bb_count > 0:
            logger.info(f"合并BB频道: {bb_count} 个")
            result_lines.append("")
            result_lines.append("#" + "=" * 60)
            result_lines.append("# 以下为提取的港澳頻道和體育世界")
            result_lines.append("#" + "=" * 60)
            result_lines.append("")
    
    # 添加TV内容（跳过第一个#EXTM3U）
    if tv_content:
        tv_lines = tv_content.split('\n')
        skip_first_extm3u = True
        for line in tv_lines:
            line = line.strip()
            if line:
                if line.startswith("#EXTM3U") and skip_first_extm3u:
                    skip_first_extm3u = False
                    continue
                result_lines.append(line)
    
    return '\n'.join(result_lines)

def save_m3u_file(content):
    """保存M3U文件"""
    if not content:
        logger.error("没有内容可保存")
        return False
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(os.path.dirname(script_dir), "EE.m3u")
        
        logger.info(f"正在保存到: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            extinf_count = content.count("#EXTINF")
            
            logger.info("✅ 文件保存成功")
            logger.info(f"📁 文件大小: {file_size/1024:.1f} KB")
            logger.info(f"📈 频道总数: {extinf_count}")
            
            # 快速统计
            lines = content.split('\n')
            now_news_count = sum(1 for line in lines if line.startswith("#EXTINF") and 
                                ('NOW新闻台' in line or 'NOW新聞台' in line))
            
            logger.info(f"📊 NOW新闻台: {now_news_count} 个（已去重）")
            
            return True
        else:
            logger.error("❌ 文件创建失败")
            return False
            
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=== M3U频道提取器（优化版）开始运行 ===")
    total_start = time.time()
    
    # 1. 获取原始TV内容
    raw_content = fetch_m3u_content()
    if not raw_content:
        logger.error("无法获取原始TV内容")
        sys.exit(1)
    
    # 2. 提取并排序
    extracted_content = extract_and_sort_channels_fast(raw_content)
    if not extracted_content:
        logger.error("未找到指定的分组频道")
        sys.exit(1)
    
    # 3. 读取BB.m3u
    bb_content = read_bb_file()
    
    # 4. 合并内容
    merged_content = merge_with_bb_fast(extracted_content, bb_content)
    
    # 5. 保存文件
    if not save_m3u_file(merged_content):
        logger.error("文件保存失败")
        sys.exit(1)
    
    total_elapsed = time.time() - total_start
    logger.info(f"=== 处理完成，总耗时: {total_elapsed:.2f}秒 ===")

if __name__ == "__main__":
    main()
