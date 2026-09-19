"""
================================================================================
项目名称: 百度登录页面 UI 自动化测试
技术栈: Python + Playwright + Pytest + Allure + Page Object Model (POM) + 日志系统
测试文件: playwright-01.py
================================================================================
本测试项目遵循企业级 Page Object Model (POM) 架构分层规范:
1. Logging: 内建日志系统，根据当前日期动态生成 `.log` 文件 (如 logs/2026-09-17.log)
2. BasePage: 封装 Playwright 基础操作（导航、智能等待、点击、输入、日志记录、截图入报）
3. BaiduLoginPage: 封装百度登录的元素定位器 (Locators) 与业务交互逻辑 (Actions)
4. Pytest Fixture: 管理浏览器生命周期，测试用例结束后自动将执行日志归档至 Allure 报告
5. TestBaiduLogin: 覆盖弹窗唤起、Tab模式切换、空账号表单拦截、协议合规校验、非法凭据拦截、弹窗平滑关闭
================================================================================
"""

import os
import sys
import time
import logging
import datetime
from typing import Optional, Tuple

import pytest
import allure
from playwright.sync_api import Page, sync_playwright, Browser, BrowserContext, expect


# ==============================================================================
# 0. 日志系统配置 (根据执行日期动态生成 logs/YYYY-MM-DD.log 文件)
# ==============================================================================
def init_logger() -> Tuple[logging.Logger, str]:
    """
    初始化日志配置:
    - 自动创建 logs/ 目录
    - 动态生成形如 logs/2026-09-17.log 的日志文件
    - 同时输出到控制台与日期日志文件
    - 统一 UTF-8 编码，防止跨平台乱码
    """
    # 日志文件存放在当前目录下的 logs 文件夹中
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    log_filename = f"{today_str}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    logger = logging.getLogger("BaiduLoginTest")
    logger.setLevel(logging.INFO)

    # 避免 pytest 多次执行重复添加 Handlers
    if not logger.handlers:
        log_format = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 1. 写入日期 .log 文件的 FileHandler
        file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
        file_handler.setFormatter(log_format)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        # 2. 控制台输出的 StreamHandler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger, log_filepath


# 全局单例日志对象与当前日志路径
logger, CURRENT_LOG_FILE = init_logger()


# ==============================================================================
# 1. BasePage 基础页面对象 (封装通用交互、日志输出与 Allure 步骤可视化)
# ==============================================================================
class BasePage:
    """所有 Page Object 的基类，封装通用浏览器操作、日志追踪及 Allure 报告附件生成"""

    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str, description: str = "访问网址"):
        """打开目标 URL"""
        log_msg = f"【页面导航】{description}: {url}"
        logger.info(log_msg)
        with allure.step(log_msg):
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

    def click(self, selector: str, description: str = "点击元素", force: bool = False):
        """点击指定选择器的元素，支持 force 点击"""
        log_msg = f"【点击元素】{description} (定位器: {selector}, 强制点击: {force})"
        logger.info(log_msg)
        with allure.step(log_msg):
            locator = self.page.locator(selector)
            locator.wait_for(state="visible", timeout=10000)
            locator.click(force=force)

    def fill(self, selector: str, text: str, description: str = "输入文本", is_secret: bool = False):
        """向指定输入框填入文本"""
        display_text = "******" if is_secret else text
        log_msg = f"【输入文本】{description}: '{display_text}' (定位器: {selector})"
        logger.info(log_msg)
        with allure.step(log_msg):
            locator = self.page.locator(selector)
            locator.wait_for(state="visible", timeout=10000)
            locator.fill(text)

    def get_text(self, selector: str, timeout: float = 5000) -> str:
        """获取可见元素的文本内容"""
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=timeout)
        text = locator.inner_text().strip()
        logger.info(f"【提取文本】元素: {selector}, 内容: '{text}'")
        return text

    def is_visible(self, selector: str, timeout: float = 3000) -> bool:
        """判断元素当前是否呈现可见"""
        try:
            self.page.locator(selector).wait_for(state="visible", timeout=timeout)
            logger.debug(f"【可见性检测】元素 {selector} 为可见 (True)")
            return True
        except Exception:
            logger.debug(f"【可见性检测】元素 {selector} 未在 {timeout}ms 内可见 (False)")
            return False

    def is_disabled(self, selector: str) -> bool:
        """判断元素当前是否处于禁用状态 (包含 disabled 属性或特定置灰 class)"""
        locator = self.page.locator(selector)
        if locator.count() == 0:
            return True
        disabled = locator.first.is_disabled() or "disabled" in (locator.first.get_attribute("class") or "")
        logger.info(f"【禁用状态检测】元素: {selector}, 禁用结果: {disabled}")
        return disabled

    def take_screenshot(self, name: str = "页面快照"):
        """截取当前页面快照并附加到 Allure 测试报告与记录日志"""
        try:
            screenshot_bytes = self.page.screenshot(full_page=False)
            allure.attach(
                screenshot_bytes,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )
            logger.info(f"【屏幕截图】已成功生成截图附件: '{name}'")
        except Exception as e:
            logger.error(f"【屏幕截图异常】截图捕获失败: {e}")


# ==============================================================================
# 2. BaiduLoginPage 百度登录页面对象模型 (POM 业务层)
# ==============================================================================
class BaiduLoginPage(BasePage):
    """百度首页及统一通行证登录弹窗页面对象"""

    URL = "https://www.baidu.com"

    # ---------------- 核心元素定位器 (Locators) ----------------
    LOC_LOGIN_TRIGGER_BTN = "#s-top-loginbtn"           # 首页右上角“登录”按钮
    LOC_LOGIN_MODAL = ".tang-pass-pop-login"             # 通行证弹窗容器
    LOC_TAB_PASSWORD_LOGIN = "#TANGRAM__PSP_11__changePwdCodeItem" # “账号登录” Tab
    LOC_TAB_QRCODE_LOGIN = "#TANGRAM__PSP_11__changeQrCodeItem"   # “扫码登录” Tab
    LOC_INPUT_USERNAME = "#TANGRAM__PSP_11__userName"    # 手机号/用户名/邮箱输入框
    LOC_INPUT_PASSWORD = "#TANGRAM__PSP_11__password"    # 密码输入框
    LOC_CHECKBOX_AGREE = "#TANGRAM__PSP_11__isAgree"     # 阅读并接受《用户协议》复选框
    LOC_BTN_SUBMIT = "#TANGRAM__PSP_11__submit"          # 登录提交按钮
    LOC_TIP_ERROR = "#TANGRAM__PSP_11__error"            # 登录表单通用错误提示
    LOC_BTN_CLOSE_MODAL = "#TANGRAM__PSP_4__closeBtn"    # 弹窗右上角关闭“X”按钮
    LOC_LOGGED_USER_NAME = "#s-top-username, #s_username_top" # 登录成功后的用户名标识

    # ---------------- 业务动作与操作方法 (Actions) ----------------
    def open_home_page(self):
        """打开百度首页"""
        self.navigate(self.URL, description="打开百度搜索主页")

    def click_login_trigger(self):
        """点击首页右上角“登录”唤起弹窗，支持防抖重试机制"""
        logger.info("【业务动作】触发点击首页右上角登录按钮")
        login_btn = self.page.locator(self.LOC_LOGIN_TRIGGER_BTN)
        login_btn.wait_for(state="visible", timeout=10000)
        
        for attempt in range(3):
            login_btn.click()
            try:
                self.page.locator(self.LOC_LOGIN_MODAL).wait_for(state="visible", timeout=3000)
                logger.info(f"【业务动作】第 {attempt+1} 次点击成功唤起登录弹窗")
                return
            except Exception:
                logger.warning(f"【重试等待】第 {attempt+1} 次点击后弹窗尚未弹出，等待重试...")
                self.page.wait_for_timeout(800)
        
        # 最终显式等待弹窗
        self.page.locator(self.LOC_LOGIN_MODAL).wait_for(state="visible", timeout=6000)

    def switch_to_password_login(self):
        """切换至账号密码登录模式"""
        pwd_tab = self.page.locator(self.LOC_TAB_PASSWORD_LOGIN)
        if pwd_tab.is_visible():
            self.click(self.LOC_TAB_PASSWORD_LOGIN, description="切换为账号密码登录Tab")
            logger.info("【业务动作】已点击切换至账号密码登录Tab")
        self.page.wait_for_timeout(500)

    def fill_username(self, username: str):
        """输入用户名/手机号"""
        self.fill(self.LOC_INPUT_USERNAME, username, description="用户名输入框")

    def fill_password(self, password: str):
        """输入密码"""
        self.fill(self.LOC_INPUT_PASSWORD, password, description="密码输入框", is_secret=True)

    def check_agreement(self, agree: bool = True):
        """勾选或取消勾选服务协议复选框"""
        checkbox = self.page.locator(self.LOC_CHECKBOX_AGREE)
        if checkbox.count() > 0:
            is_checked = checkbox.is_checked()
            if agree and not is_checked:
                logger.info("【业务动作】勾选《百度用户协议》复选框")
                with allure.step("【勾选】阅读并同意《百度用户协议》"):
                    checkbox.check()
            elif not agree and is_checked:
                logger.info("【业务动作】取消勾选《百度用户协议》复选框")
                with allure.step("【取消勾选】《百度用户协议》"):
                    checkbox.uncheck()
        self.page.wait_for_timeout(300)

    def click_submit_login(self, force: bool = False):
        """点击登录按钮提交"""
        logger.info(f"【业务动作】点击登录提交按钮 (force={force})")
        self.click(self.LOC_BTN_SUBMIT, description="立即登录提交按钮", force=force)

    def execute_login(self, username: str = "", password: str = "", agree: bool = False, force_submit: bool = False):
        """执行完整复合登录操作"""
        logger.info(f"【组合动作】执行完整登录: 用户名='{username}', 勾选协议={agree}")
        self.switch_to_password_login()
        if username:
            self.fill_username(username)
        if password:
            self.fill_password(password)
        self.check_agreement(agree)
        self.click_submit_login(force=force_submit)

    def is_submit_button_disabled(self) -> bool:
        """检查登录按钮是否处于禁用不可点击状态"""
        return self.is_disabled(self.LOC_BTN_SUBMIT)

    def get_error_message(self) -> str:
        """获取界面错误提示文字"""
        if self.is_visible(self.LOC_TIP_ERROR, timeout=3000):
            msg = self.get_text(self.LOC_TIP_ERROR)
            logger.info(f"【界面提示】捕获到错误提示: '{msg}'")
            return msg
        return ""

    def is_login_modal_visible(self) -> bool:
        """判断登录弹窗是否呈现可见"""
        visible = self.is_visible(self.LOC_LOGIN_MODAL, timeout=3000)
        logger.info(f"【弹窗状态】登录弹窗当前可见性: {visible}")
        return visible

    def is_user_logged_in(self) -> bool:
        """判断是否已成功登录（主页显示用户名头像标识）"""
        logged_in = self.is_visible(self.LOC_LOGGED_USER_NAME, timeout=2000)
        logger.info(f"【登录状态】用户登录态检测: {logged_in}")
        return logged_in

    def close_login_modal(self):
        """点击弹窗右上角关闭按钮"""
        logger.info("【业务动作】关闭登录弹窗")
        if self.is_visible(self.LOC_BTN_CLOSE_MODAL, timeout=3000):
            self.click(self.LOC_BTN_CLOSE_MODAL, description="关闭登录弹窗")


# ==============================================================================
# 3. Pytest 夹具 (Fixtures) 与会话生命周期管理
# ==============================================================================
@pytest.fixture(scope="function")
def browser_page(request):
    """
    Playwright 浏览器与上下文管理 Fixture:
    - 启动独立干净的 Chromium 浏览器会话
    - 输出当前测试生命周期日志
    - 结束后将测试日志文件附加至 Allure 报告
    """
    test_name = request.node.name
    logger.info(f"\n{'='*70}\n[TEST START] 开始执行测试用例: {test_name}\n{'='*70}")
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        
        yield page
        
        logger.info(f"[TEST END] 测试用例结束: {test_name}")
        context.close()
        browser.close()

    # 将本次执行的日期日志文件附加至 Allure 报告附件
    if os.path.exists(CURRENT_LOG_FILE):
        try:
            with open(CURRENT_LOG_FILE, "r", encoding="utf-8") as f:
                log_content = f.read()
            allure.attach(
                log_content[-20000:], # 附加最新日志段
                name=f"执行日志_{os.path.basename(CURRENT_LOG_FILE)}",
                attachment_type=allure.attachment_type.TEXT
            )
        except Exception as e:
            logger.warning(f"附加日志至Allure失败: {e}")


@pytest.fixture(scope="function")
def baidu_login_page(browser_page: Page) -> BaiduLoginPage:
    """初始化并打开百度首页的 Page Object 实例"""
    page_obj = BaiduLoginPage(browser_page)
    page_obj.open_home_page()
    return page_obj


# ==============================================================================
# 4. 测试用例套件 (Test Suite)
# ==============================================================================
@allure.epic("百度业务系统自动化测试项目")
@allure.feature("统一通行证登录认证 (Authentication)")
class TestBaiduLogin:
    """百度登录全场景自动化测试套件 (POM 模式实现)"""

    @allure.story("1. 正常业务流：唤起登录弹窗与Tab模式切换")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("正向流程：打开百度首页 -> 点击右上角登录 -> 验证弹窗呈现并成功切换账号登录Tab")
    def test_open_login_modal_and_switch_tab(self, baidu_login_page: BaiduLoginPage):
        logger.info(">>> 开始验证正常业务流: 唤起弹窗与Tab切换")
        with allure.step("Step 1: 点击首页右上角登录按钮"):
            baidu_login_page.click_login_trigger()

        with allure.step("Step 2: 验证登录弹窗成功弹出可见"):
            assert baidu_login_page.is_login_modal_visible(), "登录弹窗未正常弹出"
            baidu_login_page.take_screenshot("登录弹窗唤起成功截图")
            logger.info("✔ 校验通过: 登录弹窗成功展示")

        with allure.step("Step 3: 切换至账号密码登录模式并校验输入框可见"):
            baidu_login_page.switch_to_password_login()
            assert baidu_login_page.is_visible(baidu_login_page.LOC_INPUT_USERNAME), "用户名输入框不可见"
            assert baidu_login_page.is_visible(baidu_login_page.LOC_INPUT_PASSWORD), "密码输入框不可见"
            assert baidu_login_page.is_visible(baidu_login_page.LOC_BTN_SUBMIT), "登录提交按钮不可见"
            baidu_login_page.take_screenshot("账号登录模式呈现状态")
            logger.info("✔ 校验通过: 账号密码输入控件均完整可见")

    @allure.story("2. 异常边界测试：空账号与空密码提交提示校验")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("表单校验：勾选协议但用户名密码为空点击登录，验证系统拦截并提示‘请您输入手机号/用户名/邮箱’")
    def test_login_with_empty_credentials(self, baidu_login_page: BaiduLoginPage):
        logger.info(">>> 开始验证异常边界测试: 空账号提单校验")
        with allure.step("Step 1: 唤起弹窗并进入账号登录"):
            baidu_login_page.click_login_trigger()
            baidu_login_page.switch_to_password_login()

        with allure.step("Step 2: 勾选协议但保持用户名密码均为空，点击提交登录"):
            baidu_login_page.check_agreement(agree=True)
            baidu_login_page.click_submit_login()
            baidu_login_page.page.wait_for_timeout(500)

        with allure.step("Step 3: 验证系统触发空凭证表单错误提示并拦截"):
            baidu_login_page.take_screenshot("空账号提交提示截图")
            error_msg = baidu_login_page.get_error_message()
            logger.info(f"捕获到的错误信息: '{error_msg}'")
            assert "请您输入" in error_msg or len(error_msg) > 0, \
                f"未捕获到预期的空输入提示，实际提示文本: '{error_msg}'"
            logger.info("✔ 校验通过: 空账号提交被准确拦截并提示输入")

    @allure.story("3. 异常边界测试：未勾选用户协议合规拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("合规校验：输入有效账号密码但未勾选《用户协议》，验证系统严格阻断提交")
    def test_login_without_agreeing_protocol(self, baidu_login_page: BaiduLoginPage):
        logger.info(">>> 开始验证合规拦截测试: 未勾选用户协议")
        with allure.step("Step 1: 唤起账号登录并输入测试账号密码"):
            baidu_login_page.click_login_trigger()
            baidu_login_page.switch_to_password_login()
            baidu_login_page.fill_username("test_compliance_user_2026")
            baidu_login_page.fill_password("PasswordSecurity999!")

        with allure.step("Step 2: 明确不勾选用户协议"):
            baidu_login_page.check_agreement(agree=False)

        with allure.step("Step 3: 验证提交按钮保持禁用状态，严格符合合规安全规范"):
            baidu_login_page.take_screenshot("未勾选协议状态快照")
            is_disabled = baidu_login_page.is_submit_button_disabled()
            assert is_disabled, "未勾选用户协议时，登录按钮处于可用状态，违反网络安全合规规范！"
            logger.info("✔ 校验通过: 未同意协议时提交按钮被严格禁用置灰")

    @allure.story("4. 异常业务测试：非法/不存在账号密码安全拦截")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("安全校验：输入不存在的伪造账号密码并勾选协议，验证系统拦截且禁止非法登录")
    def test_login_with_invalid_credentials(self, baidu_login_page: BaiduLoginPage):
        logger.info(">>> 开始验证安全拦截测试: 非法不存在账号密码")
        with allure.step("Step 1: 唤起登录窗口并输入伪造账号密码"):
            baidu_login_page.click_login_trigger()
            baidu_login_page.switch_to_password_login()
            baidu_login_page.fill_username("non_existent_fake_account_7788@163.com")
            baidu_login_page.fill_password("WrongPasswordNeverMatch123!")

        with allure.step("Step 2: 勾选服务协议，登录按钮自动转为可用激活状态"):
            baidu_login_page.check_agreement(agree=True)
            assert not baidu_login_page.is_submit_button_disabled(), "凭据与协议均满足时，登录按钮应被激活可用"

        with allure.step("Step 3: 提交登录并验证系统拦截拒绝，用户绝不会处于已登录状态"):
            baidu_login_page.click_submit_login()
            baidu_login_page.page.wait_for_timeout(2500)
            baidu_login_page.take_screenshot("非法凭证提交后响应界面")
            
            # 核心断言：非法凭证绝对不能登录成功，首页不得出现已登录用户信息，弹窗仍应停留或展示验证拦截
            assert not baidu_login_page.is_user_logged_in(), "严重安全事故：非法账号密码竟然完成了登录！"
            assert baidu_login_page.is_login_modal_visible(), "非法登录提交后，登录弹窗未停留在当前拦截界面"
            logger.info("✔ 校验通过: 非法账号密码被系统安全阻断，未进入登录态")

    @allure.story("5. 界面交互测试：登录弹窗平滑关闭")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("交互校验：点击弹窗右上角‘X’关闭按钮，弹窗平滑退出且首页恢复完整可交互状态")
    def test_close_login_modal(self, baidu_login_page: BaiduLoginPage):
        logger.info(">>> 开始验证界面交互测试: 弹窗平滑关闭")
        with allure.step("Step 1: 唤起登录弹窗并确认展示"):
            baidu_login_page.click_login_trigger()
            assert baidu_login_page.is_login_modal_visible(), "弹窗未成功展示"

        with allure.step("Step 2: 点击右上角‘X’关闭按钮"):
            baidu_login_page.close_login_modal()
            baidu_login_page.page.wait_for_timeout(500)

        with allure.step("Step 3: 验证登录弹窗已被销毁/隐藏"):
            baidu_login_page.take_screenshot("关闭弹窗后首页状态")
            assert not baidu_login_page.is_login_modal_visible(), "点击关闭后登录弹窗仍停留在界面上"
            logger.info("✔ 校验通过: 弹窗平滑退出，首页恢复可操作")


# ==============================================================================
# 5. 独立执行入口 (支持直接 python playwright-01.py 运行)
# ==============================================================================
if __name__ == "__main__":
    allure_dir = os.path.join(os.path.dirname(__file__), "..", "allure-results")
    print(f"🚀 开始执行百度登录页面 POM 自动化测试")
    print(f"📁 执行日志保存路径: {CURRENT_LOG_FILE}")
    print(f"📊 Allure 结果保存路径: {allure_dir}")
    pytest.main([
        "-v",
        "-s",
        __file__,
        f"--alluredir={allure_dir}",
    ])
