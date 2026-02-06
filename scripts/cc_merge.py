#!/usr/bin/env python3
"""
CC合并脚本 - 完整版
生成CC.m3u文件，统一使用CC前缀便于记忆
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取内容
3. 提取JULI频道，分组改为HK，按指定顺序排列
4. 提取4gtv前30个直播，分组改为TW，过滤指定频道
5. 合并生成CC.m3u，包含多个EPG源
北京时间每天6:00、17:00自动运行
"""

import requests
import re
import os
import time
from datetime import datetime
import urllib3

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
    "https://epg.112114.xyz/pp.xml",
]

def log(msg):
    """输出日志"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

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
                import gzip
                try:
                    # 读取前100字节检查
                    chunk = response.raw.read(100)
                    # 尝试解压
                    try:
                        gzip.decompress(chunk)
                        log(f"✅ EPG可用 (GZIP格式): {epg_url}")
                        return True
                    except:
                        log(f"⚠️  EPG不是有效的GZIP格式: {epg_url}")
                        return False
                except:
                    return False
        else:
            # 常规XML文件
            response = requests.get(epg_url, headers=headers, timeout=timeout, stream=True, verify=False)
            
            if response.status_code == 200:
                # 检查内容类型
                content_type = response.headers.get('content-type', '').lower()
                
                # 读取前1KB检查
                chunk = response.raw.read(1024)
                text = chunk.decode('utf-8', errors='ignore')
                
                # 检查是否是XML格式
                if '<?xml' in text or '<tv' in text or '<programme' in text:
                    log(f"✅ EPG可用: {epg_url}")
                    return True
                else:
                    log(f"⚠️  EPG不是XML格式: {epg_url}")
                    return False
            else:
                log(f"❌ EPG不可访问: {epg_url} (状态码: {response.status_code})")
                return False
            
    except Exception as e:
        log(f"❌ EPG测试失败 {epg_url}: {e}")
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
        
        response = requests.get(CLOUDFLARE_PROXY, headers=headers, timeout=20, verify=False)
        
        if response.status_code == 200:
            content = response.text
            
            # 如果是HTML，尝试提取M3U内容
            if '<html' in content.lower():
                log("检测到HTML响应，尝试提取M3U内容...")
                
                # 方法1：查找<pre>或<code>标签中的内容
                m3u_match = re.search(r'(?i)<pre[^>]*>(.*?)</pre>', content, re.DOTALL)
                if not m3u_match:
                    m3u_match = re.search(r'(?i)<code[^>]*>(.*?)</code>', content, re.DOTALL)
                
                if m3u_match:
                    content = m3u_match.group(1).strip()
                    log("✅ 从HTML标签提取到M3U内容")
                else:
                    # 方法2：查找#EXTM3U开头的行
                    lines = content.split('\n')
                    m3u_lines = []
                    in_m3u = False
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('#EXTM3U'):
                            in_m3u = True
                            m3u_lines.append(line)
                        elif in_m3u:
                            if line.startswith('#EXTINF:') or ('://' in line and not line.startswith('<') and not line.startswith('<!')):
                                m3u_lines.append(line)
                            elif not line:
                                m3u_lines.append(line)
                            else:
                                # 遇到非M3U内容，停止收集
                                break
                    
                    if m3u_lines:
                        content = '\n'.join(m3u_lines)
                        log(f"✅ 提取到 {len(m3u_lines)} 行M3U内容")
                    else:
                        # 方法3：提取所有看起来像频道的行
                        channel_lines = []
                        for line in lines:
                            line = line.strip()
                            if line.startswith('#EXTINF:') or ('.m3u8' in line and '://' in line):
                                channel_lines.append(line)
                        
                        if channel_lines:
                            content = '#EXTM3U\n' + '\n'.join(channel_lines)
                            log(f"✅ 提取到 {len(channel_lines)} 个频道行")
                        else:
                            log("⚠️  无法从HTML提取M3U内容")
                            return None
            
            if content and content.strip():
                log(f"✅ 获取到内容 ({len(content)} 字符)")
                
                # 确保以#EXTM3U开头
                if not content.startswith('#EXTM3U'):
                    content = '#EXTM3U\n' + content
                
                return content
            else:
                log("⚠️  内容为空")
        else:
            log(f"❌ 代理返回错误: {response.status_code}")
            
    except Exception as e:
        log(f"❌ 代理访问失败: {e}")
    
    return None

def get_channel_priority(channel_name):
    """获取频道的优先级（越小越靠前）"""
    channel_name_lower = channel_name.lower()
    
    for i, priority_channel in enumerate(HK_PRIORITY_ORDER):
        if priority_channel.lower() in channel_name_lower:
            return i  # 返回优先级索引，越小越靠前
    
    return len(HK_PRIORITY_ORDER)  # 非优先频道排在最后

def extract_and_sort_hk_channels(content):
    """提取JULI频道，分组改为HK，按指定顺序排列"""
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
    
    # 过滤JULI频道并重命名
    hk_channels_with_priority = []
    seen = set()
    juli_count = 0
    
    for extinf, url in channels:
        # 查找JULI频道（不区分大小写）
        if 'juli' in extinf.lower():
            juli_count += 1
            # 提取原始频道名
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            
            # 重命名为HK分组
            new_extinf = re.sub(r'juli', 'HK', extinf, flags=re.IGNORECASE)
            
            # 确保group-title为HK
            if 'group-title=' in new_extinf:
                new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="HK"', new_extinf)
            else:
                # 添加group-title
                if ',' in new_extinf:
                    parts = new_extinf.split(',', 1)
                    new_extinf = f'{parts[0]} group-title="HK",{parts[1]}'
            
            # 去重
            key = f"{new_extinf}|{url}"
            if key not in seen:
                seen.add(key)
                # 计算优先级
                priority = get_channel_priority(channel_name)
                hk_channels_with_priority.append((priority, new_extinf, url, channel_name))
    
    log(f"找到 {juli_count} 个JULI频道")
    
    # 按优先级排序
    hk_channels_with_priority.sort(key=lambda x: x[0])
    
    # 提取排序后的频道
    hk_channels = [(extinf, url) for _, extinf, url, _ in hk_channels_with_priority]
    
    log(f"✅ 提取到 {len(hk_channels)} 个HK频道（原JULI）")
    
    # 显示排序结果
    if hk_channels:
        log("HK频道排序结果:")
        for i, (extinf, url) in enumerate(hk_channels[:10], 1):  # 显示前10个
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i:2d}. {channel_name}")
        if len(hk_channels) > 10:
            log(f"  ... 还有 {len(hk_channels) - 10} 个频道")
    
    return hk_channels

def should_skip_channel(channel_name):
    """检查频道是否应该被过滤"""
    channel_name_lower = channel_name.lower()
    
    # 检查是否在黑名单中
    for black_word in BLACKLIST_TW:
        if black_word.lower() in channel_name_lower:
            log(f"  过滤掉: {channel_name} (包含: {black_word})")
            return True
    
    return False

def extract_filtered_4gtv_channels(content, limit=30):
    """提取4gtv频道（前30个），分组改为TW，过滤指定频道"""
    if not content:
        return []
    
    log(f"提取4gtv前{limit}个直播，分组改为TW，过滤指定频道...")
    log(f"过滤列表: {', '.join(BLACKLIST_TW)}")
    
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
    for extinf, url in filtered_channels:
        # 提取频道名
        channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
        
        # 检查是否应该跳过
        if not should_skip_channel(channel_name):
            filtered_by_blacklist.append((extinf, url))
        else:
            log(f"  ⛔ 过滤: {channel_name}")
    
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
        log("TW频道示例:")
        for i, (extinf, url) in enumerate(tw_channels[:5], 1):
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            log(f"  {i:2d}. {channel_name}")
    
    return tw_channels

def main():
    """主函数"""
    log("🚀 CC脚本开始运行...")
    log(f"📁 输出文件: {OUTPUT_FILE}")
    
    # 显示当前时间（用于调试定时任务）
    current_time = datetime.now()
    log(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"下次运行: 北京时间 06:00 和 17:00")
    log(f"HK优先顺序: {', '.join(HK_PRIORITY_ORDER)}")
    log(f"TW频道过滤列表: {', '.join(BLACKLIST_TW)}")
    
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
    bb_count = 0
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
            bb_count += 1
    
    # 添加HK频道（JULI）- 按指定顺序排列在最前面
    if hk_channels:
        output += f"""
# =============================================
# HK频道 (原JULI，按指定顺序排列在最前面)
# =============================================
# 优先顺序: {', '.join(HK_PRIORITY_ORDER)}
"""
        
        # 显示优先频道
        priority_added = False
        for channel_type in HK_PRIORITY_ORDER:
            type_channels = [(extinf, url) for extinf, url in hk_channels if channel_type.lower() in extinf.lower()]
            if type_channels:
                if not priority_added:
                    output += f"\n# --- 优先频道（按指定顺序） ---\n"
                    priority_added = True
                
                for extinf, url in type_channels:
                    output += extinf + '\n'
                    output += url + '\n'
        
        # 显示其他HK频道
        other_hk_channels = [(extinf, url) for extinf, url in hk_channels 
                           if not any(channel_type.lower() in extinf.lower() for channel_type in HK_PRIORITY_ORDER)]
        
        if other_hk_channels:
            output += f"\n# --- 其他HK频道 ---\n"
            for extinf, url in other_hk_channels:
                output += extinf + '\n'
                output += url + '\n'
    
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
            output += f"\n#   {status} {epg}"
    
    # 添加统计信息
    output += f"""
# =============================================
# 统计信息
# =============================================
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)} (原JULI，按指定顺序排列)
# TW 频道数: {len(tw_channels)} (原4gtv前30个，已过滤，排在后)
# 过滤频道: {len(BLACKLIST_TW)} 个
# 总频道数: {bb_count + len(hk_channels) + len(tw_channels)}
# EPG状态: {'✅ 正常' if best_epg else '❌ 无可用EPG'}
# 更新时间: {timestamp} (北京时间)
# 更新频率: 每天 06:00 和 17:00 (北京时间)
# 排序规则: BB → HK(凤凰/NOW优先) → TW(已过滤)
# 脚本文件: cc_merge.py
# 工作流: .github/workflows/cc-workflow.yml
"""
    
    # 8. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 CC脚本完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {best_epg if best_epg else '无可用EPG'}")
    log(f"📺 BB频道: {bb_count}")
    log(f"📺 HK频道: {len(hk_channels)} (按指定顺序排列)")
    log(f"📺 TW频道: {len(tw_channels)} (已过滤指定频道)")
    log(f"📺 总计: {bb_count + len(hk_channels) + len(tw_channels)}")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 17:00")
    log(f"🔗 工作流: .github/workflows/cc-workflow.yml")

if __name__ == "__main__":
    main()
