#!/usr/bin/env python3
"""
Gather.m3u 合并脚本（基于新源）

功能：
1. 从新源 https://yang.sufern001.workers.dev/ 提取指定分组
   - "• Juli 「精選」" → 全部提取，重命名为 HK
   - "•台湾「限制」" → 提取包含「4gTV」或 ofiii 的龍華频道，重命名为 TW
2. 合并 BB.m3u
3. 输出 Gather.m3u
4. 无过滤，仅做名称清洗和基于URL的去重
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================

BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
# 新主要源
GAT_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = "Gather.m3u"

# 需要提取的两个分组名（原样）
SOURCE_GROUPS = ["• Juli 「精選」", "•台湾「限制」"]

# 输出分组名称
HK_GROUP = "HK"
TW_GROUP = "TW"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 过滤功能已禁用，保留为空列表
FILTER_KEYWORDS = []
FILTER_URLS = []

# 名称标准化映射（去重用）—— 暂不启用，设为空
NAME_NORMALIZATION = {}
PREFERRED_NAMES = []

# ================== 工具 ==================

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def download(url, desc):
    try:
        log(f"下载 {desc}...")
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        log(f"✅ {desc} 下载成功 ({len(r.text)} 字符)")
        return r.text
    except Exception as e:
        log(f"❌ {desc} 下载失败: {e}")
        return None

def extract_channels_from_file(content, target_groups):
    """
    从文件内容中提取指定分组列表中的所有频道。
    返回字典：{group_name: [(name, url), ...]}
    """
    lines = content.splitlines()
    result = {group: [] for group in target_groups}
    current_group = None

    log(f"开始从文件中提取分组: {target_groups}")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 检查是否是目标分组的开始标记
        for group in target_groups:
            marker = f"{group},#genre#"
            if marker in line:
                current_group = group
                log(f"✅ 在第 {i+1} 行找到目标分组: {group}")
                break

        if current_group:
            # 如果遇到下一个分组的标记，则停止当前分组的提取
            if ",#genre#" in line and current_group not in line:
                log(f"到达下一个分组 '{line.split(',')[0]}'，停止提取 '{current_group}'")
                current_group = None
                continue

            if "," in line and "://" in line:
                name, url = line.split(",", 1)
                result[current_group].append((name.strip(), url.strip()))

    for group in target_groups:
        log(f"分组 '{group}' 提取到 {len(result[group])} 个频道")
    return result

def clean_channel_name(name):
    """去除频道名称末尾的分辨率标记如 'HD 1080p', '1080p' 等"""
    original = name
    name = re.sub(r'\s*[Hh][Dd]\s*1080[pP]?\s*$', '', name)
    name = re.sub(r'\s*1080[pP]\s*$', '', name)
    name = re.sub(r'\s*[Hh][Dd]\s*$', '', name)
    name = re.sub(r'\s*720[pP]\s*$', '', name)
    name = name.strip()
    if name != original:
        log(f"清洗名称: '{original}' -> '{name}'")
    return name

def deduplicate_channels(channels):
    """
    简单去重：基于URL，相同URL只保留第一个名称
    """
    seen = {}
    deduped = []
    for name, url in channels:
        if url not in seen:
            seen[url] = name
            deduped.append((name, url))
        else:
            log(f"去重: 跳过重复URL {url} (已有名称: {seen[url]}, 当前名称: {name})")
    log(f"去重前频道数: {len(channels)}，去重后: {len(deduped)}")
    return deduped

# ================== 提取特定频道的筛选函数 ==================

def is_tw_desired_channel(name):
    """
    判断是否为台湾分组中需要的频道：
    名称必须包含「4gTV」或 ofiii，且包含「龍華」
    """
    name_lower = name.lower()
    has_keyword = ("4gtv" in name_lower or "ofiii" in name_lower)
    has_longhua = "龍華" in name or "龙华" in name_lower
    return has_keyword and has_longhua

# ================== 主流程 ==================

def main():
    log("开始生成 Gather.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    gat_content = download(GAT_URL, "新源文件") or ""

    all_extracted = {}  # group -> [(name, url)]
    if gat_content:
        all_extracted = extract_channels_from_file(gat_content, SOURCE_GROUPS)

    # 处理 HK 分组：提取「• Juli 「精選」」全部频道
    hk_raw = all_extracted.get("• Juli 「精選」", [])
    hk_cleaned = [(clean_channel_name(name), url) for name, url in hk_raw]
    hk_deduped = deduplicate_channels(hk_cleaned)
    log(f"HK 频道数（处理后）: {len(hk_deduped)}")

    # 处理 TW 分组：从「•台湾「限制」」中筛选包含「4gTV」或 ofiii 的龍華频道
    tw_raw = all_extracted.get("•台湾「限制」", [])
    tw_filtered = [(name, url) for name, url in tw_raw if is_tw_desired_channel(name)]
    log(f"TW 筛选后保留 {len(tw_filtered)} 个频道（原始 {len(tw_raw)}）")
    tw_cleaned = [(clean_channel_name(name), url) for name, url in tw_filtered]
    tw_deduped = deduplicate_channels(tw_cleaned)
    log(f"TW 频道数（处理后）: {len(tw_deduped)}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    output = f'#EXTM3U url-tvg="{EPG_URL}"\n\n'
    output += f"""# Gather.m3u
# 生成时间: {timestamp}
# 更新频率: 每天 06:00 / 17:00
# EPG: {EPG_URL}
# GitHub Actions 自动生成

"""

    bb_count = 0
    for line in bb.splitlines():
        if line.startswith("#EXTM3U"):
            continue
        output += line + "\n"
        if line.startswith("#EXTINF"):
            bb_count += 1

    # 写入 HK 分组
    if hk_deduped:
        output += f"\n# {HK_GROUP}频道 ({len(hk_deduped)})\n"
        for name, url in hk_deduped:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n'
            output += f"{url}\n"

    # 写入 TW 分组
    if tw_deduped:
        output += f"\n# {TW_GROUP}频道 ({len(tw_deduped)})\n"
        for name, url in tw_deduped:
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{name}\n'
            output += f"{url}\n"

    total = bb_count + len(hk_deduped) + len(tw_deduped)

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {HK_GROUP}频道数: {len(hk_deduped)}
# {TW_GROUP}频道数: {len(tw_deduped)}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        log("🎉 Gather.m3u 生成成功")
        log(f"📺 BB({bb_count}) + HK({len(hk_deduped)}) + TW({len(tw_deduped)}) = {total}")
    except Exception as e:
        log(f"❌ 保存失败: {e}")

if __name__ == "__main__":
    main()
