import os
import time
import sys
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    if not WXPUSHER_SPT:
        print("⚠️ 未配置 WxPusher SPT，跳过微信推送")
        return False
    try:
        url = "https://wxpusher.zjiecode.com/api/send/message"
        payload = {
            "content": text,
            "summary": "🚨 学习通新任务提醒",
            "contentType": 2,  # 2表示HTML
            "spt": WXPUSHER_SPT
        }
        res = requests.post(url, json=payload).json()
        if str(res.get("code")) == "1000":
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
    driver = webdriver.Chrome(options=chrome_options)
    print("✅ 浏览器驱动初始化完成。")
    return driver


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

        phone_input = wait.until(EC.presence_of_element_located((By.ID, "phone")))
        phone_input.clear()
        phone_input.send_keys(USERNAME)

        pwd_input = driver.find_element(By.ID, "pwd")
        pwd_input.clear()
        pwd_input.send_keys(PASSWORD)

        driver.find_element(By.ID, "loginBtn").click()
        time.sleep(5)
        print("✅ 登录成功！")

        driver.get("https://i.mooc.chaoxing.com/space/index")
        time.sleep(4)

        iframe = wait.until(EC.presence_of_element_located((By.ID, "frame_content")))
        driver.switch_to.frame(iframe)
        time.sleep(3)

        course_cards = driver.find_elements(By.CSS_SELECTOR, "li.course")
        if not course_cards:
            course_cards = driver.find_elements(By.XPATH,
                                                '//a[contains(@href,"courseid") or contains(@href,"mooc2-ans")]')

        for idx, card in enumerate(course_cards, 1):
            try:
                course_name = card.find_element(By.CSS_SELECTOR, ".course-name").text.strip()
                course_a_tag = card.find_element(By.CSS_SELECTOR, ".course-cover a")
                raw_link = course_a_tag.get_attribute("href")

                if raw_link and "chaoxing.com" in raw_link:
                    all_course_link_list.append({"name": course_name, "url": raw_link})
                    if "数据库系统原理" in course_name:
                        break
            except Exception:
                continue

        for index, course in enumerate(all_course_link_list, 1):
            all_tasks_summary[course['name']] = {"作业": [], "考试": []}
            driver.get(course['url'])
            time.sleep(3)

            # 抓取作业
            try:
                driver.switch_to.default_content()
                wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="作业"]'))).click()
                time.sleep(2)
                iframe_zy = wait.until(EC.presence_of_element_located((By.ID, "frame_content-zy")))
                driver.switch_to.frame(iframe_zy)
                time.sleep(2)
                zy_items = driver.find_elements(By.CSS_SELECTOR, ".card-item, .work-item, li")
                for item in zy_items:
                    text = item.text.strip()
                    if text: all_tasks_summary[course['name']]["作业"].append(text)
            except Exception:
                pass

            # 抓取考试
            try:
                driver.switch_to.default_content()
                ks_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//li[@dataname="ks"]//a[@title="考试"]')))
                ks_btn.click()
                time.sleep(2)
                iframe_ks = wait.until(EC.presence_of_element_located((By.ID, "frame_content-ks")))
                driver.switch_to.frame(iframe_ks)
                time.sleep(2)
                ks_items = driver.find_elements(By.CSS_SELECTOR, ".card-item, .work-item, li")
                for item in ks_items:
                    text = item.text.strip()
                    if text: all_tasks_summary[course['name']]["考试"].append(text)
            except Exception:
                pass

        print("\n🎉 任务提取完成，准备推送...")

        # 触发推送
        push_content = build_html_message(all_tasks_summary)
        if push_content:
            pushToEmail = push_to_email(push_content)
            pushToWx = push_to_wx(push_content)
            if not pushToEmail and not pushToWx:
                print("⚠️ 未配置或未匹配到推送方式。")
        else:
            print("✅ 当前没有新的待办作业或考试，无需推送。")

    except Exception as e:
        print(f"\n❌ 运行异常: {e}")
        print("📸 捕获到异常，正在截取当前页面...")
        driver.save_screenshot("error_screenshot.png")
        print("✅ 截图已保存为 error_screenshot.png")
        sys.exit(1) # 以失败状态退出

    finally:
        print("🚪 正在关闭浏览器...")
        driver.quit()
        print("✅ 浏览器已关闭。")


if __name__ == "__main__":
    main()