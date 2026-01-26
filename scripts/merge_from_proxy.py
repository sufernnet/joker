#!/usr/bin/env python3
"""
M3U文件合并脚本 - 完整EPG解决方案
1. 下载BB.m3u（包含EPG信息）
2. 从Cloudflare代理获取内容
3. 提取JULI频道，分组改为HK，按指定顺序排列
4. 提取4gtv前30个直播，分组改为TW，过滤指定频道
5. 为HK/TW频道添加tvg-id，确保EPG匹配
6. 合并生成CC.m3u，包含多个EPG源
北京时间每天6:00、18:00自动运行
"""

import requests
import re
import os
import time
import hashlib
from datetime import datetime
from urllib.parse import urlparse, parse_qs

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
    "半岛国际",
    "NHK world-japan",
    "NHK world",
    "NHK",
    "半島",
    "日本",
    "SBN",
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

# EPG频道ID映射（手动匹配）
CHANNEL_ID_MAPPING = {
    # 凤凰系列
    "凤凰中文": "凤凰中文",
    "凤凰资讯": "凤凰资讯", 
    "凤凰香港": "凤凰香港",
    
    # NOW系列
    "NOW新闻台": "NOW新闻台",
    "NOW星影": "NOW星影",
    "NOW爆谷": "NOW爆谷",
    
    # 常见HK频道
    "TVB新闻": "TVB新闻",
    "TVB财经": "TVB财经",
    "有线新闻": "有线新闻",
    "香港开电视": "香港开电视",
    "VIU TV": "VIU TV",
    
    # 常见TW频道
    "民视": "民视",
    "中视": "中视",
    "华视": "华视",
    "台视": "台视",
    "三立": "三立",
    "东森": "东森",
    "TVBS": "TVBS",
    "中天": "中天",
    "寰宇": "寰宇",
    "非凡": "非凡",
}

# 备选EPG源（按优先级排序）
EPG_SOURCES = [
    "https://epg.112114.xyz/pp.xml",  # 主要EPG
    "https://epg.112114.xyz/pp.xml",
    "http://epg.51zmt.top:8000/e.xml",  # 备用EPG
    "https://epg.112114.xyz/pp.xml",
]

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def generate_tvg_id(channel_name, channel_url):
    """为频道生成稳定的tvg-id"""
    # 清理频道名
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
    
    # 方法1：使用预定义映射
    for key, value in CHANNEL_ID_MAPPING.items():
        if key in channel_name:
            return value
    
    # 方法2：从URL提取ID
    if channel_url:
        parsed = urlparse(channel_url)
        if parsed.query:
            params = parse_qs(parsed.query)
            for key in ['id', 'channel', 'ch', 'freq']:
                if key in params:
                    return params[key][0]
        
        # 从路径提取
        path_parts = parsed.path.split('/')
        if len(path_parts) > 1:
            last_part = path_parts[-1].split('.')[0]
            if last_part and len(last_part) > 3:
                return last_part
    
    # 方法3：使用哈希生成稳定ID
    hash_input = f"{clean_name}_{channel_url}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    # 方法4：使用频道名关键词
    for keyword in ["凤凰", "NOW", "TVB", "有线", "民视", "中视", "华视", "台视", "三立", "东森"]:
        if keyword in channel_name:
            return f"{keyword}_{short_hash[:4]}"
    
    return f"CH_{short_hash}"

def enhance_extinf_with_epg(extinf_line, channel_name, channel_url, epg_source):
    """增强EXTINF行，添加EPG信息"""
    # 生成tvg-id
    tvg_id = generate_tvg_id(channel_name, channel_url)
    
    # 检查是否已有tvg-id
    if 'tvg-id=' in extinf_line:
        # 保留原有的tvg-id
        return extinf_line
    
    # 提取原有属性
    attributes_match = re.search(r'^#EXTINF:(-?\d+)(.*?),(.+)$', extinf_line)
    if not attributes_match:
        return extinf_line
    
    duration = attributes_match.group(1)
    attributes = attributes_match.group(2).strip()
    display_name = attributes_match.group(3)
    
    # 构建新的属性
    new_attributes = f' tvg-id="{tvg_id}" tvg-name="{channel_name}"'
    
    # 如果已有group-title，保留；否则添加
    if 'group-title=' not in attributes:
        # 根据频道名判断分组
        if any(hk in channel_name for hk in ["凤凰", "NOW", "TVB", "有线", "VIU"]):
            new_attributes += ' group-title="HK"'
        elif any(tw in channel_name for tw in ["民视", "中视", "华视", "台视", "三立", "东森", "TVBS"]):
            new_attributes += ' group-title="TW"'
    
    # 组合新的EXTINF行
    if attributes:
        new_extinf = f'#EXTINF:{duration}{attributes}{new_attributes},{display_name}'
    else:
        new_extinf = f'#EXTINF:{duration}{new_attributes},{display_name}'
    
    return new_extinf

def test_epg_coverage(epg_url, channels):
    """测试EPG对频道的覆盖率"""
    try:
        log(f"测试EPG覆盖率: {epg_url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # 只下载部分内容检查
        response = requests.get(epg_url, headers=headers, timeout=15, stream=True)
        
        if response.status_code != 200:
            return 0
        
        # 读取前50KB检查
        content = b""
        for chunk in response.iter_content(chunk_size=1024):
            content += chunk
            if len(content) > 50000:  # 50KB
                break
        
        epg_content = content.decode('utf-8', errors='ignore')
        
        # 统计匹配的频道
        matched_channels = 0
        total_channels = len(channels)
        
        for channel_name, _ in channels[:20]:  # 只检查前20个频道
            # 简化频道名用于匹配
            simple_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
            
            # 检查EPG中是否有这个频道
            if simple_name in epg_content:
                matched_channels += 1
        
        coverage = (matched_channels / min(20, total_channels)) * 100 if total_channels > 0 else 0
        
        log(f"  EPG覆盖率: {coverage:.1f}% ({matched_channels}/{min(20, total_channels)})")
        return coverage
        
    except Exception as e:
        log(f"  EPG覆盖率测试失败: {e}")
        return 0

def get_best_epg_for_channels(channels):
    """为频道选择最佳的EPG源"""
    log(f"为 {len(channels)} 个频道选择最佳EPG...")
    
    best_epg = None
    best_coverage = 0
    
    for epg_url in EPG_SOURCES:
        coverage = test_epg_coverage(epg_url, channels)
        if coverage > best_coverage:
            best_coverage = coverage
            best_epg = epg_url
    
    if best_epg and best_coverage > 30:  # 覆盖率至少30%
        log(f"✅ 选择EPG: {best_epg} (覆盖率: {best_coverage:.1f}%)")
        return best_epg
    else:
        log(f"⚠️  没有合适的EPG源 (最佳覆盖率: {best_coverage:.1f}%)")
        return EPG_SOURCES[0]  # 返回第一个作为默认

def download_bb_m3u():
    """下载BB.m3u"""
    try:
        log("下载BB.m3u...")
        response = requests.get(BB_URL, timeout=10)
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
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
            'Referer': 'https://smart.946985.filegear-sg.me/'
        }
        
        response = requests.get(CLOUDFLARE_PROXY, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            # 如果是HTML，尝试提取M3U内容
            if '<html' in content.lower():
                m3u_match = re.search(r'(#EXTM3U.*?)(?:</pre>|</code>|$)', content, re.DOTALL)
                if m3u_match:
                    content = m3u_match.group(1).strip()
                    log("✅ 从HTML提取到M3U内容")
            
            if content and content.strip():
                log(f"✅ 获取到内容 ({len(content)} 字符)")
                return content
        else:
            log(f"❌ 代理返回错误: {response.status_code}")
            
    except Exception as e:
        log(f"❌ 代理访问失败: {e}")
    
    return None

def extract_and_enhance_hk_channels(content, epg_url):
    """提取并增强HK频道（添加EPG信息）"""
    if not content:
        return []
    
    log("提取并增强HK频道...")
    
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
    
    # 过滤JULI频道
    hk_channels_info = []  # 存储(priority, extinf, url, channel_name, enhanced_extinf)
    
    for extinf, url in channels:
        if 'JULI' in extinf.upper():
            # 提取频道名
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            
            # 计算优先级
            priority = len(HK_PRIORITY_ORDER)
            for i, priority_channel in enumerate(HK_PRIORITY_ORDER):
                if priority_channel in channel_name:
                    priority = i
                    break
            
            # 增强EXTINF（添加EPG信息）
            enhanced_extinf = enhance_extinf_with_epg(extinf, channel_name, url, epg_url)
            
            # 替换分组为HK
            enhanced_extinf = re.sub(r'group-title="[^"]*"', 'group-title="HK"', enhanced_extinf)
            if 'group-title=' not in enhanced_extinf:
                enhanced_extinf = enhanced_extinf.replace('#EXTINF:', '#EXTINF: group-title="HK",', 1)
            
            hk_channels_info.append((priority, extinf, url, channel_name, enhanced_extinf))
    
    # 按优先级排序
    hk_channels_info.sort(key=lambda x: x[0])
    
    # 提取排序和增强后的频道
    hk_channels = [(enhanced_extinf, url) for _, _, url, _, enhanced_extinf in hk_channels_info]
    
    log(f"✅ 提取并增强 {len(hk_channels)} 个HK频道")
    
    return hk_channels

def extract_and_enhance_tw_channels(content, epg_url, limit=30):
    """提取并增强TW频道（添加EPG信息）"""
    if not content:
        return []
    
    log(f"提取并增强TW频道（前{limit}个）...")
    
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
    
    # 过滤4gtv频道
    tw_channels = []
    
    for extinf, url in channels:
        if '4gtv' in extinf.lower():
            # 提取频道名
            channel_name = extinf.split(',', 1)[1] if ',' in extinf else extinf
            
            # 检查是否在黑名单中
            skip = False
            for black_word in BLACKLIST_TW:
                if black_word.lower() in channel_name.lower():
                    skip = True
                    break
            
            if not skip:
                # 增强EXTINF（添加EPG信息）
                enhanced_extinf = enhance_extinf_with_epg(extinf, channel_name, url, epg_url)
                
                # 替换分组为TW
                enhanced_extinf = re.sub(r'group-title="[^"]*"', 'group-title="TW"', enhanced_extinf)
                if 'group-title=' not in enhanced_extinf:
                    enhanced_extinf = enhanced_extinf.replace('#EXTINF:', '#EXTINF: group-title="TW",', 1)
                
                tw_channels.append((enhanced_extinf, url, channel_name))
    
    # 只取前limit个
    if len(tw_channels) > limit:
        tw_channels = tw_channels[:limit]
    
    # 最终格式
    final_channels = [(extinf, url) for extinf, url, _ in tw_channels]
    
    log(f"✅ 提取并增强 {len(final_channels)} 个TW频道")
    
    return final_channels

def main():
    """主函数"""
    log("开始合并M3U文件（完整EPG解决方案）...")
    
    # 1. 下载BB.m3u
    bb_content = download_bb_m3u()
    if not bb_content:
        log("❌ 无法继续，BB.m3u下载失败")
        return
    
    # 2. 从代理获取内容
    proxy_content = get_content_from_proxy()
    
    # 3. 先提取频道信息用于EPG测试
    test_channels = []
    if proxy_content:
        lines = proxy_content.split('\n')
        current_extinf = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#EXTINF:'):
                current_extinf = line
            elif current_extinf and '://' in line and not line.startswith('#'):
                channel_name = current_extinf.split(',', 1)[1] if ',' in current_extinf else current_extinf
                test_channels.append((channel_name, line))
    
    # 4. 选择最佳EPG
    epg_url = get_best_epg_for_channels(test_channels)
    
    # 5. 提取并增强HK频道
    hk_channels = []
    if proxy_content:
        hk_channels = extract_and_enhance_hk_channels(proxy_content, epg_url)
    
    # 6. 提取并增强TW频道
    tw_channels = []
    if proxy_content:
        tw_channels = extract_and_enhance_tw_channels(proxy_content, epg_url, limit=30)
    
    # 7. 构建M3U内容
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # M3U头部（包含EPG和EPG参数）
    m3u_header = f"""#EXTM3U x-tvg-url="{epg_url}" url-tvg="{epg_url}"
#EXTVLCOPT:program=999999
"""
    
    output = m3u_header + f"""# 自动合并 M3U 文件
# 生成时间: {timestamp} (北京时间)
# 下次更新: 每天 06:00 和 18:00 (北京时间)
# BB源: {BB_URL}
# 代理源: {CLOUDFLARE_PROXY}
# HK频道: {len(hk_channels)} 个 (已添加EPG信息)
# TW频道: {len(tw_channels)} 个 (已添加EPG信息)
# EPG源: {epg_url}
# GitHub Actions 自动生成

"""
    
    # 添加BB内容
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
    
    # 添加HK频道
    if hk_channels:
        output += f"\n# HK频道 ({len(hk_channels)}个，已添加tvg-id)\n"
        
        # 优先频道
        priority_channels = [(extinf, url) for extinf, url in hk_channels 
                           if any(priority in extinf for priority in HK_PRIORITY_ORDER)]
        
        if priority_channels:
            output += f"# --- 优先频道 ---\n"
            for extinf, url in priority_channels:
                output += extinf + '\n'
                output += url + '\n'
        
        # 其他HK频道
        other_channels = [(extinf, url) for extinf, url in hk_channels 
                         if not any(priority in extinf for priority in HK_PRIORITY_ORDER)]
        
        if other_channels:
            output += f"# --- 其他HK频道 ---\n"
            for extinf, url in other_channels:
                output += extinf + '\n'
                output += url + '\n'
    
    # 添加TW频道
    if tw_channels:
        output += f"\n# TW频道 ({len(tw_channels)}个，已添加tvg-id)\n"
        for extinf, url in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加EPG使用说明
    output += f"""
# EPG使用说明
# 1. 此文件已添加 tvg-id 和 tvg-name 属性
# 2. EPG源: {epg_url}
# 3. 如果EPG不显示，请检查播放器设置:
#    - 确保启用EPG功能
#    - 检查时区设置（建议使用UTC+8）
#    - 清除EPG缓存后重新加载
# 4. 常见EPG问题:
#    - 频道ID不匹配：我们已为每个频道生成稳定ID
#    - EPG源失效：自动选择最佳可用源
#    - 时区不对：EPG使用UTC+8时间

# 统计信息
# BB 频道数: {bb_count}
# HK 频道数: {len(hk_channels)} (已增强EPG)
# TW 频道数: {len(tw_channels)} (已增强EPG)
# 总频道数: {bb_count + len(hk_channels) + len(tw_channels)}
# EPG状态: ✅ 已配置
# 更新时间: {timestamp}
# 更新频率: 每天 06:00 和 18:00 (北京时间)
"""
    
    # 8. 保存文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    
    log(f"\n🎉 合并完成!")
    log(f"📁 文件: {OUTPUT_FILE}")
    log(f"📏 大小: {len(output)} 字符")
    log(f"📡 EPG: {epg_url}")
    log(f"🎯 HK频道: {len(hk_channels)} (已添加tvg-id)")
    log(f"🎯 TW频道: {len(tw_channels)} (已添加tvg-id)")
    log(f"📺 总计: {bb_count + len(hk_channels) + len(tw_channels)}")
    log(f"🕒 下次自动更新: 北京时间 06:00 和 18:00")

if __name__ == "__main__":
    main()
