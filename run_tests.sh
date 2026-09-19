#!/bin/bash
# 激活项目内虚拟环境并运行测试
cd "$(dirname "$0")"
source .venv/bin/activate

echo "========================================="
echo " 正在运行餐饮系统自动化测试套件 (Pytest) "
echo "========================================="

python -m pytest restaurant_test_sdk/tests/ -v --alluredir=restaurant_test_sdk/allure-results --clean-alluredir

echo ""
echo "测试执行完毕！"
echo "如需查看 Allure 报告，请运行: allure serve restaurant_test_sdk/allure-results"
