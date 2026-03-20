"""
Backup and Restore Module for Codex Auto Registration
备份和恢复模块
"""

import os
import json
import shutil
import tarfile
import threading
import time
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    """备份管理器"""
    
    def __init__(self, config):
        self.config = config
        self.backup_dir = Path(config.get('backup', {}).get('backup_dir', 'backups'))
        self.enabled = config.get('backup', {}).get('enabled', True)
        self.interval = config.get('backup', {}).get('interval', 3600)
        self.max_backups = config.get('backup', {}).get('max_backups', 10)
        
        self.backup_dir.mkdir(exist_ok=True)
        self._stop_event = threading.Event()
        self._thread = None
        
        # 启动自动备份线程
        if self.enabled:
            self.start_auto_backup()
    
    def start_auto_backup(self):
        """启动自动备份"""
        self._thread = threading.Thread(target=self._auto_backup_loop, daemon=True)
        self._thread.start()
        logger.info(f"自动备份已启动，间隔: {self.interval}秒")
    
    def stop_auto_backup(self):
        """停止自动备份"""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        logger.info("自动备份已停止")
    
    def _auto_backup_loop(self):
        """自动备份循环"""
        while not self._stop_event.is_set():
            try:
                self.create_backup()
                self._cleanup_old_backups()
            except Exception as e:
                logger.error(f"自动备份失败: {e}")
            
            # 等待间隔
            self._stop_event.wait(self.interval)
    
    def create_backup(self, backup_name=None):
        """创建备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = backup_name or f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        logger.info(f"开始创建备份: {backup_name}")
        
        try:
            # 创建备份目录
            backup_path.mkdir(exist_ok=True)
            
            # 备份重要文件
            files_to_backup = [
                'accounts.json',
                'sub2api_import.json',
                'config.yaml',
                'codex_register.log'
            ]
            
            for file in files_to_backup:
                file_path = Path(file)
                if file_path.exists():
                    shutil.copy2(file_path, backup_path / file)
                    logger.info(f"已备份: {file}")
            
            # 创建备份信息文件
            backup_info = {
                'backup_name': backup_name,
                'created_at': timestamp,
                'files': [f for f in files_to_backup if Path(f).exists()],
                'version': '1.0.0'
            }
            
            with open(backup_path / 'backup_info.json', 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            # 创建压缩包
            tar_path = self.backup_dir / f"{backup_name}.tar.gz"
            with tarfile.open(tar_path, 'w:gz') as tar:
                tar.add(backup_path, arcname=backup_name)
            
            # 删除未压缩的备份目录
            shutil.rmtree(backup_path)
            
            logger.info(f"备份创建成功: {tar_path}")
            return str(tar_path)
            
        except Exception as e:
            logger.error(f"备份创建失败: {e}")
            raise
    
    def restore_backup(self, backup_name):
        """恢复备份"""
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        logger.info(f"开始恢复备份: {backup_name}")
        
        try:
            # 创建临时目录
            temp_dir = self.backup_dir / f"temp_{backup_name}"
            temp_dir.mkdir(exist_ok=True)
            
            # 解压备份
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # 获取备份目录
            backup_dir = temp_dir / backup_name
            
            # 检查备份信息
            info_file = backup_dir / 'backup_info.json'
            if info_file.exists():
                with open(info_file, 'r') as f:
                    backup_info = json.load(f)
                logger.info(f"备份信息: {backup_info}")
            
            # 恢复文件
            for file in backup_dir.glob('*'):
                if file.is_file() and file.name != 'backup_info.json':
                    shutil.copy2(file, Path('.') / file.name)
                    logger.info(f"已恢复: {file.name}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            logger.info(f"备份恢复成功: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"备份恢复失败: {e}")
            raise
    
    def list_backups(self):
        """列出所有备份"""
        backups = []
        
        for backup_file in self.backup_dir.glob('*.tar.gz'):
            backup_name = backup_file.stem
            stat = backup_file.stat()
            
            backups.append({
                'name': backup_name,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': str(backup_file)
            })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def get_backup_info(self, backup_name):
        """获取备份信息"""
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                # 读取备份信息文件
                try:
                    info_member = tar.getmember(f"{backup_name}/backup_info.json")
                    with tar.extractfile(info_member) as f:
                        return json.load(f)
                except:
                    # 如果没有备份信息文件，返回基本信息
                    return {
                        'backup_name': backup_name,
                        'size': backup_path.stat().st_size,
                        'created_at': datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat()
                    }
        except Exception as e:
            logger.error(f"获取备份信息失败: {e}")
            raise
    
    def _cleanup_old_backups(self):
        """清理旧备份"""
        backups = self.list_backups()
        
        if len(backups) > self.max_backups:
            old_backups = backups[self.max_backups:]
            
            for backup in old_backups:
                backup_path = Path(backup['path'])
                if backup_path.exists():
                    backup_path.unlink()
                    logger.info(f"已删除旧备份: {backup['name']}")
    
    def verify_backup(self, backup_name):
        """验证备份完整性"""
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                # 尝试验证压缩包完整性
                tar.getmembers()
                logger.info(f"备份验证成功: {backup_name}")
                return True
        except Exception as e:
            logger.error(f"备份验证失败: {e}")
            return False


def create_backup_manager(config):
    """创建备份管理器实例"""
    return BackupManager(config)


# 备份恢复API
def register_backup_routes(app, backup_manager):
    """注册备份相关的API路由"""
    
    @app.route('/api/backups')
    def list_backups():
        """列出所有备份"""
        try:
            backups = backup_manager.list_backups()
            return jsonify({'success': True, 'backups': backups})
        except Exception as e:
            return jsonify({'success': False, 'message': f'获取备份列表失败: {e}'})
    
    @app.route('/api/backups', methods=['POST'])
    def create_backup():
        """创建备份"""
        try:
            data = request.json
            backup_name = data.get('name')
            backup_path = backup_manager.create_backup(backup_name)
            return jsonify({'success': True, 'message': '备份创建成功', 'path': backup_path})
        except Exception as e:
            return jsonify({'success': False, 'message': f'创建备份失败: {e}'})
    
    @app.route('/api/backups/<backup_name>', methods=['DELETE'])
    def delete_backup(backup_name):
        """删除备份"""
        try:
            backup_path = backup_manager.backup_dir / f"{backup_name}.tar.gz"
            if backup_path.exists():
                backup_path.unlink()
                return jsonify({'success': True, 'message': '备份删除成功'})
            else:
                return jsonify({'success': False, 'message': '备份不存在'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'删除备份失败: {e}'})
    
    @app.route('/api/backups/<backup_name>/restore', methods=['POST'])
    def restore_backup(backup_name):
        """恢复备份"""
        try:
            backup_manager.restore_backup(backup_name)
            return jsonify({'success': True, 'message': '备份恢复成功'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'恢复备份失败: {e}'})
    
    @app.route('/api/backups/<backup_name>/verify', methods=['GET'])
    def verify_backup(backup_name):
        """验证备份"""
        try:
            is_valid = backup_manager.verify_backup(backup_name)
            return jsonify({'success': True, 'valid': is_valid})
        except Exception as e:
            return jsonify({'success': False, 'message': f'验证备份失败: {e}'})


if __name__ == '__main__':
    # 示例使用
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'backup': {
            'enabled': True,
            'interval': 3600,
            'max_backups': 10,
            'backup_dir': 'backups'
        }
    }
    
    backup_manager = create_backup_manager(config)
    
    # 创建测试备份
    backup_manager.create_backup('test_backup')
    
    # 列出备份
    backups = backup_manager.list_backups()
    print(f"备份列表: {backups}")
    
    # 验证备份
    if backups:
        backup_manager.verify_backup(backups[0]['name'])