# DeepSeek AI 助手 · 专业版

基于 Python tkinter 的桌面 AI 聊天客户端，支持多种大模型 API 服务商。

## 功能特性

- **多服务商支持**：DeepSeek / 英伟达免费模型 / OpenAI 兼容 API / 自定义模型
- **流式输出**：打字机效果实时显示回复
- **会话管理**：左侧边栏历史对话列表，点击加载
- **模型切换**：下拉选择或手动输入模型名称，切换服务商自动更新
- **Token 统计**：实时显示今日使用量与总计使用量，每日自动重置
- **深色主题**：一键切换浅色/深色主题
- **导出功能**：支持导出 TXT / HTML 格式
- **一键切换**：菜单栏快速切换服务商

## 支持的服务商

| 服务商 | 类型 | 说明 |
|--------|------|------|
| DeepSeek | 官方 API | 需 API 密钥，新用户赠 5 元额度 |
| 英伟达免费模型 | 免费 | 60 请求/分钟，完全免费 |
| OpenAI | API | 支持 OpenAI / OpenRouter / Groq 等 |
| 自定义模型 | 任意 OpenAI 兼容 API | 适合国内代理或私有部署 |

## 快速开始

### 环境要求

- Python 3.6+
- requests 库

### 安装依赖

```bash
pip install requests
```

### 运行

```bash
python AI-toolsok.py
```

### 配置 API 密钥

1. 启动程序后点击菜单栏 **设置 → API 设置**
2. 在对应服务商选项卡中输入 API 密钥和地址
3. 点击 **测试连接** 验证
4. 点击 **保存设置**

### 获取密钥

- DeepSeek：https://platform.deepseek.com
- 英伟达：https://build.nvidia.com

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+N | 新建对话 |
| Ctrl+S | 保存对话(TXT) |
| Ctrl+C | 复制最后回复 |
| Enter | 发送消息 |

## 配置文件

| 文件 | 说明 |
|------|------|
| `deepseek_config.json` | API 密钥、服务商、模型等设置 |
| `config.yaml` | 完整配置（含多服务商 API 地址和每日限额） |
| `.env` | 密钥环境变量（备选） |
| `chat_history/` | 自动保存的对话历史目录 |

## 常见问题

### API 错误 429 Too Many Requests

请求频率过高触发速率限制，程序会自动重试 3 次（指数退避）。如持续失败：
- 检查 DeepSeek 账户余额：https://platform.deepseek.com
- 切换至英伟达免费模型（60 次/分钟，免费）
- 降低请求频率

### API 错误 500 max_tokens 超限

`max_tokens` 参数超出 API 上限（65536），程序已自动修正，可在通用设置中调整。

### 自定义模型连接测试通过但无法使用

确认设置中已将 **当前使用** 切换为 **自定义模型**，且模型名称填写正确。

## 作者

- **靳好宝**
- 邮箱：uulov@qq.com
