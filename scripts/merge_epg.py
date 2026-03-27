#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import os
import time
import copy
import re

# =========================
# EPG源列表
# =========================
EPG_URLS = [
    "https://epg.pw/xmltv/epg.xml",
    "http://epg.51zmt.top:8000/e1.xml.gz",
    "https://epg.136605.xyz/9days.xml.gz",
    "https://epg.zsdc.eu.org/t.xml.gz",
    "https://epg.pw/xmltv/epg_CN.xml.gz",
    "https://epg.pw/xmltv/epg_TW.xml.gz",
    "https://epg.pw/xmltv/epg_HK.xml.gz",
    "https://epg.iill.top/epg",
    "https://bit.ly/a1xepg",
    "https://epg.catvod.com/epg.xml",
    "https://7pal.short.gy/alex-epg",
]

# 映射日志文件名
OUTPUT_MAP_FILE = "channel_map.txt"

# =========================
# 手工映射表：重点频道统一ID
# 可持续补充
# key 会先经过 normalize_text() 再匹配
# =========================
MANUAL_ID_MAP = {
    # CCTV
    "cctv1": "cctv1",
    "cctv-1": "cctv1",
    "cctv1hd": "cctv1",
    "cctv1综合": "cctv1",
    "央视综合": "cctv1",
    "中央1": "cctv1",
    "中央一台": "cctv1",

    "cctv2": "cctv2",
    "cctv-2": "cctv2",
    "cctv2hd": "cctv2",
    "央视财经": "cctv2",

    "cctv3": "cctv3",
    "cctv-3": "cctv3",
    "cctv3hd": "cctv3",
    "央视综艺": "cctv3",

    "cctv4": "cctv4",
    "cctv-4": "cctv4",
    "cctv4hd": "cctv4",
    "央视中文国际": "cctv4",

    "cctv5": "cctv5",
    "cctv-5": "cctv5",
    "cctv5hd": "cctv5",
    "央视体育": "cctv5",

    "cctv5+": "cctv5plus",
    "cctv-5+": "cctv5plus",
    "cctv5plus": "cctv5plus",
    "cctv5plushd": "cctv5plus",
    "央视体育赛事": "cctv5plus",

    "cctv6": "cctv6",
    "cctv-6": "cctv6",
    "cctv6hd": "cctv6",
    "央视电影": "cctv6",

    "cctv7": "cctv7",
    "cctv-7": "cctv7",
    "cctv7hd": "cctv7",

    "cctv8": "cctv8",
    "cctv-8": "cctv8",
    "cctv8hd": "cctv8",
    "央视电视剧": "cctv8",

    "cctv9": "cctv9",
    "cctv-9": "cctv9",
    "cctv9hd": "cctv9",

    "cctv10": "cctv10",
    "cctv-10": "cctv10",
    "cctv10hd": "cctv10",

    "cctv11": "cctv11",
    "cctv-11": "cctv11",
    "cctv11hd": "cctv11",

    "cctv12": "cctv12",
    "cctv-12": "cctv12",
    "cctv12hd": "cctv12",

    "cctv13": "cctv13",
    "cctv-13": "cctv13",
    "cctv13hd": "cctv13",
    "央视新闻": "cctv13",

    "cctv14": "cctv14",
    "cctv-14": "cctv14",
    "cctv14hd": "cctv14",

    "cctv15": "cctv15",
    "cctv-15": "cctv15",
    "cctv15hd": "cctv15",

    "cctv16": "cctv16",
    "cctv-16": "cctv16",
    "cctv16hd": "cctv16",

    "cctv17": "cctv17",
    "cctv-17": "cctv17",
    "cctv17hd": "cctv17",

    # 凤凰
    "凤凰中文": "phoenixchinese",
    "凤凰中文台": "phoenixchinese",
    "phoenixchinese": "phoenixchinese",
    "凤凰资讯": "phoenixinfo",
    "凤凰资讯台": "phoenixinfo",
    "phoenixinfo": "phoenixinfo",
    "凤凰香港": "phoenixhongkong",
    "phoenixhongkong": "phoenixhongkong",

    # TVB / 香港常见
    "翡翠台": "tvbjade",
    "tvbjade": "tvbjade",
    "明珠台": "tvbpearl",
    "tvbpearl": "tvbpearl",
    "无线新闻台": "tvbnewschannel",
    "无线新闻": "tvbnewschannel",
    "tvbnewschannel": "tvbnewschannel",

    # now
    "now新闻": "nownews",
    "now新闻台": "nownews",
    "nownews": "nownews",
    "now财经": "nowbusiness",
    "now财经台": "nowbusiness",
    "nowbusiness": "nowbusiness",

    # 台湾常见
    "中天新闻台": "ctinews",
    "东森新闻台": "ebcnews",
    "tvbs新闻台": "tvbsnews",
    "民视": "ftv",
    "中视": "ctv",
    "华视": "cts",
    "公视": "pts",
}


def download_epg(url, retry=3):
    """下载EPG，自动识别gzip / xml"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for i in range(retry):
        try:
            print(f"正在下载: {url}")
            response = requests.get(
                url,
                timeout=60,
                headers=headers,
                allow_redirects=True
            )
            response.raise_for_status()

            content = response.content
            final_url = response.url
            content_type = response.headers.get("Content-Type", "").lower()
            encoding = response.headers.get("Content-Encoding", "").lower()

            is_gzip = False
            if final_url.endswith(".gz"):
                is_gzip = True
            elif "gzip" in content_type or "gzip" in encoding:
                is_gzip = True
            elif len(content) >= 2 and content[:2] == b"\x1f\x8b":
                is_gzip = True

            if is_gzip:
                try:
                    with gzip.GzipFile(fileobj=BytesIO(content)) as f:
                        content = f.read()
                except Exception:
                    content = gzip.decompress(content)

            text = content.decode("utf-8", errors="ignore").strip()

            if not text.startswith("<"):
                idx = text.find("<")
                if idx != -1:
                    text = text[idx:]

            print(f"  下载成功，大小: {len(text)} 字符，最终地址: {final_url}")
            return text

        except Exception as e:
            print(f"  第{i + 1}次尝试失败: {e}")
            time.sleep(2)

    print(f"  × 下载失败: {url}")
    return None


def normalize_text(s):
    """基础标准化，便于统一频道ID"""
    if not s:
        return ""

    s = s.strip().lower()
    s = (
        s.replace("臺", "台")
         .replace("鳳", "凤")
         .replace("資訊", "资讯")
         .replace("綫", "线")
         .replace("＋", "+")
    )

    s = s.replace(" ", "").replace("_", "").replace("-", "")
    s = s.replace("频道", "").replace("頻道", "")
    s = s.replace("高清", "").replace("超清", "").replace("标清", "")
    s = s.replace("hd", "").replace("uhd", "").replace("4k", "")
    s = s.replace("电视台", "台")

    return s


def get_display_names(channel_elem):
    names = []
    for dn in channel_elem.findall("display-name"):
        if dn.text and dn.text.strip():
            names.append(dn.text.strip())
    return names


def guess_channel_id(raw_id, display_names):
    """
    统一频道ID：
    1. 手工映射
    2. CCTV自动归一
    3. 常见频道自动归一
    4. 最后兜底
    """
    candidates = []

    if raw_id:
        candidates.append(raw_id)

    for n in display_names:
        if n:
            candidates.append(n)

    # 手工映射优先
    for item in candidates:
        key = normalize_text(item)
        if key in MANUAL_ID_MAP:
            return MANUAL_ID_MAP[key]

    # CCTV 自动归一
    for item in candidates:
        key = normalize_text(item)

        m = re.match(r"^cctv(\d+)\+?$", key)
        if m:
            num = m.group(1)
            if key.endswith("+"):
                return f"cctv{num}plus"
            return f"cctv{num}"

        m = re.match(r"^央视(\d+)\+?$", key)
        if m:
            num = m.group(1)
            if key.endswith("+"):
                return f"cctv{num}plus"
            return f"cctv{num}"

    # 常见港台频道自动归一
    for item in candidates:
        key = normalize_text(item)

        if "凤凰中文" in key:
            return "phoenixchinese"
        if "凤凰资讯" in key:
            return "phoenixinfo"
        if "凤凰香港" in key:
            return "phoenixhongkong"

        if "翡翠台" in key:
            return "tvbjade"
        if "明珠台" in key:
            return "tvbpearl"
        if "无线新闻" in key:
            return "tvbnewschannel"

        if "now新闻" in key:
            return "nownews"
        if "now财经" in key:
            return "nowbusiness"

    # 兜底
    base = raw_id if raw_id else (display_names[0] if display_names else "")
    base = normalize_text(base)
    base = re.sub(r"[^a-z0-9+一-龥]", "", base)

    return base if base else "unknown"


def has_icon(channel_elem):
    icon = channel_elem.find("icon")
    return icon is not None and bool(icon.get("src"))


def merge_channel(existing, new_one):
    """
    合并channel：
    - 优先保留带 icon 的
    - display-name 去重补充
    """
    existing_has_icon = has_icon(existing)
    new_has_icon = has_icon(new_one)

    if (not existing_has_icon) and new_has_icon:
        icon = new_one.find("icon")
        if icon is not None:
            existing.append(copy.deepcopy(icon))

    existing_names = set(get_display_names(existing))
    for dn in new_one.findall("display-name"):
        text = dn.text.strip() if dn.text else ""
        if text and text not in existing_names:
            existing.append(copy.deepcopy(dn))
            existing_names.add(text)

    return existing


def build_normalized_channel(ch, new_id):
    """复制并重建 channel，替换为统一后的 id"""
    new_ch = ET.Element("channel", {"id": new_id})

    names = get_display_names(ch)
    if names:
        seen = set()
        for name in names:
            if name not in seen:
                node = ET.SubElement(new_ch, "display-name")
                node.text = name
                seen.add(name)
    else:
        node = ET.SubElement(new_ch, "display-name")
        node.text = new_id

    icon = ch.find("icon")
    if icon is not None and icon.get("src"):
        ET.SubElement(new_ch, "icon", src=icon.get("src"))

    return new_ch


def indent_xml(elem, level=0):
    """美化XML输出"""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def merge_epg_sources():
    """合并所有EPG源，统一频道ID，保留台标，输出 joker/epg.xml"""
    all_programmes = []
    programme_seen = set()
    channels = {}
    tv_attrib = {}
    source_count = 0
    mapping_logs = []

    print("=" * 70)
    print("开始合并EPG源（统一频道ID + 保留台标）")
    print("=" * 70)

    for idx, url in enumerate(EPG_URLS, 1):
        print(f"\n处理源 #{idx}:")
        xml_content = download_epg(url)

        if xml_content is None:
            continue

        try:
            root = ET.fromstring(xml_content)

            if not tv_attrib:
                tv_attrib = dict(root.attrib) if root.attrib else {}
                if tv_attrib:
                    print(f"  使用tv属性: {tv_attrib}")

            id_mapping = {}
            source_channels = root.findall("channel")
            normalized_count = 0

            # 处理 channel
            for ch in source_channels:
                raw_id = ch.get("id", "").strip()
                display_names = get_display_names(ch)
                unified_id = guess_channel_id(raw_id, display_names)

                if raw_id:
                    id_mapping[raw_id] = unified_id

                mapping_logs.append(
                    f"{raw_id or '[NO_ID]'} => {unified_id} | {' / '.join(display_names[:3])}"
                )

                normalized_channel = build_normalized_channel(ch, unified_id)

                if unified_id not in channels:
                    channels[unified_id] = normalized_channel
                else:
                    channels[unified_id] = merge_channel(channels[unified_id], normalized_channel)

                if raw_id and raw_id != unified_id:
                    normalized_count += 1

            # 处理 programme
            source_programmes = root.findall("programme")
            added_count = 0

            for prog in source_programmes:
                raw_channel = prog.get("channel", "").strip()
                new_channel = id_mapping.get(raw_channel)

                if not new_channel:
                    new_channel = guess_channel_id(raw_channel, [])

                new_prog = copy.deepcopy(prog)
                new_prog.set("channel", new_channel)

                start = new_prog.get("start", "").strip()
                stop = new_prog.get("stop", "").strip()

                title_elem = new_prog.find("title")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                key = (new_channel, start, stop, title)
                if key in programme_seen:
                    continue

                programme_seen.add(key)
                all_programmes.append(new_prog)
                added_count += 1

            print(f"  原始频道: {len(source_channels)} 个")
            print(f"  统一ID处理: {normalized_count} 个")
            print(f"  新增节目: {added_count} 个")
            source_count += 1

        except ET.ParseError as e:
            print(f"  XML解析错误: {e}")
        except Exception as e:
            print(f"  处理出错: {e}")

    print("\n" + "=" * 70)
    print(f"合并完成: 共处理 {source_count} 个源")
    print(f"统一后频道总数: {len(channels)}")
    print(f"节目总数: {len(all_programmes)}")

    if not tv_attrib:
        tv_attrib = {
            "generator-info-name": "EPG Merger",
            "date": time.strftime("%Y%m%d")
        }

    new_root = ET.Element("tv", tv_attrib)

    # 先 channel
    for cid in sorted(channels.keys()):
        new_root.append(channels[cid])

    # 再 programme
    all_programmes.sort(key=lambda x: (
        x.get("channel", ""),
        x.get("start", ""),
        x.get("stop", "")
    ))
    for prog in all_programmes:
        new_root.append(prog)

    indent_xml(new_root)
    tree = ET.ElementTree(new_root)

    # 输出到仓库根目录 joker/epg.xml
    script_dir = os.path.dirname(os.path.abspath(__file__))   # joker/scripts
    root_dir = os.path.dirname(script_dir)                    # joker
    output_file = os.path.join(root_dir, "epg.xml")
    map_file = os.path.join(root_dir, OUTPUT_MAP_FILE)

    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本目录: {script_dir}")
    print(f"仓库根目录: {root_dir}")
    print(f"输出文件路径: {output_file}")
    print(f"映射文件路径: {map_file}")

    tree.write(output_file, encoding="utf-8", xml_declaration=True)

    with open(map_file, "w", encoding="utf-8") as f:
        for line in sorted(set(mapping_logs)):
            f.write(line + "\n")

    print(f"epg.xml exists? {os.path.exists(output_file)}")
    print(f"channel_map.txt exists? {os.path.exists(map_file)}")

    if os.path.exists(output_file):
        print(f"epg.xml size: {os.path.getsize(output_file)} bytes")
    if os.path.exists(map_file):
        print(f"channel_map.txt size: {os.path.getsize(map_file)} bytes")

    print("=" * 70)
    return output_file


if __name__ == "__main__":
    merge_epg_sources()
