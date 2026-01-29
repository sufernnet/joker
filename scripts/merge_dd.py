name: 测试DD.m3u生成

on:
  workflow_dispatch:

jobs:
  test-dd:
    runs-on: ubuntu-latest
    
    steps:
    - name: 📥 检出代码
      uses: actions/checkout@v3
    
    - name: 🐍 设置Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: 📦 安装依赖
      run: pip install requests
    
    - name: 🚀 运行调试脚本
      run: |
        echo "=== 当前目录 ==="
        pwd
        ls -la
        
        echo -e "\n=== 运行脚本 ==="
        python scripts/merge_dd.py
        
        echo -e "\n=== 检查文件 ==="
        if [ -f "DD.m3u" ]; then
          echo "✅ DD.m3u 存在"
          echo "大小: $(wc -c < DD.m3u) 字节"
          echo "行数: $(wc -l < DD.m3u)"
          echo -e "\n前20行:"
          head -20 DD.m3u
        else
          echo "❌ DD.m3u 不存在"
          echo "当前目录内容:"
          ls -la
        fi
    
    - name: 📤 强制提交测试
      if: success()
      run: |
        echo "=== 提交测试 ==="
        
        if [ -f "DD.m3u" ]; then
          # 配置Git
          git config user.email "test@example.com"
          git config user.name "Test Bot"
          
          # 强制添加和提交
          git add -f DD.m3u
          git commit -m "🤖 测试DD.m3u生成"
          
          # 推送
          git push origin main
          echo "✅ 提交成功"
        else
          echo "❌ 没有DD.m3u文件可提交"
        fi
