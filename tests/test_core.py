"""
核心功能测试
"""

import pytest
import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app_enhanced import mask_sensitive_info, resolve_json_file_path, LOG_FILE, registration_status, log_message
from codex_generator_optimized import (
    get_password,
    Config,
    TempMailClient,
    OAuthStart,
    generate_oauth_url,
    parse_callback_url,
    exchange_token,
    decode_jwt_payload,
    parse_accounts_file,
    convert_account_format,
    convert_to_sub2api_format
)


class TestCoreFunctions:
    """核心函数测试"""
    
    def test_get_password(self):
        """测试密码生成"""
        password = get_password()
        assert len(password) >= 16
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
    
    def test_config_values(self):
        """测试配置值"""
        assert Config.OAUTH_CLIENT_ID == "app_EMoamEEZ73f0CkXaXp7hrann"
        assert Config.DEFAULT_PROXY == "http://127.0.0.1:7890"
        assert Config.OUTPUT_FILE == "accounts.json"
    
    def test_generate_oauth_url(self):
        """测试OAuth URL生成"""
        oauth = generate_oauth_url()
        assert isinstance(oauth, OAuthStart)
        assert oauth.auth_url.startswith("https://auth.openai.com/oauth/authorize")
        assert oauth.state
        assert oauth.code_verifier
        assert oauth.redirect_uri
    
    def test_parse_callback_url(self):
        """测试回调URL解析"""
        # 正常情况
        url = "http://localhost:1455/auth/callback?code=test_code&state=test_state"
        result = parse_callback_url(url)
        assert result["code"] == "test_code"
        assert result["state"] == "test_state"
        
        # 带fragment的情况
        url_with_fragment = "http://localhost:1455/auth/callback?code=test_code#state=test_state"
        result = parse_callback_url(url_with_fragment)
        assert result["code"] == "test_code"
        assert result["state"] == "test_state"
    
    def test_decode_jwt_payload(self):
        """测试JWT解码"""
        # 无效的token
        assert decode_jwt_payload("") == {}
        assert decode_jwt_payload("invalid") == {}
        
        # 有效的token（示例）
        # 注意：这里使用一个示例token，实际测试时需要使用真实的token
        sample_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        payload = decode_jwt_payload(sample_token)
        assert payload.get("sub") == "1234567890"
        assert payload.get("name") == "John Doe"


class TestFileOperations:
    """文件操作测试"""
    
    def test_parse_accounts_file(self):
        """测试账户文件解析"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"email": "test1@example.com", "access_token": "token1"}\n')
            f.write('{"email": "test2@example.com", "access_token": "token2"}\n')
            temp_file = f.name
        
        try:
            accounts = parse_accounts_file(temp_file)
            assert len(accounts) == 2
            assert accounts[0]["email"] == "test1@example.com"
            assert accounts[1]["email"] == "test2@example.com"
        finally:
            os.unlink(temp_file)
    
    def test_parse_empty_file(self):
        """测试空文件解析"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            accounts = parse_accounts_file(temp_file)
            assert accounts == []
        finally:
            os.unlink(temp_file)
    
    def test_convert_account_format(self):
        """测试账户格式转换"""
        account = {
            "email": "test@example.com",
            "access_token": "test_token",
            "refresh_token": "refresh_token",
            "account_id": "account_id"
        }
        
        converted = convert_account_format(account, 0)
        assert converted["name"] == "test@example.com"
        assert converted["platform"] == "openai"
        assert converted["type"] == "oauth"
        assert "credentials" in converted
        assert converted["credentials"]["access_token"] == "test_token"
    
    def test_convert_to_sub2api_format(self):
        """测试sub2api格式转换"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"email": "test@example.com", "access_token": "token1"}\n')
            input_file = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name
        
        try:
            convert_to_sub2api_format(input_file, output_file)
            
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            assert "exported_at" in data
            assert "accounts" in data
            assert len(data["accounts"]) == 1
            assert data["accounts"][0]["name"] == "test@example.com"
        finally:
            os.unlink(input_file)
            os.unlink(output_file)


class TestSecurity:
    """安全性测试"""
    
    def test_password_strength(self):
        """测试密码强度"""
        for _ in range(100):  # 多次测试确保随机性
            password = get_password()
            # 检查长度
            assert len(password) >= 16
            # 检查包含大写字母
            assert any(c.isupper() for c in password)
            # 检查包含小写字母
            assert any(c.islower() for c in password)
            # 检查包含数字
            assert any(c.isdigit() for c in password)
    
    def test_oauth_state_uniqueness(self):
        """测试OAuth state的唯一性"""
        states = set()
        for _ in range(100):
            oauth = generate_oauth_url()
            assert oauth.state not in states
            states.add(oauth.state)


class TestEnhancedWebHelpers:
    """增强版Web辅助函数测试"""

    def test_mask_sensitive_info_supports_json_lines(self):
        """测试JSON Lines中的敏感字段脱敏"""
        content = '\n'.join([
            json.dumps({"email": "test@example.com", "access_token": "a" * 30}),
            json.dumps({"refresh_token": "b" * 30, "nested": {"id_token": "c" * 30}}),
        ])

        masked = mask_sensitive_info(content)
        assert 'aaaaaaaaaa...aaaaaaaaaa' in masked
        assert 'bbbbbbbbbb...bbbbbbbbbb' in masked
        assert 'cccccccccc...cccccccccc' in masked
        assert 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' not in masked

    def test_resolve_json_file_path_rejects_path_traversal(self):
        """测试文件路径校验防止目录遍历"""
        with pytest.raises(ValueError):
            resolve_json_file_path('../secrets.json')

        with pytest.raises(ValueError):
            resolve_json_file_path('/tmp/secrets.json')

        with pytest.raises(ValueError):
            resolve_json_file_path('accounts.txt')

    def test_log_message_writes_to_log_file_only(self, tmp_path, monkeypatch):
        """测试日志写入独立日志文件，避免污染账户文件"""
        log_path = tmp_path / 'codex_register.log'
        monkeypatch.setattr('app_enhanced.LOG_FILE', log_path)
        registration_status['log_content'].clear()

        log_message('hello world')

        assert log_path.read_text(encoding='utf-8').strip().endswith('hello world')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])