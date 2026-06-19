"""
全量构建脚本 — 构建dashboard + DeepSeek AI实时分析注入

用法: python3 build_all.py
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent

print("=" * 50)
print("Step 1: 构建 dashboard...")
print("=" * 50)
ret = subprocess.run([sys.executable, 'build_dashboard.py'], cwd=BASE, capture_output=True, text=True)
if ret.returncode != 0:
    print(f"❌ 构建失败:\n{ret.stderr}")
    sys.exit(1)
print(ret.stdout.strip())

print("=" * 50)
print("Step 2: 注入 DeepSeek AI 实时分析...")
print("=" * 50)
ret = subprocess.run([sys.executable, 'deepseek_inject.py'], cwd=BASE, capture_output=True, text=True)
print(ret.stdout.strip())
if ret.returncode != 0:
    print(f"⚠️  注入异常: {ret.stderr}")

print("=" * 50)
print("✅ 构建完成")
print("=" * 50)
