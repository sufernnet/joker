# 🔥 终极秒开版（核心改造：RTP优先 + HTTP测速 + 强制保底）

async def test_stream(session, url):
    start = time.time()

    # ✅ 1. RTP 直接秒过（绝对关键）
    if "/rtp/" in url:
        return True, 0.05

    try:
        async with session.get(url, timeout=TEST_TIMEOUT) as r:
            if r.status in (200, 206):
                return True, time.time() - start
    except:
        pass

    return False, None


async def fetch_best_cctv_channels():
    all_valid = []
    raw_candidates = []  # ✅ 用于保底

    for s in CCTV_SOURCES:
        is_m3u = is_m3u_source(s)
        print(f"抓取目标频道源: {s} | is_m3u={is_m3u}")

        try:
            timeout = aiohttp.ClientTimeout(total=40)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(s) as r:
                    content = await r.text()

                entries = extract_urls_from_m3u(content) if is_m3u else extract_urls_from_txt(content)

                # ✅ 记录原始候选（用于保底）
                raw_candidates.extend(entries)

                tasks = [test_stream(session, u) for _, u in entries]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result, (ch, u) in zip(results, entries):
                    if isinstance(result, Exception):
                        continue
                    ok, t = result
                    if ok:
                        all_valid.append((ch, u, t))
        except:
            continue

    best_map = {}

    # ✅ 2. 优先选最快
    for ch, url, latency in all_valid:
        if contains_date(ch) or contains_date(url):
            continue

        key = match_target(ch)
        if not key:
            continue

        # RTP 优先级最高
        priority = 0 if "/rtp/" in url else 1

        if key not in best_map:
            best_map[key] = (url, latency, priority)
        else:
            old_url, old_latency, old_priority = best_map[key]

            if priority < old_priority or (priority == old_priority and latency < old_latency):
                best_map[key] = (url, latency, priority)

    # ✅ 3. 保底机制（防止一个都没有）
    for ch, url in raw_candidates:
        key = match_target(ch)
        if not key:
            continue

        if key not in best_map:
            best_map[key] = (url, 999, 2)  # 最低优先级

    result = []

    # ✅ 4. 按顺序输出
    for name in TARGET_CCTV_ORDER:
        if name in best_map:
            result.append((name, best_map[name][0]))

    for name in TARGET_CHC_ORDER:
        if name in best_map:
            result.append((name, best_map[name][0]))

    print("最终命中频道数:", len(result))
    return result


# ✅ 额外增强（推荐）
def normalize_name_for_match(name):
    n = (name or "").strip().lower()
    n = re.sub(r"[\s\-_·]", "", n)

    # 🚨 去掉所有画质标记
    n = re.sub(r"(hd|sd|fhd|uhd|4k|标清|高清|超清|频道)", "", n)

    n = n.replace("（", "(").replace("）", ")")
    return n
