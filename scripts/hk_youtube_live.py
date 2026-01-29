#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港YouTube直播频道抓取器 - 完整独立版
无需安装依赖，开箱即用
自动生成EE.m3u播放列表
"""

import os
import sys
import re
import json
import time
import base64
import hashlib
import struct
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict

# ==================== 内嵌YAML解析器 ====================
class SimpleYAML:
    """简易YAML解析器（无需PyYAML依赖）"""
    
    @staticmethod
    def load(stream):
        if hasattr(stream, 'read'):
            content = stream.read()
        else:
            with open(stream, 'r', encoding='utf-8') as f:
                content = f.read()
        
        result = {}
        current_key = None
        current_indent = 0
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            # 跳过空行和注释
            if not line or line.strip().startswith('#'):
                i += 1
                continue
            
            # 计算缩进
            indent = len(line) - len(line.lstrip())
            
            # 键值对
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if value:
                    # 简单值
                    if value.startswith('"') and value.endswith('"'):
                        result[key] = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        result[key] = value[1:-1]
                    elif value.lower() == 'true':
                        result[key] = True
                    elif value.lower() == 'false':
                        result[key] = False
                    elif value.lower() == 'null' or value.lower() == 'none':
                        result[key] = None
                    elif value.isdigit():
                        result[key] = int(value)
                    elif value.replace('.', '', 1).isdigit():
                        result[key] = float(value)
                    else:
                        result[key] = value
                else:
                    # 复杂值（列表或嵌套对象）
                    result[key] = []
                    
                    # 检查是否是列表
                    j = i + 1
                    while j < len(lines) and lines[j].strip().startswith('-'):
                        item = lines[j].strip()[1:].strip()
                        if item.startswith('"') and item.endswith('"'):
                            result[key].append(item[1:-1])
                        else:
                            result[key].append(item)
                        j += 1
                    
                    if j > i + 1:
                        i = j - 1
                    else:
                        # 嵌套对象
                        result[key] = {}
                        nested = {}
                        j = i + 1
                        while j < len(lines) and len(lines[j]) - len(lines[j].lstrip()) > indent:
                            nkey, nvalue = lines[j].split(':', 1)
                            nkey = nkey.strip()
                            nvalue = nvalue.strip()
                            nested[nkey] = nvalue
                            j += 1
                        result[key] = nested
                        if j > i + 1:
                            i = j - 1
            
            i += 1
        
        return result

# ==================== 配置管理器 ====================
class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file="config.yml"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            print(f"⚠️  配置文件 {self.config_file} 不存在，使用默认配置")
            return self.get_default_config()
        
        try:
            # 尝试使用内嵌的YAML解析器
            yaml_parser = SimpleYAML()
            return yaml_parser.load(self.config_file)
        except Exception as e:
            print(f"❌ 解析配置文件失败: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            'channels': [
                {
                    'name': 'TVB USA Official',
                    'youtube_id': 'UCdNUTdwVsIDQp0k0qJd5i9A',
                    'url': 'https://www.youtube.com/channel/UCdNUTdwVsIDQp0k0qJd5i9A',
                    'category': '电视台',
                    'language': '粤语',
                    'quality': '1080p'
                },
                {
                    'name': 'HOY TV',
                    'youtube_id': 'UClMrjH_g5QcO8Bdq7j81dGA',
                    'url': 'https://www.youtube.com/channel/UClMrjH_g5QcO8Bdq7j81dGA',
                    'category': '电视台',
                    'language': '粤语',
                    'quality': '720p'
                }
            ],
            'output': {
                'm3u_filename': 'EE.m3u',
                'output_dir': './'
            },
            'quality_check': {
                'enabled': True,
                'timeout': 10
            }
        }

# ==================== HTTP客户端（无requests依赖） ====================
import socket
import ssl
from urllib.parse import urlparse, quote, urlencode

class SimpleHTTPClient:
    """简易HTTP客户端（无需requests依赖）"""
    
    def __init__(self, timeout=10, user_agent=None):
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.cookies = {}
    
    def _create_ssl_context(self):
        """创建SSL上下文"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    
    def _parse_url(self, url):
        """解析URL"""
        parsed = urlparse(url)
        scheme = parsed.scheme
        hostname = parsed.hostname
        port = parsed.port or (443 if scheme == 'https' else 80)
        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        return scheme, hostname, port, path
    
    def _create_request(self, method, path, headers, hostname):
        """创建HTTP请求"""
        request_lines = []
        request_lines.append(f"{method} {path} HTTP/1.1")
        request_lines.append(f"Host: {hostname}")
        
        # 添加头信息
        headers = headers.copy()
        headers.setdefault('User-Agent', self.user_agent)
        headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        headers.setdefault('Accept-Language', 'zh-HK,zh;q=0.9,en;q=0.8')
        headers.setdefault('Accept-Encoding', 'gzip, deflate')
        headers.setdefault('Connection', 'close')
        
        # 添加cookies
        if self.cookies:
            cookie_str = '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
            headers['Cookie'] = cookie_str
        
        for key, value in headers.items():
            request_lines.append(f"{key}: {value}")
        
        request_lines.append('')
        request_lines.append('')
        return '\r\n'.join(request_lines)
    
    def _parse_response(self, response_data):
        """解析HTTP响应"""
        try:
            # 分割响应头和响应体
            header_end = response_data.find(b'\r\n\r\n')
            if header_end == -1:
                return None, None, b''
            
            headers_data = response_data[:header_end].decode('utf-8', errors='ignore')
            body = response_data[header_end + 4:]
            
            # 解析状态行和头信息
            lines = headers_data.split('\r\n')
            status_line = lines[0]
            status_code = int(status_line.split(' ')[1])
            
            headers = {}
            for line in lines[1:]:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key.lower()] = value
            
            return status_code, headers, body
        except:
            return None, None, b''
    
    def get(self, url, headers=None, allow_redirects=True, timeout=None):
        """发送GET请求"""
        if headers is None:
            headers = {}
        
        timeout = timeout or self.timeout
        
        # 处理重定向
        for _ in range(5):  # 最多重定向5次
            scheme, hostname, port, path = self._parse_url(url)
            
            # 创建socket连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                sock.connect((hostname, port))
                
                if scheme == 'https':
                    context = self._create_ssl_context()
                    sock = context.wrap_socket(sock, server_hostname=hostname)
                
                # 发送请求
                request = self._create_request('GET', path, headers, hostname)
                sock.sendall(request.encode('utf-8'))
                
                # 接收响应
                response = b''
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response += chunk
                    except socket.timeout:
                        break
                    except:
                        break
                
                sock.close()
                
                # 解析响应
                status_code, resp_headers, body = self._parse_response(response)
                if status_code is None:
                    return None
                
                # 保存cookies
                if 'set-cookie' in resp_headers:
                    cookies = resp_headers['set-cookie'].split(';')
                    for cookie in cookies:
                        if '=' in cookie:
                            key, value = cookie.strip().split('=', 1)
                            self.cookies[key] = value
                
                # 处理重定向
                if allow_redirects and status_code in [301, 302, 303, 307, 308]:
                    if 'location' in resp_headers:
                        redirect_url = resp_headers['location']
                        if not redirect_url.startswith(('http://', 'https://')):
                            redirect_url = f"{scheme}://{hostname}{redirect_url}"
                        url = redirect_url
                        continue
                
                return SimpleResponse(status_code, resp_headers, body, url)
                
            except Exception as e:
                print(f"HTTP请求失败: {e}")
                return None
        
        return None
    
    def head(self, url, headers=None, timeout=None):
        """发送HEAD请求（简化的GET实现）"""
        # 我们使用GET然后只返回头信息
        response = self.get(url, headers, allow_redirects=True, timeout=timeout)
        if response:
            response.content = b''  # 清空内容
        return response

class SimpleResponse:
    """简易HTTP响应对象"""
    
    def __init__(self, status_code, headers, content, url):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.url = url
        self.text = content.decode('utf-8', errors='ignore') if content else ''
    
    def json(self):
        """解析JSON响应"""
        try:
            return json.loads(self.text)
        except:
            return {}
    
    def raise_for_status(self):
        """检查HTTP状态码"""
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP错误 {self.status_code}")

# ==================== 直播流提取器 ====================
class YouTubeStreamExtractor:
    """YouTube直播流提取器"""
    
    def __init__(self, http_client=None):
        self.http = http_client or SimpleHTTPClient()
        self.cache = {}
    
    def extract_stream_url(self, channel_id, video_id=None):
        """提取直播流URL"""
        cache_key = f"{channel_id}_{video_id or 'live'}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < 300:  # 5分钟缓存
                return cached['url']
        
        try:
            # 如果没有提供video_id，先获取直播视频ID
            if not video_id:
                video_id = self.get_live_video_id(channel_id)
                if not video_id:
                    print(f"  无法获取直播视频ID: {channel_id}")
                    return None
            
            # 提取流URL
            stream_url = self.get_stream_from_video(video_id)
            
            if stream_url:
                self.cache[cache_key] = {
                    'url': stream_url,
                    'timestamp': time.time()
                }
            
            return stream_url
            
        except Exception as e:
            print(f"  提取流URL失败: {e}")
            return None
    
    def get_live_video_id(self, channel_id):
        """获取直播视频ID"""
        try:
            # 访问频道直播页面
            url = f"https://www.youtube.com/channel/{channel_id}/live"
            response = self.http.get(url)
            
            if not response or response.status_code != 200:
                return None
            
            # 查找视频ID的模式
            patterns = [
                r'"videoId":"([^"]{11})"',
                r'"liveStreamability":{"videoId":"([^"]{11})"',
                r'watch\?v=([^"\&]{11})',
                r'videoId["\']?\s*:\s*["\']([^"\']{11})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    video_id = match.group(1)
                    if len(video_id) == 11:
                        print(f"  找到直播视频ID: {video_id}")
                        return video_id
            
            # 检查页面是否有直播
            if '"isLive":true' in response.text or 'liveBroadcastDetails' in response.text:
                # 尝试从嵌入页面获取
                embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}"
                embed_response = self.http.get(embed_url)
                if embed_response:
                    for pattern in patterns:
                        match = re.search(pattern, embed_response.text)
                        if match:
                            video_id = match.group(1)
                            if len(video_id) == 11:
                                return video_id
            
            return None
            
        except Exception as e:
            print(f"  获取直播视频ID失败: {e}")
            return None
    
    def get_stream_from_video(self, video_id):
        """从视频ID获取流URL"""
        try:
            # 访问视频页面
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.http.get(url)
            
            if not response or response.status_code != 200:
                return None
            
            # 查找HLS流URL
            patterns = [
                r'"hlsManifestUrl":"([^"]+)"',
                r'hlsManifestUrl\\":\\"([^\\"]+)\\"',
                r'https://manifest\.googlevideo\.com[^"\s]+'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if 'manifest.googlevideo.com' in match:
                        stream_url = match.replace('\\/', '/')
                        if not stream_url.startswith('http'):
                            stream_url = 'https://' + stream_url
                        
                        # 确保是直播流
                        if 'live=1' in stream_url or 'yt_live_broadcast' in stream_url:
                            print(f"  找到HLS直播流")
                            return stream_url
            
            # 备用：返回观看页面
            return f"https://www.youtube.com/watch?v={video_id}"
            
        except Exception as e:
            print(f"  获取视频流失败: {e}")
            return None
    
    def check_stream_quality(self, stream_url, timeout=5):
        """检查流质量"""
        start_time = time.time()
        
        try:
            # 发送HEAD请求检查可用性
            response = self.http.head(stream_url, timeout=timeout)
            
            if not response:
                return {
                    'status': 'error',
                    'latency_ms': 0,
                    'error': '无响应'
                }
            
            latency = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                return {
                    'status': 'online',
                    'latency_ms': latency,
                    'error': None
                }
            else:
                return {
                    'status': 'error',
                    'latency_ms': latency,
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'latency_ms': int((time.time() - start_time) * 1000),
                'error': str(e)
            }

# ==================== M3U生成器 ====================
class M3UGenerator:
    """M3U播放列表生成器"""
    
    def __init__(self, config):
        self.config = config
        self.output_config = config.get('output', {})
    
    def generate(self, channels, filename=None):
        """生成M3U文件"""
        if not channels:
            print("⚠️  没有频道可生成M3U")
            return None
        
        # 确定输出文件名
        if not filename:
            filename = self.output_config.get('m3u_filename', 'EE.m3u')
        
        output_dir = self.output_config.get('output_dir', './')
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        filepath = os.path.join(output_dir, filename)
        
        # 生成M3U内容
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        m3u_content = f"""#EXTM3U
#PLAYLIST:香港YouTube直播频道
#GENERATED: {timestamp}
#TOTAL-CHANNELS: {len(channels)}

"""
        
        # 添加每个频道
        for idx, channel in enumerate(channels, 1):
            if not channel.get('stream_url'):
                continue
            
            # 频道信息
            name = channel.get('name', f'频道{idx}')
            category = channel.get('category', '直播')
            language = channel.get('language', '粤语')
            quality = channel.get('quality', '1080p')
            
            # TVG信息
            tvg_id = channel.get('tvg_id', f'HK{idx:03d}')
            tvg_logo = channel.get('tvg_logo', '')
            if not tvg_logo and channel.get('youtube_id'):
                tvg_logo = f"https://img.youtube.com/vi/{channel['youtube_id']}/0.jpg"
            
            # EXTINF行
            extinf_line = f'#EXTINF:-1'
            extinf_line += f' tvg-id="{tvg_id}"'
            extinf_line += f' tvg-name="{name}"'
            extinf_line += f' tvg-logo="{tvg_logo}"' if tvg_logo else ''
            extinf_line += f' group-title="{category}"'
            extinf_line += f' tvg-language="{language}"'
            extinf_line += f',{name} ({quality})'
            
            # VLC选项
            vlc_opts = '#EXTVLCOPT:http-user-agent="Mozilla/5.0"\n'
            vlc_opts += '#EXTVLCOPT:http-referrer="https://www.youtube.com/"\n'
            
            # 流URL
            stream_url = channel.get('stream_url', '')
            
            # 组合
            m3u_content += f"{extinf_line}\n{vlc_opts}{stream_url}\n\n"
        
        # 写入文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(m3u_content)
            
            print(f"✅ M3U文件已生成: {filepath}")
            print(f"📊 包含 {len(channels)} 个频道")
            return filepath
            
        except Exception as e:
            print(f"❌ 写入M3U文件失败: {e}")
            return None

# ==================== 主程序 ====================
class HKYouTubeLive:
    """香港YouTube直播抓取器主程序"""
    
    def __init__(self, config_file="config.yml"):
        """初始化"""
        print("=" * 60)
        print("香港YouTube直播抓取器 - 独立版")
        print("=" * 60)
        
        # 加载配置
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.config
        
        # 初始化组件
        self.http_client = SimpleHTTPClient(timeout=10)
        self.stream_extractor = YouTubeStreamExtractor(self.http_client)
        self.m3u_generator = M3UGenerator(self.config)
        
        # 统计数据
        self.stats = {
            'total': 0,
            'live': 0,
            'failed': 0,
            'start_time': time.time()
        }
        
        print("✅ 初始化完成")
        print()
    
    def process_channel(self, channel_config):
        """处理单个频道"""
        channel_name = channel_config.get('name', '未知频道')
        youtube_id = channel_config.get('youtube_id', '')
        
        print(f"🔍 检查: {channel_name}")
        
        if not youtube_id:
            print("  ❌ 缺少YouTube ID")
            return None
        
        # 提取直播流
        stream_url = self.stream_extractor.extract_stream_url(youtube_id)
        
        if not stream_url:
            print("  ❌ 未找到直播流")
            self.stats['failed'] += 1
            return None
        
        # 检查流质量
        quality_config = self.config.get('quality_check', {})
        if quality_config.get('enabled', True):
            print("  📊 检查质量...")
            quality_result = self.stream_extractor.check_stream_quality(
                stream_url, 
                timeout=quality_config.get('timeout', 10)
            )
            
            if quality_result['status'] == 'online':
                print(f"    ✓ 在线 | 延迟: {quality_result['latency_ms']}ms")
            else:
                print(f"    ✗ 质量检查失败: {quality_result.get('error', '未知错误')}")
                # 即使质量检查失败，也继续使用该流
        
        # 准备频道数据
        channel_data = channel_config.copy()
        channel_data['stream_url'] = stream_url
        channel_data['last_checked'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"  ✅ 成功获取直播流")
        self.stats['live'] += 1
        
        return channel_data
    
    def run(self):
        """运行主程序"""
        print("🚀 开始抓取香港YouTube直播...")
        print()
        
        # 获取频道列表
        channels_config = self.config.get('channels', [])
        self.stats['total'] = len(channels_config)
        
        if not channels_config:
            print("⚠️  配置文件中没有频道")
            return
        
        print(f"📺 共发现 {self.stats['total']} 个频道")
        print()
        
        live_channels = []
        
        # 逐个处理频道
        for channel_config in channels_config:
            if not channel_config.get('enabled', True):
                print(f"⏭️  跳过已禁用频道: {channel_config.get('name')}")
                continue
            
            channel_data = self.process_channel(channel_config)
            if channel_data:
                live_channels.append(channel_data)
            
            # 短暂延迟，避免请求过快
            time.sleep(1)
        
        print()
        print("=" * 60)
        
        # 显示统计信息
        elapsed_time = time.time() - self.stats['start_time']
        print(f"📊 任务完成!")
        print(f"   总频道数: {self.stats['total']}")
        print(f"   成功获取: {self.stats['live']}")
        print(f"   失败数量: {self.stats['failed']}")
        print(f"   耗时: {elapsed_time:.1f}秒")
        print()
        
        # 生成M3U文件
        if live_channels:
            print("🔄 正在生成M3U播放列表...")
            m3u_file = self.m3u_generator.generate(live_channels)
            
            if m3u_file:
                print()
                print("📺 直播频道列表:")
                for idx, channel in enumerate(live_channels, 1):
                    quality = channel.get('quality', 'N/A')
                    print(f"  {idx:2d}. {channel['name']} - {quality}")
                
                print()
                print(f"🎉 完成! 播放列表已保存到: {m3u_file}")
            else:
                print("❌ 生成M3U文件失败")
        else:
            print("⚠️  没有找到任何直播频道，无法生成M3U")
        
        print("=" * 60)
        
        return live_channels
    
    def save_channels_cache(self, channels, filename="channels.json"):
        """保存频道缓存"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'channels': channels
                }, f, ensure_ascii=False, indent=2)
            
            print(f"💾 频道缓存已保存: {filename}")
        except Exception as e:
            print(f"❌ 保存缓存失败: {e}")

# ==================== 主函数 ====================
def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='香港YouTube直播抓取器')
    parser.add_argument('--config', '-c', default='config.yml', 
                       help='配置文件路径 (默认: config.yml)')
    parser.add_argument('--output', '-o', 
                       help='输出M3U文件名')
    parser.add_argument('--cache', action='store_true',
                       help='保存频道缓存')
    
    args = parser.parse_args()
    
    # 创建抓取器实例
    scraper = HKYouTubeLive(args.config)
    
    # 运行抓取
    live_channels = scraper.run()
    
    # 保存缓存（如果需要）
    if args.cache and live_channels:
        scraper.save_channels_cache(live_channels)
    
    # 如果有指定输出文件名
    if args.output and live_channels:
        scraper.m3u_generator.generate(live_channels, args.output)

if __name__ == "__main__":
    main()
