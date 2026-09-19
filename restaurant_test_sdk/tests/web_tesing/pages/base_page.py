# -*- coding: utf-8 -*-
"""
页面对象模型 (POM) 基类: BasePage
封装所有通用 WebDriver 显式等待、交互动作与元素定位能力
"""
import time
from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoAlertPresentException


class BasePage:
    """所有 Page 对象的基类"""

    def __init__(self, driver: WebDriver, timeout: int = 10):
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(self.driver, timeout)

    def open(self, url: str):
        """导航至指定 URL"""
        self.driver.get(url)

    def get_title(self) -> str:
        """获取当前页面 Title"""
        return self.driver.title

    def find_element(self, by, locator: str, timeout: Optional[int] = None) -> WebElement:
        """显式等待并查找单个可见元素"""
        wait = WebDriverWait(self.driver, timeout if timeout is not None else self.timeout)
        return wait.until(EC.visibility_of_element_located((by, locator)))

    def find_elements(self, by, locator: str, timeout: Optional[int] = None) -> List[WebElement]:
        """显式等待并查找元素列表"""
        wait = WebDriverWait(self.driver, timeout if timeout is not None else self.timeout)
        try:
            wait.until(EC.presence_of_all_elements_located((by, locator)))
            return self.driver.find_elements(by, locator)
        except TimeoutException:
            return []

    def click(self, by, locator: str, timeout: Optional[int] = None):
        """等待元素可点击后点击"""
        wait = WebDriverWait(self.driver, timeout if timeout is not None else self.timeout)
        element = wait.until(EC.element_to_be_clickable((by, locator)))
        element.click()
        time.sleep(0.35)

    def type_text(self, by, locator: str, text: str, clear_first: bool = True):
        """等待输入框可见后填入文本"""
        element = self.find_element(by, locator)
        if clear_first:
            element.clear()
        element.send_keys(text)
        time.sleep(0.2)

    def get_text(self, by, locator: str) -> str:
        """获取元素文本内容"""
        return self.find_element(by, locator).text.strip()

    def select_by_value(self, by, locator: str, value: str):
        """选择下拉框指定的 option value"""
        element = self.find_element(by, locator)
        select = Select(element)
        select.select_by_value(value)
        time.sleep(0.3)

    def is_displayed(self, by, locator: str, timeout: int = 3) -> bool:
        """判断元素是否在页面上展示"""
        try:
            return self.find_element(by, locator, timeout=timeout).is_displayed()
        except (TimeoutException, NoSuchElementException):
            return False

    def execute_script(self, script: str, *args):
        """在当前页面上下文执行 JavaScript 代码"""
        return self.driver.execute_script(script, *args)

    def accept_alert(self, timeout: int = 3) -> Optional[str]:
        """处理可能弹出的 window.alert 弹窗并返回提示文本"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            alert = wait.until(EC.alert_is_present())
            text = alert.text
            alert.accept()
            return text
        except (TimeoutException, NoAlertPresentException):
            return None

    def take_screenshot_as_png(self) -> bytes:
        """获取当前页面截图的 PNG 二进制数据 (用于 Allure 报告附件)"""
        return self.driver.get_screenshot_as_png()
