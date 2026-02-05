#!/usr/bin/env python3
"""
从订阅链接提取指定分组并与本地M3U文件合并，输出CC.m3u
"""

import requests
import sys
import os
from datetime import datetime

print("=" * 70)
print("🚀 开始执行 M3U 合并脚本")
print("=" * 70)

# 打印基本信息
print(f"📂 当前工作目录: {os.getcwd()}")
print(f"📁 脚本位置: {os.path.abspath(__file__)}")
print(f"📊 Python 版本: {sys.version}")
print("=" * 70)

def extract_group_from_url():
    """从订阅链接中提取港澳台分组"""
    try:
        url = "https://stymei.sufern001.workers.dev/"
        print(f"🌐 正在从 {url} 获取数据...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        print(f"✅ 获取数据成功，长度: {len(content)} 字符")
        
        # 查找目标分组
        lines = content.split('\n')
        channels = []
        in_target_group = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 查找目标分组
            if '🔥全网通港澳台,#genre#' in line:
                print(f"🎯 找到目标分组: {line}")
                in_target_group = True
                continue
                
            # 如果在下个分组开始，停止收集
            if in_target_group and line.endswith(',#genre#'):
                break
                
            # 收集频道
            if in_target_group and ',' in line and '://' in line.split(',')[-1]:
                channels.append(line)
        
        if channels:
            print(f"✅ 提取到 {len(channels)} 个港澳台频道")
            return channels
        else:
            print("⚠️  未提取到港澳台频道")
            # 显示前几个分组供调试
            print("找到的分组有:")
            count = 0
            for line in lines:
                if '#genre#' in line:
                    print(f"  - {line}")
                    count += 1
                    if count >= 5:
                        break
            return []
            
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def load_local_m3u():
    """加载本地BB.m3u文件"""
    try:
        filepath = "BB.m3u"
        print(f"\n📖 正在加载本地文件: {filepath}")
        
        if not os.path.exists(filepath):
            print(f"⚠️  {filepath} 不存在，创建空文件")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                f.write("# 自动创建的本地文件\n")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = [line.rstrip() for line in content.split('\n') if line.strip()]
        print(f"✅ 加载成功，共 {len(lines)} 行")
        return lines
        
    except Exception as e:
        print(f"❌ 加载本地文件失败: {e}")
        return []

def save_cc_m3u(local_lines, hk_channels):
    """保存CC.m3u文件"""
    try:
        output_file = "CC.m3u"
        print(f"\n💾 正在生成: {output_file}")
        
        output_lines = []
        
        # M3U头
        output_lines.append("#EXTM3U")
        output_lines.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append("# 来源: https://stymei.sufern001.workers.dev/")
        output_lines.append("")
        
        # 本地内容
        if local_lines:
            print(f"📝 添加本地内容: {len(local_lines)} 行")
            # 跳过第一个#EXTM3U
            added = False
            for line in local_lines:
                if line.strip() == "#EXTM3U" and not added:
                    added = True
                    continue
                output_lines.append(line)
            output_lines.append("")
        
        # 港澳台分组
        if hk_channels:
            print(f"📺 添加港澳台分组: {len(hk_channels)} 个频道")
            output_lines.append("#" + "=" * 50)
            output_lines.append("# 全网通港澳台频道")
            output_lines.append("#" + "=" * 50)
            output_lines.append("全网通港澳台,#genre#")
            for channel in hk_channels:
                output_lines.append(channel)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(output_lines))
        
        # 验证
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"\n🎉 {output_file} 生成成功!")
            print(f"   位置: {os.path.abspath(output_file)}")
            print(f"   大小: {file_size} 字节")
            print(f"   行数: {len(output_lines)}")
            
            # 显示文件内容
            print("\n📋 文件前10行:")
            with open(output_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"   {i+1}: {line.rstrip()}")
                    else:
                        break
            
            return True
        else:
            print(f"❌ 文件未生成!")
            return False
            
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🔄 开始处理流程")
    print("=" * 70)
    
    # 1. 提取港澳台频道
    hk_channels = extract_group_from_url()
    
    # 2. 加载本地文件
    local_lines = load_local_m3u()
    
    # 3. 保存CC.m3u
    success = save_cc_m3u(local_lines, hk_channels)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ 任务完成!")
        # 列出当前目录
        print("\n📁 当前目录文件:")
        for item in os.listdir('.'):
            if item.endswith('.m3u') or item == 'scripts':
                print(f"   - {item}")
    else:
        print("❌ 任务失败")
        sys.exit(1)
    
    print("=" * 70)

if __name__ == "__main__":
    main()
