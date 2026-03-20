# Codex Auto Registration Tool 🚀

一个用于自动化注册OpenAI Codex账号的Python工具，支持批量注册、自动邮箱验证和sub2api格式转换。提供命令行和Web界面两种使用方式。

## 功能特性

✨ **核心功能**
- 自动注册OpenAI Codex账号
- 集成TempMail.lol临时邮箱服务
- 自动验证码提取和验证
- OAuth 2.0授权流程
- 批量注册支持
- 自动转换为sub2api格式
- Web管理界面

🔧 **技术特性**
- 模块化设计，易于扩展
- 完善的错误处理和日志系统
- 命令行参数支持
- Web管理界面
- 类型注解，代码质量高
- 支持代理配置
- 详细的运行日志

## 环境要求

- Python 3.7+
- pip包管理器

## 安装步骤

### 1. 克隆代码
```bash
git clone https://github.com/miaoge2026/codex-auto-register.git
cd codex-auto-register
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 依赖库
- `Flask` - Web框架
- `requests` - HTTP请求库
- `curl_cffi` - 模拟浏览器请求
- `Werkzeug` - Web服务器网关接口
- `Jinja2` - 模板引擎

## 🚀 快速开始

### 方式一：Web管理界面（推荐）

#### 启动Web服务
```bash
python app.py
```

#### 访问界面
打开浏览器访问: **http://localhost:5000**

#### Web界面功能
- 🎮 **控制面板**：单次/连续注册模式切换
- 📊 **实时监控**：成功/失败统计、当前邮箱显示
- 📝 **日志查看**：实时日志更新、自动滚动
- 📁 **文件管理**：文件预览、下载功能
- 🔧 **配置管理**：代理设置、参数配置

### 方式二：命令行模式

#### 单次注册模式
```bash
python codex_generator_optimized.py
```

#### 使用代理注册
```bash
python codex_generator_optimized.py --proxy http://127.0.0.1:7890
```

#### 连续批量注册
```bash
python codex_generator_optimized.py --continuous
```

#### 仅转换格式
```bash
python codex_generator_optimized.py --convert-only --output accounts.json
```

## 命令行参数

| 参数 | 缩写 | 说明 | 默认值 |
|------|------|------|---------|
| `--proxy` | `-p` | 代理服务器地址 | `http://127.0.0.1:7890` |
| `--output` | `-o` | 输出文件名 | `accounts.json` |
| `--convert-only` | `-c` | 仅转换格式模式 | `False` |
| `--continuous` | `-C` | 连续注册模式 | `False` |
| `--help` | `-h` | 显示帮助信息 | - |

## 🌐 Web界面使用说明

### 主界面布局
```
┌─────────────────────────────────────────────────────────┐
│ Codex Auto Registration - 状态指示器                    │
├─────────────┬───────────────────────────────────────────┤
│ 控制面板    │ 运行日志                                  │
│ - 代理设置  │ - 实时日志更新                            │
│ - 开始/停止 │ - 自动滚动                                │
│ - 模式选择  │                                           │
├─────────────┼───────────────────────────────────────────┤
│ 统计信息    │ 文件管理                                  │
│ - 成功/失败 │ - 文件列表                                │
│ - 当前邮箱  │ - 预览/下载                               │
└─────────────┴───────────────────────────────────────────┘
```

### 操作步骤
1. **配置代理**（可选）：在控制面板输入代理地址
2. **选择模式**：
   - 点击"单次注册"进行一次性注册
   - 点击"连续注册"进行批量注册
3. **监控状态**：实时查看运行状态和统计信息
4. **查看日志**：在日志面板查看实时输出
5. **管理文件**：在文件管理面板预览或下载生成的文件

### 功能按钮说明
- 🟢 **单次注册**：执行一次注册流程
- 🔵 **连续注册**：持续注册直到手动停止
- 🔴 **停止**：立即停止当前注册任务
- 🔄 **刷新**：手动刷新日志和文件列表

## 配置文件

### 默认配置（无需修改）
```python
# 在 codex_generator_optimized.py 中
class Config:
    OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
    OAUTH_ISSUER = "https://auth.openai.com"
    DEFAULT_PROXY = "http://127.0.0.1:7890"
    OUTPUT_FILE = "accounts.json"
    SUB2API_OUTPUT_FILE = "sub2api_import.json"
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 5000
```

## 使用说明

### 1. Web界面操作
```bash
# 启动Web服务
python app.py

# 访问 http://localhost:5000
# 在浏览器中配置代理（如果需要）
# 点击"单次注册"或"连续注册"开始
```

### 2. 命令行操作
```bash
# 不使用代理
python codex_generator_optimized.py

# 使用HTTP代理
python codex_generator_optimized.py --proxy http://127.0.0.1:7890

# 使用SOCKS5代理
python codex_generator_optimized.py --proxy socks5://127.0.0.1:1080

# 连续注册模式
python codex_generator_optimized.py --continuous
```

### 3. 格式转换
```bash
# 将注册好的账号转换为sub2api格式
python codex_generator_optimized.py --convert-only

# 指定输入输出文件
python codex_generator_optimized.py --convert-only --output my_accounts.json

# 或者在Web界面中点击"格式转换"按钮
```

### 4. 查看日志
```bash
# 运行时会自动生成日志文件
tail -f codex_register.log
```

## 输出文件

### accounts.json
注册成功的账号信息，每行一个JSON对象：
```json
{
  "id_token": "...",
  "access_token": "...",
  "refresh_token": "...",
  "account_id": "...",
  "last_refresh": "2026-03-20T05:29:48Z",
  "email": "user@example.com",
  "type": "codex",
  "expired": "2026-03-20T06:29:48Z"
}
```

### sub2api_import.json
sub2api平台的导入格式：
```json
{
  "exported_at": "2026-03-20T05:30:15Z",
  "proxies": [],
  "accounts": [
    {
      "name": "user@example.com",
      "platform": "openai",
      "type": "oauth",
      "credentials": {
        "access_token": "...",
        "refresh_token": "...",
        "chatgpt_account_id": "...",
        "model_mapping": {
          "gpt-5.4": "gpt-5.4",
          "gpt-5.3-codex": "gpt-5.3-codex"
        }
      }
    }
  ]
}
```

## 代理配置

### 支持代理类型
- HTTP代理
- HTTPS代理
- SOCKS5代理

### 代理格式
```bash
# HTTP/HTTPS
http://username:password@host:port
http://host:port

# SOCKS5
socks5://username:password@host:port
socks5://host:port
```

### 推荐代理设置
```bash
# 美国或日本节点（避免中国、香港、俄罗斯节点）
python codex_generator_optimized.py --proxy http://us-proxy.example.com:8080

# 在Web界面中输入代理地址
```

## 常见问题

### Q: 注册失败，显示"Invalid authorization step"
**A**: 这可能是OpenAI API流程更新导致的。请：
1. 检查是否有最新版本
2. 查看日志文件获取详细错误信息
3. 尝试更换代理节点
4. 在Web界面中查看详细错误日志

### Q: 无法连接到代理服务器
**A**: 
1. 检查代理地址和端口是否正确
2. 确认代理服务器是否运行
3. 尝试不使用代理测试网络连接
4. 在Web界面中验证代理设置

### Q: 邮箱收不到验证码
**A**: 
1. 检查TempMail.lol服务是否可用
2. 增加等待超时时间（修改代码中的OTP_TIMEOUT）
3. 尝试更换网络环境
4. 在Web界面中查看邮件接收日志

### Q: 如何导入到sub2api
**A**: 
1. **命令行方式**：
   ```bash
   python codex_generator_optimized.py --convert-only
   ```
2. **Web界面方式**：
   - 注册完成后自动转换
   - 或在文件管理面板中手动转换
3. 登录sub2api管理后台
4. 进入"数据管理"页面
5. 点击"导入数据"上传`sub2api_import.json`文件

### Q: Web界面无法访问
**A**: 
1. 确认服务已启动：`python app.py`
2. 检查端口是否被占用（默认5000）
3. 确认防火墙设置
4. 尝试访问 `http://localhost:5000` 或 `http://127.0.0.1:5000`

## 日志说明

程序会生成详细的运行日志：

### 日志级别
- `INFO`: 常规操作信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `DEBUG`: 调试信息（需在代码中启用）

### 日志文件
- **控制台输出**：实时显示运行状态
- **Web界面日志**：实时日志面板
- **日志文件**：`codex_register.log`（自动保存）

## 错误代码

| 代码 | 说明 | 解决方案 |
|------|------|----------|
| 401 | 认证失败 | 检查代理或网络连接 |
| 403 | 权限拒绝 | 更换代理节点 |
| 429 | 请求过多 | 降低注册频率 |
| 500 | 服务器错误 | 重试或稍后尝试 |

## 安全注意事项

⚠️ **重要提醒**
1. 请遵守OpenAI的使用条款
2. 不要滥用此工具进行大规模注册
3. 合理控制注册频率，避免被封禁
4. 妥善保管生成的账号信息
5. 使用高质量的代理服务器
6. Web界面建议添加身份验证
7. 使用HTTPS加密通信（生产环境）

## 性能优化建议

### 1. 代理池配置
使用多个代理节点轮换注册，提高成功率。

### 2. 注册间隔
在连续注册模式下，建议设置适当的等待时间：
```python
# 在代码中修改 sleep 时间
time.sleep(5)  # 增加到10-30秒
```

### 3. Web界面优化
- 使用Gunicorn部署生产环境
- 配置Nginx反向代理
- 启用Gzip压缩

### 4. 并发控制
当前版本为单线程注册，如需并发需要自行扩展。

## 部署建议

### 开发环境
```bash
python app.py
```

### 生产环境
```bash
# 使用Gunicorn部署
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 或使用Docker
docker build -t codex-register .
docker run -p 5000:5000 codex-register

# 使用Nginx反向代理
# 配置SSL证书
```

### Docker部署
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 扩展开发

### 添加新的邮箱服务
1. 创建新的邮箱客户端类
2. 实现`wait_for_message`方法
3. 在`create_temp_email`函数中添加选项

### 支持新的输出格式
1. 在`convert_account_format`函数中添加格式转换逻辑
2. 创建新的输出函数
3. 添加命令行参数

### 扩展Web界面
1. 在`app.py`中添加新的API端点
2. 在模板中添加新的页面元素
3. 添加JavaScript交互逻辑

## API接口文档

### Web API端点

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/` | 主页面 |
| `POST` | `/api/start` | 开始注册 |
| `POST` | `/api/stop` | 停止注册 |
| `GET` | `/api/status` | 获取状态 |
| `GET` | `/api/logs` | 获取日志 |
| `GET` | `/api/files` | 文件列表 |
| `GET` | `/api/files/<filename>` | 查看文件 |
| `POST` | `/api/convert` | 格式转换 |
| `GET/POST` | `/api/config` | 配置管理 |

## 贡献指南

欢迎提交Issue和Pull Request！

### 提交Issue
- 提供详细的错误信息
- 包含日志文件内容
- 说明复现步骤
- 使用Web界面截图（如果适用）

### 提交PR
- 遵循代码风格规范
- 添加必要的注释
- 更新文档
- 测试Web界面功能

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或联系开发者。

---

**免责声明**: 本工具仅供学习和研究使用，请勿用于商业用途。使用本工具产生的任何后果，开发者不承担任何责任。