#!/usr/bin/env python3
"""
从订阅链接提取指定分组并与本地M3U文件合并，输出CC.m3u
"""

import requests
import re
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

def extract_group_from_url(url, target_group_name):
    """从订阅链接中提取指定分组的内容"""
    try:
        print(f"正在从 {url} 获取数据...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text
        
        print(f"数据获取成功，长度: {len(content)} 字符")
        
        # 搜索分组
        lines = content.split('\n')
        extracted_channels = []
        found_group = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if '#genre#' in line and target_group_name in line:
                found_group = True
                print(f"✅ 找到目标分组: {line}")
                continue
            
            if found_group:
                # 如果遇到下一个分组，停止
                if '#genre#' in line:
                    break
                # 收集有效频道行
                if line and ',' in line and '://' in line.split(',')[-1]:
                    extracted_channels.append(line)
        
        if found_group and extracted_channels:
            print(f"✅ 成功提取到 {len(extracted_channels)} 个频道")
            return "全网通港澳台,#genre#", extracted_channels
        else:
            print(f"⚠️  找到分组但未提取到频道或未找到分组")
            return None, []
            
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        return None, []

def load_local_m3u(filepath):
    """加载本地M3U文件"""
    try:
        abs_path = os.path.abspath(filepath)
        print(f"尝试加载本地文件: {abs_path}")
        
        if not os.path.exists(filepath):
            print(f"⚠️  文件不存在: {filepath}")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = [line.rstrip() for line in content.split('\n') if line.strip()]
        print(f"✅ 已加载本地文件，{len(lines)} 行")
        return lines
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return []

def merge_and_save(local_content, group_header, channels, output_file):
    """合并内容并保存"""
    try:
        output_path = os.path.abspath(output_file)
        print(f"\n准备生成文件: {output_path}")
        
        output_lines = []
        
        # 添加M3U头
        output_lines.append("#EXTM3U")
        output_lines.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append(f"# 工具: merge_to_CC.py")
        output_lines.append("")
        
        # 添加本地内容（如果有）
        if local_content:
            print(f"添加本地内容: {len(local_content)} 行")
            # 跳过已存在的EXTM3U头
            for line in local_content:
                if line.strip() != "#EXTM3U" or len(output_lines) > 10:
                    output_lines.append(line)
            output_lines.append("")
        
        # 添加提取的分组
        if group_header and channels:
            print(f"添加提取分组: {len(channels)} 个频道")
            output_lines.append("#" + "="*50)
            output_lines.append("# 全网通港澳台频道")
            output_lines.append("#" + "="*50)
            output_lines.append(group_header)
            for channel in channels:
                output_lines.append(channel)
        
        # 写入文件
        print(f"写入文件到: {output_path}")
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(output_lines))
        
        # 验证文件已创建
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ 文件创建成功!")
            print(f"   文件路径: {output_path}")
            print(f"   文件大小: {file_size} 字节")
            print(f"   总行数: {len(output_lines)}")
            return True
        else:
            print(f"❌ 文件创建失败!")
            return False
        
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='提取订阅链接分组并合并到CC.m3u')
    parser.add_argument('--url', default='https://stymei.sufern001.workers.dev/',
                       help='订阅链接URL')
    parser.add_argument('--group', default='🔥全网通港澳台',
                       help='要提取的分组名称')
    parser.add_argument('--local', default='BB.m3u',
                       help='本地M3U文件')
    parser.add_argument('--output', default='CC.m3u',
                       help='输出文件')
    
    args = parser.parse_args()
    
    print("="*60)
    print("M3U合并工具 - 生成 CC.m3u")
    print("="*60)
    print(f"工作目录: {os.getcwd()}")
    print(f"脚本目录: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"本地文件: {args.local}")
    print(f"输出文件: {args.output}")
    print("="*60)
    
    # 提取分组
    group_header, channels = extract_group_from_url(args.url, args.group)
    
    # 加载本地文件
    local_content = load_local_m3u(args.local)
    
    # 合并保存
    success = merge_and_save(local_content, group_header, channels, args.output)
    
    # 最终检查
    print("\n" + "="*60)
    if success:
        print("🎉 任务完成!")
        # 再次确认文件存在
        if os.path.exists(args.output):
            with open(args.output, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"✅ 确认: {args.output} 存在，{len(lines)} 行")
        else:
            print(f"⚠️  警告: {args.output} 不存在于预期位置")
    else:
        print("❌ 任务失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
