# 🎓 学习通作业考试提醒工具 (ChaoXing_bot)

基于 Python + Selenium + GitHub Actions 构建的**自动监控学习通作业、考试任务**


## 🖥️ 在线可视化任务看板
项目已静态部署 **GitHub Pages**，打开链接即可全局查看所有课程任务、截止倒计时、紧急任务标记。

🔗 **在线访问地址**：
https://augfif.github.io/task-board/

网页展示：卡片式布局、课程分类、剩余时间倒计时、紧急任务高亮标红、界面简洁清爽。

![网页看板展示](https://github.com/Augfif/chaoxing_bot/blob/master/picture/img.png)

---

>新增 / 推送到自己的服务器（正在填坑中）

## ✨  功能特点

- 🧠 **只提醒新任务 / 快截止的任务**：利用 `history.json` ，仅在新任务发布或任务时间/状态发生变动时触发推送，不产生无用打扰。
- 🚨 **快截止（≤8 小时）加强提醒**：当作业/考试剩余时间 **≤ 8 小时** 时，每小时进行一次高频提醒。
- 🛡️ **双推送方式)**：
  - **Plan A (极客模式)**：优先将数据 POST 推送至你的私人服务器（支持二次开发与自动化处理）。
  - **Plan B (兜底防御)**：若私人服务器宕机或超时无响应，系统立即无缝降级，自动生成 HTML 看板并调用 WxPusher(需下载软件或在微信额外配置)。
- ☁️ **云端全自动运行**：绑定 GitHub Actions，利用定时任务 (Cron) 每小时执行一次。无需自备服务器或本地常驻电脑。
- 🧹 **智能数据清洗**：剔除超星平台冗余的英文词汇，只显示关键信息
- 📌 **支持课程截止**: 当前仅支持在代码中修改(详见`进阶配置`)，后续尝试解耦。

### 📱 微信推送实际效果
任务触发提醒条件时，自动发送精美格式化卡片消息至个人微信，实时接收通知。
<p align="center">
  <img src="https://github.com/Auggifi/chaoxing_bot/blob/master/picture/phone.png" width="600" alt="微信推送手机端展示">
</p>

## 🚀 部署指南 

### 1. 准备工作
- 一个 GitHub 账号。
- [WxPusher](https://wxpusher.zjiecode.com/) 账号及获取的 Simple Push Token (SPT)。
- （可选）一台用于接收 JSON 数据的云服务器/软路由。

### 2. Fork 本仓库
<details>
<summary><strong>点击查看如何fork项目</strong></summary>
<img src="https://github.com/Augfif/chaoxing_bot/blob/master/picture/make.gif" width="500"/>
<summary>请注意，如果你想使用其他分支管理器项目，请在fork时关闭“仅复制SukiSU Ultra分支”</summary>
</details>
 
<details>
<summary><strong>点击查看如何同步fork后的项目到最新</strong></summary>
<p>
  <img src="https://github.com/Augfif/chaoxing_bot/blob/master/picture/syncfork.png" width="150"/>
  <img src="https://github.com/Augfif/chaoxing_bot/blob/master/picture/syncfork(2).png" width="150"/>
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

# 开发中的功能
- 牙膏要一点一点挤,显卡要一刀一刀切,PPT要一张一张放,代码要一行一行写,更多功能及优化...敬请期待....

## 🤝 参与共建

一个人写代码挺枯燥的，如果你也是喜欢折腾的同学或者对此感兴趣，欢迎一起来完善这个小工具！

目前项目还有一些小缺点，我也列了一份 **TODO 清单**，如果你刚好会，或者想拿来练手，随时欢迎提 PR：

* **[待填坑] 服务器端代码**：现在脚本可以把数据 POST 到私人服务器，但是服务器那边怎么接、怎么存、怎么推，我还没写完... 有没有大佬帮忙糊一个 FastAPI / Flask 的模板？
* **[待优化] 课程截止解耦**：现在想要过滤掉不需要的课，还得进代码里改 `STOP_COURSE_NAME`，有点硬核。能不能改成读取一个配置文件，或者做个简单的过滤列表？
* **[待修复] 玄学 Bug**：如果你在跑脚本的时候遇到了报错（比如学习通又双叒叕改版了），欢迎带上 Log 截图提 Issue！

**怎么参与？**
1. Fork 本仓库
2. 新建一个你的分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到你的分支 (`git push origin feature/AmazingFeature`)
5. 提个 Pull Request，我会第一时间看！

## ⚠️ 免责声明
 AIGC项目仅供编程学习、个人辅助使用，各位大佬轻点喷。
 任何违规滥用、高频恶意请求造成的一切后果，均由使用者本人自负。。