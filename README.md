# 🎓 学习通作业考试提醒工具 (ChaoXing_bot)

基于 Python + Selenium + GitHub Actions 构建的**自动监控学习通作业、考试任务**

>新增 / 推送到自己的服务器（尚未完成...）

## ✨  功能特点

- 🧠 **只提醒新任务 / 快截止的任务**：利用 `history.json` ，仅在新任务发布或任务时间/状态发生变动时触发推送，不产生无用打扰。
- 🚨 **快截止（≤8 小时）加强提醒**：当作业/考试剩余时间 **≤ 8 小时** 时，每小时进行一次高频提醒。
- 🛡️ **双推送方式)**：
  - **Plan A (极客模式)**：优先将数据 POST 推送至你的私人服务器（支持二次开发与自动化处理）。
  - **Plan B (兜底防御)**：若私人服务器宕机或超时无响应，系统立即无缝降级，自动生成 HTML 看板并调用 WxPusher(需下载软件或在微信额外配置)。
- ☁️ **云端全自动运行**：绑定 GitHub Actions，利用定时任务 (Cron) 每小时执行一次。无需自备服务器或本地常驻电脑。
- 🧹 **智能数据清洗**：剔除超星平台冗余的英文词汇，只显示关键信息
- 📌 **支持课程截止**: 当前仅支持在代码中修改(详见`进阶配置`)，后续尝试解耦。

## 🚀 部署指南 

### 1. 准备工作
- 一个 GitHub 账号。
- [WxPusher](https://wxpusher.zjiecode.com/) 账号及获取的 Simple Push Token (SPT)。
- （可选）一台用于接收 JSON 数据的云服务器/软路由。

### 2. Fork 本仓库
<details>
<summary><strong>点击查看如何fork项目</strong></summary>
<img src="https://github.com/Numbersf/Action-Build/blob/SukiSU-Ultra/pic/make.gif" width="500"/>
<summary>请注意，如果你想使用其他分支管理器项目，请在fork时关闭“仅复制SukiSU Ultra分支”</summary>
</details>
 
<details>
<summary><strong>点击查看如何同步fork后的项目到最新</strong></summary>
<p>
  <img src="https://github.com/Numbersf/Action-Build/blob/SukiSU-Ultra/pic/syncfork.png" width="150"/>
  <img src="https://github.com/Numbersf/Action-Build/blob/SukiSU-Ultra/pic/syncfork(2).png" width="150"/>
</p>
<summary>请及时同步!某些更新可能会导致旧版失效报错!如果同步后依旧运行失败请删除并重新fork!完成以上步骤后仍有问题再反馈提交issue</summary>
</details>

### 3. 配置仓库权限 (重要)
进入你的仓库：
`Settings` -> `Actions` -> `General` -> `Workflow permissions` 
勾选 **Read and write permissions** 并保存。*(这是为了让脚本能够自动提交更新 `history.json` 记录，从而实现“状态记忆”)*。

### 4. 设置环境变量 (Secrets)
进入 `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`，依次添加以下内容：

| Secret 名称 | 必填 | 说明 |
| :--- | :---: | :--- |
| `CX_USERNAME` | ✅ | 学习通登录手机号/账号 |
| `CX_PASSWORD` | ✅ | 学习通登录密码 |
| `WXPUSHER_SPT`| ✅ | WxPusher 的单播推送 Token (格式一般为 `SPT_xxxx`) |
| `MY_SERVER_API`| ❌ | 你的私人服务器 Webhook 接收接口地址，若不配置则默认直接走微信推送兜底 |

### 5. 首次激活工作流
进入 `Actions` 标签页，在左侧选择 `ChaoXing Task Monitor`，点击右侧的 **Run workflow** 手动触发第一次运行。
之后，GitHub 会按照 `cx_crawler.yml` 的配置自动为你按小时巡逻。

## ⚙️ 进阶配置

在 `main.py` 顶部可以修改以下配置以适应你的需求：
- **监控终点 **：如果你不需要遍历所有的课程，可以设置一个“终点课程”的名称关键字。爬虫扫描到该课程即停止，大幅提高脚本运行速度与成功率。

## 📸 运行效果与排错
- **静默守护**：平时无任务时静默运行，一旦产生报错（如学习通界面改版），系统会自动将出错页面的截图打包为 `screenshots.zip` 上传至该次 Action 的 Artifacts 中，极大方便排查。
- **降级日志**：你可以在 Actions 的运行日志中清晰看到 `🔄 策略 1：尝试连接私人服务器...` 与 `🔄 策略 2：服务器不可用，启动降级策略...` 的智能调度过程。

## ⚠️ 免责声明
本项目仅供编程学习、AIGC 实践与个人辅助交流使用，请勿用于高并发恶意请求。合理设置运行频率，使用本脚本造成的一切后果由使用者自行承担。