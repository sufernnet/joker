#!/usr/bin/env python3
"""
Gather.m3u 合并脚本（基于原始文件结构，增加调试输出）
"""

import requests
import re
from datetime import datetime

# ================== 配置 ==================
BB_URL = "https://raw.githubusercontent.com/sufernnet/joker/main/BB.m3u"
GAT_URL = "https://yang.sufern001.workers.dev/"
OUTPUT_FILE = "Gather.m3u"

# 需要提取的两个分组名
SOURCE_GROUPS = ["• Juli 「精選」", "•台湾「限制」"]

# 分组标记的模式（请根据实际文件修改）
# 常见格式： "{group_name},#genre#"  或  "# {group_name}"  或  "{group_name}"
GROUP_MARKER_PATTERN = "{group_name},#genre#"  # 如果不同请修改

# 输出分组名称
HK_GROUP = "HK"
TW_GROUP = "TW"

EPG_URL = "https://epg.zsdc.eu.org/t.xml.gz"

# 台湾频道筛选条件（必须包含「4gTV」或 ofiii，且包含「龍華」）
TW_REQUIRE_KEYWORDS = ["4gtv", "ofiii"]
TW_REQUIRE_LONGHUA = True

# 所有过滤已禁用
FILTER_KEYWORDS = []
FILTER_URLS = []
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
    增强版提取函数，会打印所有可能的分组标记行。
    """
    lines = content.splitlines()
    result = {group: [] for group in target_groups}
    current_group = None

    log(f"开始从文件中提取分组: {target_groups}")
    log("正在扫描可能的分组标记行...")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 调试：打印包含目标分组名称的行（不限于特定格式）
        for group in target_groups:
            if group in line:
                log(f"发现包含分组名 '{group}' 的行 {i+1}: {line}")

        # 使用配置的模式匹配分组开始
        for group in target_groups:
            expected_marker = GROUP_MARKER_PATTERN.format(group_name=group)
            if expected_marker in line:
                current_group = group
                log(f"✅ 在第 {i+1} 行匹配到分组开始: {line}")
                break

        if current_group:
            # 如果遇到下一个分组的标记，则停止当前分组
            next_group_found = False
            for other_group in target_groups:
                if other_group == current_group:
                    continue
                other_marker = GROUP_MARKER_PATTERN.format(group_name=other_group)
                if other_marker in line:
                    log(f"到达下一个分组 '{other_group}'，停止提取 '{current_group}'")
                    current_group = None
                    next_group_found = True
                    break
            if next_group_found:
                continue

            # 提取频道行（假设格式为 "名称,URL"）
            if "," in line and "://" in line:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    name, url = parts
                    result[current_group].append((name.strip(), url.strip()))

    for group in target_groups:
        log(f"分组 '{group}' 提取到 {len(result[group])} 个频道")
    return result

def clean_channel_name(name):
    """去除频道名称末尾的分辨率标记"""
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
    """简单去重：基于URL保留第一个"""
    seen = {}
    deduped = []
    for name, url in channels:
        if url not in seen:
            seen[url] = name
            deduped.append((name, url))
        else:
            log(f"去重: 跳过重复URL {url} (已有名称: {seen[url]})")
    return deduped

def is_tw_desired_channel(name):
    """判断是否为台湾分组中需要的频道"""
    name_lower = name.lower()
    has_keyword = any(kw in name_lower for kw in TW_REQUIRE_KEYWORDS)
    has_longhua = "龍華" in name or "龙华" in name_lower
    if TW_REQUIRE_LONGHUA:
        return has_keyword and has_longhua
    else:
        return has_keyword

# ================== 主流程 ==================
def main():
    log("开始生成 Gather.m3u ...")

    bb = download(BB_URL, "BB.m3u")
    if not bb:
        return

    gat_content = download(GAT_URL, "新源文件") or ""
    if not gat_content:
        log("❌ 源文件为空，无法提取")
        return

    # 提取分组频道
    extracted = extract_channels_from_file(gat_content, SOURCE_GROUPS)

    # 处理 HK 分组
    hk_raw = extracted.get("• Juli 「精選」", [])
    hk_cleaned = [(clean_channel_name(name), url) for name, url in hk_raw]
    hk_deduped = deduplicate_channels(hk_cleaned)
    log(f"HK 最终频道数: {len(hk_deduped)}")

    # 处理 TW 分组（筛选）
    tw_raw = extracted.get("•台湾「限制」", [])
    tw_filtered = [(name, url) for name, url in tw_raw if is_tw_desired_channel(name)]
    log(f"TW 筛选后保留 {len(tw_filtered)} 个频道（原始 {len(tw_raw)}）")
    tw_cleaned = [(clean_channel_name(name), url) for name, url in tw_filtered]
    tw_deduped = deduplicate_channels(tw_cleaned)
    log(f"TW 最终频道数: {len(tw_deduped)}")

    # 构建输出文件（与之前相同）
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

    if hk_deduped:
        output += f"\n# {HK_GROUP}频道 ({len(hk_deduped)})\n"
        for name, url in hk_deduped:
            output += f'#EXTINF:-1 group-title="{HK_GROUP}",{name}\n{url}\n'

    if tw_deduped:
        output += f"\n# {TW_GROUP}频道 ({len(tw_deduped)})\n"
        for name, url in tw_deduped:
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{name}\n{url}\n'

    total = bb_count + len(hk_deduped) + len(tw_deduped)

    output += f"""
# 统计信息
# BB 频道数: {bb_count}
# {HK_GROUP}频道数: {len(hk_deduped)}
# {TW_GROUP}频道数: {len(tw_deduped)}
# 总频道数: {total}
# 更新时间: {timestamp}
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    log(f"🎉 Gather.m3u 生成成功，总频道数: {total}")

if __name__ == "__main__":
    main()
