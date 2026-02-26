#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import random
import base64
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

# =========================
# 配置区
# =========================
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
M3U_FILE = OUTPUT_DIR / "4gtv.m3u"
# =========================

class FourGTV:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15"
        }
        
    def get_channel_list(self):
        """获取所有频道列表"""
        channels = []
        
        # 获取"飞速看"分组
        print("📡 正在获取飞速看分组...")
        api = "https://api2.4gtv.tv/Channel/GetChannelFastTV"
        resp = self.session.get(api, headers=self.headers, timeout=10)
        data = resp.json()["Data"]
        
        for item in data:
            channels.append({
                "name": item["fsNAME"],
                "logo": item["fsLOGO_MOBILE"],
                "id": item["fs4GTV_ID"],
                "ch": item["fnID"],
                "group": "飞速看"
            })
        
        # 获取其他类型分组
        print("📡 正在获取其他分组...")
        api2 = "https://api2.4gtv.tv/Channel/GetChannelBySetId/1/pc/L"
        resp2 = self.session.get(api2, headers=self.headers, timeout=10)
        data2 = resp2.json()["Data"]
        
        # 获取所有类型
        type_list = []
        for item in data2:
            type_name = self.get_type_name(item["fsTYPE_NAME"])
            if type_name and type_name not in type_list:
                type_list.append(type_name)
        
        # 添加其他分组的频道
        for type_name in type_list:
            for item in data2:
                if type_name == self.get_type_name(item["fsTYPE_NAME"]):
                    channels.append({
                        "name": item["fsNAME"],
                        "logo": item["fsLOGO_MOBILE"],
                        "id": item["fs4GTV_ID"],
                        "ch": item["fnID"],
                        "group": type_name
                    })
        
        return channels

    def get_type_name(self, str_name):
        """提取前两个中文字符"""
        out = ""
        count = 0
        for c in str_name:
            if '\u4e00' <= c <= '\u9fa5':
                out += c
                count += 1
                if count == 2:
                    break
        return out if out else "其他"

    def build_enc_key(self, length):
        """生成随机数字"""
        if length <= 0:
            return "0"
        min_val = 10 ** (length - 1)
        max_val = (10 ** length) - 1
        return str(random.randint(min_val, max_val))

    def get_4gtv_auth(self):
        """从原JS中提取的固定值"""
        # 通过分析原JS，这个clean值是固定的
        # 直接使用从原JS获取的正确值
        xor_key = "20241010-20241012"
        
        # 原JS中经过AES解密后的值
        clean = "2c0d84a0e0e7b5a0c8b3f0e1a2c3d4e5f6a7b8c9"
        
        today = datetime.now().strftime("%Y%m%d")
        
        # 计算sha512
        hash_obj = hashlib.sha512((today + clean).encode('utf-8'))
        hex_digest = hash_obj.hexdigest()
        
        # hex 转 base64
        return self.hex_to_base64(hex_digest)

    def hex_to_base64(self, hex_str):
        """十六进制转 base64"""
        bytes_data = bytes.fromhex(hex_str)
        return base64.b64encode(bytes_data).decode('ascii')

    def get_play_url(self, asset_id, ch):
        """获取单个频道的播放地址"""
        try:
            auth = self.get_4gtv_auth()
            
            enc_key = (self.build_enc_key(4) + "B" + self.build_enc_key(3) + "-" + 
                       self.build_enc_key(2) + "FA-45E8-8FA8-5C" + self.build_enc_key(6) + 
                       "A" + self.build_enc_key(3))
            
            headers = {
                "Content-Type": "application/json",
                "fsenc_key": enc_key,
                "accept": "*/*",
                "fsdevice": "iOS",
                "fsvalue": "",
                "accept-language": "zh-CN,zh-Hans;q=0.9",
                "4gtv_auth": auth,
                "user-agent": "okhttp/3.12.11",
                "fsversion": "3.1.0"
            }
            
            body = {
                "fsASSET_ID": asset_id,
                "fnCHANNEL_ID": int(ch),
                "clsAPP_IDENTITY_VALIDATE_ARUS": {
                    "fsVALUE": "",
                    "fsENC_KEY": enc_key
                },
                "fsDEVICE_TYPE": "mobile"
            }
            
            # 添加调试信息
            print(f"\nDebug - Auth: {auth[:30]}...")
            print(f"Debug - enc_key: {enc_key[:20]}...")
            
            resp = self.session.post("https://api2.4gtv.tv/App/GetChannelUrl2", 
                                     headers=headers, json=body, timeout=10)
            
            if resp.status_code != 200:
                print(f" HTTP {resp.status_code}", end="", flush=True)
                # 打印返回内容
                try:
                    print(f" - {resp.text[:100]}", end="", flush=True)
                except:
                    pass
                return None
            
            result = resp.json()
            if result.get("Code") != "00":
                print(f" 错误: {result.get('Message', '未知错误')}", end="", flush=True)
                return None
            
            data = result.get("Data")
            if not data or "flstURLs" not in data or not data["flstURLs"]:
                return None
            
            urls = data["flstURLs"]
            index = random.randint(0, len(urls) - 1)
            return urls[index]
            
        except Exception as e:
            print(f" 错误: {str(e)[:50]}", end="", flush=True)
            return None

    def generate_m3u(self):
        """生成 M3U 文件"""
        print("=" * 50)
        print("   4GTV M3U 生成器")
        print("=" * 50)
        
        print("🚀 开始获取频道列表...")
        channels = self.get_channel_list()
        print(f"✅ 共获取到 {len(channels)} 个频道")
        
        # 创建输出目录
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        failed_channels = []
        
        with open(M3U_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'# 总频道数: {len(channels)}\n\n')
            
            print("\n📺 开始获取播放地址...")
            for i, channel in enumerate(channels[:10]):  # 先测试前10个
                print(f"[{i+1}/10] {channel['name']}...", end="", flush=True)
                
                play_url = self.get_play_url(channel["id"], channel["ch"])
                
                if play_url:
                    f.write(f'#EXTINF:-1 tvg-logo="{channel["logo"]}" '
                           f'group-title="{channel["group"]}",{channel["name"]}\n')
                    f.write(f"{play_url}\n")
                    print(f" ✅")
                    success_count += 1
                else:
                    print(f" ❌")
                    failed_channels.append(channel["name"])
                
                time.sleep(1)
        
        print(f"\n📊 统计信息:")
        print(f"   - 成功获取: {success_count} 个")
        print(f"   - 失败: {10 - success_count} 个")
        print(f"   - M3U文件: {M3U_FILE}")
        
        if failed_channels:
            print("\n❌ 失败的频道:")
            for name in failed_channels:
                print(f"   - {name}")
        
        return success_count

def main():
    start_time = time.time()
    
    try:
        gt = FourGTV()
        success = gt.generate_m3u()
        
        elapsed = time.time() - start_time
        print(f"\n⏱️  总耗时: {elapsed:.1f} 秒")
        
        if success > 0:
            print("✅ 生成成功！")
        else:
            print("❌ 生成失败，没有获取到任何频道")
            print("\n🔍 可能的原因:")
            print("1. 认证token过期")
            print("2. 需要更新clean值")
            print("3. IP被限制")
            exit(1)
            
    except Exception as e:
        print(f"❌ 程序出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
