#!/usr/bin/env python3
"""
从两个TV源中提取HK和TW频道，校验播放状态后与BB.m3u合并
支持频道过滤和排序
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
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 常量定义
HK_SOURCE_URL = "https://hacks.sufern001.workers.dev/?type=hk"
TW_SOURCE_URL = "https://hacks.sufern001.workers.dev/?type=tw"
EPG_URL = "http://epg.51zmt.top:8000/e.xml"
BB_FILE = "BB.m3u"
OUTPUT_FILE = "EE.m3u"
TIMEOUT = 10  # 播放校验超时时间（秒）
MAX_WORKERS = 5  # 并发校验最大线程数
MAX_RETRIES = 2  # 最大重试次数

# HK频道黑名单（要过滤掉的频道）
HK_BLACKLIST = [
    'snaap',
    'C+',
    '甄子丹',
    'SNAAP',
    'C+',
]

# TW频道黑名单（要过滤掉的频道）
TW_BLACKLIST = [
    '國會頻道',
    '原住民',
    'liveABC',
    'UDN TV',
    'rollor',
    'C+頻道',
    'MOMO',
    '大愛',
    '好訊息',
    'Smith',
    'FOX MOVIES',
    'PETP',
    '國會',
    '原民',
    'ABC',
    'UDN',
    'rollor',
    'Momo',
    '好訊息 1',
    '好訊息 2',
    'FOX MOVIE',
    'PET CLUB TV'
]

# 凤凰频道关键词（用于排序）
PHOENIX_KEYWORDS = ['鳳凰', '凤凰']

# NOW频道关键词（用于排序）
NOW_KEYWORDS = ['NOW']

def fetch_m3u_content(url, source_name, retry_count=MAX_RETRIES):
    """获取M3U文件内容"""
    for attempt in range(retry_count):
        try:
            logger.info(f"正在从 {source_name} 下载M3U文件 (尝试 {attempt+1}/{retry_count})...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text
            
            if not content.strip().startswith("#EXTM3U"):
                logger.warning(f"{source_name} 内容可能不是有效的M3U格式")
                
            logger.info(f"{source_name} 下载成功，大小: {len(content)} 字符")
            return content
        except requests.RequestException as e:
            logger.error(f"下载 {source_name} 失败 (尝试 {attempt+1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 2  # 递增等待时间
                logger.info(f"{wait_time}秒后重试...")
                time.sleep(wait_time)
    
    logger.error(f"{source_name} 下载失败，已达到最大重试次数")
    return None

def read_bb_file():
    """读取BB.m3u文件内容"""
    try:
        # 先尝试在当前目录查找
        if os.path.exists(BB_FILE):
            bb_path = BB_FILE
        else:
            # 尝试在脚本所在目录的上级目录查找
            script_dir = os.path.dirname(os.path.abspath(__file__))
            bb_path = os.path.join(script_dir, "..", BB_FILE)
        
        if os.path.exists(bb_path):
            with open(bb_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"读取BB.m3u成功，大小: {len(content)} 字符")
            return content
        else:
            logger.warning(f"BB.m3u文件不存在: {bb_path}")
            # 尝试其他可能位置
            possible_paths = [
                BB_FILE,
                f"../{BB_FILE}",
                f"../../{BB_FILE}",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", BB_FILE),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), BB_FILE)
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"从 {path} 读取BB.m3u成功")
                    return content
            
            logger.error(f"在所有可能位置都找不到BB.m3u文件")
            logger.info("将创建不包含BB.m3u的频道列表")
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
                channel_name = "未知頻道"  # 默认繁体
                name_match = re.search(r',([^,]+)$', extinf_line)
                if name_match:
                    channel_name = name_match.group(1).strip()
                
                # 提取原始分组
                original_group = default_group
                group_match = re.search(r'group-title="([^"]+)"', extinf_line)
                if group_match:
                    original_group = group_match.group(1)
                
                # 提取tvg-id（如果有）
                tvg_id = ""
                tvg_match = re.search(r'tvg-id="([^"]+)"', extinf_line)
                if tvg_match:
                    tvg_id = tvg_match.group(1)
                
                # 提取tvg-logo（如果有）
                tvg_logo = ""
                logo_match = re.search(r'tvg-logo="([^"]+)"', extinf_line)
                if logo_match:
                    tvg_logo = logo_match.group(1)
                
                # 创建新的EXTINF行，统一分组但保留其他属性
                new_extinf = extinf_line
                
                # 如果有group-title，替换它
                if 'group-title=' in new_extinf:
                    new_extinf = re.sub(r'group-title="[^"]+"', f'group-title="{default_group}"', new_extinf)
                else:
                    # 如果原来没有分组信息，添加分组
                    if ': ' in new_extinf:
                        new_extinf = new_extinf.replace('#EXTINF:', f'#EXTINF: group-title="{default_group}",', 1)
                    else:
                        # 检查是否有其他属性
                        attr_match = re.match(r'#EXTINF:(-?\d+)\s+(.+)', new_extinf)
                        if attr_match:
                            duration = attr_match.group(1)
                            attrs = attr_match.group(2)
                            new_extinf = f'#EXTINF:{duration} group-title="{default_group}",{attrs.split(",")[-1]}'
                        else:
                            new_extinf = f'#EXTINF:-1 group-title="{default_group}",{channel_name}'
                
                channel_data = {
                    'original_extinf': extinf_line,
                    'extinf': new_extinf,
                    'url': url_line,
                    'name': channel_name,
                    'group': default_group,
                    'original_group': original_group,
                    'tvg_id': tvg_id,
                    'tvg_logo': tvg_logo,
                    'working': None  # 是否可播放，None表示未检查
                }
                channels.append(channel_data)
        
        i += 1
    
    return channels

def filter_and_sort_channels(channels, blacklist, group_name):
    """过滤和排序频道"""
    if not channels:
        return []
    
    logger.info(f"开始过滤和排序 {group_name} 频道...")
    
    # 1. 过滤黑名单频道
    filtered_channels = []
    for channel in channels:
        channel_name = channel['name']
        should_skip = False
        
        for black_word in blacklist:
            if black_word.lower() in channel_name.lower():
                logger.info(f"过滤频道: {channel_name} (匹配黑名单: {black_word})")
                should_skip = True
                break
        
        if not should_skip:
            filtered_channels.append(channel)
    
    logger.info(f"过滤后剩余 {len(filtered_channels)} 个{group_name}频道")
    
    # 2. 如果是HK频道，进行特殊排序
    if group_name == "HK":
        # 分离凤凰、NOW和其他频道
        phoenix_channels = []
        now_channels = []
        other_channels = []
        
        for channel in filtered_channels:
            channel_name = channel['name']
            
            # 检查是否为凤凰频道
            is_phoenix = any(keyword in channel_name for keyword in PHOENIX_KEYWORDS)
            # 检查是否为NOW频道
            is_now = any(keyword in channel_name for keyword in NOW_KEYWORDS)
            
            if is_phoenix:
                phoenix_channels.append(channel)
            elif is_now:
                now_channels.append(channel)
            else:
                other_channels.append(channel)
        
        # 对凤凰频道进行特定排序
        phoenix_order = {
            '鳳凰衛視': 1,
            '鳳凰資訊HD': 2, 
            '鳳凰香港': 3,
            '鳳凰電影': 4,
            '凤凰中文': 1,
            '凤凰资讯': 2,
            '凤凰香港': 3,
            '凤凰电影': 4
        }
        
        def get_phoenix_priority(channel_name):
            for key, priority in phoenix_order.items():
                if key in channel_name:
                    return priority
            return 99  # 其他凤凰频道放在后面
        
        phoenix_channels.sort(key=lambda x: get_phoenix_priority(x['name']))
        
        # 合并排序后的频道列表
        sorted_channels = phoenix_channels + now_channels + other_channels
        
        logger.info(f"HK频道排序结果: 凤凰{len(phoenix_channels)}个, NOW{len(now_channels)}个, 其他{len(other_channels)}个")
        return sorted_channels
    
    # 对于TW频道，只过滤不排序
    return filtered_channels

def check_stream_playable(url, channel_name, retry_count=1):
    """检查流是否可以播放"""
    parsed_url = urlparse(url)
    
    # 检查URL是否有效
    if not parsed_url.scheme:
        logger.debug(f"无效的URL格式: {url}")
        return False
    
    # 跳过某些协议的直接检查
    skip_protocols = ['rtmp', 'rtsp', 'udp', 'rtp', 'p2p']
    if parsed_url.scheme in skip_protocols:
        logger.debug(f"跳过 {parsed_url.scheme} 协议检查: {channel_name}")
        return True  # 假设这些协议可播放
    
    for attempt in range(retry_count):
        try:
            # 对于HTTP/HTTPS流，使用curl检查
            if parsed_url.scheme in ['http', 'https']:
                # 尝试HEAD请求
                command = [
                    'curl', '-s', '-o', '/dev/null',
                    '-w', '%{http_code}',
                    '--max-time', str(TIMEOUT),
                    '--head',
                    '--location',  # 跟随重定向
                    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    url
                ]
                
                logger.debug(f"检查频道 [{attempt+1}/{retry_count}]: {channel_name}")
                
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=TIMEOUT + 2
                )
                
                if result.returncode == 0:
                    http_code = result.stdout.decode('utf-8', errors='ignore').strip()
                    # 2xx 或 3xx 或 4xx（某些服务器返回403但流仍然可用）
                    if http_code.startswith('2') or http_code.startswith('3') or http_code == '403':
                        return True
                    else:
                        logger.debug(f"频道 {channel_name} 返回HTTP状态码: {http_code}")
                else:
                    stderr = result.stderr.decode('utf-8', errors='ignore')[:100]
                    logger.debug(f"频道 {channel_name} curl命令失败: {stderr}")
            
            # 如果是其他支持的协议，尝试简单连接
            else:
                logger.debug(f"尝试连接 {parsed_url.scheme} 协议: {channel_name}")
                # 这里可以添加其他协议的检查逻辑
                return True  # 暂时假设可连接
                
        except subprocess.TimeoutExpired:
            logger.warning(f"频道检查超时 [{attempt+1}/{retry_count}]: {channel_name}")
            if attempt < retry_count - 1:
                time.sleep(1)  # 重试前等待
        except Exception as e:
            logger.warning(f"检查频道失败 [{attempt+1}/{retry_count}] {channel_name}: {str(e)[:100]}")
            if attempt < retry_count - 1:
                time.sleep(1)
    
    return False

def validate_channels(channels, skip_validation=False):
    """验证频道是否可以播放"""
    if not channels:
        return [], []
    
    if skip_validation:
        logger.info(f"跳过验证，标记所有 {len(channels)} 个频道为可播放")
        for channel in channels:
            channel['working'] = True
        return channels, []
    
    logger.info(f"开始验证 {len(channels)} 个频道的播放状态...")
    
    valid_channels = []
    invalid_channels = []
    
    # 使用线程池并发验证
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_channel = {}
        for channel in channels:
            future = executor.submit(
                check_stream_playable, 
                channel['url'], 
                channel['name'],
                2  # 重试次数
            )
            future_to_channel[future] = channel
        
        completed = 0
        start_time = time.time()
        
        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                is_playable = future.result()
                channel['working'] = is_playable
                
                if is_playable:
                    valid_channels.append(channel)
                    if len(valid_channels) % 10 == 0:
                        logger.info(f"✅ 已找到 {len(valid_channels)} 个可播放频道")
                else:
                    invalid_channels.append(channel)
                    if len(invalid_channels) % 20 == 0:
                        logger.info(f"❌ 已有 {len(invalid_channels)} 个不可播放频道")
                
                completed += 1
                if completed % 20 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"验证进度: {completed}/{len(channels)} (已用 {elapsed:.1f}秒)")
                    
            except Exception as e:
                logger.error(f"验证频道异常 {channel['name']}: {e}")
                channel['working'] = False
                invalid_channels.append(channel)
    
    elapsed = time.time() - start_time
    logger.info(f"验证完成: {len(valid_channels)} 个可播放, {len(invalid_channels)} 个不可播放 (用时 {elapsed:.1f}秒)")
    
    # 按频道名称排序
    valid_channels.sort(key=lambda x: x['name'])
    invalid_channels.sort(key=lambda x: x['name'])
    
    return valid_channels, invalid_channels

def build_m3u_content(hk_channels, tw_channels):
    """构建M3U文件内容"""
    lines = []
    
    # 添加文件头
    lines.append(f'#EXTM3U url-tvg="{EPG_URL}" x-tvg-url="{EPG_URL}"')
    
    # 添加生成信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"# 生成時間: {timestamp}")
    lines.append(f"# HK源地址: {HK_SOURCE_URL}")
    lines.append(f"# TW源地址: {TW_SOURCE_URL}")
    lines.append(f"# EPG源: {EPG_URL}")
    lines.append("# 包含內容: BB.m3u + HK頻道 + TW頻道")
    lines.append("# 自動更新頻道列表")
    lines.append("")
    
    # 添加HK频道
    if hk_channels:
        lines.append("#" + "="*60)
        lines.append("# HK頻道")
        lines.append("#" + "="*60)
        lines.append("")
        
        for channel in hk_channels:
            lines.append(channel['extinf'])
            lines.append(channel['url'])
        
        lines.append("")
    
    # 添加TW频道
    if tw_channels:
        lines.append("#" + "="*60)
        lines.append("# TW頻道")
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
    merged_lines.append(f'#EXTM3U url-tvg="{EPG_URL}" x-tvg-url="{EPG_URL}"')
    
    # 添加生成信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merged_lines.append(f"# 生成時間: {timestamp}")
    merged_lines.append(f"# HK源地址: {HK_SOURCE_URL}")
    merged_lines.append(f"# TW源地址: {TW_SOURCE_URL}")
    merged_lines.append(f"# EPG源: {EPG_URL}")
    merged_lines.append("# 包含內容: BB.m3u + HK頻道 + TW頻道")
    merged_lines.append("# 自動更新頻道列表")
    merged_lines.append("")
    
    # 如果有BB内容，先添加BB的内容（跳过其文件头）
    if bb_content:
        bb_lines = bb_content.split('\n')
        bb_count = 0
        bb_section_started = False
        
        for line in bb_lines:
            line = line.strip()
            if not line:
                continue
                
            # 跳过BB的文件头
            if line.startswith("#EXTM3U") and not bb_section_started:
                continue
            
            bb_section_started = True
            
            if line.startswith("#EXTINF"):
                bb_count += 1
            merged_lines.append(line)
        
        if bb_count > 0:
            logger.info(f"合併了 {bb_count} 個BB頻道")
            merged_lines.append("")  # 添加空行分隔
            merged_lines.append("#" + "="*60)
            merged_lines.append("# 以下為HK和TW頻道（已驗證可播放）")
            merged_lines.append("#" + "="*60)
            merged_lines.append("")
    
    # 添加提取的TV内容（跳过文件头）
    if tv_content:
        tv_lines = tv_content.split('\n')
        tv_section_started = False
        
        for line in tv_lines:
            line = line.strip()
            if not line:
                continue
                
            # 跳过TV的文件头
            if line.startswith("#EXTM3U") and not tv_section_started:
                continue
            
            tv_section_started = True
            merged_lines.append(line)
    
    return '\n'.join(merged_lines)

def save_m3u_file(content, filename):
    """保存M3U文件"""
    if not content:
        logger.error("沒有內容可保存")
        return False
    
    try:
        # 确定输出路径
        output_path = filename
        
        # 如果脚本在scripts目录，输出到上级目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if "scripts" in script_dir:
            output_path = os.path.join(script_dir, "..", filename)
        
        logger.info(f"將保存到: {os.path.abspath(output_path)}")
        
        # 创建目录（如果需要）
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        
        # 验证文件
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            extinf_count = content.count("#EXTINF")
            
            logger.info("✅ 文件保存成功")
            logger.info(f"📁 文件路徑: {os.path.abspath(output_path)}")
            logger.info(f"📊 文件大小: {file_size:,} 字節")
            logger.info(f"📈 頻道總數: {extinf_count}")
            
            # 统计各分类数量
            hk_count = content.count('group-title="HK"')
            tw_count = content.count('group-title="TW"')
            other_count = extinf_count - hk_count - tw_count
            
            logger.info("=== 詳細分類統計 ===")
            logger.info(f"HK頻道: {hk_count} 個")
            logger.info(f"TW頻道: {tw_count} 個")
            logger.info(f"其他頻道(BB): {other_count} 個")
            
            # 显示前几个HK频道（验证排序）
            if hk_count > 0:
                logger.info("=== HK頻道前10個（驗證排序） ===")
                lines = content.split('\n')
                hk_shown = 0
                for i, line in enumerate(lines):
                    if 'group-title="HK"' in line:
                        # 提取频道名
                        name_match = re.search(r',([^,]+)$', line)
                        if name_match:
                            logger.info(f"{hk_shown+1:2d}. {name_match.group(1)}")
                            hk_shown += 1
                            if hk_shown >= 10:
                                break
            
            return True
        else:
            logger.error("❌ 文件創建失敗")
            return False
            
    except Exception as e:
        logger.error(f"保存文件失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main(skip_validation=False):
    """主函数"""
    logger.info("="*60)
    logger.info("M3U頻道提取器開始運行")
    logger.info("="*60)
    logger.info(f"將提取HK和TW頻道，驗證播放狀態: {'跳過' if skip_validation else '執行'}")
    
    # 1. 获取HK源内容
    logger.info("="*40)
    logger.info("處理HK源")
    logger.info("="*40)
    hk_content = fetch_m3u_content(HK_SOURCE_URL, "HK源")
    if hk_content:
        hk_channels = parse_m3u_content(hk_content, "HK")
        logger.info(f"從HK源解析出 {len(hk_channels)} 個頻道")
        
        # 过滤和排序HK频道
        hk_channels = filter_and_sort_channels(hk_channels, HK_BLACKLIST, "HK")
    else:
        hk_channels = []
        logger.warning("HK源獲取失敗，將使用空列表")
    
    # 2. 获取TW源内容
    logger.info("="*40)
    logger.info("處理TW源")
    logger.info("="*40)
    tw_content = fetch_m3u_content(TW_SOURCE_URL, "TW源")
    if tw_content:
        tw_channels = parse_m3u_content(tw_content, "TW")
        logger.info(f"從TW源解析出 {len(tw_channels)} 個頻道")
        
        # 过滤TW频道
        tw_channels = filter_and_sort_channels(tw_channels, TW_BLACKLIST, "TW")
    else:
        tw_channels = []
        logger.warning("TW源獲取失敗，將使用空列表")
    
    # 3. 验证频道播放状态
    logger.info("="*40)
    logger.info("驗證頻道播放狀態")
    logger.info("="*40)
    all_channels = hk_channels + tw_channels
    
    if all_channels:
        valid_channels, invalid_channels = validate_channels(all_channels, skip_validation)
        
        # 重新分组
        hk_valid = [c for c in valid_channels if c['group'] == 'HK']
        tw_valid = [c for c in valid_channels if c['group'] == 'TW']
        
        logger.info(f"驗證結果: HK有效 {len(hk_valid)} 個, TW有效 {len(tw_valid)} 個")
        
        # 记录无效频道
        if invalid_channels and not skip_validation:
            logger.warning(f"以下 {len(invalid_channels)} 個頻道不可播放:")
            for i, channel in enumerate(invalid_channels[:20]):  # 只显示前20个
                logger.warning(f"  {i+1:2d}. {channel['name']} ({channel['group']})")
            if len(invalid_channels) > 20:
                logger.warning(f"  ... 還有 {len(invalid_channels) - 20} 個")
    else:
        hk_valid = []
        tw_valid = []
        logger.warning("沒有提取到任何HK/TW頻道")
    
    # 4. 构建TV内容
    tv_content = build_m3u_content(hk_valid, tw_valid)
    
    # 5. 读取BB.m3u
    logger.info("="*40)
    logger.info("讀取BB.m3u")
    logger.info("="*40)
    bb_content = read_bb_file()
    
    # 6. 合并内容
    merged_content = merge_with_bb(tv_content, bb_content)
    
    # 7. 保存文件
    if save_m3u_file(merged_content, OUTPUT_FILE):
        logger.info("="*60)
        logger.info("處理完成")
        logger.info("="*60)
        
        # 最终统计
        final_hk_count = merged_content.count('group-title="HK"')
        final_tw_count = merged_content.count('group-title="TW"')
        final_total = merged_content.count("#EXTINF")
        final_other = final_total - final_hk_count - final_tw_count
        
        logger.info(f"🎯 最終結果:")
        logger.info(f"   總頻道數: {final_total}")
        logger.info(f"   HK頻道: {final_hk_count}")
        logger.info(f"   TW頻道: {final_tw_count}")
        logger.info(f"   其他頻道: {final_other}")
        
        return True
    else:
        logger.error("="*60)
        logger.error("處理失敗")
        logger.error("="*60)
        return False

if __name__ == "__main__":
    # 检查是否跳过验证
    skip_validation = False
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--skip-validation', '--skip', '-s']:
            skip_validation = True
            logger.info("命令行參數: 跳過播放驗證")
    
    success = main(skip_validation)
    sys.exit(0 if success else 1)
