#!/usr/bin/env python3
"""
CC合并脚本 - 完整版
生成CC.m3u文件，统一使用CC前缀便于记忆
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取内容
3. 提取JULI频道，分组改为HK，按指定顺序排列（合并相同频道的多个源）
4. 提取4gtv前30个直播，分组改为TW，过滤指定频道
5. 合并生成CC.m3u，包含多个EPG源
北京时间每天6:00、17:00自动运行
"""

import requests
import re
import os
import sys
from datetime import datetime
import urllib3
import time

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
CLOUDFLARE_PROXY = "https://smt-proxy.sufern001.workers.dev/"
OUTPUT_FILE = "CC.m3u"

# 需要过滤掉的TW频道关键词（不区分大小写）
BLACKLIST_TW = [
    "Bloomberg TV",
    "Bloomberg",
    "SBN全球财经台",
    "SBN财经",
    "FRANCE24英文台",
    "FRANCE24",
    "半岛国际新闻台",
    "半島国际",
    "NHK world-japan",
    "NHK world",
    "SBN",
    "日本",
    "NHK",
    "CNBC Asia",
    "CNBC"
]

# HK频道优先顺序（按这个顺序排列在最前面）
HK_PRIORITY_ORDER = [
    "凤凰中文",
    "凤凰资讯", 
    "凤凰香港",
    "NOW新闻台",
    "NOW星影",
    "NOW爆谷"
]

# 备选EPG源（如果主要EPG失效）
BACKUP_EPG_URLS = [
    "https://epg.112114.xyz/pp.xml",
    "https://epg.946985.filegear-sg.me/t.xml.gz",
    "http://epg.51zmt.top:8000/e.xml",
]

def log(msg):
    """输出日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def get_output_path():
    """获取输出文件路径"""
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录
    root_dir = os.path.dirname(script_dir)
    
    # 检查当前工作目录
    cwd = os.getcwd()
    log(f"当前工作目录: {cwd}")
    log(f"脚本目录: {script_dir}")
    log(f"根目录: {root_dir}")
    
    # 优先保存到根目录
    root_output = os.path.join(root_dir, OUTPUT_FILE)
    log(f"输出路径: {root_output}")
    
    return root_output

def test_epg_url(epg_url):
    """测试EPG URL是否可访问"""
    try:
        log(f"测试EPG: {epg_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        # 设置较长的超时时间
        timeout = 15
        
        # 对于.gz文件，需要特殊处理
        if epg_url.endswith('.gz'):
            response = requests.get(epg_url, headers=headers, timeout=timeout, stream=True, verify=False)
            if response.status_code == 200:
                # 尝试读取前几个字节检查是否是gzip
                try:
                    # 读取前100字节检查
                    chunk = response.raw.read(100)
                    # 检查是否是gzip文件（前两个字节是1f 8b）
                    if len(chunk) >= 2 and chunk[0] == 0x1f and chunk[1] == 0x8b:
                        log(f"✅ EPG可用 (GZIP格式): {epg_url}")
                        return True
                    else:
                        log(f"⚠️  EPG不是有效的GZIP格式: {epg_url}")
                        return False
                except Exception as e:
                    log(f"⚠️  GZIP文件读取失败: {e}")
                    return False
        else:
            # 常规XML文件
            response = requests.get(epg_url, headers=headers, timeout=timeout, stream=True, verify=False)
            
            if response.status_code == 200:
                # 检查内容类型
                content_type = response.headers.get('content-type', '').lower()
                
                # 读取前1KB检查
                try:
                    chunk = response.raw.read(1024)
                    text = chunk.decode('utf-8', errors='ignore')
                    
                    # 检查是否是XML格式
                    if '<?xml' in text or '<tv' in text or '<programme' in text:
                        log(f"✅ EPG可用: {epg_url}")
                        return True
                    else:
                        log(f"⚠️  EPG不是XML格式: {epg_url}")
                        return False
                except UnicodeDecodeError:
                    # 可能是二进制文件，尝试其他编码
                    try:
                        text = chunk.decode('gbk', errors='ignore')
                        if '<?xml' in text or '<tv' in text or '<programme' in text:
                            log(f"✅ EPG可用 (GBK编码): {epg_url}")
                            return True
                        else:
                            log(f"⚠️  EPG不是XML格式: {epg_url}")
                            return False
                    except:
                        log(f"⚠️  EPG解码失败: {epg_url}")
                        return False
            else:
                log(f"❌ EPG不可访问: {epg_url} (状态码: {response.status_code})")
                return False
            
    except Exception as e:
        log(f"❌ EPG测试失败 {epg_url}: {str(e)[:100]}")
        return False

def get_best_epg_url(epg_urls):
    """获取最佳的EPG URL"""
    log("寻找最佳EPG源...")
    
    # 测试所有EPG
    working_epgs = []
    for epg_url in epg_urls:
        if test_epg_url(epg_url):
            working_epgs.append(epg_url)
    
    if working_epgs:
        # 优先使用第一个可用的
        best_epg = working_epgs[0]
        log(f"✅ 选择EPG: {best_epg}")
        log(f"   其他可用EPG: {len(working_epgs)-1}个")
        return best_epg
    else:
        log("⚠️  没有可用的EPG源")
        return None

def download_bb_m3u():
    """下载BB.m3u并提取EPG"""
    try:
        log("下载BB.m3u...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://github.com/'
        }
        
        response = requests.get(BB_URL, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        bb_content = response.text
        log(f"✅ BB.m3u下载成功 ({len(bb_content)} 字符)")
        
        return bb_content
        
    except Exception as e:
        log(f"❌ BB.m3u下载失败: {e}")
        return None

def get_content_from_proxy():
    """从Cloudflare代理获取内容"""
    try:
        log("从Cloudflare代理获取内容...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://smart.946985.filegear-sg.me/',
            'Origin': 'https://smart.946985.filegear-sg.me',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
        # 尝试多次请求
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(CLOUDFLARE_PROXY, headers=headers, timeout=30, verify=False)
                
                if response.status_code == 200:
                    content = response.text
                    
                    # 检查内容是否有效
                    if not content or len(content.strip()) < 100:
                        log(f"尝试 {attempt + 1}/{max_retries}: 内容过短 ({len(content)} 字符)")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                    
                    # 如果是HTML，尝试提取M3U内容
                    if '<html' in content.lower():
                        log(f"尝试 {attempt + 1}/{max_retries}: 检测到HTML响应")
                        
                        # 方法1：查找M3U内容
                        m3u_patterns = [
                            r'(#EXTM3U.*?)(?:\n\n|\Z)',  # 直到两个换行或结尾
                            r'(#EXTM3U.*?)(?:</pre>|</code>|\Z)',  # 直到标签结束或结尾
                            r'<pre[^>]*>(.*?)</pre>',  # pre标签内
                            r'<code[^>]*>(.*?)</code>'  # code标签内
                        ]
                        
                        for pattern in m3u_patterns:
                            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                            if match:
                                extracted = match.group(1) if len(match.groups()) > 0 else match.group(0)
                                if '#EXTM3U' in extracted or '#EXTINF:' in extracted:
                                    content = extracted.strip()
                                    log(f"✅ 使用模式提取到M3U内容 ({len(content)} 字符)")
                                    break
                        
                        # 如果没提取到，尝试逐行提取
                        if '<html' in content.lower() or not ('#EXTM3U' in content or '#EXTINF:' in content):
                            lines = content.split('\n')
                            m3u_lines = []
                            for line in lines:
                                line = line.strip()
                                if line.startswith('#EXTM3U') or line.startswith('#EXTINF:') or ('.m3u8' in line and '://' in line):
                                    m3u_lines.append(line)
                            
                            if m3u_lines:
                                content = '\n'.join(m3u_lines)
                                log(f"✅ 逐行提取到 {len(m3u_lines)} 行M3U内容")
                    
                    # 确保以#EXTM3U开头
                    if content and '#EXTM3U' not in content[:20]:
                        if '#EXTINF:' in content or '.m3u8' in content:
                            content = '#EXTM3U\n' + content
                            log("已添加#EXTM3U头部")
                    
                    if content and len(content.strip()) > 100:
                        log(f"✅ 获取到内容 ({len(content)} 字符)")
                        return content
                    else:
                        log(f"尝试 {attempt + 1}/{max_retries}: 内容无效 ({len(content) if content else 0} 字符)")
                        
                else:
                    log(f"尝试 {attempt + 1}/{max_retries}: HTTP {response.status_code}")
                    
            except requests.exceptions.Timeout:
                log(f"尝试 {attempt + 1}/{max_retries}: 请求超时")
            except Exception as e:
                log(f"尝试 {attempt + 1}/{max_retries}: {str(e)[:100]}")
            
            if attempt < max_retries - 1:
                time.sleep(3)
        
        log("❌ 所有重试失败")
            
    except Exception as e:
        log(f"❌ 代理访问失败: {str(e)[:100]}")
    
    return None

def get_channel_priority(channel_name):
    """获取频道的优先级（越小越靠前）"""
    channel_name_lower = channel_name.lower()
    
    for i, priority_channel in enumerate(HK_PRIORITY_ORDER):
        if priority_channel.lower() in channel_name_lower:
            return i  # 返回优先级索引，越小越靠前
    
    return len(HK_PRIORITY_ORDER)  # 非优先频道排在最后

def extract_and_sort_hk_channels(content):
    """提取JULI频道，分组改为HK，按指定顺序排列，合并相同频道的多个源"""
    if not content:
        return []
    
    log("提取JULI频道，分组改为HK，按指定顺序排列...")
    log(f"HK优先顺序: {', '.join(HK_PRIORITY_ORDER)}")
    
    # 解析M3U内容
    lines = content.split('\n')
    channels = []
    current_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('#EXTINF:'):
            current_extinf = line
        elif current_extinf and '://' in line and not line.startswith('#'):
            channels.append((current_extinf, line))
            current_extinf = None
    
    log(f"总频道数: {len(channels)}")
    
    # 创建频道字典来合并相同频道的多个源
    channel_dict = {}
    
    for extinf, url in channels:
        # 只处理JULI频道（不区分大小写）
        if 'juli' in extinf.lower():
            # 提取原始频道名
            if ',' in extinf:
                # 获取频道名称部分
                parts = extinf.split(',', 1)
                channel_info = parts[0]
                channel_name = parts[1]
                
                # 清理频道名：去掉SMT_前缀，保留原始名称
                clean_channel_name = re.sub(r'^SMT_', '', channel_name)
                
                # 创建标准化的频道信息（使用清理后的名称）
                # 确保group-title为HK
                if 'group-title=' in channel_info:
                    clean_channel_info = re.sub(r'group-title="[^"]*"', 'group-title="HK"', channel_info)
                else:
                    clean_channel_info = channel_info + ' group-title="HK"'
                
                # 完整的EXTINF行
                clean_extinf = f'{clean_channel_info},{clean_channel_name}'
                
                # 添加到字典
                if clean_extinf not in channel_dict:
                    channel_dict[clean_extinf] = []
                
                # 添加URL到列表
                channel_dict[clean_extinf].append(url)
            else:
                log(f"⚠️  无法解析EXTINF行: {extinf}")
    
    # 统计合并效果
    juli_channels = [c for c in channels if 'juli' in c[0].lower()]
    log(f"合并前JULI频道数: {len(juli_channels)}")
    log(f"合并后唯一频道数: {len(channel_dict)}")
    
    # 显示合并统计
    if channel_dict:
        total_sources = sum(len(urls) for urls in channel_dict.values())
        log(f"总源数量: {total_sources}")
        log(f"平均每个频道源数: {total_sources/len(channel_dict):.1f}")
    
    # 按优先级排序
    hk_channels_with_priority = []
    
    for extinf, urls in channel_dict.items():
        # 提取频道名
        channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
        
        # 计算优先级
        priority = get_channel_priority(channel_name)
        
        # 存储：优先级, EXTINF行, URL列表, 频道名
        hk_channels_with_priority.append((priority, extinf, urls, channel_name))
    
    # 按优先级排序
    hk_channels_with_priority.sort(key=lambda x: x[0])
    
    # 提取排序后的频道
    hk_channels = [(extinf, urls) for _, extinf, urls, _ in hk_channels_with_priority]
    
    log(f"✅ 提取到 {len(hk_channels)} 个HK频道（原JULI，已合并重复源）")
    
    # 显示排序结果
    if hk_channels:
        log("HK频道合并结果 (前10个):")
        for i, (extinf, urls) in enumerate(hk_channels[:10], 1):
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i:2d}. {channel_name[:40]} - {len(urls)} 个源")
        if len(hk_channels) > 10:
            log(f"  ... 还有 {len(hk_channels) - 10} 个频道")
    
    return hk_channels

def should_skip_channel(channel_name):
    """检查频道是否应该被过滤"""
    channel_name_lower = channel_name.lower()
    
    # 检查是否在黑名单中
    for black_word in BLACKLIST_TW:
        if black_word.lower() in channel_name_lower:
            return True
    
    return False

def extract_filtered_4gtv_channels(content, limit=30):
    """提取4gtv频道（前30个），分组改为TW，过滤指定频道"""
    if not content:
        return []
    
    log(f"提取4gtv前{limit}个直播，分组改为TW，过滤指定频道...")
    log(f"过滤列表: {', '.join(BLACKLIST_TW[:5])}...")
    
    # 解析M3U内容
    lines = content.split('\n')
    channels = []
    current_extinf = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('#EXTINF:'):
            current_extinf = line
        elif current_extinf and '://' in line and not line.startswith('#'):
            channels.append((current_extinf, line))
            current_extinf = None
    
    log(f"总频道数: {len(channels)}")
    
    # 过滤4gtv频道（不区分大小写）
    filtered_channels = []
    for extinf, url in channels:
        if '4gtv' in extinf.lower():
            filtered_channels.append((extinf, url))
    
    log(f"找到 {len(filtered_channels)} 个4gtv频道")
    
    # 过滤黑名单频道
    filtered_by_blacklist = []
    skipped_channels = []
    
    for extinf, url in filtered_channels:
        # 提取频道名
        channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
        
        # 检查是否应该跳过
        if not should_skip_channel(channel_name):
            filtered_by_blacklist.append((extinf, url))
        else:
            skipped_channels.append(channel_name[:40])
    
    if skipped_channels:
        log(f"过滤掉 {len(skipped_channels)} 个频道")
        for i, channel in enumerate(skipped_channels[:5], 1):
            log(f"  ⛔ {i}. {channel}")
        if len(skipped_channels) > 5:
            log(f"  ... 还有 {len(skipped_channels) - 5} 个被过滤的频道")
    
    log(f"过滤后剩余 {len(filtered_by_blacklist)} 个4gtv频道")
    
    # 只取前limit个
    if len(filtered_by_blacklist) > limit:
        filtered_by_blacklist = filtered_by_blacklist[:limit]
        log(f"只取前 {limit} 个过滤后的4gtv频道")
    
    # 重命名为TW分组
    tw_channels = []
    seen = set()
    
    for extinf, url in filtered_by_blacklist:
        # 替换分组为TW
        new_extinf = extinf
        
        # 替换4gtv为TW（在频道名中）
        if '4gtv' in new_extinf.lower():
            new_extinf = re.sub(r'4gtv', 'TW', new_extinf, flags=re.IGNORECASE)
        
        # 确保group-title为TW
        if 'group-title=' in new_extinf:
            new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="TW"', new_extinf)
        else:
            # 添加group-title
            if ',' in new_extinf:
                parts = new_extinf.split(',', 1)
                new_extinf = f'{parts[0]} group-title="TW",{parts[1]}'
        
        # 去重
        key = f"{new_extinf}|{url}"
        if key not in seen:
            seen.add(key)
            tw_channels.append((new_extinf, url))
    
    log(f"✅ 提取到 {len(tw_channels)} 个TW频道（原4gtv，已过滤）")
    
    # 显示前几个TW频道
    if tw_channels:
        log("TW频道示例 (前5个):")
        for i, (extinf, url) in enumerate(tw_channels[:5], 1):
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i:2d}. {channel_name[:40]}")
    
    return tw_channels

def main():
    """主函数"""
    log("🚀 CC脚本开始运行...")
    
    # 获取输出路径
    output_path = get_output_path()
    log(f"📁 输出文件: {output_path}")
    
    # 显示当前时间（用于调试定时任务）
    current_time = datetime.now()
    log(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"下次运行: 北京时间 06:00 和 17:00")
    log(f"HK优先顺序: {', '.join(HK_PRIORITY_ORDER)}")
    log(f"TW频道过滤列表: {', '.join(BLACKLIST_TW[:3])}...")
    
    # 1. 下载BB.m3u
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从代理获取内容
    proxy_content = get_content_from_proxy()
    
    # 3. 收集所有EPG源
    epg_urls = []
    
    # 从BB.m3u提取EPG
    bb_epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
    if bb_epg_match:
        epg_urls.append(bb_epg_match.group(1))
        log(f"✅ 找到BB EPG: {bb_epg_match.group(1)}")
    
    # 从代理内容提取EPG
    if proxy_content:
        proxy_epg_match = re.search(r'x-tvg-url="([^"]+)"', proxy_content)
        if proxy_epg_match:
            epg_urls.append(proxy_epg_match.group(1))
            log(f"✅ 找到JULI EPG: {proxy_epg_match.group(1)}")
    
    # 添加备选EPG
    epg_urls.extend(BACKUP_EPG_URLS)
    
    # 去重
    unique_epgs = []
    for url in epg_urls:
        if url not in unique_epgs:
            unique_epgs.append(url)
    
    log(f"找到 {len(unique_epgs)} 个EPG源")
    
    # 4. 获取最佳EPG
    best_epg = get_best_epg_url(unique_epgs)
    
    # 5. 先提取HK频道（JULI）- 按指定顺序排列在最前面
    hk_channels = []
    if proxy_content:
        hk_channels = extract_and_sort_hk_channels(proxy_content)
    else:
        log("⚠️  无法从代理获取内容，跳过HK频道")
    
    # 6. 再提取TW频道（4gtv前30个，过滤指定频道）- 排在后面
    tw_channels = []
    if proxy_content:
        tw_channels = extract_filtered_4gtv_channels(proxy_content, limit=30)
    else:
        log("⚠️  无法从代理获取内容，跳过TW频道")
    
    # 7. 构建M3U内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部（使用最佳EPG）
    if best_epg:
        m3u_header = f'#EXTM3U url-tvg="{best_epg}" x-tvg-url="{best_epg}"\n'
        log(f"✅ 使用EPG: {best_epg}")
    else:
        m3u_header = '#EXTM3U\n'
        log("⚠️  未找到可用EPG")
    
    # 计算BB频道数量
    bb_count = len(re.findall(r'^#EXTINF:', bb_content, re.MULTILINE))
    
    output = m3u_header + f"""# =============================================
# CC.m3u - 统一频道列表
# 由 cc_merge.py 自动生成
# =============================================
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 17:00 (北京时间)
# BB源: {BB_URL}
# 代理源: {CLOUDFLARE_PROXY}
# JULI分组已改为HK (按指定顺序排列在最前面)
# HK优先顺序: {', '.join(HK_PRIORITY_ORDER)}
# 4gtv分组已改为TW (前30个，排在后面，已过滤指定频道)
# 过滤频道: {', '.join(BLACKLIST_TW)}
# EPG源: {best_epg if best_epg else '无可用EPG'}
# 测试的EPG源: {len(unique_epgs)} 个
# GitHub Actions 自动生成

"""
    
    # 添加BB内容（跳过第一行）
    bb_lines = bb_content.split('\n')
    bb_actual_count = 0
    skip_first = True
    
    for line in bb_lines:
        line = line.rstrip()
        if not line:
            continue
        
        if skip_first and line.startswith('#EXTM3U'):
            skip_first = False
            continue
        
        output += line + '\n'
        if line.startswith('#EXTINF:'):
            bb_actual_count += 1
    
    # 添加HK频道（JULI）- 按指定顺序排列在最前面
    if hk_channels:
        output += f"""
# =============================================
# HK频道 (原JULI，按指定顺序排列在最前面)
# =============================================
# 优先顺序: {', '.join(HK_PRIORITY_ORDER)}
# 说明：相同频道的多个源已合并，每个URL单独一行，提供冗余备份
"""
        
        # 显示优先频道
        priority_added = False
        for channel_type in HK_PRIORITY_ORDER:
            type_channels = [(extinf, urls) for extinf, urls in hk_channels if channel_type.lower() in extinf.lower()]
            if type_channels:
                if not priority_added:
                    output += f"\n# --- 优先频道（按指定顺序） ---\n"
                    priority_added = True
                
                for extinf, urls in type_channels:
                    output += extinf + '\n'
                    # 每个URL单独一行
                    for url in urls:
                        output += url + '\n'
                    output += '\n'  # 频道间空行
        
        # 显示其他HK频道
        other_hk_channels = [(extinf, urls) for extinf, urls in hk_channels 
                           if not any(channel_type.lower() in extinf.lower() for channel_type in HK_PRIORITY_ORDER)]
        
        if other_hk_channels:
            output += f"\n# --- 其他HK频道 ---\n"
            for extinf, urls in other_hk_channels:
                output += extinf + '\n'
                # 每个URL单独一行
                for url in urls:
                    output += url + '\n'
                output += '\n'  # 频道间空行
    
    # 添加TW频道（4gtv）- 排在后面（已过滤）
    if tw_channels:
        output += f"""
# =============================================
# TW频道 (原4gtv，前30个，已过滤指定频道，排在HK之后)
# =============================================
# 已过滤: {', '.join(BLACKLIST_TW)}
"""
        for extinf, url in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加EPG信息说明
    if unique_epgs:
        output += f"""
# =============================================
# EPG信息
# =============================================
# 使用EPG: {best_epg if best_epg else '无'}
# 测试的EPG源 ({len(unique_epgs)}个):"""
        for i, epg in enumerate(unique_epgs, 1):
            status = "✅" if epg == best_epg else "  "
            output += f"\n#   {status} {i:2d}. {epg}"
    
    # 添加统计信息
    # 计算HK频道的总源数
    hk_total_sources = sum(len(urls) for _, urls in hk_channels) if hk_channels else 0
    
    output += f"""
# =============================================
# 统计信息
# =============================================
# BB 频道数: {bb_actual_count}
# HK 频道数: {len(hk_channels)} (原JULI，按指定顺序排列)
# HK 总源数: {hk_total_sources} (相同频道多个源已合并)
# TW 频道数: {len(tw_channels)} (原4gtv前30个，已过滤，排在后)
# 过滤频道数: {len(BLACKLIST_TW)} 个
# 总频道数: {bb_actual_count + len(hk_channels) + len(tw_channels)}
# EPG状态: {'✅ 正常' if best_epg else '❌ 无可用EPG'}
# 更新时间: {timestamp} (北京时间)
# 更新频率: 每天 06:00 和 17:00 (北京时间)
# 排序规则: BB → HK(凤凰/NOW优先) → TW(已过滤)
# 脚本文件: scripts/cc_merge.py
# 工作流: .github/workflows/cc-workflow.yml
# 仓库: https://github.com/${{ github.repository }}
"""
    
    # 8. 保存文件
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        
        log(f"\n🎉 CC脚本完成!")
        log(f"📁 文件: {output_path}")
        log(f"📏 大小: {len(output)} 字符")
        log(f"📡 EPG: {best_epg if best_epg else '无可用EPG'}")
        log(f"📺 BB频道: {bb_actual_count}")
        log(f"📺 HK频道: {len(hk_channels)} (按指定顺序排列)")
        log(f"📺 HK总源数: {hk_total_sources}")
        log(f"📺 TW频道: {len(tw_channels)} (已过滤指定频道)")
        log(f"📺 总计频道数: {bb_actual_count + len(hk_channels) + len(tw_channels)}")
        log(f"🕒 下次自动更新: 北京时间 06:00 和 17:00")
        log(f"🔗 工作流: .github/workflows/cc-workflow.yml")
        
        # 检查文件是否保存成功
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            log(f"✅ 文件保存成功，大小: {file_size} 字节")
            
            # 显示部分内容确认
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:20]
                log(f"📄 文件前20行预览:")
                for i, line in enumerate(lines[:10], 1):
                    log(f"  {i:2d}: {line.strip()}")
                log("  ...")
        else:
            log("❌ 文件保存失败")
            
    except Exception as e:
        log(f"❌ 文件保存失败: {e}")
        # 尝试保存到当前目录作为备份
        try:
            backup_path = OUTPUT_FILE
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(output)
            log(f"⚠️  已保存备份文件到: {backup_path}")
        except:
            log("❌ 备份文件保存也失败")

if __name__ == "__main__":
    main()
