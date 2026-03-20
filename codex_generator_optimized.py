"""
Codex Auto Registration Tool - Optimized Version
一个用于自动化注册OpenAI Codex账号的工具
"""

import os
import json
import re
import time
import random
import string
import base64
import hashlib
import secrets
import urllib.parse
import urllib.request
import urllib.error
import logging
from typing import Any, Dict, Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path

import requests
from curl_cffi import requests as curl_requests

# ====================== 配置管理 ======================
class Config:
    """配置管理类"""
    # OpenAI OAuth配置
    OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
    OAUTH_ISSUER = "https://auth.openai.com"
    OAUTH_AUTH_URL = f"{OAUTH_ISSUER}/oauth/authorize"
    OAUTH_TOKEN_URL = f"{OAUTH_ISSUER}/oauth/token"
    DEFAULT_REDIRECT_URI = "http://localhost:1455/auth/callback"
    DEFAULT_SCOPE = "openid email profile offline_access"
    
    # TempMail配置
    TEMPMAIL_API_BASE = "https://api.tempmail.lol/v2"
    
    # Sentinel配置
    SENTINEL_API_URL = "https://sentinel.openai.com/backend-api/sentinel/req"
    
    # 其他配置
    DEFAULT_PROXY = "http://127.0.0.1:7890"
    OUTPUT_FILE = "accounts.json"
    SUB2API_OUTPUT_FILE = "sub2api_import.json"
    
    # 超时配置
    REQUEST_TIMEOUT = 30
    OTP_TIMEOUT = 300
    IP_CHECK_TIMEOUT = 10

# ====================== 日志配置 ======================
def setup_logging() -> logging.Logger:
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('codex_register.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ====================== 工具函数 ======================
def get_password(length: int = 16) -> str:
    """
    生成强密码
    
    Args:
        length: 密码长度
        
    Returns:
        生成的密码字符串
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(random.choices(chars, k=length))
        if (any(c.islower() for c in password) and 
            any(c.isupper() for c in password) and 
            any(c.isdigit() for c in password)):
            return password

def _b64url_no_pad(raw: bytes) -> str:
    """Base64 URL编码，去除填充"""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _sha256_b64url_no_pad(s: str) -> str:
    """SHA256哈希后Base64 URL编码"""
    return _b64url_no_pad(hashlib.sha256(s.encode("ascii")).digest())

def _random_state(nbytes: int = 16) -> str:
    """生成随机state"""
    return secrets.token_urlsafe(nbytes)

def _pkce_verifier() -> str:
    """生成PKCE验证器"""
    return secrets.token_urlsafe(64)

def _to_int(v: Any) -> int:
    """安全转换为整数"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0

# ====================== 邮箱模块 ======================
class Message:
    """邮件消息类"""
    def __init__(self, data: dict):
        self.from_addr = data.get("from", "")
        self.subject = data.get("subject", "")
        self.body = data.get("body", "") or ""
        self.html_body = data.get("html", "") or ""

def create_curl_session(proxies: Optional[dict] = None):
    """
    创建curl_cffi Session，处理impersonate不支持的情况
    
    Args:
        proxies: 代理配置
        
    Returns:
        curl_requests.Session对象
    """
    try:
        # 先尝试使用impersonate chrome
        session = curl_requests.Session(
            proxies=proxies, 
            impersonate="chrome"
        )
        logger.debug("使用impersonate chrome模式")
    except Exception as e:
        # 如果impersonate不支持，使用普通Session
        if "impersonate" in str(e).lower():
            logger.warning("impersonate chrome not supported, using regular session")
            session = curl_requests.Session(proxies=proxies)
            # 设置Chrome-like的User-Agent
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            })
        else:
            # 其他错误直接抛出
            raise e
    
    return session

class TempMailClient:
    """TempMail.lol邮箱客户端"""
    def __init__(self, proxies: Optional[dict] = None):
        """
        初始化邮箱客户端
        
        Args:
            proxies: 代理配置
        """
        self.session = create_curl_session(proxies=proxies)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # 创建随机邮箱
        response = self.session.post(
            f"{Config.TEMPMAIL_API_BASE}/inbox/create", 
            json={}
        )
        response.raise_for_status()
        
        data = response.json()
        self.address = data["address"]
        self.token = data["token"]
        logger.info(f"生成邮箱: {self.address} (TempMail.lol)")

    def get_messages(self) -> List[dict]:
        """获取邮件列表"""
        response = self.session.get(
            f"{Config.TEMPMAIL_API_BASE}/inbox?token={self.token}"
        )
        response.raise_for_status()
        return response.json().get("emails", [])

    def wait_for_message(
        self, 
        timeout: int = Config.OTP_TIMEOUT, 
        filter_func: Optional[callable] = None
    ) -> Message:
        """
        等待邮件到达
        
        Args:
            timeout: 超时时间（秒）
            filter_func: 邮件过滤函数
            
        Returns:
            匹配的邮件消息
            
        Raises:
            TimeoutError: 超时异常
        """
        logger.info(f"等待邮件验证码（最多 {timeout // 60} 分钟）")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            messages = self.get_messages()
            elapsed = int(time.time() - start_time)
            logger.info(f"已轮询 {elapsed} 秒，收到 {len(messages)} 封邮件")
            
            for msg_data in messages:
                msg = Message(msg_data)
                if not filter_func or filter_func(msg):
                    logger.info(f"收到匹配邮件: {msg.subject}")
                    return msg
            
            time.sleep(5)
        
        raise TimeoutError(f"{timeout // 60} 分钟内未收到邮件")

def create_temp_email(proxies: Optional[dict] = None) -> Tuple[str, TempMailClient]:
    """
    创建临时邮箱
    
    Args:
        proxies: 代理配置
        
    Returns:
        (邮箱地址, 邮箱客户端实例)
    """
    client = TempMailClient(proxies=proxies)
    return client.address, client

# ====================== OAuth模块 ======================
@dataclass(frozen=True)
class OAuthStart:
    """OAuth启动信息"""
    auth_url: str
    state: str
    code_verifier: str
    redirect_uri: str

def generate_oauth_url(
    redirect_uri: str = Config.DEFAULT_REDIRECT_URI,
    scope: str = Config.DEFAULT_SCOPE
) -> OAuthStart:
    """
    生成OAuth授权URL
    
    Args:
        redirect_uri: 重定向URI
        scope: 权限范围
        
    Returns:
        OAuthStart对象
    """
    state = _random_state()
    code_verifier = _pkce_verifier()
    code_challenge = _sha256_b64url_no_pad(code_verifier)
    
    # 添加调试信息
    logger.debug(f"生成OAuth URL - State: {state[:20]}...")
    logger.debug(f"生成OAuth URL - Code Verifier: {code_verifier[:20]}...")
    
    params = {
        "client_id": Config.OAUTH_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        # 添加新参数以兼容最新API
        "audience": "https://api.openai.com",
        "response_mode": "query",
    }
    
    auth_url = f"{Config.OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"
    logger.debug(f"生成的OAuth URL: {auth_url[:100]}...")
    
    return OAuthStart(
        auth_url=auth_url,
        state=state,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri
    )

def parse_callback_url(callback_url: str) -> Dict[str, str]:
    """
    解析回调URL参数
    
    Args:
        callback_url: 回调URL
        
    Returns:
        参数字典
    """
    candidate = callback_url.strip()
    if not candidate:
        return {"code": "", "state": "", "error": "", "error_description": ""}
    
    if "://" not in candidate:
        if candidate.startswith("?"):
            candidate = f"http://localhost{candidate}"
        elif any(ch in candidate for ch in "/?#") or ":" in candidate:
            candidate = f"http://{candidate}"
        elif "=" in candidate:
            candidate = f"http://localhost/?{candidate}"
    
    parsed = urllib.parse.urlparse(candidate)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    fragment = urllib.parse.parse_qs(parsed.fragment, keep_blank_values=True)
    
    # 合并query和fragment参数
    for key, values in fragment.items():
        if key not in query or not query[key] or not (query[key][0] or "").strip():
            query[key] = values
    
    def get_param(key: str) -> str:
        values = query.get(key, [""])
        return (values[0] or "").strip()
    
    code = get_param("code")
    state = get_param("state")
    error = get_param("error")
    error_description = get_param("error_description")
    
    # 处理特殊情况
    if code and not state and "#" in code:
        code, state = code.split("#", 1)
    if not error and error_description:
        error, error_description = error_description, ""
    
    return {
        "code": code,
        "state": state,
        "error": error,
        "error_description": error_description
    }

def exchange_token(
    callback_url: str,
    expected_state: str,
    code_verifier: str,
    redirect_uri: str = Config.DEFAULT_REDIRECT_URI
) -> str:
    """
    交换OAuth token
    
    Args:
        callback_url: 回调URL
        expected_state: 期望的state
        code_verifier: PKCE验证器
        redirect_uri: 重定向URI
        
    Returns:
        JSON格式的token配置
        
    Raises:
        RuntimeError: OAuth错误
        ValueError: 参数错误
    """
    cb = parse_callback_url(callback_url)
    
    if cb["error"]:
        desc = cb["error_description"]
        raise RuntimeError(f"OAuth错误: {cb['error']}: {desc}".strip())
    
    if not cb["code"]:
        raise ValueError("Callback URL缺少?code=")
    if not cb["state"]:
        raise ValueError("Callback URL缺少?state=")
    if cb["state"] != expected_state:
        raise ValueError("State校验不匹配")
    
    # 构建请求数据
    data = {
        "grant_type": "authorization_code",
        "client_id": Config.OAUTH_CLIENT_ID,
        "code": cb["code"],
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier
    }
    
    # 发送请求
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        Config.OAUTH_TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=Config.REQUEST_TIMEOUT) as resp:
            raw = resp.read()
            if resp.status != 200:
                raise RuntimeError(f"Token交换失败: {resp.status}: {raw.decode('utf-8', 'replace')}")
            return raw.decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise RuntimeError(f"Token交换失败: {exc.code}: {raw.decode('utf-8', 'replace')}") from exc

def decode_jwt_payload(token: str) -> dict:
    """
    解码JWT token的payload部分（不验证签名）
    
    Args:
        token: JWT token
        
    Returns:
        Payload字典
    """
    if not token or token.count(".") < 2:
        return {}
    
    payload_b64 = token.split(".")[1]
    pad = "=" * ((4 - (len(payload_b64) % 4)) % 4)
    
    try:
        payload = base64.urlsafe_b64decode((payload_b64 + pad).encode("ascii"))
        return json.loads(payload.decode("utf-8"))
    except Exception as e:
        logger.error(f"解码JWT失败: {e}")
        return {}

# ====================== 辅助函数 ======================

def check_dependencies():
    """检查依赖库版本"""
    import sys
    logger.info(f"Python版本: {sys.version}")
    
    try:
        import curl_cffi
        logger.info(f"curl_cffi版本: {curl_cffi.__version__}")
    except ImportError:
        logger.error("curl_cffi未安装")
        raise
    
    try:
        import requests
        logger.info(f"requests版本: {requests.__version__}")
    except ImportError:
        logger.error("requests未安装")
        raise

def check_api_status():
    """检查OpenAI API状态"""
    try:
        # 检查API可达性
        response = requests.get("https://api.openai.com/v1/models", timeout=10)
        logger.debug(f"OpenAI API状态: {response.status_code}")
        if response.status_code == 200:
            logger.info("OpenAI API连接正常")
        else:
            logger.warning(f"OpenAI API返回异常状态: {response.status_code}")
    except Exception as e:
        logger.warning(f"检查OpenAI API状态失败: {e}")

def run_with_retry(func, max_retries=3, delay=5):
    """
    带重试的执行函数
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        
    Returns:
        函数返回值
        
    Raises:
        Exception: 最后一次尝试的异常
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {e}")
            if attempt < max_retries - 1:
                logger.info(f"{delay}秒后重试...")
                time.sleep(delay)
            else:
                logger.error("所有重试均失败")
                raise e

# ====================== 核心注册逻辑 ======================
class CodexRegistration:
    """Codex注册器"""
    
    def __init__(self, proxy: Optional[str] = None):
        """
        初始化注册器
        
        Args:
            proxy: 代理URL
        """
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.session = create_curl_session(proxies=self.proxies)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
    
    def check_ip_location(self) -> Tuple[str, str]:
        """
        检查IP地理位置
        
        Returns:
            (IP地址, 位置代码)
            
        Raises:
            RuntimeError: IP检查失败或位置受限
        """
        try:
            response = self.session.get(
                "https://cloudflare.com/cdn-cgi/trace",
                timeout=Config.IP_CHECK_TIMEOUT
            )
            
            ip_match = re.search(r"^ip=(.+)$", response.text, re.MULTILINE)
            loc_match = re.search(r"^loc=(.+)$", response.text, re.MULTILINE)
            
            ip = ip_match.group(1) if ip_match else "Unknown"
            loc = loc_match.group(1) if loc_match else "Unknown"
            
            logger.info(f"当前节点信息 -> Location: {loc}, IP: {ip}")
            
            # 检查是否受限地区
            if loc in ("CN", "HK", "RU"):
                raise RuntimeError(f"当前IP位于受限地区: {loc}，请切换代理节点")
            
            return ip, loc
            
        except Exception as e:
            logger.error(f"IP检查失败: {e}")
            raise RuntimeError(f"IP检查失败: {e}")
    
    def initialize_oauth(self) -> OAuthStart:
        """
        初始化OAuth流程
        
        Returns:
            OAuthStart对象
            
        Raises:
            RuntimeError: 初始化失败
        """
        oauth = generate_oauth_url()
        
        # 访问授权URL获取cookies
        response = self.session.get(oauth.auth_url)
        
        # 检查是否获取到oai-did cookie
        did = self.session.cookies.get("oai-did")
        if not did:
            raise RuntimeError("未能获取oai-did Cookie")
        
        logger.info(f"获取到oai-did: {did}")
        return oauth
    
    def bypass_sentinel(self, did: str) -> str:
        """
        绕过Sentinel验证
        
        Args:
            did: oai-did值
            
        Returns:
            Sentinel token
            
        Raises:
            RuntimeError: Sentinel验证失败
        """
        signup_body = {
            "username": {"value": "", "kind": "email"},
            "screen_hint": "signup"
        }
        
        sen_req_body = {
            "p": "",
            "id": did,
            "flow": "authorize_continue"
        }
        
        response = self.session.post(
            Config.SENTINEL_API_URL,
            headers={
                "origin": "https://sentinel.openai.com",
                "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                "content-type": "text/plain;charset=UTF-8"
            },
            data=json.dumps(sen_req_body)
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Sentinel验证失败: {response.text}")
        
        sen_token = response.json().get("token", "")
        logger.info(f"Sentinel验证成功，token: {sen_token[:20]}...")
        return sen_token
    
    def register_account(self, email: str, password: str, max_retries: int = 3) -> None:
        """
        注册账户，带重试机制
        
        Args:
            email: 邮箱地址
            password: 密码
            max_retries: 最大重试次数
            
        Raises:
            RuntimeError: 注册失败
        """
        # 提交注册（带重试）
        signup_body = {
            "username": {"value": email, "kind": "email"},
            "screen_hint": "signup"
        }
        
        sentinel_token = self.bypass_sentinel(self.session.cookies.get("oai-did"))
        
        # 添加详细的请求信息
        logger.debug(f"SignUp请求 - Email: {email}")
        logger.debug(f"SignUp请求 - Sentinel Token: {sentinel_token[:20]}...")
        
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    "https://auth.openai.com/api/accounts/authorize/continue",
                    headers={
                        "referer": "https://auth.openai.com/create-account",
                        "accept": "application/json",
                        "content-type": "application/json",
                        "openai-sentinel-token": sentinel_token,
                        # 添加额外头部以兼容最新API
                        "x-requested-with": "XMLHttpRequest",
                        "sec-fetch-site": "same-origin",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-dest": "empty",
                    },
                    json=signup_body,
                    timeout=Config.REQUEST_TIMEOUT
                )
                
                logger.debug(f"SignUp响应 - Status: {response.status_code}")
                logger.debug(f"SignUp响应 - Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    break
                elif response.status_code >= 500:
                    # 服务器错误，重试
                    logger.warning(f"SignUp服务器错误，尝试重试 {attempt + 1}/{max_retries}")
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    # 其他错误，检查响应内容
                    if "Invalid authorization step" in response.text:
                        logger.error("检测到Invalid authorization step错误")
                        logger.error(f"完整响应: {response.text}")
                        # 可能是API更新，尝试添加新参数
                        if attempt == max_retries - 1:
                            raise RuntimeError(f"SignUp失败: {response.text}")
                    else:
                        raise RuntimeError(f"SignUp失败: {response.text}")
                        
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"SignUp请求异常，尝试重试 {attempt + 1}/{max_retries}: {e}")
                time.sleep(2 ** attempt)
        
        logger.info("SignUp请求成功")
        
        # 设置密码
        reg_body = {"password": password, "username": email}
        response = self.session.post(
            "https://auth.openai.com/api/accounts/user/register",
            headers={
                "referer": "https://auth.openai.com/create-account/password",
                "accept": "application/json",
                "content-type": "application/json"
            },
            json=reg_body
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"密码注册失败: {response.text}")
        
        logger.info(f"密码设置成功: {password}")
        
        # 触发OTP
        response = self.session.get(
            "https://auth.openai.com/api/accounts/email-otp/send",
            headers={
                "referer": "https://auth.openai.com/create-account/password",
                "accept": "application/json"
            }
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"OTP发送失败: {response.text}")
        
        logger.info("OTP发送成功")
    
    def verify_otp(self, otp_code: str) -> None:
        """
        验证OTP
        
        Args:
            otp_code: OTP验证码
            
        Raises:
            RuntimeError: 验证失败
        """
        response = self.session.post(
            "https://auth.openai.com/api/accounts/email-otp/validate",
            headers={
                "referer": "https://auth.openai.com/email-verification",
                "accept": "application/json",
                "content-type": "application/json"
            },
            json={"code": otp_code}
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"OTP验证失败: {response.text}")
        
        logger.info("OTP验证成功")
    
    def create_account_info(self) -> None:
        """创建账户信息"""
        create_account_body = {
            "name": "gali",
            "birthdate": "2000-02-20"
        }
        
        response = self.session.post(
            "https://auth.openai.com/api/accounts/create_account",
            headers={
                "referer": "https://auth.openai.com/about-you",
                "accept": "application/json",
                "content-type": "application/json"
            },
            json=create_account_body
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"创建账户信息失败: {response.text}")
        
        logger.info("账户信息创建成功")
    
    def select_workspace(self) -> str:
        """
        选择工作空间
        
        Returns:
            continue_url
            
        Raises:
            RuntimeError: 选择失败
        """
        # 获取Workspace ID
        auth_cookie = self.session.cookies.get("oai-client-auth-session")
        if not auth_cookie:
            raise RuntimeError("未能获取oai-client-auth-session")
        
        auth_data = base64.b64decode(auth_cookie.split(".")[0])
        auth_json = json.loads(auth_data)
        workspace_id = auth_json["workspaces"][0]["id"]
        
        logger.info(f"提取Workspace ID: {workspace_id}")
        
        # 选择Workspace
        select_body = {"workspace_id": workspace_id}
        response = self.session.post(
            "https://auth.openai.com/api/accounts/workspace/select",
            headers={
                "referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
                "content-type": "application/json"
            },
            json=select_body
        )
        
        if "continue_url" not in response.json():
            raise RuntimeError(f"未能获取continue_url: {response.text}")
        
        continue_url = response.json()["continue_url"]
        logger.info(f"获取到continue_url: {continue_url}")
        return continue_url
    
    def complete_registration(self, oauth: OAuthStart, callback_url: str) -> dict:
        """
        完成注册流程
        
        Args:
            oauth: OAuthStart对象
            callback_url: 回调URL
            
        Returns:
            Token配置字典
        """
        # 交换Token
        token_json = exchange_token(
            callback_url=callback_url,
            expected_state=oauth.state,
            code_verifier=oauth.code_verifier,
            redirect_uri=oauth.redirect_uri
        )
        
        token_config = json.loads(token_json)
        logger.info(f"Token交换成功，邮箱: {token_config.get('email', 'unknown')}")
        return token_config
    
    def run_registration(self, email_client: TempMailClient) -> dict:
        """
        执行完整注册流程
        
        Args:
            email_client: 邮箱客户端
            
        Returns:
            Token配置字典
            
        Raises:
            RuntimeError: 注册失败
        """
        # 1. IP检测
        self.check_ip_location()
        
        # 2. 初始化OAuth
        oauth = self.initialize_oauth()
        
        # 3. 注册账户
        password = get_password()
        self.register_account(email_client.address, password)
        
        # 4. 等待OTP
        def otp_filter(msg: Message) -> bool:
            subject = msg.subject.lower()
            return any(kw in subject for kw in ["openai", "验证码", "verification", "code", "otp"])
        
        msg = email_client.wait_for_message(timeout=Config.OTP_TIMEOUT, filter_func=otp_filter)
        otp_match = re.search(r'\b(\d{6})\b', msg.body or msg.html_body or msg.subject or "")
        
        if not otp_match:
            raise RuntimeError("未在邮件中找到6位验证码")
        
        otp_code = otp_match.group(1)
        logger.info(f"提取到OTP: {otp_code}")
        
        # 5. 验证OTP
        self.verify_otp(otp_code)
        
        # 6. 创建账户信息
        self.create_account_info()
        
        # 7. 选择工作空间
        continue_url = self.select_workspace()
        
        # 8. 跟踪重定向
        response = self.session.get(continue_url, allow_redirects=False)
        for _ in range(3):  # 最多跟踪3次重定向
            if "Location" in response.headers:
                response = self.session.get(response.headers["Location"], allow_redirects=False)
            else:
                break
        
        callback_url = response.headers.get("Location")
        if not callback_url:
            raise RuntimeError("未能获取最终的Callback URL")
        
        # 9. 完成注册
        return self.complete_registration(oauth, callback_url)

def run_single_registration(proxy: Optional[str] = None) -> Optional[dict]:
    """
    执行单次注册（带完整的错误处理和重试机制）
    
    Args:
        proxy: 代理URL
        
    Returns:
        Token配置字典，失败时返回None
    """
    try:
        logger.info("=" * 50)
        logger.info("开始新的注册流程")
        logger.info("=" * 50)
        
        # 检查依赖和API状态
        check_dependencies()
        check_api_status()
        
        # 创建邮箱
        logger.info("正在生成临时邮箱...")
        email, email_client = create_temp_email(proxies={"http": proxy, "https": proxy} if proxy else None)
        logger.info(f"邮箱创建成功: {email}")
        
        # 创建注册器
        logger.info("初始化注册器...")
        registrar = CodexRegistration(proxy=proxy)
        
        # 执行注册（带重试）
        def run_reg():
            return registrar.run_registration(email_client)
        
        result = run_with_retry(run_reg, max_retries=3, delay=5)
        
        if result:
            logger.info("=" * 50)
            logger.info(f"注册成功！邮箱: {result.get('email', 'unknown')}")
            logger.info(f"账户ID: {result.get('account_id', 'unknown')}")
            logger.info("=" * 50)
            return result
        else:
            logger.error("注册返回空结果")
            return None
        
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"注册失败: {e}")
        logger.error("完整的错误信息:")
        logger.exception(e)
        logger.error("=" * 50)
        return None

# ====================== 文件操作模块 ======================
def save_account(account: dict, output_file: str = Config.OUTPUT_FILE) -> None:
    """
    保存账户信息到文件
    
    Args:
        account: 账户配置字典
        output_file: 输出文件路径
    """
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(account, ensure_ascii=False) + "\n")
    logger.info(f"账户已保存到 {output_file}")

def parse_accounts_file(filepath: str) -> List[dict]:
    """
    解析账户文件（每行一个JSON对象）
    
    Args:
        filepath: 文件路径
        
    Returns:
        账户字典列表
    """
    if not os.path.exists(filepath):
        logger.warning(f"文件不存在: {filepath}")
        return []
    
    accounts = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    decoder = json.JSONDecoder()
    idx = 0
    
    while idx < len(content):
        # 跳过空白字符
        match = re.match(r'\s*', content[idx:])
        if match:
            idx += match.end()
        
        if idx >= len(content):
            break
        
        try:
            obj, end = decoder.raw_decode(content, idx)
            accounts.append(obj)
            idx += end - idx if end > idx else 1
        except json.JSONDecodeError:
            idx += 1
    
    logger.info(f"从 {filepath} 解析到 {len(accounts)} 个账户")
    return accounts

def extract_user_info_from_token(token: str) -> dict:
    """
    从token中提取用户信息
    
    Args:
        token: access_token或id_token
        
    Returns:
        用户信息字典
    """
    claims = decode_jwt_payload(token)
    if not claims:
        return {}
    
    info = {}
    
    # 提取chatgpt相关信息
    auth_info = claims.get("https://api.openai.com/auth", {})
    if auth_info:
        info["chatgpt_account_id"] = auth_info.get("chatgpt_account_id", "")
        info["chatgpt_user_id"] = auth_info.get("chatgpt_user_id", "")
    
    # 提取client_id
    info["client_id"] = claims.get("client_id", Config.OAUTH_CLIENT_ID)
    
    # 提取过期时间
    if claims.get("exp"):
        info["expires_at"] = claims["exp"]
        info["expires_in"] = claims["exp"] - claims.get("iat", int(time.time()))
    
    # 提取organization_id
    orgs = auth_info.get("organizations", [])
    info["organization_id"] = orgs[0].get("id", "") if orgs else ""
    
    return info

def convert_account_format(account: dict, index: int) -> dict:
    """
    将账户转换为sub2api格式
    
    Args:
        account: 原始账户字典
        index: 索引
        
    Returns:
        转换后的账户字典
    """
    email = account.get("email", "")
    
    # 从access_token中提取用户信息
    token_info = extract_user_info_from_token(account.get("access_token", ""))
    
    # 构建credentials
    credentials = {
        "access_token": account.get("access_token", ""),
        "chatgpt_account_id": token_info.get("chatgpt_account_id", account.get("account_id", "")),
        "client_id": token_info.get("client_id", Config.OAUTH_CLIENT_ID),
        "model_mapping": {
            "gpt-5.4": "gpt-5.4",
            "gpt-5.3-codex": "gpt-5.3-codex"
        },
        "organization_id": token_info.get("organization_id", ""),
    }
    
    # 可选字段
    if token_info.get("chatgpt_user_id"):
        credentials["chatgpt_user_id"] = token_info["chatgpt_user_id"]
    
    if token_info.get("expires_at"):
        credentials["expires_at"] = token_info["expires_at"]
    
    if token_info.get("expires_in"):
        credentials["expires_in"] = token_info["expires_in"]
    
    if account.get("refresh_token"):
        credentials["refresh_token"] = account["refresh_token"]
    
    # 构建extra
    extra = {"email": email} if email else {}
    
    # 构建账户名称
    name = email if email else f"codex-account-{index + 1}"
    
    return {
        "name": name,
        "platform": "openai",
        "type": "oauth",
        "credentials": credentials,
        "extra": extra,
        "concurrency": 1,
        "priority": 0,
        "rate_multiplier": 1,
        "auto_pause_on_expired": True,
    }

def convert_to_sub2api_format(
    input_file: str = Config.OUTPUT_FILE,
    output_file: str = Config.SUB2API_OUTPUT_FILE
) -> None:
    """
    转换为sub2api导入格式
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    """
    accounts = parse_accounts_file(input_file)
    
    if not accounts:
        logger.warning("没有找到任何账户数据")
        return
    
    # 转换账户格式
    converted_accounts = []
    for i, account in enumerate(accounts):
        converted = convert_account_format(account, i)
        converted_accounts.append(converted)
        logger.info(f"[{i + 1}] 转换账户: {converted['name']}")
    
    # 构建导入数据
    import_data = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "proxies": [],
        "accounts": converted_accounts,
    }
    
    # 写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(import_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"转换完成！已生成 {output_file}")
    logger.info(f"共 {len(converted_accounts)} 个账户可导入sub2api")

# ====================== 主程序 ======================
def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Codex Auto Registration Tool")
    parser.add_argument("--proxy", default=Config.DEFAULT_PROXY, help="代理URL")
    parser.add_argument("--output", default=Config.OUTPUT_FILE, help="输出文件")
    parser.add_argument("--convert-only", action="store_true", help="仅转换格式")
    parser.add_argument("--continuous", action="store_true", help="连续注册模式")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    
    args = parser.parse_args()
    
    # 设置调试模式
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("调试模式已启用")
    
    if args.convert_only:
        # 仅转换格式
        logger.info("启动格式转换模式...")
        convert_to_sub2api_format(args.output)
        logger.info("格式转换完成！")
        return
    
    if args.continuous:
        # 连续注册模式
        logger.info("=" * 50)
        logger.info("启动连续注册模式")
        logger.info(f"代理设置: {args.proxy}")
        logger.info("=" * 50)
        success_count = 0
        
        while True:
            try:
                result = run_single_registration(proxy=args.proxy)
                
                if result:
                    success_count += 1
                    save_account(result, args.output)
                    
                    # 自动转换格式
                    try:
                        convert_to_sub2api_format(args.output)
                    except Exception as e:
                        logger.error(f"转换格式失败: {e}")
                
                # 等待间隔（显示进度）
                for i in range(5):
                    logger.info(f"下次注册将在 {5-i} 秒后开始...")
                    time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("=" * 50)
                logger.info(f"\n注册停止，共成功注册 {success_count} 个账户")
                logger.info("=" * 50)
                break
            except Exception as e:
                logger.error(f"注册失败: {e}")
                logger.error("3秒后重试...")
                time.sleep(3)
    else:
        # 单次注册模式
        logger.info("=" * 50)
        logger.info("启动单次注册模式")
        logger.info(f"代理设置: {args.proxy}")
        logger.info("=" * 50)
        result = run_single_registration(proxy=args.proxy)
        
        if result:
            save_account(result, args.output)
            convert_to_sub2api_format(args.output)
            logger.info("=" * 50)
            logger.info("注册完成！")
            logger.info("=" * 50)
        else:
            logger.error("=" * 50)
            logger.error("注册失败，请查看日志获取详细信息")
            logger.error("=" * 50)

if __name__ == "__main__":
    main()