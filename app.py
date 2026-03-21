"""
Codex Auto Registration Web Interface
Web管理界面 for Codex自动注册工具
"""

from __future__ import annotations

import threading
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template, request, send_file

from codex_generator_optimized import Config, convert_to_sub2api_format, run_single_registration

app = Flask(__name__)
app.config['SECRET_KEY'] = 'codex-auto-register-2026'

ALLOWED_FILE_SUFFIXES = {'.json'}
MAX_LOG_LINES = 500
MAX_LOG_RESPONSE_LINES = 500
status_lock = threading.Lock()

# 全局状态
registration_status = {
    'is_running': False,
    'is_continuous': False,
    'success_count': 0,
    'fail_count': 0,
    'current_email': '',
    'start_time': None,
    'log_content': [],
    'proxy': Config.DEFAULT_PROXY,
}

# 日志文件路径
LOG_FILE = 'codex_register.log'
ACCOUNTS_FILE = Config.OUTPUT_FILE
SUB2API_FILE = Config.SUB2API_OUTPUT_FILE


def _safe_json() -> dict[str, Any]:
    """安全读取JSON请求体。"""
    return request.get_json(silent=True) or {}


def _update_status(**updates: Any) -> None:
    """线程安全地更新状态。"""
    with status_lock:
        registration_status.update(updates)


def _append_log(log_entry: str) -> None:
    """线程安全地追加日志并控制最大数量。"""
    with status_lock:
        log_content = registration_status['log_content']
        log_content.append(log_entry)
        if len(log_content) > MAX_LOG_LINES:
            registration_status['log_content'] = log_content[-MAX_LOG_LINES:]


def _snapshot_status() -> dict[str, Any]:
    """生成可序列化的状态快照。"""
    with status_lock:
        snapshot = deepcopy(registration_status)

    start_time = snapshot.get('start_time')
    if isinstance(start_time, datetime):
        snapshot['start_time'] = start_time.isoformat()
    return snapshot


def _resolve_json_file(filename: str) -> Path:
    """只允许访问当前目录下的JSON文件，避免路径穿越。"""
    candidate = Path(filename)
    if candidate.name != filename or candidate.suffix.lower() not in ALLOWED_FILE_SUFFIXES:
        abort(400)

    file_path = Path.cwd() / candidate.name
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    return file_path


def run_registration_thread(proxy: str | None = None, continuous: bool = False) -> None:
    """运行注册线程。"""
    _update_status(
        is_running=True,
        is_continuous=continuous,
        start_time=datetime.now(),
        current_email='',
    )

    try:
        while _snapshot_status()['is_running']:
            result = run_single_registration(proxy=proxy)

            if result:
                with status_lock:
                    registration_status['success_count'] += 1
                    registration_status['current_email'] = result.get('email', '')

                try:
                    convert_to_sub2api_format(ACCOUNTS_FILE, SUB2API_FILE)
                except Exception as exc:
                    log_error(f"格式转换失败: {exc}")
            else:
                with status_lock:
                    registration_status['fail_count'] += 1

            if not continuous:
                break

            time.sleep(5)

    except Exception as exc:
        log_error(f"注册线程异常: {exc}")
    finally:
        _update_status(is_running=False, is_continuous=False)


def log_message(message: str, level: str = 'INFO') -> None:
    """记录日志。"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {level}: {message}"
    _append_log(log_entry)

    with open(LOG_FILE, 'a', encoding='utf-8') as file_obj:
        file_obj.write(log_entry + '\n')


def log_error(message: str) -> None:
    """记录错误。"""
    log_message(message, 'ERROR')


def log_info(message: str) -> None:
    """记录信息。"""
    log_message(message, 'INFO')


@app.route('/')
def index():
    """主页面。"""
    return render_template('index.html', status=_snapshot_status())


@app.route('/api/start', methods=['POST'])
def start_registration():
    """开始注册。"""
    if _snapshot_status()['is_running']:
        return jsonify({'success': False, 'message': '注册已在运行中'})

    data = _safe_json()
    proxy = str(data.get('proxy', '')).strip()
    continuous = bool(data.get('continuous', False))

    _update_status(proxy=proxy)

    thread = threading.Thread(
        target=run_registration_thread,
        args=(proxy if proxy else None, continuous),
        daemon=True,
    )
    thread.start()

    log_info(f"开始{'连续' if continuous else '单次'}注册，代理: {proxy or '无'}")
    return jsonify({'success': True, 'message': '注册已启动'})


@app.route('/api/stop', methods=['POST'])
def stop_registration():
    """停止注册。"""
    if not _snapshot_status()['is_running']:
        return jsonify({'success': False, 'message': '没有正在运行的注册任务'})

    _update_status(is_running=False)
    log_info('停止注册任务')
    return jsonify({'success': True, 'message': '注册已停止'})


@app.route('/api/status')
def get_status():
    """获取状态。"""
    return jsonify(_snapshot_status())


@app.route('/api/logs')
def get_logs():
    """获取日志。"""
    requested_lines = request.args.get('lines', 100, type=int)
    lines = max(1, min(requested_lines, MAX_LOG_RESPONSE_LINES))
    logs = _snapshot_status()['log_content'][-lines:]
    return jsonify({'logs': logs})


@app.route('/api/files')
def list_files():
    """列出文件。"""
    files = []
    for file_path in sorted(Path.cwd().glob('*.json')):
        if file_path.is_file():
            stat = file_path.stat()
            files.append(
                {
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

    return jsonify({'files': files})


@app.route('/api/files/<filename>')
def get_file(filename: str):
    """获取文件内容。"""
    try:
        file_path = _resolve_json_file(filename)
        with open(file_path, 'r', encoding='utf-8') as file_obj:
            content = file_obj.read()

        return jsonify(
            {
                'success': True,
                'filename': file_path.name,
                'content': content,
                'size': len(content),
            }
        )
    except Exception as exc:
        if getattr(exc, 'code', None):
            raise
        return jsonify({'success': False, 'message': f'读取文件失败: {exc}'})


@app.route('/api/files/<filename>/download')
def download_file(filename: str):
    """下载文件。"""
    return send_file(_resolve_json_file(filename), as_attachment=True)


@app.route('/api/convert', methods=['POST'])
def convert_format():
    """转换格式。"""
    try:
        data = _safe_json()
        input_file = str(data.get('input_file', ACCOUNTS_FILE)).strip() or ACCOUNTS_FILE
        output_file = str(data.get('output_file', SUB2API_FILE)).strip() or SUB2API_FILE

        convert_to_sub2api_format(input_file, output_file)

        log_info(f"格式转换完成: {input_file} -> {output_file}")
        return jsonify({'success': True, 'message': '格式转换完成'})
    except Exception as exc:
        log_error(f"格式转换失败: {exc}")
        return jsonify({'success': False, 'message': f'转换失败: {exc}'})


@app.route('/api/config', methods=['GET', 'POST'])
def config_management():
    """配置管理。"""
    if request.method == 'GET':
        return jsonify({'proxy': _snapshot_status()['proxy'], 'default_proxy': Config.DEFAULT_PROXY})

    data = _safe_json()
    proxy = str(data.get('proxy', '')).strip()

    _update_status(proxy=proxy)
    log_info(f"更新代理设置: {proxy or '无'}")

    return jsonify({'success': True, 'message': '配置已更新'})


def create_templates() -> None:
    """确保模板目录存在。"""
    Path('templates').mkdir(exist_ok=True)


if __name__ == '__main__':
    create_templates()
    print('=' * 50)
    print('Codex Auto Registration Web Interface')
    print('=' * 50)
    print('Web管理界面已启动！')
    print('访问地址: http://localhost:5000')
    print('=' * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
