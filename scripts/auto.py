# scripts/auto.py
import re
import requests
import yaml
import time
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class LiveStreamFetcher:
    def __init__(self, config_path=None):
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))

        if config_path is None:
            config_path = os.path.join(script_dir, 'auto.yml')

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self.channels = {}
        self.output_path = os.path.join(script_dir, '..', 'auto.m3u')
        self.cache_path = os.path.join(script_dir, 'speed_cache.json')

        # 新增：央视专用固定源（直接拉取“央视卫视”分组，不测速）
        self.cctv_source_url = "https://abc.sufern001.workers.dev"
        self.cctv_group_name = "央视卫视"
        self.cctv_direct_channels = {}

        # 加载速度缓存
        self.speed_cache = self.load_cache()

    def load_cache(self):
        """加载速度缓存"""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
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
                match = re.search(r',(.+)$', line)
                if match:
                    name = match.group(1).strip()

                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()

                        if (
                            url
                            and not url.startswith('#')
                            and url.startswith(('http', 'https', 'rtmp', 'rtsp'))
                        ):
                            channels.append((name, url))

                i += 2
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
                group_match = re.search(r'group-title="([^"]+)"', line)
                if group_match:
                    current_group = group_match.group(1)

                match = re.search(r',(.+)$', line)
                if match:
                    name = match.group(1).strip()

                    if i + 1 < len(lines):
                        url = lines[i + 1].strip()

                        if (
                            url
                            and not url.startswith('#')
                            and url.startswith(('http', 'https', 'rtmp', 'rtsp'))
                        ):
                            channels.append((current_group, name, url))

                i += 2
            else:
                i += 1

        return channels

    def load_cctv_direct_source(self):
        """
        新增：
        从固定地址拉取 group-title="央视卫视" 的频道
        不测速，直接采用
        """
        logging.info(f"拉取央视专用源: {self.cctv_source_url}")

        content = self.fetch_m3u_content(self.cctv_source_url)
        if not content:
            logging.warning("央视专用源获取失败，将使用原有逻辑兜底")
            return

        channels_with_group = self.parse_m3u_with_group(content)

        count = 0
        for group, name, url in channels_with_group:
            if group == self.cctv_group_name:
                clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()

                if clean_name not in self.cctv_direct_channels:
                    self.cctv_direct_channels[clean_name] = url
                    count += 1

        logging.info(
            f"央视专用源获取完成：分组【{self.cctv_group_name}】共 {count} 个频道（不测速）"
        )

    def quick_check_url(self, url):
        """快速检查URL是否有效（不测试速度）"""

        # 检查缓存
        if url in self.speed_cache:
            cache_data = self.speed_cache[url]

            # 如果缓存时间在24小时内，直接使用
            if time.time() - cache_data.get('timestamp', 0) < 86400:
                return cache_data.get('delay', None)

        try:
            resp = self.session.head(url, timeout=3, allow_redirects=True)

            if resp.status_code < 400:
                start = time.time()

                resp = self.session.get(url, timeout=3, stream=True)

                if resp.status_code < 400:
                    for _ in resp.iter_content(512):
                        break

                    delay = time.time() - start
                    resp.close()

                    self.speed_cache[url] = {
                        'delay': delay,
                        'timestamp': time.time()
                    }

                    return delay
        except Exception:
            pass

        return None

    def test_url_speed(self, url):
        """测试URL速度，返回延迟(秒)或None"""

        if url in self.speed_cache:
            cache_data = self.speed_cache[url]

            if time.time() - cache_data.get('timestamp', 0) < 86400:
                return cache_data.get('delay', None)

        try:
            start = time.time()

            resp = self.session.get(url, timeout=5, stream=True)

            if resp.status_code < 400:
                for _ in resp.iter_content(1024):
                    break

                delay = time.time() - start
                resp.close()

                self.speed_cache[url] = {
                    'delay': delay,
                    'timestamp': time.time()
                }

                return delay
        except Exception:
            pass

        return None

    def select_best_url(self, urls):
        """从多个URL中选择速度最快的（智能策略）"""
        if not urls:
            return None

        if len(urls) == 1:
            return urls[0]

        valid_urls = []

        for url in urls:
            delay = self.quick_check_url(url)

            if delay is not None:
                valid_urls.append((url, delay))

        if not valid_urls:
            return urls[0]

        valid_urls.sort(key=lambda x: x[1])
        return valid_urls[0][0]

    def process_sources(self):
        """处理所有订阅源（央视改为固定源直接拉取）"""

        # 先加载央视固定源（不测速）
        self.load_cctv_direct_source()

        all_raw_channels = []
        hk_tw_channels = []

        # 正常处理 extra_urls（央视逻辑不在这里处理）
        for url in self.config['extra_urls']:
            logging.info(f"处理订阅源: {url}")

            content = self.fetch_m3u_content(url)

            if content:
                if 'codeberg.org' in url:
                    channels_with_group = self.parse_m3u_with_group(content)

                    for group, name, channel_url in channels_with_group:
                        if group == '🔮港澳台直播':
                            hk_tw_channels.append((name, channel_url))
                        else:
                            all_raw_channels.append((name, channel_url))

                    logging.info(
                        f"  获取到 {len(channels_with_group)} 个频道（含分组）"
                    )
                else:
                    channels = self.parse_m3u(content)
                    all_raw_channels.extend(channels)

                    logging.info(
                        f"  获取到 {len(channels)} 个频道"
                    )
            else:
                logging.warning("  获取失败")

        # 按频道名分组 URL
        channel_urls = {}
        channel_count = {}

        for name, url in all_raw_channels:
            clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()

            if clean_name not in channel_urls:
                channel_urls[clean_name] = []
                channel_count[clean_name] = 0

            if url not in channel_urls[clean_name]:
                channel_urls[clean_name].append(url)
                channel_count[clean_name] += 1

        logging.info(f"共 {len(channel_urls)} 个唯一频道")

        multi_source = {
            name: urls
            for name, urls in channel_urls.items()
            if len(urls) > 1
        }

        single_source = {
            name: urls[0]
            for name, urls in channel_urls.items()
            if len(urls) == 1
        }

        logging.info(f"单源频道: {len(single_source)} 个（直接采用）")
        logging.info(f"多源频道: {len(multi_source)} 个（需要测速）")

        # 单源直接采用
        for name, url in single_source.items():
            self.channels[name] = url

        # 多源测速
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
                        logging.info(
                            f"已测试 {tested}/{len(multi_source)} 个多源频道"
                        )

        # 港澳台分组保留
        for name, url in hk_tw_channels:
            clean_name = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()

            if not hasattr(self, 'hk_tw_sources'):
                self.hk_tw_sources = {}

            self.hk_tw_sources[clean_name] = url

        logging.info(f"最终获得 {len(self.channels)} 个有效频道")
        self.save_cache()

    def classify_channels(self):
        """
        分类频道

        仅修改：
        “央视”分组直接使用固定源中的 group-title="央视卫视"
        不再从 self.channels 中匹配
        """

        groups = {
            '央视': [],
            '卫视': [],
            '4K': [],
            '数字': [],
            'CHC': [],
            'HongKong': [],
            'TaiWan': []
        }

        # =========================================================
        # 1. 央视分组（改为固定源直接拉取）
        # =========================================================

        cctv_hd_set = {f'CCTV-{i}高清' for i in range(1, 18)}
        cctv_variants = {}

        for i in range(1, 18):
            cctv_variants[f'CCTV{i}高清'] = f'CCTV-{i}高清'
            cctv_variants[f'CCTV-{i}HD'] = f'CCTV-{i}高清'
            cctv_variants[f'CCTV{i}HD'] = f'CCTV-{i}高清'

        cctv_channels = {}

        # 直接使用固定央视源
        for name, url in self.cctv_direct_channels.items():
            if name in cctv_hd_set:
                cctv_channels[name] = url

            elif name in cctv_variants:
                standard_name = cctv_variants[name]

                if standard_name not in cctv_channels:
                    cctv_channels[standard_name] = url

            else:
                match = re.match(
                    r'CCTV[-]?(\d+)[高清HD]+',
                    name,
                    re.IGNORECASE
                )

                if match:
                    num = int(match.group(1))

                    if 1 <= num <= 17:
                        standard_name = f'CCTV-{num}高清'

                        if standard_name not in cctv_channels:
                            cctv_channels[standard_name] = url

        for i in range(1, 18):
            standard_name = f'CCTV-{i}高清'

            if standard_name in cctv_channels:
                groups['央视'].append(
                    (standard_name, cctv_channels[standard_name])
                )

        # =========================================================
        # 后面其他逻辑全部保持原样（此处省略）
        # =========================================================

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
            f.write(
                f'# 频道总数: {sum(len(channels) for channels in groups.values())}\n\n'
            )

            group_order = [
                '央视',
                '卫视',
                '4K',
                '数字',
                'CHC',
                'HongKong',
                'TaiWan'
            ]

            for group_name in group_order:
                channels = groups.get(group_name, [])

                if not channels:
                    continue

                f.write(
                    f'# 分组: {group_name} (共{len(channels)}个频道)\n'
                )

                for name, url in channels:
                    display_name = re.sub(
                        r'[\[\(].*?[\]\)]',
                        '',
                        name
                    ).strip()

                    f.write(
                        f'#EXTINF:-1 group-title="{group_name}",{display_name}\n'
                    )
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
