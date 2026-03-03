#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import time

# EPG源列表
EPG_URLS = [
    "http://epg.51zmt.top:8000/e1.xml.gz",
    "https://epg.136605.xyz/9days.xml.gz",
    "https://epg.zsdc.eu.org/t.xml.gz",
    "https://epg.pw/xmltv/epg_CN.xml.gz",
    "https://epg.pw/xmltv/epg_TW.xml.gz",
    "https://epg.pw/xmltv/epg_HK.xml.gz",
]

def download_and_decompress(url, retry=3):
    """下载并解压 .gz 文件，返回XML字符串"""
    for i in range(retry):
        try:
            print(f"正在下载: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            
            # 解压gzip文件
            with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
                content = f.read()
                print(f"  下载成功，大小: {len(content)} 字节")
                return content.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"  第{i+1}次尝试失败: {e}")
            time.sleep(2)
    
    print(f"  × 下载失败: {url}")
    return None

def merge_epg_sources():
    """合并所有EPG源"""
    all_programmes = []
    tv_attrib = {}
    source_count = 0
    
    print("="*50)
    print("开始合并EPG源")
    print("="*50)
    
    for url in EPG_URLS:
        print(f"\n处理源 #{source_count+1}:")
        xml_content = download_and_decompress(url)
        
        if xml_content is None:
            continue
            
        try:
            # 解析XML
            root = ET.fromstring(xml_content)
            
            # 保存第一个源的tv标签属性
            if not tv_attrib and root.attrib:
                tv_attrib = root.attrib
                print(f"  使用tv属性: {tv_attrib}")
            
            # 提取所有programme元素
            programmes = root.findall('programme')
            count = len(programmes)
            all_programmes.extend(programmes)
            print(f"  提取到 {count} 个节目")
            source_count += 1
            
        except ET.ParseError as e:
            print(f"  XML解析错误: {e}")
        except Exception as e:
            print(f"  处理出错: {e}")
    
    print("\n" + "="*50)
    print(f"合并完成: 共处理 {source_count} 个源，提取 {len(all_programmes)} 个节目")
    
    # 创建新的根元素
    if not tv_attrib:
        tv_attrib = {"generator-info-name": "EPG Merger", "date": time.strftime("%Y%m%d")}
    
    new_root = ET.Element('tv', tv_attrib)
    
    # 将所有programme添加到新根元素下
    for prog in all_programmes:
        new_root.append(prog)
    
    # 创建ElementTree并写入压缩文件
    tree = ET.ElementTree(new_root)
    
    # 获取脚本所在目录的上一级目录（根目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    output_file = os.path.join(root_dir, 'epg.xml.gz')
    
    print(f"文件将保存到: {output_file}")
    
    with gzip.open(output_file, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    file_size = os.path.getsize(output_file)
    print(f"合并文件已保存: {output_file} ({file_size} 字节)")
    print("="*50)
    
    return output_file

if __name__ == "__main__":
    merge_epg_sources()
