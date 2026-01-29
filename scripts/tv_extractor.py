#!/usr/bin/env python3
"""
从TV源中提取"港澳頻道"和"體育世界"并与BB.m3u合并，保存为EE.m3u
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
BB_FILE = "BB.m3u"  # 假设BB.m3u在仓库根目录
OUTPUT_FILE = "../EE.m3u"  # 上一级目录（joker目录）

def fetch_m3u_content():
    """获取原始M3U文件内容"""
    try:
        logger.info(f"正在从 {SOURCE_URL} 下载M3U文件...")
        response = requests.get(SOURCE_URL, timeout=30)
        response.raise_for_status()
        logger.info(f"下载成功，大小: {len(response.text)} 字符")
        
        # 调试：查看文件内容的前1000字符
        preview = response.text[:1000]
        logger.info(f"文件预览（前1000字符）:\n{preview}")
        
        return response.text
    except requests.RequestException as e:
        logger.error(f"下载M3U文件失败: {e}")
        return None

def read_bb_file():
    """读取BB.m3u文件内容"""
    try:
        # BB.m3u在仓库根目录
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

def extract_channels(content):
    """提取港澳頻道和體育世界"""
    if not content:
        return None
    
    logger.info("开始提取指定分组频道...")
    
    # 修正：使用正确的繁体字分组名
    target_groups = ["港澳頻道", "體育世界"]
    
    # 按行分割内容
    lines = content.split('\n')
    extracted_lines = []
    
    # 添加文件头
    extracted_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 用于调试和统计
    found_groups = {}
    for group in target_groups:
        found_groups[group] = 0
    
    # 查找所有分组用于调试
    all_groups = set()
    for line in lines:
        if '#EXTINF' in line and 'group-title="' in line:
            match = re.search(r'group-title="([^"]+)"', line)
            if match:
                all_groups.add(match.group(1))
    
    logger.info(f"源文件中找到的所有分组: {sorted(all_groups)}")
    logger.info(f"目标分组: {target_groups}")
    
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
                    logger.info(f"找到目标分组 '{group_name}' 的频道")
                    # 添加EXTINF行
                    extracted_lines.append(line)
                    found_groups[group_name] += 1
                    
                    # 查找对应的URL行
                    j = i + 1
                    url_added = False
                    while j < len(lines):
                        url_line = lines[j].strip()
                        if not url_line:
                            j += 1
                            continue
                        if url_line.startswith("#EXTINF"):
                            break
                        # 添加URL行
                        if url_line and not url_line.startswith("#"):
                            extracted_lines.append(url_line)
                            url_added = True
                            logger.info(f"  添加URL: {url_line[:50]}...")
                        j += 1
                    
                    if not url_added:
                        logger.warning(f"分组 '{group_name}' 的频道没有找到URL")
                    
                    i = j - 1  # 跳过已处理的URL行
        i += 1
    
    # 输出统计信息
    logger.info("=== 提取统计 ===")
    for group, count in found_groups.items():
        logger.info(f"{group}: {count} 个频道")
    
    total_channels = sum(found_groups.values())
    logger.info(f"总计提取: {total_channels} 个频道")
    
    if total_channels == 0:
        logger.error("没有提取到任何频道，请检查分组名称")
        return None
    
    return '\n'.join(extracted_lines) if len(extracted_lines) > 1 else None

def merge_with_bb(tv_content, bb_content):
    """将提取的TV内容与BB.m3u合并"""
    merged_lines = []
    
    # 添加文件头
    merged_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 添加生成信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merged_lines.append(f"# 生成时间: {timestamp}")
    merged_lines.append(f"# 源地址: {SOURCE_URL}")
    merged_lines.append(f"# EPG源: {EPG_URL}")
    merged_lines.append("# 包含内容: BB.m3u + 港澳頻道 + 體育世界")
    merged_lines.append("# 自动更新频道列表")
    merged_lines.append("")
    
    # 如果有BB内容，先添加BB的内容（跳过其文件头）
    if bb_content:
        bb_lines = bb_content.split('\n')
        bb_count = 0
        for line in bb_lines:
            line = line.strip()
            if line:
                if line.startswith("#EXTM3U"):
                    continue  # 跳过BB的文件头
                if line.startswith("#EXTINF"):
                    bb_count += 1
                merged_lines.append(line)
        
        if bb_count > 0:
            logger.info(f"合并了 {bb_count} 个BB频道")
            merged_lines.append("")  # 添加空行分隔
    
    # 添加提取的TV内容（跳过文件头）
    if tv_content:
        tv_lines = tv_content.split('\n')
        first_extm3u_skipped = False
        tv_count = 0
        
        for line in tv_lines:
            line = line.strip()
            if line:
                if line.startswith("#EXTM3U") and not first_extm3u_skipped:
                    first_extm3u_skipped = True
                    continue
                if line.startswith("#EXTINF"):
                    tv_count += 1
                merged_lines.append(line)
        
        logger.info(f"合并了 {tv_count} 个TV频道")
    
    return '\n'.join(merged_lines)

def save_m3u_file(content):
    """保存M3U文件"""
    if not content:
        logger.error("没有内容可保存")
        return False
    
    try:
        # 获取脚本目录的上一级目录（joker目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        output_path = os.path.join(parent_dir, "EE.m3u")
        
        logger.info(f"将保存到: {output_path}")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 验证文件
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            extinf_count = content.count("#EXTINF")
            
            logger.info("✅ 文件保存成功")
            logger.info(f"📁 文件路径: {output_path}")
            logger.info(f"📊 文件大小: {file_size} 字节")
            logger.info(f"📈 频道总数: {extinf_count}")
            
            # 统计各分组数量
            hk_count = content.count("港澳頻道")
            sports_count = content.count("體育世界")
            
            logger.info("=== 详细统计 ===")
            logger.info(f"港澳頻道: {hk_count} 个频道")
            logger.info(f"體育世界: {sports_count} 个频道")
            
            # 显示文件开头和结尾
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                logger.info(f"📝 文件总行数: {len(lines)}")
                
                if len(lines) > 0:
                    logger.info("=== 文件开头（前10行）===")
                    for j in range(min(10, len(lines))):
                        line = lines[j].rstrip()
                        if line:  # 只显示非空行
                            logger.info(f"  {line}")
                    
                    logger.info("=== 文件结尾（最后5行）===")
                    for j in range(max(0, len(lines)-5), len(lines)):
                        line = lines[j].rstrip()
                        if line:  # 只显示非空行
                            logger.info(f"  {line}")
            
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
    
    # 1. 获取原始TV内容
    raw_content = fetch_m3u_content()
    if not raw_content:
        logger.error("无法获取原始TV内容，程序退出")
        sys.exit(1)
    
    # 2. 提取指定频道
    extracted_content = extract_channels(raw_content)
    if not extracted_content:
        logger.error("未找到指定的分组频道")
        sys.exit(1)
    
    # 3. 读取BB.m3u
    bb_content = read_bb_file()
    
    # 4. 合并内容
    merged_content = merge_with_bb(extracted_content, bb_content)
    
    # 5. 保存文件
    if save_m3u_file(merged_content):
        logger.info("=== 处理完成 ===")
    else:
        logger.error("=== 处理失败 ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
