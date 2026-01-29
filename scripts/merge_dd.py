#!/usr/bin/env python3
"""
DD.m3u合并脚本 - 调试版
"""

import requests
import re
import os
from datetime import datetime

# 配置
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://gh-proxy.org/https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1"
OUTPUT_FILE = "DD.m3u"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download_and_debug(url, description):
    """下载并调试内容"""
    try:
        log(f"下载 {description}...")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        log(f"状态码: {response.status_code}")
        log(f"内容长度: {len(response.text)} 字符")
        
        if response.status_code == 200:
            content = response.text
            
            # 显示前500字符
            log(f"内容前500字符:")
            print("-" * 50)
            print(content[:500])
            print("-" * 50)
            
            # 检查是否是M3U格式
            if content.startswith('#EXTM3U'):
                log("✅ 是有效的M3U格式")
            else:
                log("⚠️  不是标准M3U格式")
                
                # 尝试查找M3U内容
                if '#EXTINF:' in content:
                    log("✅ 找到 #EXTINF: 标记，可能是M3U内容")
                else:
                    log("❌ 没有找到 #EXTINF: 标记")
            
            return content
        else:
            log(f"下载失败: {response.status_code}")
            return None
            
    except Exception as e:
        log(f"下载异常: {e}")
        return None

def analyze_channels(content):
    """分析频道内容"""
    if not content:
        log("内容为空")
        return []
    
    log("分析频道...")
    
    # 查找所有EXTINF行
    lines = content.split('\n')
    extinf_lines = []
    urls = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('#EXTINF:'):
            extinf_lines.append((i, line))
        elif line and '://' in line and not line.startswith('#'):
            urls.append((i, line))
    
    log(f"找到 {len(extinf_lines)} 个 #EXTINF 行")
    log(f"找到 {len(urls)} 个 URL 行")
    
    # 匹配EXTINF和URL
    channels = []
    for i, extinf in extinf_lines:
        # 找对应的URL（在EXTINF后面的几行内）
        for j, url in urls:
            if j > i and j - i <= 5:  # URL在EXTINF后5行内
                channels.append((extinf, url[1]))
                break
    
    log(f"匹配到 {len(channels)} 个完整频道")
    
    # 显示前5个频道
    if channels:
        log("前5个频道:")
        for idx, (extinf, url) in enumerate(channels[:5]):
            # 提取频道名
            if ',' in extinf:
                name = extinf.split(',', 1)[1]
                log(f"  {idx+1}. {name[:50]}...")
                log(f"     URL: {url[:80]}...")
            else:
                log(f"  {idx+1}. {extinf[:50]}...")
    
    return channels

def classify_channels(channels):
    """分类频道"""
    log("分类频道...")
    
    hk_keywords = ["香港", "HK", "Hong Kong", "TVB", "凤凰", "有线", "NOW", "VIU", "港"]
    tw_keywords = ["台湾", "TW", "Taiwan", "台视", "中视", "华视", "民视", "三立", "东森", "TVBS"]
    
    hk_channels = []
    tw_channels = []
    other_channels = []
    
    for extinf, url in channels:
        # 提取频道名
        if ',' in extinf:
            channel_name = extinf.split(',', 1)[1]
        else:
            channel_name = extinf
        
        log(f"分析频道: {channel_name[:30]}...")
        
        # 检查是否包含关键词
        name_lower = channel_name.lower()
        
        is_hk = False
        is_tw = False
        
        # 检查香港关键词
        for keyword in hk_keywords:
            if keyword.lower() in name_lower:
                log(f"  → 识别为香港频道 (关键词: {keyword})")
                is_hk = True
                break
        
        # 检查台湾关键词
        if not is_hk:
            for keyword in tw_keywords:
                if keyword.lower() in name_lower:
                    log(f"  → 识别为台湾频道 (关键词: {keyword})")
                    is_tw = True
                    break
        
        # 处理频道
        if is_hk:
            # 确保有group-title
            if 'group-title=' not in extinf:
                new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="香港",', 1)
            else:
                new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="香港"', extinf)
            hk_channels.append((new_extinf, url, channel_name))
        elif is_tw:
            if 'group-title=' not in extinf:
                new_extinf = extinf.replace('#EXTINF:', '#EXTINF: group-title="台湾",', 1)
            else:
                new_extinf = re.sub(r'group-title="[^"]*"', 'group-title="台湾"', extinf)
            tw_channels.append((new_extinf, url, channel_name))
        else:
            other_channels.append((extinf, url, channel_name))
            log(f"  → 未识别，归为其他")
    
    log(f"分类结果: 香港 {len(hk_channels)} 个, 台湾 {len(tw_channels)} 个, 其他 {len(other_channels)} 个")
    
    # 显示分类详情
    if hk_channels:
        log("香港频道列表:")
        for extinf, url, name in hk_channels[:5]:
            log(f"  • {name[:40]}...")
    
    if tw_channels:
        log("台湾频道列表:")
        for extinf, url, name in tw_channels[:5]:
            log(f"  • {name[:40]}...")
    
    return hk_channels, tw_channels, other_channels

def main():
    """主函数"""
    log("=== DD.m3u 生成调试 ===")
    
    # 1. 下载BB.m3u
    log("\n=== 1. 下载BB.m3u ===")
    bb_content = download_and_debug(BB_URL, "BB.m3u")
    
    if not bb_content:
        log("❌ BB.m3u下载失败，使用默认内容")
        bb_content = "#EXTM3U url-tvg=\"https://epg.112114.xyz/pp.xml\"\n#EXTINF:-1,测试频道\nhttp://example.com\n"
    
    # 2. 下载港澳台源
    log("\n=== 2. 下载港澳台源 ===")
    gat_content = download_and_debug(GAT_URL, "港澳台源")
    
    if not gat_content:
        log("⚠️  港澳台源下载失败，使用测试数据")
        # 创建测试数据
        gat_content = """#EXTM3U
#EXTINF:-1,香港卫视中文台
http://example.com/hk1
#EXTINF:-1,台湾中视新闻台
http://example.com/tw1
#EXTINF:-1,凤凰卫视香港台
http://example.com/fh
#EXTINF:-1,TVBS新闻台
http://example.com/tvbs
#EXTINF:-1,香港TVB翡翠台
http://example.com/tvb
#EXTINF:-1,台湾民视新闻台
http://example.com/ftv
"""
    
    # 3. 分析港澳台频道
    log("\n=== 3. 分析港澳台频道 ===")
    channels = analyze_channels(gat_content)
    
    # 4. 分类频道
    log("\n=== 4. 分类频道 ===")
    hk_channels, tw_channels, other_channels = classify_channels(channels)
    
    # 5. 提取EPG
    log("\n=== 5. 提取EPG ===")
    epg_match = re.search(r'url-tvg="([^"]+)"', bb_content)
    epg_url = epg_match.group(1) if epg_match else None
    log(f"EPG: {epg_url if epg_url else '未找到'}")
    
    # 6. 构建DD.m3u
    log("\n=== 6. 生成DD.m3u ===")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 头部
    if epg_url:
        header = f'#EXTM3U url-tvg="{epg_url}"\n'
    else:
        header = '#EXTM3U\n'
    
    output = header + f"""# DD.m3u - 港澳台专版
# 生成时间: {timestamp}
# 下次更新: 每天 06:00 和 17:00
# BB源: {BB_URL}
# 港澳台源: {GAT_URL}
# EPG: {epg_url if epg_url else '沿用BB'}
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
    
    # 添加香港频道
    if hk_channels:
        output += f"\n# 香港频道 ({len(hk_channels)}个)\n"
        for extinf, url, name in hk_channels:
            output += extinf + '\n'
            output += url + '\n'
    else:
        log("⚠️  没有香港频道")
        output += f"\n# 香港频道 (0个 - 未找到匹配的频道)\n"
    
    # 添加台湾频道
    if tw_channels:
        output += f"\n# 台湾频道 ({len(tw_channels)}个)\n"
        for extinf, url, name in tw_channels:
            output += extinf + '\n'
            output += url + '\n'
    else:
        log("⚠️  没有台湾频道")
        output += f"\n# 台湾频道 (0个 - 未找到匹配的频道)\n"
    
    # 添加其他频道（如果需要）
    if other_channels and len(other_channels) > 0:
        output += f"\n# 其他频道 ({len(other_channels)}个)\n"
        for extinf, url, name in other_channels[:20]:  # 只显示前20个
            output += extinf + '\n'
            output += url + '\n'
    
    # 添加统计
    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# 香港频道数: {len(hk_channels)}
# 台湾频道数: {len(tw_channels)}
# 其他频道数: {len(other_channels)}
# 总频道数: {bb_count + len(hk_channels) + len(tw_channels) + len(other_channels)}
# 更新时间: {timestamp}
# 下次更新: 每天 06:00 和 17:00
"""
    
    # 7. 保存文件
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        
        log(f"✅ DD.m3u 生成成功")
        log(f"文件大小: {len(output)} 字符")
        log(f"香港频道: {len(hk_channels)} 个")
        log(f"台湾频道: {len(tw_channels)} 个")
        
        # 显示文件前10行
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            log("文件前10行:")
            for i, line in enumerate(f.readlines()[:10]):
                log(f"  {i+1}: {line.rstrip()}")
                
    except Exception as e:
        log(f"❌ 保存文件失败: {e}")

if __name__ == "__main__":
    main()
