"""
Codex Auto Registration Usage Examples
使用示例脚本
"""

import requests
import json
from pathlib import Path

def example_command_line_usage():
    """命令行使用示例"""
    print("=" * 50)
    print("命令行使用示例")
    print("=" * 50)
    
    examples = [
        "# 单次注册模式",
        "python codex_generator_optimized.py",
        "",
        "# 使用HTTP代理注册",
        "python codex_generator_optimized.py --proxy http://127.0.0.1:7890",
        "",
        "# 连续批量注册",
        "python codex_generator_optimized.py --continuous",
        "",
        "# 仅转换格式",
        "python codex_generator_optimized.py --convert-only --output accounts.json",
        "",
        "# 查看帮助",
        "python codex_generator_optimized.py --help"
    ]
    
    for line in examples:
        print(line)

def example_web_api_usage():
    """Web API使用示例"""
    print("\n" + "=" * 50)
    print("Web API使用示例")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    examples = [
        ("# 获取状态", f"curl {base_url}/api/status"),
        ("# 开始单次注册", f"curl -X POST {base_url}/api/start -H 'Content-Type: application/json' -d '{{\"proxy\": \"\", \"continuous\": false}}'"),
        ("# 开始连续注册", f"curl -X POST {base_url}/api/start -H 'Content-Type: application/json' -d '{{\"proxy\": \"\", \"continuous\": true}}'"),
        ("# 停止注册", f"curl -X POST {base_url}/api/stop"),
        ("# 获取日志", f"curl {base_url}/api/logs?lines=100"),
        ("# 列出文件", f"curl {base_url}/api/files"),
        ("# 格式转换", f"curl -X POST {base_url}/api/convert"),
        ("# 性能指标", f"curl {base_url}/api/metrics"),
        ("# 备份列表", f"curl {base_url}/api/backups"),
        ("# 创建备份", f"curl -X POST {base_url}/api/backups"),
    ]
    
    for desc, cmd in examples:
        print(f"{desc}\n{cmd}\n")

def example_docker_usage():
    """Docker使用示例"""
    print("\n" + "=" * 50)
    print("Docker使用示例")
    print("=" * 50)
    
    examples = [
        "# 构建Docker镜像",
        "docker build -t codex-register:latest .",
        "",
        "# 运行Docker容器",
        "docker run -p 5000:5000 -v ./logs:/app/logs codex-register:latest",
        "",
        "# 使用docker-compose",
        "docker-compose up -d",
        "",
        "# 查看日志",
        "docker logs -f codex-register",
        "",
        "# 停止服务",
        "docker-compose down"
    ]
    
    for line in examples:
        print(line)

def example_config_yaml():
    """配置示例"""
    print("\n" + "=" * 50)
    print("配置示例 (config.yaml)")
    print("=" * 50)
    
    config = """
# OpenAI OAuth配置
oauth:
  client_id: "app_EMoamEEZ73f0CkXaXp7hrann"
  issuer: "https://auth.openai.com"
  redirect_uri: "http://localhost:1455/auth/callback"

# 代理配置
proxy:
  enabled: true
  url: "http://127.0.0.1:7890"
  type: "http"

# Web服务器配置
web:
  host: "0.0.0.0"
  port: 5000
  debug: false

# 安全配置
security:
  enable_auth: false
  auth_token: "your-secret-token"
  allowed_ips:
    - "127.0.0.1"
    - "192.168.1.0/24"

# 备份配置
backup:
  enabled: true
  interval: 3600
  max_backups: 10
  backup_dir: "backups"

# 性能配置
performance:
  worker_count: 4
  request_timeout: 30
  connect_timeout: 10
  read_timeout: 20

# 日志配置
logging:
  level: "INFO"
  max_size: "10MB"
  backup_count: 5
"""
    
    print(config)

def example_backup_restore():
    """备份恢复示例"""
    print("\n" + "=" * 50)
    print("备份恢复示例")
    print("=" * 50)
    
    examples = [
        "# 创建备份",
        "curl -X POST http://localhost:5000/api/backups",
        "",
        "# 列出备份",
        "curl http://localhost:5000/api/backups",
        "",
        "# 恢复备份",
        "curl -X POST http://localhost:5000/api/backups/backup_20240101_120000/restore",
        "",
        "# 验证备份",
        "curl http://localhost:5000/api/backups/backup_20240101_120000/verify",
        "",
        "# 删除备份",
        "curl -X DELETE http://localhost:5000/api/backups/backup_20240101_120000"
    ]
    
    for line in examples:
        print(line)

def example_python_api():
    """Python API使用示例"""
    print("\n" + "=" * 50)
    print("Python API使用示例")
    print("=" * 50)
    
    code = """
import requests
import json

class CodexRegisterClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_status(self):
        '''获取系统状态'''
        response = self.session.get(f"{self.base_url}/api/status")
        return response.json()
    
    def start_registration(self, proxy="", continuous=False):
        '''开始注册'''
        data = {
            "proxy": proxy,
            "continuous": continuous
        }
        response = self.session.post(
            f"{self.base_url}/api/start",
            json=data
        )
        return response.json()
    
    def stop_registration(self):
        '''停止注册'''
        response = self.session.post(f"{self.base_url}/api/stop")
        return response.json()
    
    def get_logs(self, lines=100):
        '''获取日志'''
        response = self.session.get(f"{self.base_url}/api/logs?lines={lines}")
        return response.json()
    
    def convert_format(self):
        '''格式转换'''
        response = self.session.post(f"{self.base_url}/api/convert")
        return response.json()
    
    def create_backup(self, name=None):
        '''创建备份'''
        data = {"name": name} if name else {}
        response = self.session.post(f"{self.base_url}/api/backups", json=data)
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = CodexRegisterClient()
    
    # 获取状态
    status = client.get_status()
    print(f"当前状态: {status['is_running']}")
    
    # 开始注册
    result = client.start_registration(proxy="http://127.0.0.1:7890")
    print(f"开始注册: {result}")
    
    # 获取日志
    logs = client.get_logs()
    print(f"最新日志: {logs['logs'][-3:]}")
"""
    
    print(code)

if __name__ == "__main__":
    example_command_line_usage()
    example_web_api_usage()
    example_docker_usage()
    example_config_yaml()
    example_backup_restore()
    example_python_api()
    
    print("\n" + "=" * 50)
    print("更多示例请查看项目文档")
    print("=" * 50)