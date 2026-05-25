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
- 📌 **支持课程过滤配置**：可通过 GitHub Secret 或本地配置文件过滤不需要监控的课程，无需再进入代码修改 `STOP_COURSE_NAME`。

### 📱 微信推送实际效果
任务触发提醒条件时，自动发送精美格式化卡片消息至个人微信，实时接收通知。
<div align="center">
  <img src="https://github.com/Augfif/chaoxing_bot/blob/master/picture/phone.png?raw=true" width="300" alt="手机界面展示" />
</div>

## 🚀 部署指南 

### 1. 准备工作
- 一个 GitHub 账号。
- [WxPusher](https://wxpusher.zjiecode.com/) 账号及获取的 Simple Push Token (SPT)。
- （可选）一台用于接收 JSON 数据的云服务器/软路由。

### 2. Fork 本仓库
<details>
<summary><strong>点击查看如何fork项目</strong></summary>
<img src="https://github.com/Augfif/chaoxing_bot/blob/master/picture/make.gif" width="500"/>
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
| `WXPUSHER_SPT`| ✅ | WxPusher 的单播推送 Token，格式一般为 `SPT_xxxx` |
| `MY_SERVER_API`| ❌ | 你的私人服务器 Webhook 接收接口地址，若不配置则默认直接走微信推送兜底 |
| `COURSE_CONFIG_JSON` | ❌ | 课程过滤配置，可用于跳过不想监控的课程 |

### 5. 首次激活工作流
进入 `Actions` 标签页，在左侧选择 `ChaoXing Task Monitor`，点击右侧的 **Run workflow** 手动触发第一次运行。
之后，GitHub 会按照 `cx_crawler.yml` 的配置自动为你按小时巡逻。

## ⚙️ 进阶配置

### 课程过滤配置

如果你不想监控某些课程，可以通过课程过滤配置跳过它们。  
课程过滤支持两种方式：

1. GitHub Actions 部署时，通过 `COURSE_CONFIG_JSON` Secret 配置。
2. 本地运行时，通过 `config.json` 配置文件配置。

### 使用 GitHub Secret 配置课程过滤

进入仓库：

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

新增一个 Secret：

```text
COURSE_CONFIG_JSON
```

示例内容：

```json
{"course_filter":{"include_keywords":[],"exclude_keywords":["体育","就业指导","形势与政策"],"stop_after_keyword":""}}
```

配置说明：

| 字段 | 说明 |
| :--- | :--- |
| `include_keywords` | 只监控课程名中包含这些关键词的课程。留空表示监控所有课程 |
| `exclude_keywords` | 跳过课程名中包含这些关键词的课程 |
| `stop_after_keyword` | 扫描到包含该关键词的课程后停止继续扫描。留空表示不启用 |

例如课程名是：

```text
2025春 大学英语（二）
```

如果你在 `exclude_keywords` 中填写：

```json
["大学英语"]
```

该课程就会被跳过，不再参与作业和考试任务检查。

### 使用本地配置文件

如果你是在本地运行脚本，可以复制示例配置文件：

```bash
cp config.example.json config.json
```

然后修改 `config.json`：

```json
{
  "course_filter": {
    "include_keywords": [],
    "exclude_keywords": ["体育", "就业指导"],
    "stop_after_keyword": ""
  }
}
```

`config.json` 是个人配置文件，不建议提交到公开仓库。

### 配置优先级

脚本读取课程过滤配置的优先级如下：

1. 优先读取环境变量 `COURSE_CONFIG_JSON`
2. 如果没有环境变量，则读取本地 `config.json`
3. 如果两者都没有，则默认监控所有课程

这样可以兼容 GitHub Actions 云端部署和本地调试两种场景。
## 📸 运行效果与排错
- **静默守护**：平时无任务时静默运行，一旦产生报错（如学习通界面改版），系统会自动将出错页面的截图打包为 `screenshots.zip` 上传至该次 Action 的 Artifacts 中，极大方便排查。
- **降级日志**：你可以在 Actions 的运行日志中清晰看到 `🔄 策略 1：尝试连接私人服务器...` 与 `🔄 策略 2：服务器不可用，启动降级策略...` 的智能调度过程。

# 开发中的功能
- 牙膏要一点一点挤,显卡要一刀一刀切,PPT要一张一张放,代码要一行一行写,更多功能及优化...敬请期待....

## 🤝 参与共建

一个人写代码挺枯燥的，如果你也是喜欢折腾的同学或者对此感兴趣，欢迎一起来完善这个小工具！

目前项目还有一些小缺点，我也列了一份 **TODO 清单**，如果你刚好会，或者想拿来练手，随时欢迎提 PR：

* **[待填坑] 服务器端代码**：现在脚本可以把数据 POST 到私人服务器，但是服务器那边怎么接、怎么存、怎么推，我还没写完... 有没有大佬帮忙糊一个 FastAPI / Flask 的模板？
* **[已优化] 课程过滤配置**：已支持通过 `COURSE_CONFIG_JSON` 或 `config.json` 配置课程过滤规则，无需再进入代码修改 `STOP_COURSE_NAME`。
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
