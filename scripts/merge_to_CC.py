#!/usr/bin/env python3
"""
CC.m3u 合并脚本 - 标准M3U格式
从 https://stymei.sufern001.workers.dev/ 提取"🔥全网通港澳台"分组
生成标准M3U格式：#EXTINF标签 + group-title属性
"""

import requests
from datetime import datetime
import os
import re

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def extract_tvg_info(channel_name):
    """从频道名提取tvg-id和tvg-name"""
    # 移除特殊字符，只保留字母数字和中文字符
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', channel_name)
    
    # 如果包含中文，使用原名称作为tvg-name
    if re.search(r'[\u4e00-\u9fff]', channel_name):
        tvg_name = channel_name
        # 生成英文ID：取拼音首字母或使用数字
        tvg_id = f"channel_{hash(channel_name) % 10000}"
    else:
        tvg_name = channel_name
        tvg_id = clean_name
    
    return tvg_id, tvg_name

def download_source():
    """下载源数据"""
    try:
        url = "https://stymei.sufern001.workers.dev/"
        log(f"正在下载源数据: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/plain'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        log(f"✅ 下载成功，{len(content)} 字符")
        return content
        
    except Exception as e:
        log(f"❌ 下载失败: {e}")
        return None

def extract_channels(content):
    """从源数据提取港澳台频道"""
    source_group = "🔥全网通港澳台"
    target_group = "全网通港澳台"
    
    log(f"正在提取分组: {source_group}")
    
    if not content:
        log("❌ 源数据为空")
        return []
    
    lines = content.split('\n')
    channels = []
    in_target_group = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 查找目标分组
        if f"{source_group},#genre#" in line:
            log(f"✅ 在第 {i+1} 行找到目标分组")
            in_target_group = True
            continue
        
        # 如果开始下一个分组，停止
        if in_target_group and '#genre#' in line and source_group not in line:
            log("到达下一个分组，停止提取")
            break
        
        # 收集频道行 (格式: 频道名,URL)
        if in_target_group and line and ',' in line:
            parts = line.split(',')
            if len(parts) >= 2:
                channel_name = parts[0].strip()
                url = ','.join(parts[1:]).strip()  # 处理URL中可能包含逗号的情况
                
                # 验证URL
                if url and ('://' in url or url.startswith('http')):
                    # 提取tvg信息
                    tvg_id, tvg_name = extract_tvg_info(channel_name)
                    channels.append({
                        'name': channel_name,
                        'url': url,
                        'tvg_id': tvg_id,
                        'tvg_name': tvg_name,
                        'group': target_group
                    })
    
    log(f"✅ 提取到 {len(channels)} 个港澳台频道")
    
    # 调试：显示前几个频道
    if channels:
        log("前5个频道:")
        for i, ch in enumerate(channels[:5]):
            log(f"  {i+1}. {ch['name']} -> {ch['url'][:50]}...")
    
    return channels

def load_local_bb():
    """加载本地BB.m3u文件"""
    bb_file = "BB.m3u"
    
    try:
        if not os.path.exists(bb_file):
            log(f"⚠️  {bb_file} 不存在，创建默认文件")
            # 创建标准M3U格式的默认文件
            default_content = '''#EXTM3U
#EXTINF:-1 tvg-id="" tvg-name="本地频道1" tvg-logo="" group-title="本地",本地频道1
http://example.com/channel1

#EXTINF:-1 tvg-id="" tvg-name="本地频道2" tvg-logo="" group-title="本地",本地频道2
http://example.com/channel2'''
            
            with open(bb_file, 'w', encoding='utf-8') as f:
                f.write(default_content)
            
            # 读取创建的内容
            content = default_content
        else:
            log(f"正在加载本地文件: {bb_file}")
            with open(bb_file, 'r', encoding='utf-8') as f:
                content = f.read()
        
        lines = content.split('\n')
        log(f"✅ 加载本地文件成功，{len(lines)} 行")
        
        # 返回原始内容，保持原有格式
        return content
        
    except Exception as e:
        log(f"❌ 加载本地文件失败: {e}")
        return "#EXTM3U\n"

def generate_cc_m3u(local_content, hk_channels):
    """生成标准M3U格式的CC.m3u"""
    output_file = "CC.m3u"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log(f"正在生成标准M3U格式文件: {output_file}")
    
    output_lines = []
    
    # 1. M3U头部信息
    output_lines.append("#EXTM3U")
    output_lines.append(f"# CC.m3u - 标准M3U格式")
    output_lines.append(f"# 生成时间: {timestamp}")
    output_lines.append(f"# 源URL: https://stymei.sufern001.workers.dev/")
    output_lines.append(f"# 提取分组: 🔥全网通港澳台 -> 全网通港澳台")
    output_lines.append(f"# 频道总数: {len(hk_channels)} 个港澳台频道")
    output_lines.append("")
    
    # 2. 添加本地内容（保持原样）
    if local_content and local_content.strip():
        output_lines.append("#" + "=" * 60)
        output_lines.append("# 本地频道")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        local_lines = local_content.split('\n')
        # 跳过空的#EXTM3U行（如果已添加）
        for line in local_lines:
            if line.strip() == "#EXTM3U" and len(output_lines) > 1:
                continue
            output_lines.append(line)
        
        output_lines.append("")
    
    # 3. 添加港澳台频道（标准M3U格式）
    if hk_channels:
        output_lines.append("#" + "=" * 60)
        output_lines.append("# 全网通港澳台频道")
        output_lines.append("#" + "=" * 60)
        output_lines.append("")
        
        for channel in hk_channels:
            # 生成#EXTINF行
            extinf_line = f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}" tvg-name="{channel["tvg_name"]}" tvg-logo="" group-title="{channel["group"]}",{channel["name"]}'
            output_lines.append(extinf_line)
            
            # URL行
            output_lines.append(channel["url"])
            
            # 可选：添加空行分隔（美观）
            output_lines.append("")
        
        # 移除最后一个空行
        if output_lines[-1] == "":
            output_lines.pop()
    
    # 4. 添加统计信息
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# 统计信息")
    output_lines.append(f"# 港澳台频道数: {len(hk_channels)}")
    output_lines.append(f"# 更新时间: {timestamp}")
    output_lines.append("# GitHub Actions 自动生成")
    output_lines.append("#" + "=" * 60)
    
    return '\n'.join(output_lines)

def main():
    log("开始生成标准M3U格式的CC.m3u ...")
    print("=" * 70)
    
    try:
        # 1. 下载源数据
        source_content = download_source()
        if not source_content:
            log("❌ 无法获取源数据，退出")
            return
        
        # 2. 提取港澳台频道
        hk_channels = extract_channels(source_content)
        
        if not hk_channels:
            log("⚠️  未提取到港澳台频道，检查源数据格式")
            # 显示源数据中的分组供调试
            lines = source_content.split('\n')
            log("源数据中的分组:")
            for line in lines:
                if '#genre#' in line:
                    log(f"  - {line}")
        
        # 3. 加载本地BB.m3u
        local_content = load_local_bb()
        
        # 4. 生成CC.m3u内容
        cc_content = generate_cc_m3u(local_content, hk_channels)
        
        # 5. 保存文件
        output_file = "CC.m3u"
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(cc_content)
        
        # 验证文件
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            line_count = cc_content.count('\n') + 1
            
            log(f"✅ CC.m3u 生成成功!")
            log(f"   文件位置: {os.path.abspath(output_file)}")
            log(f"   文件大小: {file_size} 字节")
            log(f"   总行数: {line_count}")
            log(f"   港澳台频道数: {len(hk_channels)}")
            
            # 显示文件格式示例
            print("\n📋 生成的文件格式示例:")
            print("=" * 60)
            lines = cc_content.split('\n')
            for i, line in enumerate(lines[:15]):  # 显示前15行
                if i < len(lines):
                    print(line)
            print("...")
            print("=" * 60)
            
            # 显示具体的EXTINF示例
            print("\n🎯 生成的EXTINF格式示例:")
            for channel in hk_channels[:3]:  # 显示前3个频道
                print(f'#EXTINF:-1 tvg-id="{channel["tvg_id"]}" tvg-name="{channel["tvg_name"]}" tvg-logo="" group-title="{channel["group"]}",{channel["name"]}')
                print(channel["url"][:50] + "..." if len(channel["url"]) > 50 else channel["url"])
                print()
            
        else:
            log("❌ 文件保存失败")
            
    except Exception as e:
        log(f"❌ 执行过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)
    log("执行完成")

if __name__ == "__main__":
    main()
