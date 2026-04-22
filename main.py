import os
import time
import sys
import requests
import re
import zipfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ===================== 读取环境变量与配置 =====================
USERNAME = os.environ.get("CX_USERNAME")
PASSWORD = os.environ.get("CX_PASSWORD")
WXPUSHER_SPT = os.environ.get("WXPUSHER_SPT")

# 🎯 监控终点课程关键字：抓完这门课就停止，如果不需要则设置为空字符串 ""
STOP_COURSE_NAME = "数据库系统原理"

# ===================== 数据清洗与提取 =====================
def parse_task_info(raw_text):
    """
    清洗数据：提取标题和时间/状态
    """
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    if not lines:
        return None

    # 第一行通常是标题
    title = lines[0]
    # 过滤掉标题中的英文字母和空括号
    title = re.sub(r'[a-zA-Z]', '', title).strip()
    title = re.sub(r'\(\s*\)', '', title).strip()

    # 提取时间/状态（尝试取第二行或后续包含数字/状态的行）
    time_str = "未获取到时间"
    if len(lines) > 1:
        # 转换常见英文单位
        raw_time = lines[1].lower()
        raw_time = raw_time.replace("hour", "小时").replace("minutes", "分钟").replace("minute", "分钟").replace("left", "剩余")
        # 移除英文字母，保留中文和数字
        time_str = re.sub(r'[a-z]', '', raw_time).strip()

    if not title:
        return None

    return {"title": title, "time": time_str}

# ===================== HTML 渲染 (看板样式) =====================
def build_html_message(tasks_summary):
    """使用卡片式看板样式渲染 HTML"""
    html = """
    <div style="background-color: #f4f5f7; padding: 15px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #181d26;">
      <div style="font-size: 20px; font-weight: bold; margin-bottom: 15px; text-align: center;">学术任务看板</div>
    """

    has_tasks = False
    for course, tasks in tasks_summary.items():
        # 如果这门课既没作业也没考试，跳过
        if not tasks["作业"] and not tasks["考试"]:
            continue

        has_tasks = True
        emoji = "💻" if any(kw in course for kw in ["数据", "算法", "计算", "编程", "程序", "软件", "系统"]) else "📚"

        html += f"""
        <div style="background: #ffffff; border: 1px solid #e0e2e6; border-radius: 12px; margin-bottom: 16px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
            <div style="background-color: #f8fafc; padding: 12px 15px; font-size: 16px; font-weight: bold; border-bottom: 1px solid #e0e2e6; color: #1b61c9;">
                {emoji} {course}
            </div>
            <div style="padding: 15px;">
        """

        # 渲染考试
        for ks in tasks["考试"]:
            html += f"""
            <div style="border: 1px dashed #b91c1c; border-radius: 8px; padding: 10px; margin-bottom: 10px; background-color: #fff5f5;">
                <div style="font-size: 14px; font-weight: bold; color: #b91c1c;">[考试] {ks['title']}</div>
                <div style="font-size: 12px; color: #b91c1c; margin-top: 4px;">状态：{ks['time']}</div>
            </div>
            """

        # 渲染作业
        for zy in tasks["作业"]:
            html += f"""
            <div style="border: 1px dashed #16a34a; border-radius: 8px; padding: 10px; margin-bottom: 10px; background-color: #f0fdf4;">
                <div style="font-size: 14px; font-weight: bold; color: #16a34a;">[作业] {zy['title']}</div>
                <div style="font-size: 12px; color: #16a34a; margin-top: 4px;">状态：{zy['time']}</div>
            </div>
            """

        html += "</div></div>"

    html += "</div>"
    return html if has_tasks else None

# ===================== 推送逻辑 (WxPusher) =====================
def push_to_wx(text):
    if not WXPUSHER_SPT:
        print("⚠️ 未配置 WxPusher SPT")
        return False
    try:
        url = "https://wxpusher.zjiecode.com/api/send/message/simple-push"
        payload = {
            "content": text,
            "summary": "🚨 学习通任务截止提醒",
            "contentType": 2,
            "spt": WXPUSHER_SPT
        }
        res = requests.post(url, json=payload).json()
        if str(res.get("code")) == "0":
            print("✅ WxPusher 推送成功")
            return True
        else:
            print(f"❌ WxPusher 推送失败: {res.get('msg')}")
            return False
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

# ===================== 浏览器驱动与辅助函数 =====================
def setup_driver() -> WebDriver:
    """配置并返回一个带有优化选项的 Selenium WebDriver 实例"""
    print("🚀 正在初始化浏览器驱动...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("window-size=1920,1080") # 设置截图分辨率

    # 禁用图片和样式表加载，提升速度
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

def save_screenshot_for_analysis(driver: WebDriver, course_name: str, task_type: str):
    """为指定页面截图，用于分析"""
    safe_course_name = "".join(c for c in course_name if c.isalnum())
    filename = f"analysis_{safe_course_name}_{task_type}.png"
    try:
        driver.save_screenshot(filename)
        print(f"📸 {task_type}页面未找到任何条目或出错，已截图保存为 {filename}")
    except Exception as e:
        print(f"❌ 截图失败: {e}")

# ===================== 核心爬虫逻辑 =====================
def main():
    if not USERNAME or not PASSWORD:
        print("❌ 环境变量缺失，请在 GitHub Secrets 中配置 CX_USERNAME 和 CX_PASSWORD。")
        sys.exit(1)

    driver = setup_driver()
    wait = WebDriverWait(driver, 15)
    all_course_link_list = []
    all_tasks_summary = {}

    try:
        # 1. 登录
        print("🔄 正在登录学习通...")
        driver.get("https://passport2.chaoxing.com/login?fid=1745")
        wait.until(EC.presence_of_element_located((By.ID, "phone"))).send_keys(USERNAME)
        driver.find_element(By.ID, "pwd").send_keys(PASSWORD)
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("i.mooc.chaoxing.com"))
        print("✅ 登录成功")

        # 2. 获取课程列表
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content")))

        try:
            course_cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.course")))
        except TimeoutException:
            print("⚠️ 未找到 'li.course' 类型的课程卡片，尝试备用查找方案...")
            course_cards = driver.find_elements(By.XPATH, '//a[contains(@href,"courseid") or contains(@href,"mooc2-ans")]')

        if not course_cards:
            print("⚠️ 未能在页面上找到任何课程，请检查是否没有课程或页面结构已更改。")
            save_screenshot_for_analysis(driver, "AllCourses", "not_found")

        for card in course_cards:
            try:
                name = card.find_element(By.CSS_SELECTOR, ".course-name").text.strip()
                link = card.find_element(By.CSS_SELECTOR, ".course-cover a").get_attribute("href")
                all_course_link_list.append({"name": name, "url": link})
                # 如果遇到终点课程，停止获取列表
                if STOP_COURSE_NAME and STOP_COURSE_NAME in name:
                    print(f"📍 已识别到终点课程：{name}，停止扫描后续课程列表。")
                    break
            except Exception as e:
                print(f"⚠️ 解析某个课程卡片时出错，已跳过: {e}")
                continue

        print(f"✅ 成功获取到 {len(all_course_link_list)} 门课程。")

        # 3. 顺序遍历抓取
        for index, course in enumerate(all_course_link_list, 1):
            c_name = course['name']
            print(f"\n[{index}/{len(all_course_link_list)}] 正在处理: {c_name}")
            all_tasks_summary[c_name] = {"作业": [], "考试": []}

            # --- 抓取作业 ---
            driver.get(course['url'])
            try:
                driver.switch_to.default_content()
                wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@title="作业"]'))).click()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content-zy")))
                zy_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-item, .work-item, li")))
                for item in zy_items:
                    parsed = parse_task_info(item.text)
                    if parsed: all_tasks_summary[c_name]["作业"].append(parsed)
                print(f"  - 作业: 找到 {len(all_tasks_summary[c_name]['作业'])} 项。")
            except TimeoutException:
                print(f"  - 作业: 无数据或加载超时。")
                save_screenshot_for_analysis(driver, c_name, "homework_nodata")
            except Exception as e:
                print(f"  - 作业: 抓取时发生未知错误: {e}")
                save_screenshot_for_analysis(driver, c_name, "homework_error")

            # --- 抓取考试 ---
            driver.get(course['url']) # 重新进入课程主页保证侧边栏可见
            try:
                driver.switch_to.default_content()
                wait.until(EC.element_to_be_clickable((By.XPATH, '//li[@dataname="ks"]//a[@title="考试"]'))).click()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content-ks")))
                ks_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-item, .work-item, li")))
                for item in ks_items:
                    parsed = parse_task_info(item.text)
                    if parsed: all_tasks_summary[c_name]["考试"].append(parsed)
                print(f"  - 考试: 找到 {len(all_tasks_summary[c_name]['考试'])} 项。")
            except TimeoutException:
                print(f"  - 考试: 无数据或加载超时。")
                save_screenshot_for_analysis(driver, c_name, "exam_nodata")
            except Exception as e:
                print(f"  - 考试: 抓取时发生未知错误: {e}")
                save_screenshot_for_analysis(driver, c_name, "exam_error")

        # 4. 推送
        print("\n🎉 任务提取完成，准备推送...")
        content = build_html_message(all_tasks_summary)
        if content:
            if not push_to_wx(content):
                print("⚠️ 未配置或未匹配到推送方式。")
        else:
            print("✅ 暂无待办任务，无需推送。")

    except Exception as e:
        print(f"\n❌ 脚本主流程运行异常: {e}")
        print("📸 捕获到严重异常，正在截取当前页面...")
        save_screenshot_for_analysis(driver, "FatalError", "main_process")
        sys.exit(1) # 退出并标记 GitHub Actions 失败

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
                        os.remove(file) # 打包后删除原图，保持工作区整洁
            print("✅ 截图已打包至 screenshots.zip")
        except Exception as e:
            print(f"❌ 打包截图失败: {e}")


if __name__ == "__main__":
    main()