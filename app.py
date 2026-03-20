"""
Codex Auto Registration Web Interface
Web管理界面 for Codex自动注册工具
"""

import os
import json
import threading
import time
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, abort

from codex_generator_optimized import (
    run_single_registration, 
    convert_to_sub2api_format,
    Config
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'codex-auto-register-2026'

# 全局状态
registration_status = {
    'is_running': False,
    'is_continuous': False,
    'success_count': 0,
    'fail_count': 0,
    'current_email': '',
    'start_time': None,
    'log_content': [],
    'proxy': Config.DEFAULT_PROXY
}

# 日志文件路径
LOG_FILE = 'codex_register.log'
ACCOUNTS_FILE = Config.OUTPUT_FILE
SUB2API_FILE = Config.SUB2API_OUTPUT_FILE

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
                    convert_to_sub2api_format(ACCOUNTS_FILE, SUB2API_FILE)
                except Exception as e:
                    log_error(f"格式转换失败: {e}")
            else:
                registration_status['fail_count'] += 1
            
            # 如果不是连续模式，退出循环
            if not continuous:
                break
            
            # 等待间隔
            time.sleep(5)
            
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
    
    # 写入文件
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def log_error(message):
    """记录错误"""
    log_message(message, 'ERROR')

def log_info(message):
    """记录信息"""
    log_message(message, 'INFO')

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html', status=registration_status)

@app.route('/api/start', methods=['POST'])
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
    
    log_info(f"开始{'连续' if continuous else '单次'}注册，代理: {proxy or '无'}")
    return jsonify({'success': True, 'message': '注册已启动'})

@app.route('/api/stop', methods=['POST'])
def stop_registration():
    """停止注册"""
    if not registration_status['is_running']:
        return jsonify({'success': False, 'message': '没有正在运行的注册任务'})
    
    registration_status['is_running'] = False
    log_info("停止注册任务")
    return jsonify({'success': True, 'message': '注册已停止'})

@app.route('/api/status')
def get_status():
    """获取状态"""
    return jsonify(registration_status)

@app.route('/api/logs')
def get_logs():
    """获取日志"""
    lines = request.args.get('lines', 100, type=int)
    logs = registration_status['log_content'][-lines:]
    return jsonify({'logs': logs})

@app.route('/api/files')
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
def get_file(filename):
    """获取文件内容"""
    try:
        file_path = Path(filename)
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'success': False, 'message': '文件不存在'})
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': content,
            'size': len(content)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'读取文件失败: {e}'})

@app.route('/api/files/<filename>/download')
def download_file(filename):
    """下载文件"""
    try:
        file_path = Path(filename)
        if not file_path.exists() or not file_path.is_file():
            abort(404)
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        abort(500)

@app.route('/api/convert', methods=['POST'])
def convert_format():
    """转换格式"""
    try:
        data = request.json
        input_file = data.get('input_file', ACCOUNTS_FILE)
        output_file = data.get('output_file', SUB2API_FILE)
        
        convert_to_sub2api_format(input_file, output_file)
        
        log_info(f"格式转换完成: {input_file} -> {output_file}")
        return jsonify({'success': True, 'message': '格式转换完成'})
    except Exception as e:
        log_error(f"格式转换失败: {e}")
        return jsonify({'success': False, 'message': f'转换失败: {e}'})

@app.route('/api/config', methods=['GET', 'POST'])
def config_management():
    """配置管理"""
    if request.method == 'GET':
        return jsonify({
            'proxy': registration_status['proxy'],
            'default_proxy': Config.DEFAULT_PROXY
        })
    
    elif request.method == 'POST':
        data = request.json
        proxy = data.get('proxy', '')
        
        registration_status['proxy'] = proxy
        log_info(f"更新代理设置: {proxy or '无'}")
        
        return jsonify({'success': True, 'message': '配置已更新'})

def create_templates():
    """创建模板目录和文件"""
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # 创建基础模板
    base_template = templates_dir / 'base.html'
    if not base_template.exists():
        base_template.write_text('''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Codex Auto Registration</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; }
        .status-running { color: #28a745; }
        .status-stopped { color: #dc3545; }
        .log-container { max-height: 400px; overflow-y: auto; }
        .file-list { max-height: 300px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
''')
    
    # 创建主页面模板
    index_template = templates_dir / 'index.html'
    if not index_template.exists():
        index_template.write_text('''
{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-8">
        <h2><i class="fas fa-robot"></i> Codex Auto Registration</h2>
        <p class="text-muted">自动化注册OpenAI Codex账号的管理界面</p>
    </div>
    <div class="col-md-4 text-end">
        <span class="badge {% if status.is_running %}bg-success{% else %}bg-secondary{% endif %}">
            <i class="fas fa-circle"></i>
            {{ '运行中' if status.is_running else '已停止' }}
        </span>
    </div>
</div>

<div class="row mt-4">
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <i class="fas fa-cogs"></i> 控制面板
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label">代理设置</label>
                    <input type="text" id="proxy" class="form-control" 
                           placeholder="http://127.0.0.1:7890" 
                           value="{{ status.proxy }}">
                </div>
                
                <div class="d-grid gap-2">
                    <button class="btn btn-success" onclick="startSingle()">
                        <i class="fas fa-play"></i> 单次注册
                    </button>
                    <button class="btn btn-primary" onclick="startContinuous()">
                        <i class="fas fa-sync-alt"></i> 连续注册
                    </button>
                    <button class="btn btn-danger" onclick="stopRegistration()">
                        <i class="fas fa-stop"></i> 停止
                    </button>
                </div>
            </div>
        </div>
        
        <div class="card mt-3">
            <div class="card-header">
                <i class="fas fa-chart-bar"></i> 统计信息
            </div>
            <div class="card-body">
                <div class="row text-center">
                    <div class="col-6">
                        <h3 class="text-success">{{ status.success_count }}</h3>
                        <p class="mb-0">成功</p>
                    </div>
                    <div class="col-6">
                        <h3 class="text-danger">{{ status.fail_count }}</h3>
                        <p class="mb-0">失败</p>
                    </div>
                </div>
                {% if status.current_email %}
                <div class="mt-3">
                    <small class="text-muted">当前邮箱:</small>
                    <div class="text-truncate">{{ status.current_email }}</div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="col-md-8">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="fas fa-file-alt"></i> 运行日志</span>
                <button class="btn btn-sm btn-outline-secondary" onclick="refreshLogs()">
                    <i class="fas fa-sync-alt"></i> 刷新
                </button>
            </div>
            <div class="card-body log-container" id="logContainer">
                {% for log in status.log_content[-20:] %}
                <div class="log-entry">{{ log }}</div>
                {% endfor %}
            </div>
        </div>
        
        <div class="card mt-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="fas fa-folder-open"></i> 文件管理</span>
                <button class="btn btn-sm btn-outline-secondary" onclick="refreshFiles()">
                    <i class="fas fa-sync-alt"></i> 刷新
                </button>
            </div>
            <div class="card-body file-list" id="fileList">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>文件名</th>
                            <th>大小</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="fileTableBody">
                        <!-- 文件列表通过JS加载 -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let logRefreshInterval;
let statusRefreshInterval;

function startSingle() {
    startRegistration(false);
}

function startContinuous() {
    startRegistration(true);
}

function startRegistration(continuous) {
    const proxy = $('#proxy').val();
    
    $.ajax({
        url: '/api/start',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            proxy: proxy,
            continuous: continuous
        }),
        success: function(response) {
            if (response.success) {
                showAlert('success', response.message);
                startRefreshIntervals();
            } else {
                showAlert('danger', response.message);
            }
        },
        error: function() {
            showAlert('danger', '启动失败，请重试');
        }
    });
}

function stopRegistration() {
    $.ajax({
        url: '/api/stop',
        method: 'POST',
        success: function(response) {
            if (response.success) {
                showAlert('info', response.message);
                stopRefreshIntervals();
            } else {
                showAlert('warning', response.message);
            }
        },
        error: function() {
            showAlert('danger', '停止失败，请重试');
        }
    });
}

function refreshStatus() {
    $.get('/api/status', function(response) {
        // 更新状态
        if (response.is_running) {
            $('.badge').removeClass('bg-secondary').addClass('bg-success')
                .html('<i class="fas fa-circle"></i> 运行中');
        } else {
            $('.badge').removeClass('bg-success').addClass('bg-secondary')
                .html('<i class="fas fa-circle"></i> 已停止');
        }
        
        // 更新统计
        $('h3.text-success').text(response.success_count);
        $('h3.text-danger').text(response.fail_count);
        
        if (response.current_email) {
            $('.text-truncate').text(response.current_email);
        }
    });
}

function refreshLogs() {
    $.get('/api/logs', function(response) {
        const logContainer = $('#logContainer');
        logContainer.empty();
        
        response.logs.forEach(function(log) {
            logContainer.append('<div class="log-entry">' + log + '</div>');
        });
        
        // 自动滚动到底部
        logContainer.scrollTop(logContainer[0].scrollHeight);
    });
}

function refreshFiles() {
    $.get('/api/files', function(response) {
        const tbody = $('#fileTableBody');
        tbody.empty();
        
        response.files.forEach(function(file) {
            const size = formatFileSize(file.size);
            const modified = new Date(file.modified).toLocaleString();
            
            tbody.append(`
                <tr>
                    <td>${file.name}</td>
                    <td>${size}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewFile('${file.name}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="downloadFile('${file.name}')">
                            <i class="fas fa-download"></i>
                        </button>
                    </td>
                </tr>
            `);
        });
    });
}

function viewFile(filename) {
    $.get('/api/files/' + filename, function(response) {
        if (response.success) {
            showFileModal(filename, response.content);
        } else {
            showAlert('danger', response.message);
        }
    });
}

function downloadFile(filename) {
    window.location.href = '/api/files/' + filename + '/download';
}

function convertFormat() {
    $.ajax({
        url: '/api/convert',
        method: 'POST',
        success: function(response) {
            if (response.success) {
                showAlert('success', response.message);
                refreshFiles();
            } else {
                showAlert('danger', response.message);
            }
        },
        error: function() {
            showAlert('danger', '转换失败，请重试');
        }
    });
}

function startRefreshIntervals() {
    // 每3秒刷新状态
    statusRefreshInterval = setInterval(refreshStatus, 3000);
    // 每5秒刷新日志
    logRefreshInterval = setInterval(refreshLogs, 5000);
}

function stopRefreshIntervals() {
    if (statusRefreshInterval) {
        clearInterval(statusRefreshInterval);
    }
    if (logRefreshInterval) {
        clearInterval(logRefreshInterval);
    }
}

function showAlert(type, message) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('.container').first().prepend(alertHtml);
}

function showFileModal(filename, content) {
    const modalHtml = `
        <div class="modal fade" id="fileModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${filename}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre class="bg-light p-3" style="max-height: 500px; overflow-y: auto;">${escapeHtml(content)}</pre>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $('body').append(modalHtml);
    $('#fileModal').modal('show');
    $('#fileModal').on('hidden.bs.modal', function() {
        $(this).remove();
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 页面加载时刷新一次
$(document).ready(function() {
    refreshStatus();
    refreshLogs();
    refreshFiles();
});
</script>
{% endblock %}
''')

if __name__ == '__main__':
    create_templates()
    print("=" * 50)
    print("Codex Auto Registration Web Interface")
    print("=" * 50)
    print("Web管理界面已启动！")
    print("访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)