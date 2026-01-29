#!/usr/bin/env python3
"""
从TV源中提取"港澳频道"和"体育世界"并保存为EE.m3u
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
OUTPUT_FILE = "EE.m3u"

def fetch_m3u_content():
    """获取原始M3U文件内容"""
    try:
        logger.info(f"正在从 {SOURCE_URL} 下载M3U文件...")
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        logger.info("下载成功")
        return response.text
    except requests.RequestException as e:
        logger.error(f"下载M3U文件失败: {e}")
        return None

def extract_channels(content):
    """提取港澳频道和体育世界"""
    if not content:
        return None
    
    logger.info("开始提取指定分组频道...")
    
    # 定义要提取的分组
    target_groups = ["港澳频道", "体育世界"]
    
    # 按行分割内容
    lines = content.split('\n')
    extracted_lines = []
    extract_mode = False
    
    # 添加文件头
    extracted_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    for i in range(len(lines)):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            continue
            
        # 检查是否是分组行
        if line.startswith("#EXTINF"):
            # 检查是否包含目标分组
            for group in target_groups:
                if f'group-title="{group}"' in line:
                    extract_mode = True
                    extracted_lines.append(line)
                    break
                else:
                    extract_mode = False
        # 如果是URL行且在提取模式中
        elif extract_mode and line and not line.startswith("#"):
            extracted_lines.append(line)
            extract_mode = False  # 重置提取模式
    
    return '\n'.join(extracted_lines) if len(extracted_lines) > 1 else None

def save_m3u_file(content):
    """保存M3U文件"""
    if not content:
        logger.error("没有内容可保存")
        return False
    
    try:
        # 添加生成信息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info_comment = f"# 生成时间: {timestamp}\n"
        info_comment += f"# 源地址: {SOURCE_URL}\n"
        info_comment += f"# EPG源: {EPG_URL}\n"
        info_comment += f"# 包含分组: 港澳频道, 体育世界\n"
        info_comment += "# 自动更新频道列表\n\n"
        
        full_content = info_comment + content
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # 统计频道数量
        extinf_count = content.count("#EXTINF")
        logger.info(f"已保存到 {OUTPUT_FILE}, 共提取 {extinf_count} 个频道")
        
        # 显示文件大小
        file_size = os.path.getsize(OUTPUT_FILE)
        logger.info(f"文件大小: {file_size} 字节")
        
        return True
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=== M3U频道提取器开始运行 ===")
    
    # 获取原始内容
    raw_content = fetch_m3u_content()
    if not raw_content:
        logger.error("无法获取原始内容，程序退出")
        sys.exit(1)
    
    # 提取指定频道
    extracted_content = extract_channels(raw_content)
    if not extracted_content:
        logger.error("未找到指定的分组频道")
        sys.exit(1)
    
    # 保存文件
    if save_m3u_file(extracted_content):
        logger.info("=== 处理完成 ===")
    else:
        logger.error("=== 处理失败 ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
