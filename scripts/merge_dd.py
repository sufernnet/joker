# ===== ⚠️ 修复：写入 TW 分组时，使用清洗后的名称 =====
if sorted_tw:
    output += f"\n# {TW_GROUP}频道 ({len(sorted_tw)})\n"
    for extinf_line, cleaned_name, url in sorted_tw:
        try:
            # 步骤1：先替换 group-title
            modified = re.sub(r'group-title="[^"]*"', f'group-title="{TW_GROUP}"', extinf_line)
            
            # 步骤2：再替换末尾的频道名称（最后一个逗号之后的部分）
            parts = modified.rsplit(',', 1)
            if len(parts) == 2:
                # 用清洗后的名称替换原始名称
                modified = parts[0] + ',' + cleaned_name
            
            output += modified + "\n" + url + "\n"
        except Exception as e:
            # 降级处理：如果替换失败，使用简单格式
            log(f"⚠️ 写入失败，使用降级格式: {cleaned_name}")
            output += f'#EXTINF:-1 group-title="{TW_GROUP}",{cleaned_name}\n{url}\n'
