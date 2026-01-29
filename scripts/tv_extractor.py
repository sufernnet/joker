#!/usr/bin/env python3
"""
从TV源中提取"港澳频道"和"體育世界"并保存为EE.m3u
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
        logger.info(f"下载成功，大小: {len(response.text)} 字符")
        return response.text
    except requests.RequestException as e:
        logger.error(f"下载M3U文件失败: {e}")
        return None

def extract_channels(content):
    """提取港澳频道和體育世界"""
    if not content:
        return None
    
    logger.info("开始提取指定分组频道...")
    
    # 目标分组
    target_groups = ["港澳频道", "體育世界"]
    
    # 按行分割内容
    lines = content.split('\n')
    extracted_lines = []
    extract_mode = False
    channel_count = 0
    
    # 添加文件头
    extracted_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 用于调试
    found_groups = set()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            i += 1
            continue
        
        # 检查是否是分组行
        if line.startswith("#EXTINF"):
            # 提取分组信息
            group_match = re.search(r'group-title="([^"]+)"', line)
            if group_match:
                group_name = group_match.group(1)
                found_groups.add(group_name)
                
                # 检查是否为目标分组
                if group_name in target_groups:
                    extract_mode = True
                    extracted_lines.append(line)
                    
                    # 查找对应的URL行
                    for j in range(i+1, min(i+5, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith("#"):
                            extracted_lines.append(next_line)
                            channel_count += 1
                            logger.info(f"找到频道: {line[:50]}...")
                            i = j  # 跳过URL行
                            break
                else:
                    extract_mode = False
        i += 1
    
    # 输出调试信息
    logger.info(f"源文件中找到的分组: {sorted(found_groups)}")
    logger.info(f"目标分组: {target_groups}")
    logger.info(f"提取到 {channel_count} 个频道")
    
    return '\n'.join(extracted_lines) if len(extracted_lines) > 1 else None

def save_m3u_file(content):
    """保存M3U文件"""
    if not content:
        logger.error("没有内容可保存")
        return False
    
    try:
        # 获取当前工作目录
        current_dir = os.getcwd()
        logger.info(f"当前目录: {current_dir}")
        
        # 完整的输出路径
        output_path = os.path.join(current_dir, OUTPUT_FILE)
        logger.info(f"将保存到: {output_path}")
        
        # 添加生成信息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info_comment = f"# 生成时间: {timestamp}\n"
        info_comment += f"# 源地址: {SOURCE_URL}\n"
        info_comment += f"# EPG源: {EPG_URL}\n"
        info_comment += f"# 包含分组: 港澳频道, 體育世界\n"
        info_comment += "# 自动更新频道列表\n\n"
        
        full_content = info_comment + content
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # 验证文件
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            extinf_count = content.count("#EXTINF")
            
            logger.info("✅ 文件保存成功")
            logger.info(f"📁 文件路径: {output_path}")
            logger.info(f"📊 文件大小: {file_size} 字节")
            logger.info(f"📈 频道数量: {extinf_count}")
            
            # 读取并显示部分内容
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                logger.info(f"📝 文件行数: {len(lines)}")
                if len(lines) > 0:
                    logger.info("前5行内容:")
                    for j in range(min(5, len(lines))):
                        logger.info(f"  {lines[j].rstrip()}")
            
            return True
        else:
            logger.error("❌ 文件创建失败")
            return False
            
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
        # 列出当前目录文件
        logger.info("当前目录文件列表:")
        for file in os.listdir('.'):
            logger.info(f"  {file}")
    else:
        logger.error("=== 处理失败 ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
