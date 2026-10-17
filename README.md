# 🌱 Mia Agent 1.0

一个适合 Python 初学者理解和展示的 Streamlit 学习助手。

**在线体验：[Mia Agent 1.0](https://mia-agent-lixingfei4.streamlit.app/)**

公开版默认免费演示模式，计算、七天计划生成与文件下载已在云端验证。自由 AI 聊天需配置服务端 Groq 密钥和体验口令。

- **免费演示**：无需账户或密钥；通过规则调用安全计算器、生成七天学习计划并下载 Markdown 文件。此模式不是大模型聊天。
- **AI 聊天**：可选 Groq API；模型选择工具 → Python 执行 → 结果返回模型。显示真实工具调用记录。
- 默认不调用 API，不产生模型费用。不提供网页搜索、任意代码执行或电脑文件访问。

## 在 Mac 上开始

建议安装 [Python 3.12 或 3.13](https://www.python.org/downloads/)，避免使用过新的版本导致依赖安装失败。
在项目文件夹打开终端，依次运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

打开终端显示的本机地址，通常为 http://localhost:8501 。此地址只有自己电脑可用，不能作为公开演示链接。

依次输入「你好」「帮我计算 125 × 36」「制定 7 天 Python 学习计划」，展开工具记录，再点击下载按钮。

## 接入真正的 AI（可选）

核查日期：2026-10-18。

1. 前往 https://console.groq.com 注册并创建 API Key。确认账户保持 **Free**，不要升级 Developer 或添加付费方案。
2. 官方提供 Free Plan，但会限制请求和 token；模型可用性、额度、地区及网络可达性以个人控制台为准，不保证永久免费或在所有地区可用。超过限制会报错，等待恢复。
3. 复制 `.streamlit/secrets.toml.example` 为 `.streamlit/secrets.toml`，在自己电脑填写密钥和体验口令。不要把密钥发到聊天或提交 GitHub。
4. 重启应用，切换「AI 聊天」并填写体验口令。默认模型 `openai/gpt-oss-20b`，如控制台不支持，在 Secrets 修改 `GROQ_MODEL` 为支持工具调用的可用模型。
5. 测试普通问答、计算和学习计划下载。无密钥时只能测试演示模式；模拟测试不能证明真实 API 可用。

参考：[Groq 免费限额](https://console.groq.com/docs/rate-limits)、[计费条件](https://console.groq.com/docs/billing-faqs)、[工具调用](https://console.groq.com/docs/tool-use/overview)。

## 部署为可分享链接

[Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) 官方提供免费托管，需账户、GitHub 授权和可用的网络环境。

1. 把本文件夹的源码上传到 GitHub 仓库，**排除 `.venv`、`.env` 和 `secrets.toml`**。
2. 打开 https://share.streamlit.io ，使用 GitHub 登录并完成所需授权。
3. Create app → 选择仓库、`main` 分支和 `app.py`；Python 选择 3.12。
4. 第一次直接部署免费演示版，不填任何密钥。
5. 如需 AI：Advanced settings → Secrets，粘贴示例中的三项并替换为真实值。Secrets 不写入代码。
6. Deploy 成功后，复制实际生成的 `https://…streamlit.app` 链接，用无痕窗口复测计算和下载后分享。

部署说明：https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## 使用限制与边界

- 输入最多 1000 字符；每会话 20 次提交，至少间隔 3 秒。清空对话不会清空额度。
- 所有访客共享每小时 30 次 API 请求上限（一次对话可能请求三次），每次最多 1200 输出 token、最多三轮模型请求。
- 共享额度只保存在进程内，重启、多进程或重新建立会话会影响限额；这些是演示保护，不是严密的计费或反滥用系统。应保持 Free 账户。
- AI 模式强制配置体验口令；只向可信体验者提供口令。演示模式公开可用。
- 计算仅允许有限算术语法，禁用函数、名称、属性访问；限制表达式长度、复杂度、指数和结果大小。
- AI 对话发送到 Groq；应用不主动把对话存入数据库，但托管平台和 API 服务有各自的数据政策。不要输入隐私信息。

## 读代码的顺序

1. `tools.py`：理解函数、参数、返回值。
2. `agent.py`：演示规则和真正的模型工具调用循环。
3. `app.py`：网页、聊天历史、下载和额度控制。

运行验证：`python -m unittest discover -s tests -v`。
