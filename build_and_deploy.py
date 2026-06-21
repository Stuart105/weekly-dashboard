"""一键构建 + 部署 — 方案A 每周更新
用法: python3 build_and_deploy.py [Excel文件路径] [提交信息]
"""
import subprocess, sys, shutil, os
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
excel = sys.argv[1] if len(sys.argv) > 1 else None
msg = sys.argv[2] if len(sys.argv) > 2 else f"W{datetime.now().strftime('%W')} 周报更新"

if excel:
    print(f"📥 解析 Excel: {excel}")
    ret = subprocess.run([sys.executable, 'extract_data.py', excel], cwd=BASE)
    if ret.returncode != 0:
        print("❌ 数据提取失败")
        sys.exit(1)

print("🔨 构建 Dashboard...")
subprocess.run([sys.executable, 'build_dashboard.py'], cwd=BASE)
subprocess.run([sys.executable, 'deepseek_inject.py'], cwd=BASE)

# 复制为 index.html
shutil.copy(BASE / 'weekly-dashboard.html', BASE / 'index.html')

print(f"📦 提交: {msg}")
subprocess.run(['git', 'add', '-A'], cwd=BASE)
subprocess.run(['git', 'commit', '-m', msg], cwd=BASE)
subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE)
print("✅ 完成！GitHub Pages 自动部署中...")
