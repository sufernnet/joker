# scripts/auto.py
import re
import requests
import yaml
import time
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LiveStreamFetcher:
    def __init__(self, config_path=None):
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if config_path is None:
            config_path = os.path.join(script_dir, 'auto.yml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        
        self.channels = {}
        self.output_path = os.path.join(script_dir, '..', 'auto.m3u')
        self.cache_path = os.path.join(script_dir, 'speed_cache.json')
        
        # 加载速度缓存
        self.speed_cache = self.load_cache()
        
        # 央视专用订阅源
        self.cctv_source_url = "https://abc.sufern001.workers.dev"
        self.cctv_channels = {}  # 存储央视频道的URL

    def load_cache(self):
        """加载速度缓存"""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_cache(self):
        """保存速度缓存"""
        # 只保留最近7天的记录
        current_time = time.time()
        filtered_cache = {}
        for url, data in self.speed_cache.items():
            if current_time - data.get('timestamp', 0) < 7 * 24 * 3600:
                filtered_cache[url] = data
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_cache, f, ensure_ascii=False, indent=2)

    def fetch_m3u_content(self, url):
        """获取单个订阅源内容"""
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logging.error(f"获取失败 {url}: {e}")
        return None

    def parse_m3u(self, content):
        """解析M3U内容，返回频道列表 [(name, url)]"""
        channels = []
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # 提取频道名
                match = re.search(r',(.+)$', line)
                if match:
                    name = match.group(1).strip()
                    # 下一行是URL
                    if i + 1 < len(lines):
                        url = lines[i+1].strip()
                        if url and not url.startswith('#') and url.startswith(('http', 'https', 'rtmp', 'rtsp')):
                            channels.append((name, url))
                        i += 2
                    else:
                        i += 1
            else:
                i += 1
        return channels

    def parse_m3u_with_group(self, content):
        """解析M3U内容，返回带分组信息的频道列表 [(group, name, url)]"""
        channels = []
        lines = content.split('\n')
        current_group = ''
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # 提取分组和频道名
                group_match = re.search(r'group-title="([^"]+)"', line)
                if group_match:
                    current_group = group_match.group(1)
                match = re.search(r',(.+)$', line)
                if match:
                    name = match.group(1).strip()
                    if i + 1 < len(lines):
                        url = lines[i+1].strip()
                        if url and not url.startswith('#') and url.startswith(('http', 'https', 'rtmp', 'rtsp')):
                            channels.append((current_group, name, url))
                        i += 2
                    else:
                        i += 1
            else:
                i += 1
        return channels

    def fetch_cctv_channels(self):
        """从专用源获取央视卫视分组中的频道"""
        logging.info(f"从央视源获取频道: {self.cctv_source_url}")
        content = self.fetch_m3u_content(self.cctv_source_url)
        if not content:
            logging.error("获取央视源失败")
            return {}
        
        channels_with_group = self.parse_m3u_with_group(content)
        cctv_channels = {}
        
        for group, name, url in channels_with_group:
            # 只获取"央视卫视"分组
            if group == "央视卫视":
                # 清理名称
                clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
                cctv_channels[clean_name] = url
        
        logging.info(f"从央视源获取到 {len(cctv_channels)} 个央视/卫视频道")
        return cctv_channels

    def quick_check_url(self, url):
        """快速检查URL是否有效（不测试速度）"""
        # 检查缓存
        if url in self.speed_cache:
            cache_data = self.speed_cache[url]
            # 如果缓存时间在24小时内，直接使用
            if time.time() - cache_data.get('timestamp', 0) < 86400:
                return cache_data.get('delay', None)
        
        # 快速检查：只检查HTTP状态码
        try:
            resp = self.session.head(url, timeout=3, allow_redirects=True)
            if resp.status_code < 400:
                # 简单测试一下速度（只测试一次）
                start = time.time()
                resp = self.session.get(url, timeout=3, stream=True)
                if resp.status_code < 400:
                    for chunk in resp.iter_content(512):
                        break
                    delay = time.time() - start
                    resp.close()
                    # 缓存结果
                    self.speed_cache[url] = {'delay': delay, 'timestamp': time.time()}
                    return delay
        except:
            pass
        return None

    def test_url_speed(self, url):
        """测试URL速度，返回延迟(秒)或None"""
        # 检查缓存
        if url in self.speed_cache:
            cache_data = self.speed_cache[url]
            # 如果缓存时间在24小时内，直接使用
            if time.time() - cache_data.get('timestamp', 0) < 86400:
                return cache_data.get('delay', None)
        
        try:
            start = time.time()
            # 使用GET获取前几个字节
            resp = self.session.get(url, timeout=5, stream=True)
            if resp.status_code < 400:
                for chunk in resp.iter_content(1024):
                    break
                delay = time.time() - start
                resp.close()
                # 缓存结果
                self.speed_cache[url] = {'delay': delay, 'timestamp': time.time()}
                return delay
        except:
            pass
        return None

    def select_best_url(self, urls):
        """从多个URL中选择速度最快的（智能策略）"""
        if not urls:
            return None
        if len(urls) == 1:
            return urls[0]
        
        # 先快速检查所有URL
        valid_urls = []
        for url in urls:
            delay = self.quick_check_url(url)
            if delay is not None:
                valid_urls.append((url, delay))
        
        if not valid_urls:
            return urls[0]
        
        # 按速度排序
        valid_urls.sort(key=lambda x: x[1])
        return valid_urls[0][0]

    def process_sources(self):
        """处理所有订阅源（央视频道直接从专用源获取，不测速）"""
        
        # 第一步：从专用源获取央视/卫视频道（不测速，直接采用）
        self.cctv_channels = self.fetch_cctv_channels()
        
        all_raw_channels = []  # (name, url) - 用于其他频道
        hk_tw_channels = []    # 存储港澳台分组的频道
        
        # 第二步：处理其他订阅源
        for url in self.config['extra_urls']:
            logging.info(f"处理订阅源: {url}")
            content = self.fetch_m3u_content(url)
            if content:
                # 特殊处理包含港澳台分组的源
                if 'codeberg.org' in url:
                    channels_with_group = self.parse_m3u_with_group(content)
                    for group, name, channel_url in channels_with_group:
                        if group == '🔮港澳台直播':
                            hk_tw_channels.append((name, channel_url))
                        else:
                            all_raw_channels.append((name, channel_url))
                    logging.info(f" 获取到 {len(channels_with_group)} 个频道（含分组）")
                else:
                    channels = self.parse_m3u(content)
                    all_raw_channels.extend(channels)
                    logging.info(f" 获取到 {len(channels)} 个频道")
            else:
                logging.warning(f" 获取失败")
        
        # 第三步：处理其他频道（排除央视和卫视，因为已经单独获取了）
        # 过滤掉央视和卫视频道，避免重复
        def is_cctv_or_weishi(name):
            """判断是否是央视或卫视频道"""
            # 央视关键词
            if re.match(r'CCTV[-]?\d+', name, re.IGNORECASE):
                return True
            # 卫视关键词
            weishi_keywords = ['卫视', '湖南', '浙江', '江苏', '东方', '北京', '广东', '深圳', 
                              '天津', '山东', '安徽', '辽宁', '黑龙江', '四川', '湖北', '江西',
                              '重庆', '河南', '河北', '陕西', '山西', '云南', '广西', '吉林',
                              '东南', '福建', '贵州', '甘肃', '内蒙古', '新疆', '宁夏', '青海',
                              '海南', '西藏']
            for kw in weishi_keywords:
                if kw in name:
                    return True
            return False
        
        filtered_channels = [(name, url) for name, url in all_raw_channels if not is_cctv_or_weishi(name)]
        
        # 按频道名分组URL
        channel_urls = {}
        for name, url in filtered_channels:
            clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
            if clean_name not in channel_urls:
                channel_urls[clean_name] = []
            if url not in channel_urls[clean_name]:
                channel_urls[clean_name].append(url)
        
        # 第四步：智能选择最佳URL（只对其他频道测速）
        logging.info(f"其他频道: {len(channel_urls)} 个唯一频道")
        
        # 统计多源频道
        multi_source = {name: urls for name, urls in channel_urls.items() if len(urls) > 1}
        single_source = {name: urls[0] for name, urls in channel_urls.items() if len(urls) == 1}
        
        logging.info(f"单源频道: {len(single_source)} 个（直接采用）")
        logging.info(f"多源频道: {len(multi_source)} 个（需要测速）")
        
        # 单源频道直接采用
        for name, url in single_source.items():
            self.channels[name] = url
        
        # 多源频道进行测速（并发处理）
        if multi_source:
            logging.info("开始测试多源频道速度...")
            tested = 0
            with ThreadPoolExecutor(max_workers=20) as executor:
                future_to_name = {}
                for name, urls in multi_source.items():
                    future = executor.submit(self.select_best_url, urls)
                    future_to_name[future] = name
                
                for future in as_completed(future_to_name):
                    name = future_to_name[future]
                    best_url = future.result()
                    if best_url:
                        self.channels[name] = best_url
                    tested += 1
                    if tested % 50 == 0:
                        logging.info(f"已测试 {tested}/{len(multi_source)} 个多源频道")
        
        # 处理港澳台频道的分组信息
        for name, url in hk_tw_channels:
            clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
            if not hasattr(self, 'hk_tw_sources'):
                self.hk_tw_sources = {}
            self.hk_tw_sources[clean_name] = url
        
        logging.info(f"其他频道: {len(self.channels)} 个有效频道")
        logging.info(f"央视频道: {len(self.cctv_channels)} 个有效频道")
        self.save_cache()  # 保存缓存

    def classify_channels(self):
        """分类频道到不同分组（央视分组直接从cctv_channels获取）"""
        groups = {
            '央视': [],
            '卫视': [],
            '4K': [],
            '数字': [],
            'CHC': [],
            'HongKong': [],
            'TaiWan': []
        }
        
        # ========== 1. 央视分组：直接从cctv_channels获取 ==========
        cctv_ordered = []
        for i in range(1, 18):
            standard_name = f'CCTV-{i}高清'
            # 在cctv_channels中查找匹配的频道
            found = False
            for name, url in self.cctv_channels.items():
                # 标准化名称匹配
                if name == standard_name:
                    cctv_ordered.append((standard_name, url))
                    found = True
                    break
                elif re.match(f'CCTV[-]?{i}[高清HD]+', name, re.IGNORECASE):
                    cctv_ordered.append((standard_name, url))
                    found = True
                    break
                elif name.replace(' ', '') == standard_name.replace(' ', ''):
                    cctv_ordered.append((standard_name, url))
                    found = True
                    break
            
            # 如果没找到，尝试从主频道中查找备用
            if not found and standard_name in self.channels:
                cctv_ordered.append((standard_name, self.channels[standard_name]))
        
        groups['央视'] = cctv_ordered
        
        # ========== 2. 数字分组：只保留指定的8个频道 ==========
        digital_allow = {
            'CCTV-第一剧场', 'CCTV-风云剧场', 'CCTV-风云音乐', 
            'CCTV-风云足球', 'CCTV-怀旧剧场', 'CCTV-央视文化', 
            'CCTV-世界地理', 'CCTV-央视台球'
        }
        
        digital_mapping = {
            '第一剧场': 'CCTV-第一剧场', '风云剧场': 'CCTV-风云剧场',
            '风云音乐': 'CCTV-风云音乐', '风云足球': 'CCTV-风云足球',
            '怀旧剧场': 'CCTV-怀旧剧场', '央视文化': 'CCTV-央视文化',
            '世界地理': 'CCTV-世界地理', '央视台球': 'CCTV-央视台球',
            'CCTV第一剧场': 'CCTV-第一剧场', 'CCTV风云剧场': 'CCTV-风云剧场',
            'CCTV风云音乐': 'CCTV-风云音乐', 'CCTV风云足球': 'CCTV-风云足球',
            'CCTV怀旧剧场': 'CCTV-怀旧剧场', 'CCTV世界地理': 'CCTV-世界地理'
        }
        
        digital_channels = {}
        for name, url in self.channels.items():
            if name in digital_allow:
                digital_channels[name] = url
            elif name in digital_mapping:
                standard_name = digital_mapping[name]
                if standard_name not in digital_channels:
                    digital_channels[standard_name] = url
            else:
                for keyword in digital_allow:
                    if keyword.replace('CCTV-', '') in name or name in keyword:
                        if keyword not in digital_channels:
                            digital_channels[keyword] = url
        
        digital_order = ['CCTV-第一剧场', 'CCTV-风云剧场', 'CCTV-风云音乐', 
                        'CCTV-风云足球', 'CCTV-怀旧剧场', 'CCTV-央视文化', 
                        'CCTV-世界地理', 'CCTV-央视台球']
        for channel in digital_order:
            if channel in digital_channels:
                groups['数字'].append((channel, digital_channels[channel]))
        
        # ========== 3. CHC分组：只保留3个频道 ==========
        chc_allow = {
            'CHC动作电影': ['CHC动作电影', 'CHC动作', '动作电影'],
            'CHC影迷电影': ['CHC影迷电影', 'CHC影迷', '影迷电影'],
            'CHC家庭影院': ['CHC家庭影院', 'CHC家庭', '家庭影院']
        }
        
        chc_channels = {}
        for name, url in self.channels.items():
            for standard, keywords in chc_allow.items():
                if any(kw in name for kw in keywords):
                    if standard not in chc_channels:
                        chc_channels[standard] = url
                    break
        
        chc_order = ['CHC动作电影', 'CHC影迷电影', 'CHC家庭影院']
        for channel in chc_order:
            if channel in chc_channels:
                groups['CHC'].append((channel, chc_channels[channel]))
        
        # ========== 4. 卫视分组：从cctv_channels中提取卫视 ==========
        province_keywords = {
            '湖南卫视': ['湖南卫视', '湖南卫视HD', 'HNTV', '湖南'],
            '浙江卫视': ['浙江卫视', '浙江卫视HD', 'ZJTV', '浙江'],
            '江苏卫视': ['江苏卫视', '江苏卫视HD', 'JSTV', '江苏'],
            '东方卫视': ['东方卫视', '上海卫视', '东方卫视HD', '上海'],
            '北京卫视': ['北京卫视', '北京卫视HD', 'BTV', '北京'],
            '广东卫视': ['广东卫视', '广东卫视HD', '广东'],
            '深圳卫视': ['深圳卫视', '深圳卫视HD', '深圳'],
            '天津卫视': ['天津卫视', '天津卫视HD', '天津'],
            '山东卫视': ['山东卫视', '山东卫视HD', '山东'],
            '安徽卫视': ['安徽卫视', '安徽卫视HD', '安徽'],
            '辽宁卫视': ['辽宁卫视', '辽宁卫视HD', '辽宁'],
            '黑龙江卫视': ['黑龙江卫视', '黑龙江卫视HD', '黑龙江'],
            '四川卫视': ['四川卫视', '四川卫视HD', '四川'],
            '湖北卫视': ['湖北卫视', '湖北卫视HD', '湖北'],
            '江西卫视': ['江西卫视', '江西卫视HD', '江西'],
            '重庆卫视': ['重庆卫视', '重庆卫视HD', '重庆'],
            '河南卫视': ['河南卫视', '河南卫视HD', '河南'],
            '河北卫视': ['河北卫视', '河北卫视HD', '河北'],
            '陕西卫视': ['陕西卫视', '陕西卫视HD', '陕西'],
            '山西卫视': ['山西卫视', '山西卫视HD', '山西'],
            '云南卫视': ['云南卫视', '云南卫视HD', '云南'],
            '广西卫视': ['广西卫视', '广西卫视HD', '广西'],
            '吉林卫视': ['吉林卫视', '吉林卫视HD', '吉林'],
            '东南卫视': ['东南卫视', '福建卫视', '福建'],
            '贵州卫视': ['贵州卫视', '贵州卫视HD', '贵州'],
            '甘肃卫视': ['甘肃卫视', '甘肃卫视HD', '甘肃'],
            '内蒙古卫视': ['内蒙古卫视', '内蒙古'],
            '新疆卫视': ['新疆卫视', '新疆'],
            '宁夏卫视': ['宁夏卫视', '宁夏'],
            '青海卫视': ['青海卫视', '青海'],
            '海南卫视': ['海南卫视', '海南', '旅游卫视'],
            '西藏卫视': ['西藏卫视', '西藏']
        }
        
        weishi_found = set()
        # 从cctv_channels中提取卫视
        for name, url in self.cctv_channels.items():
            for display_name, keywords in province_keywords.items():
                if any(kw in name for kw in keywords):
                    if display_name not in weishi_found:
                        groups['卫视'].append((display_name, url))
                        weishi_found.add(display_name)
                    break
        
        # ========== 5. HongKong分组：凤凰台只保留3个并置顶 ==========
        hk_channels = {}
        
        phoenix_order = ['凤凰中文', '凤凰资讯', '凤凰香港']
        phoenix_found = {}
        
        for name, url in self.channels.items():
            if '凤凰' in name:
                if '中文' in name and '凤凰中文' not in phoenix_found:
                    phoenix_found['凤凰中文'] = url
                elif '资讯' in name and '凤凰资讯' not in phoenix_found:
                    phoenix_found['凤凰资讯'] = url
                elif '香港' in name and '凤凰香港' not in phoenix_found:
                    phoenix_found['凤凰香港'] = url
                elif '卫视' in name and '凤凰中文' not in phoenix_found:
                    phoenix_found['凤凰中文'] = url
            else:
                if any(kw in name for kw in ['香港', 'TVB', '無綫', '无线', '千禧', '翡翠', 
                                            '明珠', '星影', '爆谷', 'HOY', 'NOW', 'HBO', 
                                            'CABLE', '港台', 'RTHK', '无线', '亚洲电视', 
                                            'ATV', 'VIU']):
                    if name not in hk_channels:
                        hk_channels[name] = url
        
        for phoenix in phoenix_order:
            if phoenix in phoenix_found:
                groups['HongKong'].append((phoenix, phoenix_found[phoenix]))
        
        for name, url in hk_channels.items():
            groups['HongKong'].append((name, url))
        
        # ========== 6. TaiWan分组：从港澳台分组中提取 ==========
        taiwan_channels = {}
        
        if hasattr(self, 'hk_tw_sources'):
            for name, url in self.hk_tw_sources.items():
                if any(kw in name for kw in ['台湾', '台视', '寰宇', '中视', '华视', '民视',
                                            '三立', '公视', '东森', '中天', 'TVBS', '年代', 
                                            '非凡', '八大', '纬来', '客家', '原住民']):
                    if name not in taiwan_channels:
                        taiwan_channels[name] = url
        
        for name, url in self.channels.items():
            if any(kw in name for kw in ['台湾', '台视', '寰宇', '中视', '华视', '民视',
                                        '三立', '公视', '东森', '中天', 'TVBS', '年代', 
                                        '非凡', '八大', '纬来', '客家', '原住民']):
                if name not in taiwan_channels:
                    taiwan_channels[name] = url
        
        for name, url in taiwan_channels.items():
            groups['TaiWan'].append((name, url))
        
        # ========== 7. 4K分组：保留所有4K频道 ==========
        keywords_4k = ['4K', '4k', 'UHD', '2160p', 'CCTV-4K', 'CCTV4K']
        for name, url in self.channels.items():
            if any(kw in name for kw in keywords_4k):
                groups['4K'].append((name, url))
        
        # 去重
        for group in groups:
            seen = set()
            unique = []
            for name, url in groups[group]:
                if name not in seen:
                    seen.add(name)
                    unique.append((name, url))
            groups[group] = unique
        
        return groups

    def generate_m3u(self, groups):
        """生成M3U播放列表"""
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            f.write('# 自动生成的直播源列表\n')
            f.write(f'# 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'# 频道总数: {sum(len(channels) for channels in groups.values())}\n\n')
            
            group_order = ['央视', '卫视', '4K', '数字', 'CHC', 'HongKong', 'TaiWan']
            
            for group_name in group_order:
                channels = groups.get(group_name, [])
                if not channels:
                    continue
                f.write(f'# 分组: {group_name} (共{len(channels)}个频道)\n')
                for name, url in channels:
                    display_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
                    f.write(f'#EXTINF:-1 group-title="{group_name}",{display_name}\n')
                    f.write(f'{url}\n')
                f.write('\n')
        
        logging.info(f"生成M3U文件: {self.output_path}")
        return self.output_path

    def run(self):
        """主流程"""
        logging.info("=" * 50)
        logging.info("开始拉取直播源（优化速度模式）...")
        logging.info("=" * 50)
        
        start_time = time.time()
        
        self.process_sources()
        groups = self.classify_channels()
        
        logging.info("=" * 50)
        logging.info("分组统计:")
        total = 0
        for group, channels in groups.items():
            count = len(channels)
            total += count
            logging.info(f"  {group}: {count} 个频道")
        logging.info(f"  总计: {total} 个频道")
        logging.info("=" * 50)
        
        self.generate_m3u(groups)
        
        elapsed = time.time() - start_time
        logging.info(f"完成! 总耗时: {elapsed:.2f} 秒")

if __name__ == '__main__':
    fetcher = LiveStreamFetcher()
    fetcher.run()
