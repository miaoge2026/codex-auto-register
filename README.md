# Codex Auto Registration Tool 🚀

一个用于自动化注册OpenAI Codex账号的Python工具，支持批量注册、自动邮箱验证和sub2api格式转换。

## 功能特性

✨ **核心功能**
- 自动注册OpenAI Codex账号
- 集成TempMail.lol临时邮箱服务
- 自动验证码提取和验证
- OAuth 2.0授权流程
- 批量注册支持
- 自动转换为sub2api格式

🔧 **技术特性**
- 模块化设计，易于扩展
- 完善的错误处理和日志系统
- 命令行参数支持
- 类型注解，代码质量高
- 支持代理配置
- 详细的运行日志

## 环境要求

- Python 3.7+
- pip包管理器

## 安装步骤

### 1. 克隆代码
```bash
git clone <repository-url>
cd codex_auto_register
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 依赖库
- `requests` - HTTP请求库
- `curl_cffi` - 模拟浏览器请求
- `dataclasses` - 数据结构（Python 3.7+内置）

## 快速开始

### 单次注册模式
```bash
python codex_generator_optimized.py
```

### 使用代理注册
```bash
python codex_generator_optimized.py --proxy http://127.0.0.1:7890
```

### 连续批量注册
```bash
python codex_generator_optimized.py --continuous
```

### 仅转换格式
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
```

## 使用说明

### 1. 单次注册
```bash
# 不使用代理
python codex_generator_optimized.py

# 使用HTTP代理
python codex_generator_optimized.py --proxy http://127.0.0.1:7890

# 使用SOCKS5代理
python codex_generator_optimized.py --proxy socks5://127.0.0.1:1080
```

### 2. 批量注册
```bash
# 连续注册模式，直到手动停止
python codex_generator_optimized.py --continuous

# 使用自定义代理
python codex_generator_optimized.py --continuous --proxy http://your-proxy:port
```

### 3. 格式转换
```bash
# 将注册好的账号转换为sub2api格式
python codex_generator_optimized.py --convert-only

# 指定输入输出文件
python codex_generator_optimized.py --convert-only --output my_accounts.json
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
```

## 常见问题

### Q: 注册失败，显示"Invalid authorization step"
**A**: 这可能是OpenAI API流程更新导致的。请：
1. 检查是否有最新版本
2. 查看日志文件获取详细错误信息
3. 尝试更换代理节点

### Q: 无法连接到代理服务器
**A**: 
1. 检查代理地址和端口是否正确
2. 确认代理服务器是否运行
3. 尝试不使用代理测试网络连接

### Q: 邮箱收不到验证码
**A**: 
1. 检查TempMail.lol服务是否可用
2. 增加等待超时时间（修改代码中的OTP_TIMEOUT）
3. 尝试更换网络环境

### Q: 如何导入到sub2api
**A**: 
1. 运行转换命令生成sub2api_import.json
2. 登录sub2api管理后台
3. 进入"数据管理"页面
4. 点击"导入数据"上传文件

## 日志说明

程序会生成详细的运行日志：

### 日志级别
- `INFO`: 常规操作信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `DEBUG`: 调试信息（需在代码中启用）

### 日志文件
- 控制台输出：实时显示运行状态
- 日志文件：`codex_register.log`（自动保存）

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

## 性能优化建议

### 1. 代理池配置
使用多个代理节点轮换注册，提高成功率。

### 2. 注册间隔
在连续注册模式下，建议设置适当的等待时间：
```python
# 在代码中修改 sleep 时间
time.sleep(5)  # 增加到10-30秒
```

### 3. 并发控制
当前版本为单线程注册，如需并发需要自行扩展。

## 扩展开发

### 添加新的邮箱服务
1. 创建新的邮箱客户端类
2. 实现`wait_for_message`方法
3. 在`create_temp_email`函数中添加选项

### 支持新的输出格式
1. 在`convert_account_format`函数中添加格式转换逻辑
2. 创建新的输出函数
3. 添加命令行参数

## 贡献指南

欢迎提交Issue和Pull Request！

### 提交Issue
- 提供详细的错误信息
- 包含日志文件内容
- 说明复现步骤

### 提交PR
- 遵循代码风格规范
- 添加必要的注释
- 更新文档

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue或联系开发者。

---

**免责声明**: 本工具仅供学习和研究使用，请勿用于商业用途。使用本工具产生的任何后果，开发者不承担任何责任。