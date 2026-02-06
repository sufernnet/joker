name: 自动合并M3U（使用Cloudflare代理）

on:
  # 手动触发
  workflow_dispatch:
  
  # 定时触发：北京时间 06:00 和 17:00
  schedule:
    - cron: '0 22 * * *'  # UTC 22:00 = 北京时间 06:00 (UTC+8)
    - cron: '0 9 * * *'   # UTC 09:00 = 北京时间 17:00 (UTC+8)
  
  # 当脚本更新时也触发
  push:
    paths:
      - 'scripts/merge_from_proxy.py'
      - '.github/workflows/merge-m3u.yml'

jobs:
  merge-m3u:
    runs-on: ubuntu-latest
    
    steps:
    - name: 📥 检出代码（带深度）
      uses: actions/checkout@v3
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        fetch-depth: 0  # 获取完整历史
    
    - name: 🐍 设置Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: 📦 安装依赖
      run: |
        pip install requests beautifulsoup4
    
    - name: 🕒 显示时间信息
      run: |
        echo "=== 时间信息 ==="
        echo "当前UTC时间: $(date -u '+%Y-%m-%d %H:%M:%S')"
        echo "当前北京时间: $(date -d '+8 hours' '+%Y-%m-%d %H:%M:%S')"
        echo "工作流名称: ${{ github.workflow }}"
        echo "触发事件: ${{ github.event_name }}"
        echo "触发时间: ${{ github.event.schedule || '手动触发' }}"
    
    - name: 🚀 运行合并脚本
      run: |
        echo "开始运行合并脚本..."
        python scripts/merge_from_proxy.py
        
        echo -e "\n=== 检查生成的文件 ==="
        if [ -f "CC.m3u" ]; then
          echo "✅ CC.m3u 已生成"
          echo "文件大小: $(wc -c < CC.m3u) 字节"
          echo "行数: $(wc -l < CC.m3u)"
          echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
          
          echo -e "\n=== 文件内容预览 ==="
          echo "前10行:"
          head -10 CC.m3u
          echo "..."
          
          echo -e "\n=== 文件结构验证 ==="
          echo "EPG信息:"
          grep -i "url-tvg" CC.m3u || echo "未找到EPG信息"
          echo "HK频道数: $(grep -c 'group-title=\"HK\"' CC.m3u || echo 0)"
          echo "TW频道数: $(grep -c 'group-title=\"TW\"' CC.m3u || echo 0)"
        else
          echo "❌ CC.m3u 未生成"
          exit 1
        fi
    
    - name: 🔄 同步远程更改
      run: |
        echo "同步远程仓库..."
        # 配置Git用户
        git config user.email "github-actions[bot]@users.noreply.github.com"
        git config user.name "github-actions[bot]"
        
        # 拉取最新更改（使用rebase避免合并提交）
        git pull origin main --rebase --autostash
        
        echo "✅ 同步完成"
    
    - name: 📤 提交更新
      run: |
        echo "准备提交更新..."
        
        # 检查文件是否存在
        if [ ! -f "CC.m3u" ]; then
          echo "❌ CC.m3u不存在，无法提交"
          exit 1
        fi
        
        # 检查文件是否有变化
        if git diff --quiet CC.m3u; then
          echo "📭 CC.m3u 无变化，无需提交"
          exit 0
        fi
        
        # 添加文件
        git add CC.m3u
        
        # 提交
        git commit -m "🤖 自动更新 CC.m3u [$(date -u '+%Y-%m-%d %H:%M UTC')]"
        
        echo "提交信息:"
        git log -1 --oneline
        
        # 推送更改
        echo "推送更改..."
        git push origin main
        
        echo "✅ 提交完成"
    
    - name: 📊 输出结果
      if: always()
      run: |
        echo "=== 运行总结 ==="
        echo "🕒 运行完成时间: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
        echo "🕐 北京时间: $(date -d '+8 hours' '+%Y-%m-%d %H:%M:%S')"
        echo ""
        echo "📅 下次计划运行:"
        echo "  • UTC 22:00 (北京时间 06:00)"
        echo "  • UTC 09:00 (北京时间 17:00)"
        echo ""
        echo "🔗 生成的文件:"
        echo "  • GitHub: https://github.com/${{ github.repository }}/blob/main/CC.m3u"
        echo "  • Raw: https://raw.githubusercontent.com/${{ github.repository }}/main/CC.m3u"
        echo ""
        echo "⚙️  配置信息:"
        echo "  • 代理地址: https://smt-proxy.sufern001.workers.dev/"
        echo "  • 脚本文件: scripts/merge_from_proxy.py"
        echo "  • 更新频率: 每天2次 (06:00, 17:00 北京时间)"
        echo ""
        echo "📊 运行状态:"
        if [ -f "CC.m3u" ]; then
          echo "  ✅ CC.m3u 生成成功"
          LINES=$(wc -l < CC.m3u)
          SIZE=$(wc -c < CC.m3u)
          echo "    行数: $LINES"
          echo "    大小: $SIZE 字节"
        else
          echo "  ❌ CC.m3u 生成失败"
        fi
