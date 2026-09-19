# -*- coding: utf-8 -*-
"""
Web UI 自动化测试 Pytest 共享 Fixture (conftest.py)
配置 Chrome Headless 模式与失败自动截图钩子
"""
import os
import sys
import pytest
import allure
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 将项目根目录添加进 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from restaurant_test_sdk.tests.web_tesing.pages.dashboard_page import DashboardPage


def pytest_addoption(parser):
    """支持命令行参数切换有头/无头模式"""
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="以无头模式运行 Chrome 浏览器 (默认关闭，直接弹出真实 Chrome 窗口)"
    )


@pytest.fixture(scope="function")
def driver(request):
    """初始化并管理 Chrome WebDriver 实例 (默认调起真实 Chrome 浏览器窗口)"""
    is_headless = request.config.getoption("--headless")

    options = Options()
    if is_headless:
        # 无头模式 (后台静默执行)
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    else:
        # 有头模式 (调起真实 Chrome 浏览器窗口在桌面呈现自动化操作)
        options.add_argument("--start-maximized")
        # 移除自动化受控黄色/信息横条提示
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1600,1000")
    options.add_argument("--allow-file-access-from-files")

    driver_instance = webdriver.Chrome(options=options)
    driver_instance.implicitly_wait(3)

    if not is_headless:
        try:
            driver_instance.maximize_window()
        except Exception:
            pass

    yield driver_instance

    # 测试结束退出浏览器
    try:
        driver_instance.quit()
    except Exception:
        pass


@pytest.fixture(scope="function")
def dashboard_page(driver):
    """提供初始化好并已打开目标看板页面的 DashboardPage 实例"""
    page = DashboardPage(driver)
    page.load()
    return page


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """测试失败时自动捕获页面截图并上传至 Allure 报告"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver", None)
        if driver:
            try:
                screenshot = driver.get_screenshot_as_png()
                allure.attach(
                    screenshot,
                    name=f"Failure_Screenshot_{item.name}",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception:
                pass
