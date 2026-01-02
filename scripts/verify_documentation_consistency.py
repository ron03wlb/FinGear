"""
驗證文檔一致性

檢查所有文檔中的因子權重配置是否與 config/parameters.yaml 一致
"""

import sys
from pathlib import Path
import yaml
import re

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_config_weights():
    """從配置文件載入權重"""
    config_path = project_root / 'config' / 'parameters.yaml'

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        return config['screening']['factor_weights']


def check_claude_md():
    """檢查 CLAUDE.md"""
    file_path = project_root / 'CLAUDE.md'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        'PE Relative: **30%**': 'PE 估值權重 30%',
        'ROE: 15%, EPS YoY: 15%': 'ROE 和 EPS YoY 各 15%',
        'FCF: 10%': 'FCF 10%',
    }

    results = []
    for pattern, desc in checks.items():
        if pattern in content:
            results.append((True, f"✅ {desc}"))
        else:
            results.append((False, f"❌ {desc}"))

    return results


def check_implementation_md():
    """檢查 docs/Implementation.md"""
    file_path = project_root / 'docs' / 'Implementation.md'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        r"PE相對估值評分 × 0\.30": "偽代碼中 PE 權重 0.30",
        r"ROE評分 × 0\.15": "偽代碼中 ROE 權重 0.15",
        r"\| \*\*PE 相對估值\*\* \| \*\*30%\*\*": "權重配置表格中 PE 30%",
    }

    results = []
    for pattern, desc in checks.items():
        if re.search(pattern, content):
            results.append((True, f"✅ {desc}"))
        else:
            results.append((False, f"❌ {desc}"))

    return results


def check_readme_md():
    """檢查 README.md"""
    file_path = project_root / 'README.md'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        'PE 估值 30%': 'PE 估值 30%',
        'ROE 15%': 'ROE 15%',
    }

    results = []
    for pattern, desc in checks.items():
        if pattern in content:
            results.append((True, f"✅ {desc}"))
        else:
            results.append((False, f"❌ {desc}"))

    return results


def main():
    """主驗證函數"""
    print("=" * 70)
    print("文檔一致性驗證")
    print("=" * 70)

    # 1. 載入配置文件權重
    print("\n📋 配置文件權重 (config/parameters.yaml):")
    print("-" * 70)

    config_weights = load_config_weights()
    total = 0
    for factor, weight in config_weights.items():
        total += weight
        print(f"  {factor:20} : {weight:5.2f} ({weight*100:5.1f}%)")

    print(f"  {'總和':20} : {total:5.2f} ({total*100:5.1f}%)")

    if abs(total - 1.0) < 0.001:
        print("\n✅ 配置文件權重總和正確 (1.00)")
    else:
        print(f"\n❌ 配置文件權重總和錯誤: {total:.4f}")
        return False

    # 2. 檢查各文檔
    all_passed = True

    print("\n\n📄 CLAUDE.md 一致性檢查:")
    print("-" * 70)
    for passed, msg in check_claude_md():
        print(f"  {msg}")
        if not passed:
            all_passed = False

    print("\n\n📄 docs/Implementation.md 一致性檢查:")
    print("-" * 70)
    for passed, msg in check_implementation_md():
        print(f"  {msg}")
        if not passed:
            all_passed = False

    print("\n\n📄 README.md 一致性檢查:")
    print("-" * 70)
    for passed, msg in check_readme_md():
        print(f"  {msg}")
        if not passed:
            all_passed = False

    # 3. 總結
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ 所有文檔一致性檢查通過！")
        print("=" * 70)
        return True
    else:
        print("❌ 部分文檔檢查失敗，請手動檢查並修正")
        print("=" * 70)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
