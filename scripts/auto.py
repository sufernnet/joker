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
        return channels
    
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
        """处理所有订阅源（优化版：不测试单源频道）"""
        all_raw_channels = []  # (name, url)
        
        # 第一步：收集所有频道
        for url in self.config['extra_urls']:
            logging.info(f"处理订阅源: {url}")
            content = self.fetch_m3u_content(url)
            if content:
                channels = self.parse_m3u(content)
                logging.info(f"  获取到 {len(channels)} 个频道")
                all_raw_channels.extend(channels)
            else:
                logging.warning(f"  获取失败")
        
        # 第二步：按频道名分组URL
        channel_urls = {}
        channel_count = {}
        for name, url in all_raw_channels:
            # 清理名称中的特殊字符
            clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
            if clean_name not in channel_urls:
                channel_urls[clean_name] = []
                channel_count[clean_name] = 0
            if url not in channel_urls[clean_name]:
                channel_urls[clean_name].append(url)
                channel_count[clean_name] += 1
        
        # 第三步：智能选择最佳URL
        logging.info(f"共 {len(channel_urls)} 个唯一频道")
        
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
        
        logging.info(f"最终获得 {len(self.channels)} 个有效频道")
        self.save_cache()  # 保存缓存
    
    def classify_channels(self):
        """分类频道到不同分组"""
        groups = {
            '央视': [],
            '卫视': [],
            '4K': [],
            '数字': [],
            'CHC': [],
            'HongKong': [],
            'TaiWan': []
        }
        
        # 央视1-17频道
        cctv_list = []
        for i in range(1, 18):
            cctv_list.extend([f'CCTV{i}', f'CCTV-{i}', f'中央电视台{i}套', f'央视{i}套'])
        cctv_list.extend(['CCTV1综合', 'CCTV2财经', 'CCTV3综艺', 'CCTV4中文国际', 
                         'CCTV5体育', 'CCTV6电影', 'CCTV7军事农业', 'CCTV8电视剧',
                         'CCTV9纪录', 'CCTV10科教', 'CCTV11戏曲', 'CCTV12社会与法',
                         'CCTV13新闻', 'CCTV14少儿', 'CCTV15音乐', 'CCTV16奥林匹克',
                         'CCTV17农业农村'])
        
        # 卫视列表
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
        
        # 4K频道关键词
        keywords_4k = ['4K', '4k', 'UHD', '2160p', 'CCTV-4K', 'CCTV4K']
        
        # 数字频道关键词
        digital_keywords = ['地理', '第一剧场', '风云', '怀旧剧场', '戏曲', '音乐', '少儿', 
                           '科教', '纪录', '发现', '世界地理', '风云剧场', '风云音乐', 
                           '风云足球', '第一时尚', '电视指南', '国防军事', '女性时尚', 
                           '高尔夫网球', '央视文化', '央视记录', 'CCTV地理', 'CCTV第一剧场']
        
        # CHC频道
        chc_keywords = ['CHC', '华诚', '动作电影', '家庭影院']
        
        # 香港频道
        hk_keywords = ['香港', 'TVB', '翡翠', '明珠', '凤凰卫视', '凤凰', 'NOW', 
                      'CABLE', '港台', 'RTHK', '无线', '亚洲电视', 'ATV', 'VIU']
        
        # 台湾频道
        tw_keywords = ['台湾', '台视', '中视', '华视', '民视', '公视', '三立', 
                      '东森', '中天', 'TVBS', '年代', '非凡', '八大', '纬来', 
                      '客家', '原住民']
        
        processed = set()
        
        for name, url in self.channels.items():
            if name in processed:
                continue
                
            name_upper = name.upper()
            
            # 4K分组
            if any(kw in name for kw in keywords_4k):
                groups['4K'].append((name, url))
                processed.add(name)
            
            # 央视分组
            elif any(cctv in name_upper for cctv in cctv_list) or ('CCTV' in name_upper and '4K' not in name_upper):
                groups['央视'].append((name, url))
                processed.add(name)
            
            # CHC分组
            elif any(kw in name_upper for kw in chc_keywords):
                groups['CHC'].append((name, url))
                processed.add(name)
            
            # 香港分组
            elif any(kw in name for kw in hk_keywords):
                groups['HongKong'].append((name, url))
                processed.add(name)
            
            # 台湾分组
            elif any(kw in name for kw in tw_keywords):
                groups['TaiWan'].append((name, url))
                processed.add(name)
            
            # 数字分组
            elif any(kw in name for kw in digital_keywords):
                groups['数字'].append((name, url))
                processed.add(name)
            
            # 卫视分组
            else:
                for display_name, keywords in province_keywords.items():
                    if any(kw in name for kw in keywords):
                        groups['卫视'].append((display_name, url))
                        processed.add(name)
                        break
        
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
            
            for group_name, channels in groups.items():
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
        
        # 统计各分组数量
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
