#!/usr/bin/env python3
"""
CC.m3u 合并脚本
从 https://stymei.sufern001.workers.dev/ 提取"🔥全网通港澳台"分组
重命名为"全网通港澳台"，与本地 BB.m3u 合并，输出 CC.m3u
"""

import requests
from datetime import datetime
import os

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def main():
    log("开始生成 CC.m3u ...")
    print("=" * 70)
    
    # 配置
    source_url = "https://stymei.sufern001.workers.dev/"
    bb_file = "BB.m3u"
    output_file = "CC.m3u"
    source_group = "🔥全网通港澳台"
    target_group = "全网通港澳台"
    
    log(f"工作目录: {os.getcwd()}")
    log(f"源URL: {source_url}")
    log(f"目标分组: {source_group} -> {target_group}")
    
    try:
        # 1. 下载源数据
        log("正在下载源数据...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(source_url, headers=headers, timeout=30)
        response.raise_for_status()
        source_content = response.text
        log(f"✅ 下载成功，{len(source_content)} 字符")
        
        # 2. 提取港澳台分组
        log(f"正在提取分组: {source_group}")
        lines = source_content.split('\n')
        channels = []
        in_target_group = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找目标分组
            if f"{source_group},#genre#" in line:
                log("✅ 找到目标分组")
                in_target_group = True
                continue
            
            # 如果开始下一个分组，停止
            if in_target_group and '#genre#' in line:
                break
            
            # 收集频道
            if in_target_group and line and ',' in line and '://' in line.split(',')[-1]:
                channels.append(line)
        
        log(f"提取到 {len(channels)} 个港澳台频道")
        
        # 3. 加载本地BB.m3u
        log(f"加载本地文件: {bb_file}")
        if os.path.exists(bb_file):
            with open(bb_file, 'r', encoding='utf-8') as f:
                bb_content = f.read()
            bb_lines = [l.rstrip() for l in bb_content.split('\n') if l.strip()]
            log(f"✅ 加载本地文件成功，{len(bb_lines)} 行")
        else:
            log("⚠️ BB.m3u 不存在，使用空内容")
            bb_lines = ["#EXTM3U", "# 本地频道列表"]
        
        # 4. 生成CC.m3u内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output_lines = []
        
        # 头部信息
        output_lines.append("#EXTM3U")
        output_lines.append(f"# CC.m3u - 生成时间: {timestamp}")
        output_lines.append(f"# 源URL: {source_url}")
        output_lines.append(f"# 提取分组: {source_group} -> {target_group}")
        output_lines.append("")
        
        # 本地内容
        if bb_lines:
            # 跳过已存在的EXTM3U
            extm3u_found = False
            for line in bb_lines:
                if line.strip() == "#EXTM3U" and not extm3u_found:
                    extm3u_found = True
                    continue
                output_lines.append(line)
        
        # 港澳台分组
        if channels:
            output_lines.append("")
            output_lines.append("#" + "=" * 60)
            output_lines.append("# 全网通港澳台频道")
            output_lines.append("#" + "=" * 60)
            output_lines.append(f"{target_group},#genre#")
            for channel in channels:
                output_lines.append(channel)
        
        # 5. 保存文件
        log(f"正在保存到: {output_file}")
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(output_lines))
        
        # 验证
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            log(f"✅ CC.m3u 生成成功!")
            log(f"   文件大小: {file_size} 字节")
            log(f"   总行数: {len(output_lines)}")
            log(f"   港澳台频道: {len(channels)} 个")
            
            # 显示文件头
            print("\n📋 文件前10行:")
            with open(output_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"   {i+1}: {line.rstrip()}")
                    else:
                        break
        else:
            log("❌ 文件保存失败")
            
    except Exception as e:
        log(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)
    log("执行完成")

if __name__ == "__main__":
    main()
