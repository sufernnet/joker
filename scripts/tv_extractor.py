#!/usr/bin/env python3
"""
从TV源中提取"港澳頻道"和"體育世界"并与BB.m3u合并，保存为EE.m3u
修改：1. 合并重复NOW新闻台 2. 體育世界中NOW频道排最前
"""

import requests
import re
import os
import sys
from datetime import datetime
import logging

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
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        logger.info(f"下载成功，大小: {len(response.text)} 字符")
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
            logger.info(f"读取BB.m3u成功")
            return content
        else:
            logger.warning(f"BB.m3u文件不存在")
            return None
    except Exception as e:
        logger.error(f"读取BB.m3u失败: {e}")
        return None

def extract_channels_simple(content):
    """提取频道，只做NOW新闻台去重和體育世界NOW频道优先"""
    if not content:
        return None
    
    logger.info("开始提取指定分组频道...")
    
    # 目标分组
    target_groups = ["港澳頻道", "體育世界"]
    
    # 按行分割内容
    lines = content.split('\n')
    
    # 存储提取的频道
    hk_channels = []  # 港澳頻道所有频道
    sports_now_channels = []  # 體育世界中的NOW频道
    sports_other_channels = []  # 體育世界中的其他频道
    
    # 用于NOW新闻台去重
    now_news_found = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # 检查是否是分组行
        if line.startswith("#EXTINF"):
            # 提取分组信息
            group_match = re.search(r'group-title="([^"]+)"', line)
            if group_match:
                group_name = group_match.group(1)
                
                # 检查是否为目标分组
                if group_name in target_groups:
                    # 查找对应的URL行
                    j = i + 1
                    while j < len(lines):
                        url_line = lines[j].strip()
                        if url_line and not url_line.startswith("#"):
                            break
                        j += 1
                    
                    if j < len(lines) and lines[j].strip():
                        url_line = lines[j].strip()
                        
                        # 港澳頻道处理
                        if group_name == "港澳頻道":
                            # NOW新闻台去重：只保留第一个
                            if ('NOW新闻台' in line or 'NOW新聞台' in line):
                                if not now_news_found:
                                    hk_channels.append((line, url_line))
                                    now_news_found = True
                                    logger.info("添加NOW新闻台")
                                else:
                                    logger.info("跳过重复的NOW新闻台")
                            else:
                                hk_channels.append((line, url_line))
                        
                        # 體育世界处理
                        elif group_name == "體育世界":
                            # 分离NOW频道和其他频道
                            if 'NOW' in line.upper():
                                sports_now_channels.append((line, url_line))
                                logger.info(f"NOW体育频道: {line[:60]}...")
                            else:
                                sports_other_channels.append((line, url_line))
                        
                        i = j  # 跳过URL行
        i += 1
    
    # 输出统计
    logger.info(f"港澳頻道: {len(hk_channels)} 个频道")
    logger.info(f"體育世界 - NOW频道: {len(sports_now_channels)} 个")
    logger.info(f"體育世界 - 其他频道: {len(sports_other_channels)} 个")
    
    # 构建输出
    extracted_lines = []
    extracted_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 添加港澳頻道（保持原顺序，只是去除了重复的NOW新闻台）
    if hk_channels:
        extracted_lines.append("# 港澳頻道")
        for extinf, url in hk_channels:
            extracted_lines.append(extinf)
            extracted_lines.append(url)
        extracted_lines.append("")
    
    # 添加體育世界（NOW频道在前）
    if sports_now_channels or sports_other_channels:
        extracted_lines.append("# 體育世界")
        
        # 先添加NOW频道
        if sports_now_channels:
            extracted_lines.append("## NOW体育频道")
            for extinf, url in sports_now_channels:
                extracted_lines.append(extinf)
                extracted_lines.append(url)
        
        # 再添加其他频道
        if sports_other_channels:
            if sports_now_channels:
                extracted_lines.append("")  # 空行分隔
            extracted_lines.append("## 其他体育频道")
            for extinf, url in sports_other_channels:
                extracted_lines.append(extinf)
                extracted_lines.append(url)
    
    return '\n'.join(extracted_lines)

def merge_with_bb_simple(tv_content, bb_content):
    """简单合并"""
    merged_lines = []
    
    # 文件头
    merged_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merged_lines.append(f"# 生成时间: {timestamp}")
    merged_lines.append(f"# 源地址: {SOURCE_URL}")
    merged_lines.append(f"# EPG源: {EPG_URL}")
    merged_lines.append("# 包含: BB.m3u + 港澳頻道 + 體育世界")
    merged_lines.append("# 修改: 1.NOW新闻台去重 2.體育世界NOW优先")
    merged_lines.append("")
    
    # BB内容
    if bb_content:
        bb_lines = bb_content.split('\n')
        for line in bb_lines:
            line = line.strip()
            if line and not line.startswith("#EXTM3U"):
                merged_lines.append(line)
        merged_lines.append("")
    
    # TV内容（跳过第一个#EXTM3U）
    if tv_content:
        tv_lines = tv_content.split('\n')
        skip_first = True
        for line in tv_lines:
            if line.startswith("#EXTM3U") and skip_first:
                skip_first = False
                continue
            merged_lines.append(line)
    
    return '\n'.join(merged_lines)

def save_m3u_file(content):
    """保存文件"""
    if not content:
        logger.error("没有内容可保存")
        return False
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(os.path.dirname(script_dir), "EE.m3u")
        
        logger.info(f"保存到: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 简单验证
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            extinf_count = content.count("#EXTINF")
            now_news_count = content.count("NOW新闻台") + content.count("NOW新聞台")
            
            logger.info("✅ 保存成功")
            logger.info(f"文件大小: {file_size} 字节")
            logger.info(f"频道总数: {extinf_count}")
            logger.info(f"NOW新闻台数量: {now_news_count} (应≤1)")
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"保存失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=== 开始运行 ===")
    
    # 1. 获取TV内容
    raw_content = fetch_m3u_content()
    if not raw_content:
        sys.exit(1)
    
    # 2. 提取（只做去重和排序）
    extracted_content = extract_channels_simple(raw_content)
    if not extracted_content:
        sys.exit(1)
    
    # 3. 读取BB
    bb_content = read_bb_file()
    
    # 4. 合并
    merged_content = merge_with_bb_simple(extracted_content, bb_content)
    
    # 5. 保存
    if save_m3u_file(merged_content):
        logger.info("=== 完成 ===")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
