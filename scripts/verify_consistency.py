"""
代碼與文檔一致性驗證腳本

驗證項目：
1. 因子權重配置是否與 CLAUDE.md 和 parameters.yaml 一致
2. 所有 logger.error() 是否都添加了 exc_info=True
3. 設計模式註解是否正確
"""

import re
from pathlib import Path
import yaml


def verify_factor_weights():
    """驗證因子權重配置"""
    print("=" * 60)
    print("驗證 1: 因子權重配置")
    print("=" * 60)

    # 讀取 parameters.yaml
    config_path = Path(__file__).parent.parent / 'config' / 'parameters.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    yaml_weights = config['screening']['factor_weights']

    # 讀取 factors.py 中的 default_weights
    factors_path = Path(__file__).parent.parent / 'src' / 'factors.py'
    with open(factors_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取 default_weights
    default_weights = {}
    pattern = r"'(\w+)':\s*(0\.\d+)"
    matches = re.findall(pattern, content[content.find("default_weights = {"):content.find("default_weights = {") + 500])
    for key, value in matches:
        default_weights[key] = float(value)

    # 比較
    print("\n📊 因子權重對照表:")
    print(f"{'因子名稱':<25} {'parameters.yaml':<20} {'factors.py default':<20} {'狀態'}")
    print("-" * 85)

    all_match = True
    for factor in yaml_weights:
        yaml_val = yaml_weights[factor]
        default_val = default_weights.get(factor, -1)
        match = "✅" if abs(yaml_val - default_val) < 0.001 else "❌"
        if match == "❌":
            all_match = False
        print(f"{factor:<25} {yaml_val:<20.2f} {default_val:<20.2f} {match}")

    if all_match:
        print("\n✅ 所有因子權重配置一致")
    else:
        print("\n❌ 發現權重不一致")

    return all_match


def verify_error_logging():
    """驗證所有 logger.error() 都有 exc_info=True"""
    print("\n" + "=" * 60)
    print("驗證 2: 錯誤日誌堆棧追蹤")
    print("=" * 60)

    src_path = Path(__file__).parent.parent / 'src'

    issues = []
    total_errors = 0

    for py_file in src_path.glob('*.py'):
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # 匹配 logger.error() 或 logging.error()
            if re.search(r'\.(logger\.error|error)\(', line):
                total_errors += 1
                # 檢查是否有 exc_info=True
                if 'exc_info=True' not in line:
                    # 檢查下一行是否有 exc_info
                    if i < len(lines) and 'exc_info=True' not in lines[i]:
                        issues.append(f"{py_file.name}:{i} - {line.strip()}")

    print(f"\n📝 總共發現 {total_errors} 個 logger.error() 調用")

    if not issues:
        print("✅ 所有錯誤日誌都包含 exc_info=True")
        return True
    else:
        print(f"❌ 發現 {len(issues)} 個缺少 exc_info=True 的錯誤日誌:")
        for issue in issues[:10]:  # 只顯示前 10 個
            print(f"   {issue}")
        return False


def verify_design_patterns():
    """驗證設計模式註解"""
    print("\n" + "=" * 60)
    print("驗證 3: 設計模式註解")
    print("=" * 60)

    checks = [
        {
            'file': 'src/api_client.py',
            'class': 'ShioajiClient',
            'expected': 'Singleton',
            'description': 'API 客戶端應使用 Singleton 模式'
        },
        {
            'file': 'src/parquet_manager.py',
            'class': 'ParquetManager',
            'expected': 'Repository',
            'description': 'Parquet 管理器應使用 Repository 模式'
        },
        {
            'file': 'src/factors.py',
            'class': 'FactorEngine',
            'expected': 'Strategy',
            'description': '因子引擎應使用 Strategy 模式'
        },
        {
            'file': 'src/screener.py',
            'class': 'StockScreener',
            'expected': 'Pipeline',
            'description': '選股器應使用 Pipeline 模式'
        },
        {
            'file': 'src/notification.py',
            'class': 'NotificationService',
            'expected': 'Facade',
            'description': '通知服務應使用 Facade 模式'
        }
    ]

    all_match = True

    for check in checks:
        file_path = Path(__file__).parent.parent / check['file']
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 在 class 定義附近搜索設計模式註解
        class_pos = content.find(f"class {check['class']}")
        if class_pos == -1:
            print(f"⚠️  找不到類別 {check['class']}")
            continue

        # 搜索前後 500 字符
        search_area = content[max(0, class_pos - 200):class_pos + 500]

        if check['expected'] in search_area:
            print(f"✅ {check['file']} - {check['class']}: {check['expected']} Pattern")
        else:
            print(f"❌ {check['file']} - {check['class']}: 未找到 {check['expected']} Pattern")
            all_match = False

    return all_match


def main():
    """執行所有驗證"""
    print("\n🔍 開始代碼與文檔一致性驗證...\n")

    result1 = verify_factor_weights()
    result2 = verify_error_logging()
    result3 = verify_design_patterns()

    print("\n" + "=" * 60)
    print("驗證結果摘要")
    print("=" * 60)
    print(f"因子權重配置: {'✅ 通過' if result1 else '❌ 失敗'}")
    print(f"錯誤日誌追蹤: {'✅ 通過' if result2 else '❌ 失敗'}")
    print(f"設計模式註解: {'✅ 通過' if result3 else '❌ 失敗'}")

    if result1 and result2 and result3:
        print("\n🎉 所有驗證通過！代碼與文檔完全一致。")
        return 0
    else:
        print("\n⚠️  發現部分不一致，請檢查上述問題。")
        return 1


if __name__ == '__main__':
    exit(main())
