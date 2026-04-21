# auto.py
import re
import requests
import yaml
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LiveStreamFetcher:
    def __init__(self, config_path='auto.yml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        self.channels = {}  # 存储最终频道 {name: url}
        
    def fetch_m3u_content(self, url):
        """获取单个订阅源内容"""
        try:
            resp = self.session.get(url, timeout=10)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logging.error(f"获取失败 {url}: {e}")
        return None
    
    def parse_m3u(self, content, source_url):
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
                        if url and not url.startswith('#'):
                            channels.append((name, url))
                i += 2
            else:
                i += 1
        return channels
    
    def test_url_speed(self, url):
        """测试URL速度，返回延迟(秒)或None"""
        try:
            start = time.time()
            # 只请求头部，快速检测
            resp = self.session.head(url, timeout=5, allow_redirects=True)
            if resp.status_code < 400:
                delay = time.time() - start
                return delay
            # 如果head失败，尝试get前几个字节
            resp = self.session.get(url, timeout=5, stream=True)
            if resp.status_code < 400:
                for chunk in resp.iter_content(1024):
                    break
                delay = time.time() - start
                resp.close()
                return delay
        except:
            pass
        return None
    
    def select_best_url(self, urls):
        """从多个URL中选择速度最快的"""
        if not urls:
            return None
        if len(urls) == 1:
            return urls[0]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(self.test_url_speed, url): url for url in urls}
            best_url = None
            best_delay = float('inf')
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                delay = future.result()
                if delay is not None and delay < best_delay:
                    best_delay = delay
                    best_url = url
        return best_url if best_url else urls[0]
    
    def process_sources(self):
        """处理所有订阅源"""
        all_raw_channels = []  # (name, url)
        
        for url in self.config['extra_urls']:
            logging.info(f"处理订阅源: {url}")
            content = self.fetch_m3u_content(url)
            if content:
                channels = self.parse_m3u(content, url)
                logging.info(f"  获取到 {len(channels)} 个频道")
                all_raw_channels.extend(channels)
        
        # 按频道名分组URL
        channel_urls = {}
        for name, url in all_raw_channels:
            # 清理名称中的特殊字符
            clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
            if clean_name not in channel_urls:
                channel_urls[clean_name] = set()
            channel_urls[clean_name].add(url)
        
        # 为每个频道选择最快地址
        for name, urls in channel_urls.items():
            best_url = self.select_best_url(list(urls))
            if best_url:
                self.channels[name] = best_url
                logging.debug(f"选择频道 {name}: {best_url}")
        
        logging.info(f"共处理 {len(self.channels)} 个唯一频道")
    
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
            if i == 1:
                cctv_list.append('CCTV1综合')
            elif i == 2:
                cctv_list.append('CCTV2财经')
            elif i == 3:
                cctv_list.append('CCTV3综艺')
            elif i == 4:
                cctv_list.append('CCTV4中文国际')
            elif i == 5:
                cctv_list.append('CCTV5体育')
            elif i == 6:
                cctv_list.append('CCTV6电影')
            elif i == 7:
                cctv_list.append('CCTV7军事农业')
            elif i == 8:
                cctv_list.append('CCTV8电视剧')
            elif i == 9:
                cctv_list.append('CCTV9纪录')
            elif i == 10:
                cctv_list.append('CCTV10科教')
            elif i == 11:
                cctv_list.append('CCTV11戏曲')
            elif i == 12:
                cctv_list.append('CCTV12社会与法')
            elif i == 13:
                cctv_list.append('CCTV13新闻')
            elif i == 14:
                cctv_list.append('CCTV14少儿')
            elif i == 15:
                cctv_list.append('CCTV15音乐')
            elif i == 16:
                cctv_list.append('CCTV16奥林匹克')
            elif i == 17:
                cctv_list.append('CCTV17农业农村')
        
        # 卫视列表（省份映射）
        province_keywords = {
            '湖南': ['湖南卫视', '湖南卫视HD', 'HNTV', '湖南'],
            '浙江': ['浙江卫视', '浙江卫视HD', 'ZJTV', '浙江'],
            '江苏': ['江苏卫视', '江苏卫视HD', 'JSTV', '江苏'],
            '上海': ['东方卫视', '上海卫视', '东方卫视HD', '上海'],
            '北京': ['北京卫视', '北京卫视HD', 'BTV', '北京'],
            '广东': ['广东卫视', '广东卫视HD', '广东'],
            '深圳': ['深圳卫视', '深圳卫视HD', '深圳'],
            '天津': ['天津卫视', '天津卫视HD', '天津'],
            '山东': ['山东卫视', '山东卫视HD', '山东'],
            '安徽': ['安徽卫视', '安徽卫视HD', '安徽'],
            '辽宁': ['辽宁卫视', '辽宁卫视HD', '辽宁'],
            '黑龙江': ['黑龙江卫视', '黑龙江卫视HD', '黑龙江'],
            '四川': ['四川卫视', '四川卫视HD', '四川'],
            '湖北': ['湖北卫视', '湖北卫视HD', '湖北'],
            '江西': ['江西卫视', '江西卫视HD', '江西'],
            '重庆': ['重庆卫视', '重庆卫视HD', '重庆'],
            '河南': ['河南卫视', '河南卫视HD', '河南'],
            '河北': ['河北卫视', '河北卫视HD', '河北'],
            '陕西': ['陕西卫视', '陕西卫视HD', '陕西'],
            '山西': ['山西卫视', '山西卫视HD', '山西'],
            '云南': ['云南卫视', '云南卫视HD', '云南'],
            '广西': ['广西卫视', '广西卫视HD', '广西'],
            '吉林': ['吉林卫视', '吉林卫视HD', '吉林'],
            '福建': ['东南卫视', '福建卫视', '福建'],
            '贵州': ['贵州卫视', '贵州卫视HD', '贵州'],
            '甘肃': ['甘肃卫视', '甘肃卫视HD', '甘肃'],
            '内蒙古': ['内蒙古卫视', '内蒙古'],
            '新疆': ['新疆卫视', '新疆'],
            '宁夏': ['宁夏卫视', '宁夏'],
            '青海': ['青海卫视', '青海'],
            '海南': ['海南卫视', '海南', '旅游卫视'],
            '西藏': ['西藏卫视', '西藏']
        }
        
        # 4K频道关键词
        keywords_4k = ['4K', '4k', 'UHD', '2160p']
        
        # 数字频道关键词
        digital_keywords = ['地理', '第一剧场', '风云', '怀旧剧场', '戏曲', '音乐', '少儿', '科教', '纪录', '发现', '世界地理', '风云剧场', '风云音乐', '风云足球', '第一时尚', '电视指南', '国防军事', '女性时尚', '高尔夫网球', '央视文化', '央视记录']
        
        # CHC频道
        chc_keywords = ['CHC', '华诚', '动作电影', '家庭影院', '高清电影']
        
        # 香港频道
        hk_keywords = ['香港', 'TVB', '翡翠', '明珠', '凤凰', 'NOW', 'CABLE', '港台', 'RTHK', '无线', '亚洲电视', 'ATV', 'VIU']
        
        # 台湾频道
        tw_keywords = ['台湾', '台视', '中视', '华视', '民视', '公视', '三立', '东森', '中天', 'TVBS', '年代', '非凡', '八大', '纬来', '客家', '原住民']
        
        for name, url in self.channels.items():
            name_upper = name.upper()
            name_lower = name.lower()
            
            # 央视分组（优先匹配）
            if any(cctv in name_upper for cctv in cctv_list) or ('CCTV' in name_upper and not any(kw in name_upper for kw in ['CCTV-4K', 'CCTV4K'])):
                groups['央视'].append((name, url))
            
            # 4K分组（包含CCTV4K等）
            if any(kw in name for kw in keywords_4k):
                groups['4K'].append((name, url))
            
            # 卫视分组
            for province, keywords in province_keywords.items():
                if any(kw in name for kw in keywords):
                    groups['卫视'].append((name, url))
                    break
            
            # 数字分组
            if any(kw in name for kw in digital_keywords):
                groups['数字'].append((name, url))
            
            # CHC分组
            if any(kw in name_upper for kw in chc_keywords):
                groups['CHC'].append((name, url))
            
            # 香港分组
            if any(kw in name for kw in hk_keywords):
                groups['HongKong'].append((name, url))
            
            # 台湾分组
            if any(kw in name for kw in tw_keywords):
                groups['TaiWan'].append((name, url))
        
        # 去重（同一个频道可能出现在多个分组，保留第一次出现）
        for group in groups:
            seen = set()
            unique = []
            for name, url in groups[group]:
                if name not in seen:
                    seen.add(name)
                    unique.append((name, url))
            groups[group] = unique
        
        return groups
    
    def generate_m3u(self, groups, output_path='auto.m3u'):
        """生成M3U播放列表"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            f.write('# 自动生成的直播源列表\n')
            f.write(f'# 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            for group_name, channels in groups.items():
                if not channels:
                    continue
                f.write(f'# 分组: {group_name} (共{len(channels)}个频道)\n')
                for name, url in channels:
                    # 清理名称中的特殊字符用于显示
                    display_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
                    f.write(f'#EXTINF:-1 group-title="{group_name}",{display_name}\n')
                    f.write(f'{url}\n')
                f.write('\n')
        
        logging.info(f"生成M3U文件: {output_path}")
        return output_path
    
    def run(self):
        """主流程"""
        logging.info("=" * 50)
        logging.info("开始拉取直播源...")
        logging.info("=" * 50)
        
        self.process_sources()
        groups = self.classify_channels()
        
        # 统计各分组数量
        logging.info("=" * 50)
        logging.info("分组统计:")
        for group, channels in groups.items():
            logging.info(f"  {group}: {len(channels)} 个频道")
        logging.info("=" * 50)
        
        output_file = self.generate_m3u(groups)
        logging.info(f"完成! 输出文件: {output_file}")

if __name__ == '__main__':
    fetcher = LiveStreamFetcher()
    fetcher.run()
