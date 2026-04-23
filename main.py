import os
import time
import sys
import requests
import re
import zipfile
import json
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
# 你的服务器接收数据的 API 地址（建议配置在 GitHub Secrets 中）
MY_SERVER_API = os.environ.get("MY_SERVER_API", "http://你的服务器IP:端口/api/receive_task")


# 🎯 监控终点课程关键字：抓完这门课就停止，如果不需要则设置为空字符串 ""
STOP_COURSE_NAME = "数据库系统原理"
HISTORY_FILE = "history.json"

# ====================== 核心正则规则 ======================
# 规则：删除特定状态词、通用英文，但保留时间单位(hour/minute)和特定技术词(C++/HTML等)
# 核心语法 [a-zA-Z]+(?!hour|minutes) 是负向先行断言：匹配所有英文字母单词，但是排除 hour、minutes
TASK_CLEANUP_PATTERN = re.compile(
    r'\b(To be|Taken|Submitted|marked|Analysis|Completed|Done|Record|Intelligence|reviewed|Only|study|through|APP|exam|task|points|left|expired|finished|over|end)\b'
    r'|[a-zA-Z]+(?!hour|minutes)'
    r'|\s+%',
    re.IGNORECASE
)

# ===================== 数据清洗与提取 =====================
def parse_task_info(raw_text):
    """
    清洗数据：提取标题和时间/状态
    """
    # 1. 执行正则替换
    text = TASK_CLEANUP_PATTERN.sub('', raw_text)

    # 2. 清理多余连续空格、制表符、空行，排版美观
    text = re.sub(r'[ \t]+', ' ', text)   # 多个空格缩成一个
    text = re.sub(r'\(\s*\)', '', text) # 删除空括号
    text = re.sub(r'\n+', '\n', text).strip() # 删除多余空行

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return None

    title = lines[0]
    time_str = "未获取到时间"
    if len(lines) > 1:
        # 转换常见单位
        raw_time = lines[1].lower().replace("hour", "小时").replace("minutes", "分钟").replace("minute", "分钟")
        time_str = re.sub(r'[a-z]', '', raw_time).strip()

    return {"title": title, "time": time_str}

def get_hours_left(time_str):
    """从 '剩余 5 小时 30 分钟' 或 '剩余 1 天' 中提取剩余总小时数"""
    hours = 0
    h_match = re.search(r'(\d+)\s*小时', time_str)
    d_match = re.search(r'(\d+)\s*天', time_str)

    if d_match:
        hours += int(d_match.group(1)) * 24
    if h_match:
        hours += int(h_match.group(1))

    # 如果只有分钟没有小时，算作 0.5 小时
    if not h_match and not d_match and '分钟' in time_str:
        return 0.5

    return hours if (hours > 0 or '分钟' in time_str) else 9999 # 解析失败返回超大值

# ===================== 历史记录管理 =====================
def load_history():
    """加载历史任务记录"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                print("✅ 成功加载历史记录文件。")
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 加载历史文件失败: {e}，将视所有任务为新任务。")
            return {}
    print("ℹ️ 未找到历史记录文件，将视所有任务为新任务。")
    return {}

def save_history(current_summary):
    """保存当前所有任务到历史文件"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_summary, f, ensure_ascii=False, indent=4)
        print(f"✅ 本次抓取的 {sum(len(tasks['作业']) + len(tasks['考试']) for tasks in current_summary.values())} 个任务已保存至 {HISTORY_FILE}")
    except Exception as e:
        print(f"❌ 保存历史文件失败: {e}")

# ===================== HTML 渲染 (看板样式) =====================
def build_html_message(tasks_summary):
    """使用卡片式看板样式渲染 HTML"""
    html = """
    <div style="background-color: #f4f5f7; padding: 15px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #181d26;">
      <div style="font-size: 20px; font-weight: bold; margin-bottom: 15px; text-align: center;">学术任务看板</div>
    """

    has_tasks = False
    for course, tasks in tasks_summary.items():
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
        for ks in tasks["考试"]:
            html += f"""
            <div style="border: 1px dashed #b91c1c; border-radius: 8px; padding: 10px; margin-bottom: 10px; background-color: #fff5f5;">
                <div style="font-size: 14px; font-weight: bold; color: #b91c1c;">[考试] {ks['title']}</div>
                <div style="font-size: 12px; color: #b91c1c; margin-top: 4px;">状态：{ks['time']}</div>
            </div>
            """
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

# ===================== 推送逻辑 =====================
def push_to_server(tasks_summary):
    if not MY_SERVER_API or MY_SERVER_API == "http://你的服务器IP:端口/api/receive_task":
        return False
    try:
        # 设置 timeout 为 5 秒，防止 GitHub Action 卡死
        res = requests.post(MY_SERVER_API, json=tasks_summary, timeout=5)
        if res.status_code == 200:
            print("✅ 成功推送到私人服务器接管")
            return True
        else:
            print(f"⚠️ 服务器返回异常状态码: {res.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接私人服务器 (宕机或超时): {e}")
        return False

def push_to_wx(text):
    if not WXPUSHER_SPT:
        print("⚠️ 未配置 WxPusher SPT，跳过推送。")
        return False
    try:
        url = "https://wxpusher.zjiecode.com/api/send/message/simple-push"
        payload = {"content": text, "summary": "🚨 学习通任务截止提醒", "contentType": 2, "spt": WXPUSHER_SPT}
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
    print("🚀 正在初始化浏览器驱动...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("window-size=1920,1080")
    prefs = {"profile.managed_default_content_settings.images": 2, "permissions.default.stylesheet": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    print("✅ 浏览器驱动初始化完成。")
    return driver

def save_screenshot_for_analysis(driver: WebDriver, course_name: str, task_type: str):
    # 确保截图目录存在
    if not os.path.exists('screenshots'):
        os.makedirs('screenshots')
    safe_course_name = "".join(c for c in course_name if c.isalnum())
    filename = f"screenshots/analysis_{safe_course_name}_{task_type}.png"
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

    # 1. 加载历史记录
    old_history = load_history()
    new_tasks_to_push = {}

    try:
        # 2. 登录
        print("🔄 正在登录学习通...")
        driver.get("https://passport2.chaoxing.com/login?fid=1745")
        wait.until(EC.presence_of_element_located((By.ID, "phone"))).send_keys(USERNAME)
        driver.find_element(By.ID, "pwd").send_keys(PASSWORD)
        driver.find_element(By.ID, "loginBtn").click()
        wait.until(EC.url_contains("i.mooc.chaoxing.com"))
        print("✅ 登录成功")

        # 3. 获取课程列表
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
                if STOP_COURSE_NAME and STOP_COURSE_NAME in name:
                    print(f"📍 已识别到终点课程：{name}，停止扫描后续课程列表。")
                    break
            except Exception as e:
                print(f"⚠️ 解析某个课程卡片时出错，已跳过: {e}")
                continue
        print(f"✅ 成功获取到 {len(all_course_link_list)} 门课程。")

        # 4. 顺序遍历抓取
        for index, course in enumerate(all_course_link_list, 1):
            c_name = course['name']
            print(f"\n[{index}/{len(all_course_link_list)}] 正在处理: {c_name}")
            all_tasks_summary[c_name] = {"作业": [], "考试": []}
            for task_type in ["作业", "考试"]:
                driver.get(course['url'])
                try:
                    driver.switch_to.default_content()
                    wait.until(EC.element_to_be_clickable((By.XPATH, f'//a[@title="{task_type}"]'))).click()
                    frame_id = f"frame_content-{'zy' if task_type == '作业' else 'ks'}"
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, frame_id)))
                    items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-item, .work-item, li")))
                    for item in items:
                        parsed = parse_task_info(item.text)
                        if parsed: all_tasks_summary[c_name][task_type].append(parsed)
                    print(f"  - {task_type}: 找到 {len(all_tasks_summary[c_name][task_type])} 项。")
                except TimeoutException:
                    print(f"  - {task_type}: 无数据或加载超时。")
                    save_screenshot_for_analysis(driver, c_name, f"{task_type}_nodata")
                except Exception as e:
                    print(f"  - {task_type}: 抓取时发生未知错误: {e}")
                    save_screenshot_for_analysis(driver, c_name, f"{task_type}_error")

        # 5. 比对历史，生成待推送内容
        print("\n🔄 正在分析任务紧急程度...")
        for course_name, tasks in all_tasks_summary.items():
            new_tasks_to_push[course_name] = {"作业": [], "考试": []}
            for task_type in ["作业", "考试"]:
                for task in tasks[task_type]:
                    title, time_str = task['title'], task['time']
                    history_list = old_history.get(course_name, {}).get(task_type, [])
                    history_item = next((item for item in history_list if item['title'] == title), None)

                    h_left = get_hours_left(time_str)

                    # 触发条件 1：全新的任务
                    if not history_item:
                        print(f"  - [新增] {course_name} -> {task_type}: {title}")
                        new_tasks_to_push[course_name][task_type].append(task)

                    # 触发条件 2：状态发生变化（排除时间解析失败的情况）
                    elif time_str != "未获取到时间" and time_str != history_item['time']:

                        # 重点：判断是否进入 8 小时倒计时
                        if h_left <= 8:
                            print(f"  - 🚨 [紧急] {course_name} -> {title} (仅剩 {time_str})")
                            new_tasks_to_push[course_name][task_type].append(task)
                        else:
                            print(f"  - [更新] {course_name} -> {title} (时间变动，但大于 8 小时，暂不提醒)")

        # 6. 推送 (带有降级策略)
        print("\n🎉 分析完成，准备推送...")
        has_content = any(tasks["作业"] or tasks["考试"] for tasks in new_tasks_to_push.values())

        if has_content:
            print("🔄 策略 1：尝试连接私人服务器...")
            server_success = push_to_server(new_tasks_to_push)

            if not server_success:
                print("🔄 策略 2：服务器不可用，启动降级策略，使用 GitHub 直接推送到微信...")
                content = build_html_message(new_tasks_to_push)
                if not push_to_wx(content):
                    print("⚠️ 降级推送也失败了。")
        else:
            print("✅ 当前无紧急或新增任务，无需打扰。")

    except Exception as e:
        print(f"\n❌ 脚本主流程运行异常: {e}")
        print("📸 捕获到严重异常，正在截取当前页面...")
        save_screenshot_for_analysis(driver, "FatalError", "main_process")
        sys.exit(1)

    finally:
        print("🚪 正在关闭浏览器...")
        if 'driver' in locals() and driver:
            driver.quit()
        print("✅ 浏览器已关闭。")

        # 7. 保存最新记录并打包截图
        save_history(all_tasks_summary)
        print("📦 正在打包所有截图...")
        try:
            # 检查截图目录是否存在
            if os.path.exists('screenshots') and os.listdir('screenshots'):
                with zipfile.ZipFile('screenshots.zip', 'w') as zf:
                    for file in os.listdir('screenshots'):
                        if file.endswith('.png'):
                            file_path = os.path.join('screenshots', file)
                            zf.write(file_path, file) # 写入 zip 时不带父目录
                            os.remove(file_path)
                print("✅ 截图已打包至 screenshots.zip")
            else:
                print("ℹ️ 没有需要打包的截图。")
        except Exception as e:
            print(f"❌ 打包截图失败: {e}")

if __name__ == "__main__":
    main()