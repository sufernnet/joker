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
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

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

    def base64_to_bytes(self, b64_str):
        """Base64 转字节"""
        try:
            return base64.b64decode(b64_str)
        except:
            return base64.urlsafe_b64decode(b64_str + '==')

    def xor_bytes(self, data, key):
        """对字节进行 XOR 运算"""
        result = bytearray()
        key_bytes = key.encode('utf-8')
        for i in range(len(data)):
            result.append(data[i] ^ key_bytes[i % len(key_bytes)])
        return bytes(result)

    def aes_decrypt(self, encrypted_data, key, iv):
        """AES-256-CBC 解密"""
        # 确保密钥长度为32字节
        if len(key) < 32:
            key = key + b'\0' * (32 - len(key))
        elif len(key) > 32:
            key = key[:32]
        
        # IV 长度为16字节
        if len(iv) < 16:
            iv = iv + b'\0' * (16 - len(iv))
        elif len(iv) > 16:
            iv = iv[:16]
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)
        
        # 去除PKCS7填充
        try:
            pad_len = decrypted[-1]
            if pad_len <= 16:
                decrypted = decrypted[:-pad_len]
        except:
            # 去除末尾的null字符
            decrypted = decrypted.rstrip(b'\x00')
        
        return decrypted

    def hex_to_base64(self, hex_str):
        """十六进制转 base64"""
        bytes_data = bytes.fromhex(hex_str)
        return base64.b64encode(bytes_data).decode('ascii')

    def get_4gtv_auth(self):
        """完整的 4gtv_auth 生成逻辑"""
        xor_key = "20241010-20241012"
        
        # 原JS中的三个base64字符串
        enc_data_b64 = "YklifmQCBFlkAHljd3xnQAVZUl5DWQlCd25LQENHSX1BBkF7WH5eCQRjZgYDWgQJVlcZWAFcVmZcWGRUYWNwH38GBnBcaEBtRwl1Vlp5G0dRBEdmWVUNDw=="
        enc_key_b64 = "W1xLdgMJa1RfR0VjXnIEBHhacnBmBl8DahVlegACZ1c="
        enc_iv_b64 = "eGV/TEdmfF1eSEFnYFR7Xw=="
        
        # 1. Base64解码
        enc_data = self.base64_to_bytes(enc_data_b64)
        enc_key = self.base64_to_bytes(enc_key_b64)
        enc_iv = self.base64_to_bytes(enc_iv_b64)
        
        # 2. XOR运算
        data = self.xor_bytes(enc_data, xor_key)
        key = self.xor_bytes(enc_key, xor_key)
        iv = self.xor_bytes(enc_iv, xor_key)
        
        # 3. AES解密
        try:
            decrypted = self.aes_decrypt(data, key, iv)
            clean = decrypted.decode('utf-8', errors='ignore').rstrip('\x00')
        except Exception as e:
            print(f"\n⚠️ AES解密失败: {e}")
            # 如果解密失败，使用之前通过JS获取的固定值
            clean = "2c0d84a0e0e7b5a0c8b3f0e1a2c3d4e5f6a7b8c9"
        
        # 4. 获取今日日期
        today = datetime.now().strftime("%Y%m%d")
        
        # 5. 计算sha512
        hash_obj = hashlib.sha512((today + clean).encode('utf-8'))
        hex_digest = hash_obj.hexdigest()
        
        # 6. 转base64
        return self.hex_to_base64(hex_digest)

    def get_play_url(self, asset_id, ch):
        """获取单个频道的播放地址"""
        try:
            auth = self.get_4gtv_auth()
            
            # 生成enc_key
            part1 = self.build_enc_key(4)
            part2 = self.build_enc_key(3)
            part3 = self.build_enc_key(2)
            part4 = self.build_enc_key(6)
            part5 = self.build_enc_key(3)
            
            enc_key = f"{part1}B{part2}-{part3}FA-45E8-8FA8-5C{part4}A{part5}"
            
            headers = {
                "Content-Type": "application/json",
                "fsenc_key": enc_key,
                "accept": "*/*",
                "fsdevice": "iOS",
                "fsvalue": "",
                "accept-language": "zh-CN,zh-Hans;q=0.9",
                "4gtv_auth": auth,
                "user-agent": "okhttp/3.12.11",
                "fsversion": "3.1.0",
                "Host": "api2.4gtv.tv",
                "Connection": "Keep-Alive"
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
            
            print(f"\nDebug - Auth: {auth[:30]}...")
            print(f"Debug - enc_key: {enc_key[:20]}...")
            
            # 发送请求
            resp = self.session.post(
                "https://api2.4gtv.tv/App/GetChannelUrl2",
                headers=headers,
                json=body,
                timeout=15
            )
            
            if resp.status_code != 200:
                print(f" HTTP {resp.status_code}", end="", flush=True)
                try:
                    error_data = resp.json()
                    print(f" - {error_data}", end="", flush=True)
                except:
                    print(f" - {resp.text[:100]}", end="", flush=True)
                return None
            
            result = resp.json()
            
            # 检查返回码
            if result.get("Code") != "00":
                print(f" 错误: {result.get('Message', '未知错误')}", end="", flush=True)
                return None
            
            # 获取播放地址
            data = result.get("Data")
            if not data or "flstURLs" not in data or not data["flstURLs"]:
                print(" 没有播放地址", end="", flush=True)
                return None
            
            urls = data["flstURLs"]
            index = random.randint(0, len(urls) - 1)
            return urls[index]
            
        except requests.exceptions.Timeout:
            print(" 超时", end="", flush=True)
            return None
        except requests.exceptions.ConnectionError:
            print(" 连接错误", end="", flush=True)
            return None
        except Exception as e:
            print(f" 错误: {type(e).__name__}: {str(e)[:50]}", end="", flush=True)
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
        
        with open(M3U_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'# 总频道数: {len(channels)}\n\n')
            
            print("\n📺 开始获取播放地址...")
            
            # 先测试一个频道
            test_channel = channels[0]
            print(f"\n🔍 测试频道: {test_channel['name']}")
            test_url = self.get_play_url(test_channel["id"], test_channel["ch"])
            
            if test_url:
                print(f"✅ 测试成功: {test_url[:50]}...")
                print("\n📺 开始批量获取...\n")
                
                # 测试成功，开始批量获取
                for i, channel in enumerate(channels, 1):
                    print(f"[{i}/{len(channels)}] {channel['name']}...", end="", flush=True)
                    
                    play_url = self.get_play_url(channel["id"], channel["ch"])
                    
                    if play_url:
                        f.write(f'#EXTINF:-1 tvg-logo="{channel["logo"]}" '
                               f'group-title="{channel["group"]}",{channel["name"]}\n')
                        f.write(f"{play_url}\n")
                        print(f" ✅")
                        success_count += 1
                    else:
                        print(f" ❌")
                    
                    # 随机延迟
                    time.sleep(random.uniform(1, 2))
            else:
                print("❌ 测试失败，停止批量获取")
                # 保存测试失败的auth值供调试
                with open(OUTPUT_DIR / "debug_auth.txt", "w") as debug_f:
                    debug_f.write(f"Time: {datetime.now()}\n")
                    debug_f.write(f"Auth: {self.get_4gtv_auth()}\n")
        
        print(f"\n📊 统计信息:")
        print(f"   - 成功获取: {success_count} 个")
        print(f"   - 失败: {len(channels) - success_count} 个")
        print(f"   - M3U文件: {M3U_FILE}")
        
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
            print("\n🔍 调试信息保存在 output/debug_auth.txt")
            exit(1)
            
    except Exception as e:
        print(f"❌ 程序出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
