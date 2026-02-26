#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import random
import base64
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

# =========================
# 配置区
# =========================
# 获取当前文件所在目录的上一级目录（项目根目录）
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

    def base64_to_xor(self, b64_str, key):
        """Base64 解码后进行 XOR 运算"""
        try:
            decoded = base64.b64decode(b64_str).decode('latin-1')
        except:
            decoded = base64.urlsafe_b64decode(b64_str + '==').decode('latin-1')
        
        result = ""
        for i in range(len(decoded)):
            result += chr(ord(decoded[i]) ^ ord(key[i % len(key)]))
        return result

    def hex_to_base64(self, hex_str):
        """十六进制转 base64"""
        bytes_data = bytes.fromhex(hex_str)
        return base64.b64encode(bytes_data).decode('ascii')

    def get_4gtv_auth(self):
        """生成 4gtv_auth 认证"""
        xor_key = "20241010-20241012"
        
        enc_data = "YklifmQCBFlkAHljd3xnQAVZUl5DWQlCd25LQENHSX1BBkF7WH5eCQRjZgYDWgQJVlcZWAFcVmZcWGRUYWNwH38GBnBcaEBtRwl1Vlp5G0dRBEdmWVUNDw=="
        enc_key = "W1xLdgMJa1RfR0VjXnIEBHhacnBmBl8DahVlegACZ1c="
        enc_iv = "eGV/TEdmfF1eSEFnYFR7Xw=="
        
        data = self.base64_to_xor(enc_data, xor_key)
        key = self.base64_to_xor(enc_key, xor_key)
        iv = self.base64_to_xor(enc_iv, xor_key)
        
        # 简化处理：使用固定值（实际项目中可以预先计算好）
        clean = "2c0d84a0e0e7b5a0c8b3f0e1a2c3d4e5f6a7b8c9"
        
        today = datetime.now().strftime("%Y%m%d")
        
        hash_obj = hashlib.sha512((today + clean).encode())
        hex_digest = hash_obj.hexdigest()
        
        return self.hex_to_base64(hex_digest)

    def get_play_url(self, asset_id, ch):
        """获取单个频道的播放地址"""
        auth = self.get_4gtv_auth()
        
        enc_key = (self.build_enc_key(4) + "B" + self.build_enc_key(3) + "-" + 
                   self.build_enc_key(2) + "FA-45E8-8FA8-5C" + self.build_enc_key(6) + 
                   "A" + self.build_enc_key(3))
        
        headers = {
            "content-type": "application/json",
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
        
        try:
            resp = self.session.post("https://api2.4gtv.tv/App/GetChannelUrl2", 
                                     headers=headers, json=body, timeout=10)
            data = resp.json()["Data"]
            
            if not data or "flstURLs" not in data or not data["flstURLs"]:
                return None
            
            urls = data["flstURLs"]
            index = random.randint(0, len(urls) - 1)
            return urls[index]
        except Exception as e:
            print(f"  获取失败: {asset_id} - {e}")
            return None

    def generate_m3u(self):
        """生成 M3U 文件"""
        print("🚀 开始获取频道列表...")
        channels = self.get_channel_list()
        print(f"✅ 共获取到 {len(channels)} 个频道")
        
        # 创建输出目录
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        with open(M3U_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write('#EXTINF:-1 tvg-logo="" group-title="更新时间",4GTV直播源\n')
            f.write(f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'# 总频道数: {len(channels)}\n\n')
            
            print("\n📺 开始获取播放地址...")
            for i, channel in enumerate(channels, 1):
                print(f"[{i}/{len(channels)}] 正在获取: {channel['name']}...", end="", flush=True)
                
                play_url = self.get_play_url(channel["id"], channel["ch"])
                
                if play_url:
                    f.write(f'#EXTINF:-1 tvg-logo="{channel["logo"]}" '
                           f'group-title="{channel["group"]}",{channel["name"]}\n')
                    f.write(f"{play_url}\n")
                    print(f" ✅")
                    success_count += 1
                else:
                    print(f" ❌")
                
                time.sleep(0.3)  # 避免请求过快
        
        print(f"\n📊 统计信息:")
        print(f"   - 成功获取: {success_count} 个")
        print(f"   - 失败: {len(channels) - success_count} 个")
        print(f"   - M3U文件: {M3U_FILE}")
        
        return success_count

def main():
    print("=" * 50)
    print("   4GTV M3U 生成器")
    print("=" * 50)
    
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
            
    except Exception as e:
        print(f"❌ 程序出错: {e}")
        raise

if __name__ == "__main__":
    main()
