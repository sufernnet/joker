#!/usr/bin/env python3
"""
从两个TV源中提取HK和TW频道，校验播放状态后与BB.m3u合并
"""

import requests
import re
import os
import sys
import time
import subprocess
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
HK_SOURCE_URL = "https://hacks.sufern001.workers.dev/?type=hk"
TW_SOURCE_URL = "https://hacks.sufern001.workers.dev/?type=tw"
EPG_URL = "http://epg.51zmt.top:8000/e.xml"
BB_FILE = "BB.m3u"  # 在仓库根目录
OUTPUT_FILE = "EE.m3u"  # 在仓库根目录
FFMPEG_PATH = "ffmpeg"
TIMEOUT = 10  # 播放校验超时时间（秒）
MAX_WORKERS = 5  # 并发校验最大线程数

def fetch_m3u_content(url, source_name):
    """获取M3U文件内容"""
    try:
        logger.info(f"正在从 {source_name} 下载M3U文件...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text
        
        if not content.strip().startswith("#EXTM3U"):
            logger.warning(f"{source_name} 内容可能不是有效的M3U格式")
            
        logger.info(f"{source_name} 下载成功，大小: {len(content)} 字符")
        return content
    except requests.RequestException as e:
        logger.error(f"下载 {source_name} 失败: {e}")
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

def parse_m3u_content(content, default_group):
    """解析M3U内容，返回频道列表"""
    if not content:
        return []
    
    channels = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # 检查是否是频道信息行
        if line.startswith("#EXTINF"):
            # 提取频道信息
            extinf_line = line
            
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
                # 提取频道名称
                channel_name = "未知频道"
                name_match = re.search(r',([^,]+)$', extinf_line)
                if name_match:
                    channel_name = name_match.group(1).strip()
                
                # 提取原始分组
                original_group = default_group
                group_match = re.search(r'group-title="([^"]+)"', extinf_line)
                if group_match:
                    original_group = match.group(1)
                
                # 创建新的EXTINF行，统一分组
                new_extinf = re.sub(r'group-title="[^"]+"', f'group-title="{default_group}"', extinf_line)
                if 'group-title=' not in new_extinf:
                    # 如果原来没有分组信息，添加分组
                    # 确保格式正确
                    if ': ' in new_extinf:
                        new_extinf = new_extinf.replace('#EXTINF:', f'#EXTINF: group-title="{default_group}",', 1)
                    else:
                        new_extinf = new_extinf.replace('#EXTINF:', f'#EXTINF: group-title="{default_group}",')
                
                channel_data = {
                    'original_extinf': extinf_line,
                    'extinf': new_extinf,
                    'url': url_line,
                    'name': channel_name,
                    'group': default_group,
                    'original_group': original_group,
                    'working': None  # 是否可播放，None表示未检查
                }
                channels.append(channel_data)
        
        i += 1
    
    return channels

def check_stream_playable(url, channel_name):
    """检查流是否可以播放"""
    try:
        # 简化检查，只检查连接和HTTP状态
        command = [
            'curl', '-s', '-o', '/dev/null',
            '-w', '%{http_code}',
            '--max-time', str(TIMEOUT),
            url
        ]
        
        logger.debug(f"检查频道: {channel_name}")
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT + 2
        )
        
        if result.returncode == 0:
            http_code = result.stdout.decode('utf-8', errors='ignore').strip()
            # 2xx 或 3xx 状态码通常表示可访问
            if http_code.startswith('2') or http_code.startswith('3'):
                return True
            else:
                logger.debug(f"频道 {channel_name} 返回HTTP状态码: {http_code}")
                return False
        else:
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning(f"频道检查超时: {channel_name}")
        return False
    except Exception as e:
        logger.warning(f"检查频道失败 {channel_name}: {e}")
        return False

def validate_channels(channels):
    """验证频道是否可以播放"""
    logger.info(f"开始验证 {len(channels)} 个频道的播放状态...")
    
    valid_channels = []
    invalid_channels = []
    
    # 简化验证：使用curl检查连接
    # 使用线程池并发验证
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_channel = {}
        for channel in channels:
            future = executor.submit(
                check_stream_playable, 
                channel['url'], 
                channel['name']
            )
            future_to_channel[future] = channel
        
        completed = 0
        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                is_playable = future.result()
                channel['working'] = is_playable
                
                if is_playable:
                    valid_channels.append(channel)
                    logger.info(f"✅ 可播放: {channel['name']}")
                else:
                    invalid_channels.append(channel)
                    logger.warning(f"❌ 不可播放: {channel['name']}")
                
                completed += 1
                if completed % 20 == 0:
                    logger.info(f"验证进度: {completed}/{len(channels)}")
                    
            except Exception as e:
                logger.error(f"验证频道异常 {channel['name']}: {e}")
                invalid_channels.append(channel)
    
    logger.info(f"验证完成: {len(valid_channels)} 个可播放, {len(invalid_channels)} 个不可播放")
    return valid_channels, invalid_channels

def build_m3u_content(hk_channels, tw_channels):
    """构建M3U文件内容"""
    lines = []
    
    # 添加文件头
    lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 添加生成信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"# 生成时间: {timestamp}")
    lines.append(f"# HK源地址: {HK_SOURCE_URL}")
    lines.append(f"# TW源地址: {TW_SOURCE_URL}")
    lines.append(f"# EPG源: {EPG_URL}")
    lines.append("# 包含内容: BB.m3u + HK频道 + TW频道")
    lines.append("# 自动更新频道列表")
    lines.append("")
    
    # 添加HK频道
    if hk_channels:
        lines.append("#" + "="*60)
        lines.append("# HK频道")
        lines.append("#" + "="*60)
        lines.append("")
        
        for channel in hk_channels:
            lines.append(channel['extinf'])
            lines.append(channel['url'])
        
        lines.append("")
    
    # 添加TW频道
    if tw_channels:
        lines.append("#" + "="*60)
        lines.append("# TW频道")
        lines.append("#" + "="*60)
        lines.append("")
        
        for channel in tw_channels:
            lines.append(channel['extinf'])
            lines.append(channel['url'])
    
    return '\n'.join(lines)

def merge_with_bb(tv_content, bb_content):
    """将提取的TV内容与BB.m3u合并"""
    if not tv_content and not bb_content:
        return ""
    
    merged_lines = []
    
    # 添加文件头
    merged_lines.append(f'#EXTM3U url-tvg="{EPG_URL}"')
    
    # 添加生成信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merged_lines.append(f"# 生成时间: {timestamp}")
    merged_lines.append(f"# HK源地址: {HK_SOURCE_URL}")
    merged_lines.append(f"# TW源地址: {TW_SOURCE_URL}")
    merged_lines.append(f"# EPG源: {EPG_URL}")
    merged_lines.append("# 包含内容: BB.m3u + HK频道 + TW频道")
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
            merged_lines.append("#" + "="*60)
            merged_lines.append("# 以下为HK和TW频道（已验证可播放）")
            merged_lines.append("#" + "="*60)
            merged_lines.append("")
    
    # 添加提取的TV内容（跳过文件头）
    if tv_content:
        tv_lines = tv_content.split('\n')
        for line in tv_lines:
            line = line.strip()
            if line:
                # 跳过文件头
                if line.startswith("#EXTM3U"):
                    continue
                merged_lines.append(line)
    
    return '\n'.join(merged_lines)

def save_m3u_file(content, filename):
    """保存M3U文件"""
    if not content:
        logger.error("没有内容可保存")
        return False
    
    try:
        # 保存到仓库根目录
        output_path = f"../{filename}"
        
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
            hk_count = content.count('group-title="HK"')
            tw_count = content.count('group-title="TW"')
            
            logger.info("=== 详细分类统计 ===")
            logger.info(f"HK频道: {hk_count} 个")
            logger.info(f"TW频道: {tw_count} 个")
            
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
    logger.info("将提取HK和TW频道，并验证播放状态")
    
    # 1. 获取HK源内容
    logger.info("=== 处理HK源 ===")
    hk_content = fetch_m3u_content(HK_SOURCE_URL, "HK源")
    if hk_content:
        hk_channels = parse_m3u_content(hk_content, "HK")
        logger.info(f"从HK源解析出 {len(hk_channels)} 个频道")
    else:
        hk_channels = []
        logger.warning("HK源获取失败，将使用空列表")
    
    # 2. 获取TW源内容
    logger.info("=== 处理TW源 ===")
    tw_content = fetch_m3u_content(TW_SOURCE_URL, "TW源")
    if tw_content:
        tw_channels = parse_m3u_content(tw_content, "TW")
        logger.info(f"从TW源解析出 {len(tw_channels)} 个频道")
    else:
        tw_channels = []
        logger.warning("TW源获取失败，将使用空列表")
    
    # 3. 验证频道播放状态
    logger.info("=== 开始验证频道播放状态 ===")
    all_channels = hk_channels + tw_channels
    
    if all_channels:
        valid_channels, invalid_channels = validate_channels(all_channels)
        
        # 重新分组
        hk_valid = [c for c in valid_channels if c['group'] == 'HK']
        tw_valid = [c for c in valid_channels if c['group'] == 'TW']
        
        logger.info(f"验证结果: HK有效 {len(hk_valid)} 个, TW有效 {len(tw_valid)} 个")
        
        # 记录无效频道
        if invalid_channels:
            logger.warning(f"以下 {len(invalid_channels)} 个频道不可播放:")
            for channel in invalid_channels[:10]:  # 只显示前10个
                logger.warning(f"  - {channel['name']} ({channel['group']})")
            if len(invalid_channels) > 10:
                logger.warning(f"  ... 还有 {len(invalid_channels) - 10} 个")
    else:
        hk_valid = []
        tw_valid = []
        logger.warning("没有提取到任何频道")
    
    # 4. 构建TV内容
    tv_content = build_m3u_content(hk_valid, tw_valid)
    
    # 5. 读取BB.m3u
    bb_content = read_bb_file()
    
    # 6. 合并内容
    merged_content = merge_with_bb(tv_content, bb_content)
    
    # 7. 保存文件
    if save_m3u_file(merged_content, OUTPUT_FILE):
        logger.info("=== 处理完成 ===")
        
        # 最终统计
        final_hk_count = merged_content.count('group-title="HK"')
        final_tw_count = merged_content.count('group-title="TW"')
        final_total = merged_content.count("#EXTINF")
        
        logger.info(f"最终结果: 总频道数={final_total}, HK频道={final_hk_count}, TW频道={final_tw_count}")
        
        return True
    else:
        logger.error("=== 处理失败 ===")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
