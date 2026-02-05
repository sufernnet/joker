#!/usr/bin/env python3
"""
从订阅链接提取指定分组并与本地M3U文件合并，输出CC.m3u
"""

import requests
import re
import sys
import os
import argparse
from datetime import datetime
import traceback

def extract_group_from_url(url, target_group_name):
    """从订阅链接中提取指定分组的内容"""
    try:
        print(f"📡 正在从 {url} 获取数据...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        content = response.text
        
        print(f"✅ 数据获取成功，长度: {len(content)} 字符")
        
        # 搜索分组
        lines = content.split('\n')
        extracted_channels = []
        found_group = False
        capture_started = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # 检查是否为分组标题行
            if '#genre#' in line:
                if target_group_name in line:
                    found_group = True
                    capture_started = True
                    print(f"🎯 找到目标分组: {line}")
                    continue
                elif capture_started:
                    # 遇到下一个分组，停止捕获
                    break
            
            # 如果已开始捕获目标分组，收集频道行
            if capture_started and line and ',' in line:
                # 检查是否是有效的频道行（频道名称,URL）
                parts = line.split(',')
                if len(parts) >= 2 and ('://' in parts[-1] or parts[-1].startswith('http')):
                    extracted_channels.append(line)
        
        if found_group:
            print(f"✅ 成功提取到 {len(extracted_channels)} 个频道")
            return "全网通港澳台,#genre#", extracted_channels
        else:
            print(f"⚠️  未找到分组: {target_group_name}")
            print("找到的分组有:")
            for line in lines:
                if '#genre#' in line:
                    print(f"  - {line}")
            return None, []
            
    except requests.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return None, []
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        return None, []

def load_local_m3u(filepath):
    """加载本地M3U文件"""
    try:
        # 转换为绝对路径
        if not os.path.isabs(filepath):
            filepath = os.path.join(os.getcwd(), filepath)
        
        print(f"📂 尝试加载本地文件: {filepath}")
        
        if not os.path.exists(filepath):
            print(f"⚠️  文件不存在: {filepath}")
            # 创建基本的M3U结构
            return ["#EXTM3U", "# 自动生成的BB.m3u文件"]
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = [line.rstrip() for line in content.split('\n') if line.strip()]
        print(f"✅ 已加载本地文件，{len(lines)} 行")
        return lines
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return ["#EXTM3U", f"# 错误: 无法加载 {filepath}"]

def merge_and_save(local_content, group_header, channels, output_file):
    """合并内容并保存"""
    try:
        # 确保输出路径是绝对路径
        if not os.path.isabs(output_file):
            output_file = os.path.join(os.getcwd(), output_file)
        
        print(f"\n💾 准备生成文件: {output_file}")
        print(f"   当前工作目录: {os.getcwd()}")
        
        output_lines = []
        
        # 添加M3U头
        output_lines.append("#EXTM3U")
        output_lines.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append(f"# 工具: merge_to_CC.py")
        output_lines.append(f"# 源URL: https://stymei.sufern001.workers.dev/")
        output_lines.append("")
        
        # 添加本地内容（如果有）
        if local_content and len(local_content) > 0:
            print(f"📝 添加本地内容: {len(local_content)} 行")
            # 跳过已存在的EXTM3U头
            extm3u_found = False
            for line in local_content:
                if line.strip() == "#EXTM3U":
                    if not extm3u_found:
                        extm3u_found = True
                        continue
                output_lines.append(line)
            output_lines.append("")
        
        # 添加提取的分组
        if group_header and channels and len(channels) > 0:
            print(f"📺 添加提取分组: {len(channels)} 个频道")
            output_lines.append("#" + "="*60)
            output_lines.append("# 全网通港澳台频道（从源URL提取）")
            output_lines.append("#" + "="*60)
            output_lines.append(group_header)
            for channel in channels:
                output_lines.append(channel)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 写入文件
        print(f"🔄 写入文件到: {output_file}")
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(output_lines))
        
        # 验证文件已创建
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            line_count = len(output_lines)
            print(f"\n🎉 文件创建成功!")
            print(f"   📍 文件路径: {output_file}")
            print(f"   📊 文件大小: {file_size} 字节")
            print(f"   📄 总行数: {line_count}")
            
            # 显示文件部分内容
            print(f"\n📋 文件前10行内容:")
            with open(output_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"   {i+1}: {line.rstrip()}")
                    else:
                        break
            
            return True
        else:
            print(f"❌ 文件创建失败! 路径: {output_file}")
            print(f"   当前目录内容:")
            for item in os.listdir('.'):
                print(f"   - {item}")
            return False
        
    except Exception as e:
        print(f"❌ 保存失败: {e}")
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
    
    print("="*70)
    print("🔄 M3U合并工具 - 生成 CC.m3u")
    print("="*70)
    print(f"🏠 工作目录: {os.getcwd()}")
    print(f"🐍 脚本位置: {os.path.abspath(__file__)}")
    print(f"📥 本地文件: {args.local}")
    print(f"📤 输出文件: {args.output}")
    print(f"🌐 源URL: {args.url}")
    print(f"🏷️  提取分组: {args.group}")
    print("="*70)
    
    # 提取分组
    group_header, channels = extract_group_from_url(args.url, args.group)
    
    # 加载本地文件
    local_content = load_local_m3u(args.local)
    
    # 合并保存
    print("\n" + "="*70)
    success = merge_and_save(local_content, group_header, channels, args.output)
    
    # 最终检查
    print("\n" + "="*70)
    if success:
        # 再次确认文件存在
        if os.path.exists(args.output):
            with open(args.output, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"✅ 最终确认: {args.output} 已成功生成")
            print(f"   文件位置: {os.path.abspath(args.output)}")
            print(f"   实际行数: {len(lines)}")
            print("🎊 任务完成!")
        else:
            print(f"⚠️  警告: 文件 {args.output} 不存在于预期位置")
            print("当前目录内容:")
            for item in os.listdir('.'):
                print(f"  - {item}")
    else:
        print("❌ 任务失败")
        sys.exit(1)
    
    print("="*70)

if __name__ == "__main__":
    main()
