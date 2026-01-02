"""
验证因子权重配置

用途：检查 config/parameters.yaml 中的因子权重是否正确配置
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from src.factors import FactorEngine


def verify_weights():
    """验证因子权重配置"""
    print("=" * 60)
    print("因子权重配置验证")
    print("=" * 60)

    # 1. 读取配置文件
    config_path = project_root / 'config' / 'parameters.yaml'

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            weights = config.get('screening', {}).get('factor_weights', {})
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False

    # 2. 显示权重配置
    print("\n📊 当前因子权重配置：")
    print("-" * 60)

    total_weight = 0
    for factor, weight in weights.items():
        total_weight += weight
        percentage = weight * 100
        bar = "█" * int(percentage / 2)
        print(f"{factor:20} | {weight:.2f} ({percentage:5.1f}%) | {bar}")

    print("-" * 60)
    print(f"{'总和':20} | {total_weight:.2f} ({total_weight*100:5.1f}%)")
    print()

    # 3. 验证总和
    if abs(total_weight - 1.0) < 0.001:
        print("✅ 权重总和验证通过 (1.00)")
    else:
        print(f"❌ 权重总和验证失败: {total_weight:.4f} (应为 1.00)")
        return False

    # 4. 验证 FactorEngine 是否正确加载
    print("\n🔧 测试 FactorEngine 加载配置...")

    try:
        # 创建模拟的 data_manager（仅用于测试权重加载）
        class MockDataManager:
            pass

        engine = FactorEngine(data_manager=MockDataManager())
        loaded_weights = engine.weights

        print("\n📥 FactorEngine 加载的权重：")
        print("-" * 60)

        for factor, weight in loaded_weights.items():
            percentage = weight * 100
            expected = weights.get(factor, 0)
            match = "✓" if abs(weight - expected) < 0.001 else "✗"
            print(f"{match} {factor:20} | {weight:.2f} ({percentage:5.1f}%)")

        print("-" * 60)
        print("\n✅ FactorEngine 配置加载成功！")

    except Exception as e:
        print(f"❌ FactorEngine 加载失败: {e}")
        return False

    # 5. 重点检查 PE 估值权重
    pe_weight = weights.get('pe_relative', 0)
    print(f"\n🎯 PE 相对估值权重: {pe_weight:.2f} ({pe_weight*100:.0f}%)")

    if pe_weight == 0.30:
        print("✅ PE 估值权重已正确设置为 30%")
    else:
        print(f"⚠️  PE 估值权重为 {pe_weight*100:.0f}%，预期为 30%")

    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)

    return True


if __name__ == '__main__':
    success = verify_weights()
    sys.exit(0 if success else 1)
