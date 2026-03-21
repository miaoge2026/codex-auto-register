"""
Codex Auto Registration Web Interface - Enhanced Version with Authentication and Monitoring
增强版Web管理界面，包含身份验证和性能监控
"""

import json
import threading
import time
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import Flask, render_template, request, jsonify, send_file, abort, session

try:
    import yaml
except ImportError:  # pragma: no cover - 开发环境兼容
    yaml = None

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:  # pragma: no cover - 开发环境兼容
    class Limiter:  # type: ignore[override]
        """flask-limiter缺失时的轻量兜底实现。"""

        def __init__(self, *args, **kwargs):
            pass

        def limit(self, _rule):
            def decorator(func):
                return func

            return decorator

    def get_remote_address():
        return request.remote_addr or '127.0.0.1'

from codex_generator_optimized import (
    run_single_registration, 
    convert_to_sub2api_format,
    Config
)

app = Flask(__name__)

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = Path('config.yaml')
    if config_path.exists() and yaml is not None:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

config = load_config()

# 应用配置
app.config['SECRET_KEY'] = config.get('web', {}).get('secret_key', 'codex-auto-register-2026')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 速率限制
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# 安全配置
AUTH_TOKEN = config.get('security', {}).get('auth_token', '')
ENABLE_AUTH = config.get('security', {}).get('enable_auth', False)
ALLOWED_IPS = config.get('security', {}).get('allowed_ips', [])


# 文件路径配置
BASE_DIR = Path('.').resolve()
LOG_FILE = BASE_DIR / 'codex_register.log'
ALLOWED_JSON_SUFFIXES = {'.json'}


def resolve_json_file_path(filename):
    """解析并校验仅允许访问工作目录下的JSON文件。"""
    if not filename:
        raise ValueError('文件名不能为空')

    candidate = Path(filename)
    if candidate.is_absolute():
        raise ValueError('非法文件名')

    resolved = (BASE_DIR / candidate).resolve()
    try:
        resolved.relative_to(BASE_DIR)
    except ValueError as exc:
        raise ValueError('非法文件名') from exc

    if resolved.suffix.lower() not in ALLOWED_JSON_SUFFIXES:
        raise ValueError('仅支持JSON文件')

    return resolved


def _mask_json_payload(data):
    """递归脱敏JSON对象中的敏感token字段。"""
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if key in {'access_token', 'refresh_token', 'id_token'} and isinstance(value, str):
                masked[key] = mask_token(value)
            else:
                masked[key] = _mask_json_payload(value)
        return masked
    if isinstance(data, list):
        return [_mask_json_payload(item) for item in data]
    return data

# 全局状态
registration_status = {
    'is_running': False,
    'is_continuous': False,
    'success_count': 0,
    'fail_count': 0,
    'current_email': '',
    'start_time': None,
    'log_content': [],
    'proxy': config.get('proxy', {}).get('url', ''),
    'performance_metrics': {
        'total_requests': 0,
        'failed_requests': 0,
        'avg_response_time': 0,
        'uptime': 0
    }
}

# 启动时间
START_TIME = time.time()

def require_auth(f):
    """身份验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ENABLE_AUTH:
            return f(*args, **kwargs)
        
        # 检查session
        if 'authenticated' in session and session['authenticated']:
            return f(*args, **kwargs)
        
        # 检查token
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if token and token == AUTH_TOKEN:
            return f(*args, **kwargs)
        
        # IP白名单检查
        client_ip = get_remote_address()
        if client_ip in ALLOWED_IPS:
            return f(*args, **kwargs)
        
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    return decorated_function

def check_auth(username, password):
    """检查用户名密码"""
    # 这里使用简单的token验证，实际应用中应该使用更安全的机制
    expected_token = hashlib.sha256(AUTH_TOKEN.encode()).hexdigest()
    provided_token = hashlib.sha256(password.encode()).hexdigest()
    return username == 'admin' and provided_token == expected_token

@app.route('/login', methods=['POST'])
def login():
    """登录接口"""
    if not ENABLE_AUTH:
        return jsonify({'success': True, 'message': 'Auth disabled'})
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if check_auth(username, password):
        session['authenticated'] = True
        session.permanent = True
        return jsonify({'success': True, 'message': 'Login successful'})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    """登出接口"""
    session.pop('authenticated', None)
    return jsonify({'success': True, 'message': 'Logout successful'})

@app.route('/')
@require_auth
def index():
    """主页面"""
    return render_template('index.html', status=registration_status, config=config)

@app.route('/api/start', methods=['POST'])
@require_auth
@limiter.limit("10 per minute")
def start_registration():
    """开始注册"""
    if registration_status['is_running']:
        return jsonify({'success': False, 'message': '注册已在运行中'})
    
    data = request.json
    proxy = data.get('proxy', '')
    continuous = data.get('continuous', False)
    
    # 保存代理设置
    registration_status['proxy'] = proxy
    
    # 启动注册线程
    thread = threading.Thread(
        target=run_registration_thread,
        args=(proxy if proxy else None, continuous),
        daemon=True
    )
    thread.start()
    
    return jsonify({'success': True, 'message': '注册已启动'})

@app.route('/api/stop', methods=['POST'])
@require_auth
def stop_registration():
    """停止注册"""
    if not registration_status['is_running']:
        return jsonify({'success': False, 'message': '没有正在运行的注册任务'})
    
    registration_status['is_running'] = False
    return jsonify({'success': True, 'message': '注册已停止'})

@app.route('/api/status')
@require_auth
def get_status():
    """获取状态"""
    # 更新性能指标
    uptime = time.time() - START_TIME
    registration_status['performance_metrics']['uptime'] = uptime
    
    return jsonify(registration_status)

@app.route('/api/logs')
@require_auth
def get_logs():
    """获取日志"""
    lines = request.args.get('lines', 100, type=int)
    logs = registration_status['log_content'][-lines:]
    return jsonify({'logs': logs})

@app.route('/api/files')
@require_auth
def list_files():
    """列出文件"""
    files = []
    current_dir = Path('.')
    
    for file in current_dir.glob('*.json'):
        if file.is_file():
            stat = file.stat()
            files.append({
                'name': file.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    return jsonify({'files': files})

@app.route('/api/files/<filename>')
@require_auth
def get_file(filename):
    """获取文件内容"""
    try:
        file_path = resolve_json_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'success': False, 'message': '文件不存在'})
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 敏感信息脱敏
        content = mask_sensitive_info(content)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': content,
            'size': len(content)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'读取文件失败: {e}'})

@app.route('/api/files/<filename>/download')
@require_auth
def download_file(filename):
    """下载文件"""
    try:
        file_path = resolve_json_file_path(filename)
        if not file_path.exists() or not file_path.is_file():
            abort(404)
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        abort(500)

@app.route('/api/convert', methods=['POST'])
@require_auth
def convert_format():
    """转换格式"""
    try:
        data = request.json
        input_path = resolve_json_file_path(data.get('input_file', Config.OUTPUT_FILE))
        output_path = resolve_json_file_path(data.get('output_file', Config.SUB2API_OUTPUT_FILE))

        convert_to_sub2api_format(str(input_path), str(output_path))
        
        return jsonify({'success': True, 'message': '格式转换完成'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'转换失败: {e}'})

@app.route('/api/config', methods=['GET', 'POST'])
@require_auth
def config_management():
    """配置管理"""
    if request.method == 'GET':
        return jsonify({
            'proxy': registration_status['proxy'],
            'default_proxy': Config.DEFAULT_PROXY,
            'security': {
                'enable_auth': ENABLE_AUTH,
                'allowed_ips': ALLOWED_IPS
            }
        })
    
    elif request.method == 'POST':
        data = request.json
        proxy = data.get('proxy', '')
        
        registration_status['proxy'] = proxy
        
        return jsonify({'success': True, 'message': '配置已更新'})

@app.route('/api/metrics')
@require_auth
def get_metrics():
    """获取性能指标"""
    metrics = registration_status['performance_metrics'].copy()
    metrics['start_time'] = START_TIME
    metrics['current_time'] = time.time()
    metrics['memory_usage'] = get_memory_usage()
    return jsonify(metrics)

def mask_sensitive_info(content):
    """脱敏敏感信息，支持标准JSON和JSON Lines。"""
    try:
        data = json.loads(content)
        return json.dumps(_mask_json_payload(data), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        sanitized_lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                sanitized_lines.append(json.dumps(_mask_json_payload(json.loads(stripped)), ensure_ascii=False))
            except json.JSONDecodeError:
                return content
        return '\n'.join(sanitized_lines)

def mask_token(token):
    """脱敏token"""
    if len(token) < 20:
        return token
    return token[:10] + '...' + token[-10:]

def get_memory_usage():
    """获取内存使用情况"""
    try:
        import psutil
        process = psutil.Process()
        return {
            'memory_percent': process.memory_percent(),
            'memory_info': process.memory_info()._asdict()
        }
    except:
        return {'memory_percent': 0, 'memory_info': {}}

def run_registration_thread(proxy=None, continuous=False):
    """运行注册线程"""
    global registration_status
    
    registration_status['is_running'] = True
    registration_status['is_continuous'] = continuous
    registration_status['start_time'] = datetime.now()
    
    try:
        while registration_status['is_running']:
            # 运行单次注册
            result = run_single_registration(proxy=proxy)
            
            if result:
                registration_status['success_count'] += 1
                registration_status['current_email'] = result.get('email', '')
                
                # 自动转换格式
                try:
                    convert_to_sub2api_format(Config.OUTPUT_FILE, Config.SUB2API_OUTPUT_FILE)
                except Exception as e:
                    log_error(f"格式转换失败: {e}")
            else:
                registration_status['fail_count'] += 1
            
            # 如果不是连续模式，退出循环
            if not continuous:
                break
            
            # 等待间隔
            time.sleep(config.get('registration', {}).get('retry_delay', 5))
            
    except Exception as e:
        log_error(f"注册线程异常: {e}")
    finally:
        registration_status['is_running'] = False
        registration_status['is_continuous'] = False

def log_message(message, level='INFO'):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {level}: {message}"
    
    # 添加到内存日志
    registration_status['log_content'].append(log_entry)
    
    # 限制日志条数
    if len(registration_status['log_content']) > 1000:
        registration_status['log_content'] = registration_status['log_content'][-500:]
    
    # 写入日志文件，避免污染账户数据
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def log_error(message):
    """记录错误"""
    log_message(message, 'ERROR')

def log_info(message):
    """记录信息"""
    log_message(message, 'INFO')

if __name__ == '__main__':
    print("=" * 50)
    print("Codex Auto Registration Web Interface - Enhanced")
    print("=" * 50)
    print(f"访问地址: http://{config.get('web', {}).get('host', '0.0.0.0')}:{config.get('web', {}).get('port', 5000)}")
    print(f"身份验证: {'已启用' if ENABLE_AUTH else '已禁用'}")
    print("=" * 50)
    app.run(
        host=config.get('web', {}).get('host', '0.0.0.0'),
        port=config.get('web', {}).get('port', 5000),
        debug=config.get('web', {}).get('debug', False)
    )