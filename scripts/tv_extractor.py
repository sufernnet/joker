#!/usr/bin/env python3
"""
从TV源中提取"港澳頻道"和"體育世界"并与BB.m3u合并，保存为EE.m3u
港澳頻道中凤凰频道排前，NOW频道排后
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

def extract_and_sort_channels(content):
    """提取港澳頻道和體育世界，并对港澳頻道排序"""
    if not content:
        return None
    
    logger.info("开始提取指定分组频道...")
    
    # 目标分组
    target_groups = ["港澳頻道", "體育世界"]
    
    # 按行分割内容
    lines = content.split('\n')
    
    # 存储提取的频道，港澳頻道分组需要分类
    phoenix_channels = []  # 凤凰频道
    now_channels = []      # NOW频道
    other_hk_channels = []  # 港澳頻道其他频道
    sports_channels = []    # 體育世界频道
    
    # 用于调试
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
                    url_line = ""
                    while j < len(lines):
                        temp_line = lines[j].strip()
                        if not temp_line:
                            j += 1
                            continue
                        if temp_line.startswith("#EXTINF"):
                            break
                        if temp_line and not temp_line.startswith("#"):
                            url_line = temp_line
                            break
                        j += 1
                    
                    if url_line:
                        channel_data = {
                            'extinf': line,
                            'url': url_line,
                            'group': group_name
                        }
                        
                        # 港澳頻道分组需要进一步分类
                        if group_name == "港澳頻道":
                            # 检查是否是凤凰频道
                            if '凤凰' in line or '鳳凰' in line:
                                phoenix_channels.append(channel_data)
                                logger.info(f"凤凰频道: {line[:80]}")
                            # 检查是否是NOW频道
                            elif 'NOW' in line.upper():
                                now_channels.append(channel_data)
                                logger.info(f"NOW频道: {line[:80]}")
                            else:
                                other_hk_channels.append(channel_data)
                            
                            found_groups[group_name] += 1
                        
                        # 體育世界分组直接添加
                        elif group_name == "體育世界":
                            sports_channels.append(channel_data)
                            found_groups[group_name] += 1
                            logger.info(f"体育频道: {line[:80]}")
        
        i += 1
    
    # 输出统计信息
    logger.info("=== 提取统计 ===")
    logger.info(f"港澳頻道 - 凤凰频道: {len(phoenix_channels)} 个")
    logger.info(f"港澳頻道 - NOW频道: {len(now_channels)} 个")
    logger.info(f"港澳頻道 - 其他频道: {len(other_hk_channels)} 个")
    logger.info(f"體育世界: {len(sports_channels)} 个")
    
    total_channels = sum(found_groups.values())
    logger.info(f"总计提取: {total_channels} 个频道")
    
    if total_channels == 0:
        logger.error("没有提取到任何频道，请检查分组名称")
        return None
    
    # 构建排序后的内容
    extracted_lines = []
    
    # 添加文件头
    extracted_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 添加注释说明排序规则
    extracted_lines.append("# 港澳頻道排序规则: 凤凰频道 → NOW频道 → 其他频道")
    extracted_lines.append("")
    
    # 按顺序添加港澳頻道
    hk_added = False
    
    # 1. 先添加凤凰频道
    for channel in phoenix_channels:
        extracted_lines.append(channel['extinf'])
        extracted_lines.append(channel['url'])
        hk_added = True
    
    # 2. 再添加NOW频道
    for channel in now_channels:
        extracted_lines.append(channel['extinf'])
        extracted_lines.append(channel['url'])
        hk_added = True
    
    # 3. 最后添加其他港澳频道
    for channel in other_hk_channels:
        extracted_lines.append(channel['extinf'])
        extracted_lines.append(channel['url'])
        hk_added = True
    
    # 如果有港澳频道，添加分隔空行
    if hk_added:
        extracted_lines.append("")
    
    # 添加體育世界频道
    if sports_channels:
        extracted_lines.append("# 體育世界频道")
        for channel in sports_channels:
            extracted_lines.append(channel['extinf'])
            extracted_lines.append(channel['url'])
    
    return '\n'.join(extracted_lines)

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
    merged_lines.append("# 港澳頻道排序: 凤凰频道 → NOW频道 → 其他频道")
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
            merged_lines.append("#" + "="*50)
            merged_lines.append("# 以下为港澳頻道和體育世界")
            merged_lines.append("#" + "="*50)
            merged_lines.append("")
    
    # 添加提取的TV内容（跳过文件头）
    if tv_content:
        tv_lines = tv_content.split('\n')
        for line in tv_lines:
            line = line.strip()
            if line:
                merged_lines.append(line)
    
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
            
            # 统计各分类数量
            phoenix_count = content.count("凤凰") + content.count("鳳凰")
            now_count = content.upper().count("NOW")
            sports_count = content.count("體育世界")
            
            logger.info("=== 详细分类统计 ===")
            logger.info(f"凤凰频道: {phoenix_count} 个")
            logger.info(f"NOW频道: {now_count} 个")
            logger.info(f"體育世界: {sports_count} 个")
            
            # 显示排序验证
            logger.info("=== 排序验证 ===")
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # 查找第一个凤凰频道和NOW频道的位置
                first_phoenix = -1
                first_now = -1
                for idx, line in enumerate(lines):
                    line_lower = line.lower()
                    if ('凤凰' in line or '鳳凰' in line) and first_phoenix == -1:
                        first_phoenix = idx
                    if 'NOW' in line.upper() and first_now == -1:
                        first_now = idx
                
                if first_phoenix != -1:
                    logger.info(f"第一个凤凰频道在第 {first_phoenix + 1} 行")
                if first_now != -1:
                    logger.info(f"第一个NOW频道在第 {first_now + 1} 行")
                
                if first_phoenix != -1 and first_now != -1:
                    if first_phoenix < first_now:
                        logger.info("✅ 排序正确: 凤凰频道在NOW频道之前")
                    else:
                        logger.warning("⚠️  排序可能有问题: NOW频道在凤凰频道之前")
            
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
    logger.info("排序规则: 港澳頻道中凤凰频道优先，NOW频道次之")
    
    # 1. 获取原始TV内容
    raw_content = fetch_m3u_content()
    if not raw_content:
        logger.error("无法获取原始TV内容，程序退出")
        sys.exit(1)
    
    # 2. 提取并排序指定频道
    extracted_content = extract_and_sort_channels(raw_content)
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
