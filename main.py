import os
import time
import sys
import requests
import smtplib
import zipfile # 新增：用于打包截图
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ===================== 读取环境变量配置 =====================
USERNAME = os.environ.get("CX_USERNAME")
PASSWORD = os.environ.get("CX_PASSWORD")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.qq.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 465))
EMAIL_ACCOUNT = os.environ.get("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
WXPUSHER_SPT = os.environ.get("WXPUSHER_SPT")


# ===================== 推送逻辑 (复刻 ZDM) =====================
def build_html_message(tasks_summary):
    """将抓取到的数据渲染为类似 ZDM 的 HTML 表格"""
    html = "<h3>📘 学习通作业与考试监控汇总</h3>"
    html += "<table border='1' style='border-collapse: collapse; width: 100%; text-align: left;'>"
    html += "<tr style='background-color: #f2f2f2;'><th width='30%'>课程名称</th><th width='35%'>未交作业</th><th width='35%'>待考考试</th></tr>"

    has_tasks = False
    for course, tasks in tasks_summary.items():
        zy_list = "<br>".join(tasks["作业"]) if tasks["作业"] else "无"
        ks_list = "<br>".join(tasks["考试"]) if tasks["考试"] else "无"

        if tasks["作业"] or tasks["考试"]:
            has_tasks = True
            html += f"<tr><td>{course}</td><td style='color:red;'>{zy_list}</td><td style='color:red;'>{ks_list}</td></tr>"

    html += "</table>"
    html += "<br><p>💡 提示：此邮件由 GitHub Actions 自动化脚本生成。</p>"

    return html if has_tasks else None


def push_to_email(text):
    if not EMAIL_ACCOUNT or not EMAIL_PASSWORD:
        print("⚠️ 未配置邮箱账号密码，跳过邮件推送")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = Header(EMAIL_ACCOUNT, 'utf-8')
        msg['To'] = Header(EMAIL_ACCOUNT, 'utf-8')
        msg['Subject'] = Header('🚨 学习通新任务提醒', 'utf-8')
        msg.attach(MIMEText(text, 'html', 'utf-8'))

        server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)
        server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ACCOUNT, [EMAIL_ACCOUNT], msg.as_string())
        server.quit()
        print("✅ 邮件推送成功！")
        return True
    except Exception as e:
        print(f"❌ 邮件推送失败: {e}")
        return False


def push_to_wx(text):
    """使用 WxPusher 的极简推送(spt)发送消息"""
    if not WXPUSHER_SPT:
        print("⚠️ 未配置 WxPusher SPT，跳过微信推送")
        return False
    try:
        url = "https://wxpusher.zjiecode.com/api/send/message/simple-push"
        payload = {
            "content": text,
            "summary": "🚨 学习通新任务提醒",
            "contentType": 2,
            "spt": WXPUSHER_SPT
        }
        res = requests.post(url, json=payload).json()
        if str(res.get("code")) == "0":
            print("✅ WxPusher 推送成功！")
            return True
        else:
            print(f"❌ WxPusher 推送失败: {res.get('msg')}")
            return False
    except Exception as e:
        print(f"❌ WxPusher 请求异常: {e}")
        return False


# ===================== 浏览器驱动管理 =====================
def setup_driver() -> WebDriver:
    """配置并返回一个 Selenium WebDriver 实例"""
    print("🚀 正在初始化浏览器驱动...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("window-size=1920,1080") # 设置截图分辨率

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "permissions.default.stylesheet": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    print("✅ 浏览器驱动初始化完成。")
    return driver

# ===================== 辅助函数 =====================
def save_screenshot_for_analysis(driver: WebDriver, course_name: str, task_type: str):
    """为未找到任务的页面截图"""
    safe_course_name = "".join(c for c in course_name if c.isalnum())
    filename = f"analysis_{safe_course_name}_{task_type}.png"
    try:
        driver.save_screenshot(filename)
        print(f"📸 {task_type}页面未找到任何条目，已截图保存为 {filename}")
    except Exception as e:
        print(f"❌ 截图失败: {e}")

# ===================== 核心爬虫逻辑 =====================
def main():
    if not USERNAME or not PASSWORD:
        print("❌ 未找到学习通账号密码环境变量！请在 GitHub Secrets 中配置 CX_USERNAME 和 CX_PASSWORD。")
        sys.exit(1)

    driver = setup_driver()
    wait = WebDriverWait(driver, 15)
    all_course_link_list = []
    all_tasks_summary = {}

    try:
        print("🔄 正在登录学习通...")
        driver.get("https://passport2.chaoxing.com/login?fid=1745")
        wait.until(EC.presence_of_element_located((By.ID, "phone"))).send_keys(USERNAME)
        driver.find_element(By.ID, "pwd").send_keys(PASSWORD)
        driver.find_element(By.ID, "loginBtn").click()

        # 等待登录成功后的页面跳转
        wait.until(EC.url_contains("i.mooc.chaoxing.com"))
        print("✅ 登录成功！")

        driver.get("https://i.mooc.chaoxing.com/space/index")

        # 切换到课程列表 iframe
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content")))

        # 等待课程卡片加载
        course_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.course .course-info")))

        for card in course_cards:
            try:
                course_name = card.find_element(By.CSS_SELECTOR, ".course-name").text.strip()
                course_a_tag = card.find_element(By.CSS_SELECTOR, "a.course-cover")
                raw_link = course_a_tag.get_attribute("href")

                if raw_link and "chaoxing.com" in raw_link:
                    all_course_link_list.append({"name": course_name, "url": raw_link})
            except Exception as e:
                print(f"⚠️ 解析某个课程卡片时出错: {e}")
                continue

        print(f"✅ 成功获取到 {len(all_course_link_list)} 门课程。")

        for index, course in enumerate(all_course_link_list, 1):
            print(f"\n[{index}/{len(all_course_link_list)}] 正在处理课程: {course['name']}")
            all_tasks_summary[course['name']] = {"作业": [], "考试": []}
            driver.get(course['url'])

            # 抓取作业
            try:
                driver.switch_to.default_content()
                wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="作业"]'))).click()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content-zy")))

                # 等待至少一个任务项出现，最多等5秒
                zy_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-item, .work-item, li")))
                for item in zy_items:
                    text = item.text.strip()
                    if text: all_tasks_summary[course['name']]["作业"].append(text)
                print(f"  - 作业: 找到 {len(all_tasks_summary[course['name']]['作业'])} 项。")
            except TimeoutException:
                print("  - 作业: 未在规定时间内找到任何作业项。")
                save_screenshot_for_analysis(driver, course['name'], "homework")
            except Exception as e:
                print(f"  - 作业: 抓取时发生未知错误: {e}")
                save_screenshot_for_analysis(driver, course['name'], "homework_error")

            # 抓取考试
            try:
                driver.switch_to.default_content()
                wait.until(EC.element_to_be_clickable((By.XPATH, '//li[@dataname="ks"]//a[@title="考试"]'))).click()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content-ks")))

                # 等待至少一个任务项出现，最多等5秒
                ks_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-item, .work-item, li")))
                for item in ks_items:
                    text = item.text.strip()
                    if text: all_tasks_summary[course['name']]["考试"].append(text)
                print(f"  - 考试: 找到 {len(all_tasks_summary[course['name']]['考试'])} 项。")
            except TimeoutException:
                print("  - 考试: 未在规定时间内找到任何考试项。")
                save_screenshot_for_analysis(driver, course['name'], "exam")
            except Exception as e:
                print(f"  - 考试: 抓取时发生未知错误: {e}")
                save_screenshot_for_analysis(driver, course['name'], "exam_error")

        print("\n🎉 任务提取完成，准备推送...")
        push_content = build_html_message(all_tasks_summary)
        if push_content:
            pushed_email = push_to_email(push_content)
            pushed_wx = push_to_wx(push_content)
            if not pushed_email and not pushed_wx:
                print("⚠️ 未配置或未匹配到推送方式。")
        else:
            print("✅ 当前没有新的待办作业或考试，无需推送。")

    except Exception as e:
        print(f"\n❌ 运行异常: {e}")
        print("📸 捕获到异常，正在截取当前页面...")
        driver.save_screenshot("error_screenshot.png")
        print("✅ 截图已保存为 error_screenshot.png")
        sys.exit(1)

    finally:
        print("🚪 正在关闭浏览器...")
        if 'driver' in locals() and driver:
            driver.quit()
        print("✅ 浏览器已关闭。")

        print("📦 正在打包所有截图...")
        try:
            with zipfile.ZipFile('screenshots.zip', 'w') as zf:
                for file in os.listdir('.'):
                    if file.endswith('.png'):
                        zf.write(file)
                        print(f"  - 已添加 {file}")
            print("✅ 截图已打包至 screenshots.zip")
        except Exception as e:
            print(f"❌ 打包截图失败: {e}")


if __name__ == "__main__":
    main()