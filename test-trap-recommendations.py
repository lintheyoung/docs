#!/usr/bin/env python3
"""
RatTrap API - 捕鼠器推荐接口测试脚本
测试端点: POST /trap-recommendations
覆盖正常场景、边界条件、错误处理

使用方法:
1. 直接运行测试脚本（会自动使用 Preview 环境测试账号登录）
   - 邮箱: test@example.com
   - 密码: test1234
   - 自动获取 JWT Token 并打印到控制台
2. 运行: python3 test-trap-recommendations.py
3. 可选配置:
   - 修改 TEST_EMAIL/TEST_PASSWORD 使用不同账号
   - 修改 TEST_MEDIA_ASSET_ID 使用不同测试图片
   - 可用 ID: ma_test_trap_image_001, ma_test_trap_image_002, ma_test_trap_image_003

测试覆盖:
- 必填字段验证
- 枚举值验证
- limit 参数边界测试
- no_trap 模式测试（购买新捕鼠器推荐）
- existing_trap 模式测试（现有捕鼠器识别）
- preferences 组合测试（用户偏好）
- 认证和权限测试
- 边界和异常情况
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
import uuid

# ==================== 配置区域 ====================
# Preview 环境测试账号（自动登录）
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "test1234"

# API 基础地址
BASE_URL = "https://vwinvkxxheuexvpvzibt.supabase.co/functions/v1"
AUTH_URL = "https://vwinvkxxheuexvpvzibt.supabase.co"

# Supabase Anon Key（公开密钥，用于认证 API）
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3aW52a3h4aGV1ZXh2cHZ6aWJ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzOTgwOTcsImV4cCI6MjA3OTk3NDA5N30.QS6bhQMQdgPG2_bU9sYpMGyGPX7JNTJp2cZ8KVutucc"

# 测试用 media_asset_id（Preview 环境预配置的测试数据）
# 可用的测试 ID: ma_test_trap_image_001, ma_test_trap_image_002, ma_test_trap_image_003
TEST_MEDIA_ASSET_ID = "ma_test_trap_image_001"

# 全局 Token（自动登录后设置）
AUTH_TOKEN = None

# ==================== 颜色定义 ====================
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color

# ==================== 测试统计 ====================
@dataclass
class TestStats:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

stats = TestStats()

# ==================== 辅助函数 ====================
def print_header(text: str):
    print()
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{text}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")

def print_section(text: str):
    print()
    print(f"{Colors.MAGENTA}{'─' * 70}{Colors.NC}")
    print(f"{Colors.MAGENTA}{text}{Colors.NC}")
    print(f"{Colors.MAGENTA}{'─' * 70}{Colors.NC}")

def print_test(text: str):
    stats.total += 1
    print()
    print(f"{Colors.BLUE}[测试 {stats.total}] {text}{Colors.NC}")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def print_info(text: str):
    print(f"{Colors.YELLOW}→ {text}{Colors.NC}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")

def api_call(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    extra_headers: Optional[Dict] = None,
    use_auth: bool = True
) -> requests.Response:
    """执行 API 调用并打印请求/响应信息"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if use_auth:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    if extra_headers:
        headers.update(extra_headers)

    # 打印请求信息
    print(f"{Colors.YELLOW}{'━' * 70}{Colors.NC}")
    print(f"{Colors.YELLOW}📤 请求{Colors.NC}")
    print(f"{Colors.YELLOW}方法: {Colors.NC}{method}")
    print(f"{Colors.YELLOW}URL: {Colors.NC}{url}")
    if not use_auth:
        print(f"{Colors.YELLOW}认证: {Colors.NC}无 (测试未授权访问)")
    if data is not None:
        print(f"{Colors.YELLOW}Body:{Colors.NC}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"{Colors.YELLOW}{'━' * 70}{Colors.NC}")

    # 执行请求（LLM 调用可能需要较长时间）
    try:
        response = requests.request(method, url, json=data, headers=headers, timeout=90)
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}请求异常: {e}{Colors.NC}")
        raise

    # 打印响应信息
    print(f"{Colors.CYAN}📥 响应{Colors.NC}")
    print(f"{Colors.CYAN}状态码: {Colors.NC}{response.status_code}")
    print(f"{Colors.CYAN}Body:{Colors.NC}")
    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=2, ensure_ascii=False))

        # 检查是否为 LLM_QUOTA_EXCEEDED 错误
        if response.status_code in [429, 503]:
            error_code = response_json.get('error', {}).get('code')
            if error_code == 'LLM_QUOTA_EXCEEDED':
                print()
                print(f"{Colors.RED}{'=' * 70}{Colors.NC}")
                print(f"{Colors.RED}❌ 致命错误: LLM 服务配额已用尽{Colors.NC}")
                print(f"{Colors.RED}{'=' * 70}{Colors.NC}")
                print()
                print(f"{Colors.YELLOW}错误信息:{Colors.NC}")
                print(f"  {response_json.get('error', {}).get('message', 'LLM quota exceeded')}")
                print()
                print(f"{Colors.YELLOW}建议操作:{Colors.NC}")
                print(f"  1. 检查 OpenRouter 账户余额")
                print(f"  2. 充值账户（建议至少 $50）")
                print(f"  3. 联系运维团队处理")
                print()
                print(f"{Colors.YELLOW}测试已中止，避免继续消耗无效请求{Colors.NC}")
                print()
                sys.exit(1)

    except:
        print(response.text)
    print(f"{Colors.CYAN}{'━' * 70}{Colors.NC}")
    print()

    return response

def check_status(expected: int, actual: int, test_name: str) -> bool:
    """检查 HTTP 状态码"""
    if actual == expected:
        print(f"{Colors.GREEN}✓ 通过: {test_name} (HTTP {actual}){Colors.NC}")
        stats.passed += 1
        return True
    else:
        print(f"{Colors.RED}✗ 失败: {test_name} - 期望 HTTP {expected}, 实际 HTTP {actual}{Colors.NC}")
        stats.failed += 1
        return False

def check_field(data: Dict, field: str, expected: Any, test_name: str) -> bool:
    """检查 JSON 字段值"""
    keys = field.strip('.').split('.')
    value = data
    try:
        for key in keys:
            value = value[key]
        if value == expected:
            print(f"{Colors.GREEN}  ✓ {test_name}: {field} = {expected}{Colors.NC}")
            return True
        else:
            print(f"{Colors.RED}  ✗ {test_name}: {field} 期望 '{expected}', 实际 '{value}'{Colors.NC}")
            return False
    except (KeyError, TypeError):
        print(f"{Colors.RED}  ✗ {test_name}: {field} 不存在{Colors.NC}")
        return False

def check_field_exists(data: Dict, field: str, test_name: str) -> bool:
    """检查字段是否存在"""
    keys = field.strip('.').split('.')
    value = data
    try:
        for key in keys:
            value = value[key]
        print(f"{Colors.GREEN}  ✓ {test_name}: {field} 存在{Colors.NC}")
        return True
    except (KeyError, TypeError):
        print(f"{Colors.RED}  ✗ {test_name}: {field} 不存在{Colors.NC}")
        return False

def check_array_length(data: Dict, field: str, expected_length: int, test_name: str) -> bool:
    """检查数组长度"""
    keys = field.strip('.').split('.')
    value = data
    try:
        for key in keys:
            value = value[key]
        if isinstance(value, list):
            actual_length = len(value)
            if actual_length == expected_length:
                print(f"{Colors.GREEN}  ✓ {test_name}: {field} 长度 = {expected_length}{Colors.NC}")
                return True
            else:
                print(f"{Colors.RED}  ✗ {test_name}: {field} 长度期望 {expected_length}, 实际 {actual_length}{Colors.NC}")
                return False
        else:
            print(f"{Colors.RED}  ✗ {test_name}: {field} 不是数组{Colors.NC}")
            return False
    except (KeyError, TypeError):
        print(f"{Colors.RED}  ✗ {test_name}: {field} 不存在{Colors.NC}")
        return False

def check_array_max_length(data: Dict, field: str, max_length: int, test_name: str) -> bool:
    """检查数组长度不超过最大值"""
    keys = field.strip('.').split('.')
    value = data
    try:
        for key in keys:
            value = value[key]
        if isinstance(value, list):
            actual_length = len(value)
            if actual_length <= max_length:
                print(f"{Colors.GREEN}  ✓ {test_name}: {field} 长度 {actual_length} <= {max_length}{Colors.NC}")
                return True
            else:
                print(f"{Colors.RED}  ✗ {test_name}: {field} 长度 {actual_length} > {max_length}{Colors.NC}")
                return False
        else:
            print(f"{Colors.RED}  ✗ {test_name}: {field} 不是数组{Colors.NC}")
            return False
    except (KeyError, TypeError):
        print(f"{Colors.RED}  ✗ {test_name}: {field} 不存在{Colors.NC}")
        return False

# ==================== 自动登录获取 Token ====================
def auto_login() -> str:
    """自动登录 Preview 环境获取 JWT Token"""
    global AUTH_TOKEN

    print_section("🔐 自动登录 Preview 环境")
    print_info(f"Email: {TEST_EMAIL}")
    print_info(f"Password: {'*' * len(TEST_PASSWORD)}")

    try:
        response = requests.post(
            f"{AUTH_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                AUTH_TOKEN = token
                print_success("登录成功！")
                print()
                print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")
                print(f"{Colors.CYAN}🎫 JWT Token (前 50 个字符):{Colors.NC}")
                print(f"{Colors.GREEN}{token[:50]}...{Colors.NC}")
                print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")
                print()

                # 打印 token 过期时间
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.now().timestamp() + expires_in
                print_info(f"Token 有效期: {expires_in} 秒 (约 {expires_in // 60} 分钟)")
                print_info(f"过期时间: {datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M:%S')}")
                print()

                return token
            else:
                print_error("响应中未找到 access_token")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                sys.exit(1)
        else:
            print_error(f"登录失败 (HTTP {response.status_code})")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            except:
                print(response.text)
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print_error(f"登录请求失败: {e}")
        sys.exit(1)

# ==================== 创建测试用的 media_asset_id ====================
def get_test_media_asset() -> Optional[str]:
    """获取测试用的 media_asset_id"""
    print_info("使用 Preview 环境预配置的测试数据...")
    print_info(f"media_asset_id: {TEST_MEDIA_ASSET_ID}")
    print_info("💡 Preview 环境自动初始化了以下测试 ID:")
    print_info("   - ma_test_trap_image_001")
    print_info("   - ma_test_trap_image_002")
    print_info("   - ma_test_trap_image_003")
    return TEST_MEDIA_ASSET_ID

# ==================== 开始测试 ====================
def main():
    print()
    print(f"{Colors.CYAN}╔{'═' * 68}╗{Colors.NC}")
    print(f"{Colors.CYAN}║{' ' * 12}RatTrap API - 捕鼠器推荐接口测试{' ' * 23}║{Colors.NC}")
    print(f"{Colors.CYAN}║{' ' * 12}测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{' ' * 21}║{Colors.NC}")
    print(f"{Colors.CYAN}╚{'═' * 68}╝{Colors.NC}")
    print()

    # 自动登录获取 Token
    auto_login()

    # 准备测试数据
    test_media_id = get_test_media_asset()

    # ============================================
    # 第一部分：必填字段验证
    # ============================================
    print_header("第一部分：必填字段验证")

    # 测试 1: 完全空的 body
    print_test("完全空的 body（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {})
    if check_status(400, resp.status_code, "空 body 验证"):
        try:
            data = resp.json()
            print_info(f"错误信息: {data.get('error', {}).get('message')}")
        except:
            pass

    # 测试 2: 缺少 mode
    print_test("缺少 mode 字段（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "rodent_target": "rat"
    })
    check_status(400, resp.status_code, "缺少 mode")

    # 测试 3: 缺少 rodent_target
    print_test("缺少 rodent_target 字段（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap"
    })
    check_status(400, resp.status_code, "缺少 rodent_target")

    # 测试 4: mode=existing_trap 但缺少 media_asset_id
    print_test("mode=existing_trap 但缺少 media_asset_id（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "existing_trap",
        "rodent_target": "rat"
    })
    check_status(400, resp.status_code, "existing_trap 模式缺少 media_asset_id")

    # ============================================
    # 第二部分：无效枚举值测试
    # ============================================
    print_header("第二部分：无效枚举值测试")

    # 测试 5: 无效的 mode 值
    print_test("无效的 mode 值（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "invalid_mode",
        "rodent_target": "rat"
    })
    check_status(400, resp.status_code, "无效 mode")

    # 测试 6: 无效的 rodent_target 值
    print_test("无效的 rodent_target 值（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "dog"
    })
    check_status(400, resp.status_code, "无效 rodent_target")

    # 测试 7: 无效的 budget_level
    print_test("无效的 budget_level（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "preferences": {
            "budget_level": "very_high"
        }
    })
    check_status(400, resp.status_code, "无效 budget_level")

    # 测试 8: 无效的 environment
    print_test("无效的 environment（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "country": "TW",
            "environment": "spaceship"
        }
    })
    check_status(400, resp.status_code, "无效 environment")

    # ============================================
    # 第三部分：limit 参数边界测试
    # ============================================
    print_header("第三部分：limit 参数边界测试")

    # 测试 9: limit=0（应失败或返回空数组）
    print_test("limit=0（应返回 400 或空数组）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "limit": 0
    })
    if resp.status_code == 400:
        check_status(400, resp.status_code, "limit=0 返回错误")
    elif resp.status_code == 200:
        data = resp.json()
        if 'recommended_traps' in data and len(data['recommended_traps']) == 0:
            print_success("limit=0 返回空数组")
            stats.passed += 1
        else:
            print_error("limit=0 但返回了数据")
            stats.failed += 1

    # 测试 10: limit=-1（负数，应失败）
    print_test("limit=-1（负数，应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "limit": -1
    })
    check_status(400, resp.status_code, "负数 limit")

    # 测试 11: limit=11（超过最大值 10）
    print_test("limit=11（超过最大值 10，应返回 400 或截断到 10）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "limit": 11
    })
    if resp.status_code == 400:
        check_status(400, resp.status_code, "limit=11 返回错误")
    elif resp.status_code == 200:
        data = resp.json()
        if 'recommended_traps' in data:
            actual_length = len(data['recommended_traps'])
            if actual_length <= 10:
                print_success(f"limit=11 被截断到 {actual_length}")
                stats.passed += 1
            else:
                print_error(f"limit=11 返回了 {actual_length} 个结果")
                stats.failed += 1

    # 测试 12: limit=1（最小有效值）
    print_test("limit=1（最小有效值）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "limit": 1
    })
    if check_status(200, resp.status_code, "limit=1"):
        data = resp.json()
        check_array_max_length(data, "recommended_traps", 1, "返回数组长度")

    # 测试 13: limit=10（最大有效值）
    print_test("limit=10（最大有效值）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "limit": 10
    })
    if check_status(200, resp.status_code, "limit=10"):
        data = resp.json()
        check_array_max_length(data, "recommended_traps", 10, "返回数组长度")

    # 测试 14: 不传 limit（使用默认值 3）
    print_test("不传 limit（应使用默认值 3）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat"
    })
    if check_status(200, resp.status_code, "默认 limit"):
        data = resp.json()
        check_array_max_length(data, "recommended_traps", 3, "返回数组长度")

    # ============================================
    # 第四部分：no_trap 模式正常场景
    # ============================================
    print_header("第四部分：no_trap 模式正常场景")

    # 测试 15: 最简模式（只传必填字段）
    print_test("no_trap 模式 - 最简请求（rat）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat"
    })
    if check_status(200, resp.status_code, "no_trap 最简请求"):
        data = resp.json()
        check_field(data, "object", "trap_recommendation_result", "对象类型")
        check_field(data, "mode", "no_trap", "模式")
        check_field(data, "rodent_target", "rat", "目标鼠种")
        check_field_exists(data, "recommended_traps", "推荐列表")
        check_field_exists(data, "created", "创建时间")

        # 验证 existing_trap 字段
        if data.get("existing_trap") is None:
            print_success("existing_trap 为 null（符合 no_trap 模式）")
        else:
            print_warning(f"existing_trap 不为 null: {data.get('existing_trap')}")

    # 测试 16: rodent_target=mouse
    print_test("no_trap 模式 - rodent_target=mouse")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "mouse"
    })
    if check_status(200, resp.status_code, "rodent_target=mouse"):
        data = resp.json()
        check_field(data, "rodent_target", "mouse", "目标鼠种")

    # 测试 17: rodent_target=unknown（应返回 400）
    print_test("no_trap 模式 - rodent_target=unknown（应返回 400 UNKNOWN_RODENT_NOT_SUPPORTED）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "unknown"
    })
    if check_status(400, resp.status_code, "rodent_target=unknown 返回错误"):
        try:
            data = resp.json()
            error_code = data.get('error', {}).get('code')
            if error_code == "UNKNOWN_RODENT_NOT_SUPPORTED":
                print_success(f"正确返回错误码: {error_code}")
            else:
                print_warning(f"错误码不符: 期望 UNKNOWN_RODENT_NOT_SUPPORTED, 实际 {error_code}")
        except:
            pass

    # 测试 18: 带 user_location
    print_test("no_trap 模式 - 带完整 user_location")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "country": "TW",
            "city": "Taipei",
            "environment": "apartment"
        }
    })
    check_status(200, resp.status_code, "带 user_location")

    # 测试 19: 不同的 environment 值
    print_test("no_trap 模式 - environment=restaurant_kitchen")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "country": "US",
            "city": "New York",
            "environment": "restaurant_kitchen"
        }
    })
    check_status(200, resp.status_code, "environment=restaurant_kitchen")

    # 测试 20: environment=farm
    print_test("no_trap 模式 - environment=farm")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "environment": "farm"
        }
    })
    check_status(200, resp.status_code, "environment=farm")

    # ============================================
    # 第五部分：preferences 测试
    # ============================================
    print_header("第五部分：preferences 组合测试")

    # 测试 21: avoid_killing=true
    print_test("preferences - avoid_killing=true")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "mouse",
        "preferences": {
            "avoid_killing": True
        }
    })
    if check_status(200, resp.status_code, "avoid_killing=true"):
        data = resp.json()
        # 检查推荐的陷阱是否为非致命型（cage_trap）
        if 'recommended_traps' in data and len(data['recommended_traps']) > 0:
            trap_types = [trap.get('trap_type') for trap in data['recommended_traps']]
            print_info(f"推荐的陷阱类型: {trap_types}")
            # 不应该包含 snap_trap, electronic_trap, glue_board
            killing_types = ['snap_trap', 'electronic_trap', 'glue_board']
            has_killing = any(t in killing_types for t in trap_types)
            if not has_killing:
                print_success("未推荐致命型陷阱（符合 avoid_killing）")
            else:
                print_warning("推荐了致命型陷阱")

    # 测试 22: avoid_killing=false
    print_test("preferences - avoid_killing=false")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "preferences": {
            "avoid_killing": False
        }
    })
    check_status(200, resp.status_code, "avoid_killing=false")

    # 测试 23: has_children_or_pets=true
    print_test("preferences - has_children_or_pets=true")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "mouse",
        "preferences": {
            "has_children_or_pets": True
        }
    })
    if check_status(200, resp.status_code, "has_children_or_pets=true"):
        data = resp.json()
        # 检查安全等级
        if 'recommended_traps' in data and len(data['recommended_traps']) > 0:
            safety_levels = [trap.get('safety_level') for trap in data['recommended_traps']]
            print_info(f"推荐陷阱的安全等级: {safety_levels}")

    # 测试 24: budget_level=low
    print_test("preferences - budget_level=low")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "preferences": {
            "budget_level": "low"
        }
    })
    if check_status(200, resp.status_code, "budget_level=low"):
        data = resp.json()
        if 'recommended_traps' in data and len(data['recommended_traps']) > 0:
            price_bands = [trap.get('price_band') for trap in data['recommended_traps']]
            print_info(f"推荐陷阱的价格段: {price_bands}")

    # 测试 25: budget_level=medium
    print_test("preferences - budget_level=medium")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "mouse",
        "preferences": {
            "budget_level": "medium"
        }
    })
    check_status(200, resp.status_code, "budget_level=medium")

    # 测试 26: budget_level=high
    print_test("preferences - budget_level=high")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "preferences": {
            "budget_level": "high"
        }
    })
    check_status(200, resp.status_code, "budget_level=high")

    # 测试 27: 组合 preferences（避免杀死 + 有儿童/宠物 + 低预算）
    print_test("preferences - 组合条件（避免杀死 + 有儿童/宠物 + 低预算）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "mouse",
        "preferences": {
            "avoid_killing": True,
            "has_children_or_pets": True,
            "budget_level": "low"
        }
    })
    if check_status(200, resp.status_code, "组合 preferences"):
        data = resp.json()
        if 'recommended_traps' in data and len(data['recommended_traps']) > 0:
            for i, trap in enumerate(data['recommended_traps'], 1):
                print_info(f"推荐 {i}: {trap.get('label')} - "
                          f"类型:{trap.get('trap_type')}, "
                          f"安全:{trap.get('safety_level')}, "
                          f"价格:{trap.get('price_band')}")

    # 测试 28: 只传部分 preferences
    print_test("preferences - 只传 has_children_or_pets")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "preferences": {
            "has_children_or_pets": True
        }
    })
    check_status(200, resp.status_code, "部分 preferences")

    # ============================================
    # 第六部分：existing_trap 模式测试
    # ============================================
    print_header("第六部分：existing_trap 模式测试")

    # 测试 29: existing_trap 模式 - 基本请求
    print_test("existing_trap 模式 - 基本请求")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "existing_trap",
        "rodent_target": "rat",
        "media_asset_id": test_media_id
    })
    if check_status(200, resp.status_code, "existing_trap 基本请求"):
        data = resp.json()
        check_field(data, "mode", "existing_trap", "模式")
        check_field_exists(data, "existing_trap", "现有陷阱分析")

        # 检查 existing_trap 结构
        if data.get('existing_trap'):
            existing = data['existing_trap']
            check_field_exists(existing, "detected_type", "检测类型")
            check_field_exists(existing, "is_suitable", "适用性")
            check_field_exists(existing, "suitability_score", "适用性分数")
            print_info(f"检测到的陷阱类型: {existing.get('detected_type')}")
            print_info(f"是否适用: {existing.get('is_suitable')}")
            print_info(f"适用性分数: {existing.get('suitability_score')}")

    # 测试 30: existing_trap 模式 - 带 preferences
    print_test("existing_trap 模式 - 带 preferences")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "existing_trap",
        "rodent_target": "mouse",
        "media_asset_id": test_media_id,
        "preferences": {
            "avoid_killing": True
        }
    })
    check_status(200, resp.status_code, "existing_trap 带 preferences")

    # 测试 31: existing_trap 模式 - 空字符串 media_asset_id
    print_test("existing_trap 模式 - 空字符串 media_asset_id（应返回 400）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "existing_trap",
        "rodent_target": "rat",
        "media_asset_id": ""
    })
    check_status(400, resp.status_code, "空字符串 media_asset_id")

    # 测试 32: existing_trap 模式 - 无效的 media_asset_id
    print_test("existing_trap 模式 - 无效的 media_asset_id")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "existing_trap",
        "rodent_target": "rat",
        "media_asset_id": "ma_nonexistent_12345"
    })
    # 可能返回 404 或 400，取决于后端实现
    if resp.status_code in [400, 404]:
        print_success(f"正确返回错误 (HTTP {resp.status_code})")
        stats.passed += 1
    else:
        print_error(f"期望 400 或 404，实际 {resp.status_code}")
        stats.failed += 1

    # ============================================
    # 第七部分：完整请求测试
    # ============================================
    print_header("第七部分：完整请求测试")

    # 测试 33: 所有可选字段都提供
    print_test("no_trap 模式 - 所有可选字段")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "country": "TW",
            "city": "Taipei",
            "environment": "apartment"
        },
        "preferences": {
            "avoid_killing": False,
            "has_children_or_pets": True,
            "budget_level": "medium"
        },
        "limit": 5
    })
    if check_status(200, resp.status_code, "完整请求"):
        data = resp.json()
        check_array_max_length(data, "recommended_traps", 5, "limit=5 验证")

        # 验证推荐结果的完整性
        if 'recommended_traps' in data and len(data['recommended_traps']) > 0:
            print_info(f"返回 {len(data['recommended_traps'])} 个推荐")
            trap = data['recommended_traps'][0]

            # 验证 TrapProduct 结构
            check_field(trap, "object", "trap_product", "产品对象类型")
            check_field_exists(trap, "id", "产品 ID")
            check_field_exists(trap, "trap_type", "陷阱类型")
            check_field_exists(trap, "label", "产品标签")
            check_field_exists(trap, "description", "产品描述")
            check_field_exists(trap, "for_rodent", "适用鼠种")
            check_field_exists(trap, "suitability_score", "适用性分数")
            check_field_exists(trap, "safety_level", "安全等级")
            check_field_exists(trap, "price_band", "价格段")
            check_field_exists(trap, "recommended_reason", "推荐理由")

    # 测试 34: existing_trap 模式 - 完整请求
    print_test("existing_trap 模式 - 完整请求")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "existing_trap",
        "rodent_target": "mouse",
        "media_asset_id": test_media_id,
        "user_location": {
            "country": "US",
            "city": "Los Angeles",
            "environment": "house"
        },
        "preferences": {
            "avoid_killing": True,
            "has_children_or_pets": True,
            "budget_level": "high"
        },
        "limit": 3
    })
    if check_status(200, resp.status_code, "existing_trap 完整请求"):
        data = resp.json()
        # 应该同时有 existing_trap 和 recommended_traps
        check_field_exists(data, "existing_trap", "现有陷阱分析")
        check_field_exists(data, "recommended_traps", "推荐列表")

    # ============================================
    # 第八部分：认证和权限测试
    # ============================================
    print_header("第八部分：认证和权限测试")

    # 测试 35: 无 Authorization header
    print_test("无 Authorization header（应返回 401）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat"
    }, use_auth=False)
    check_status(401, resp.status_code, "无认证")

    # 测试 36: 无效的 token
    print_test("无效的 Bearer token（应返回 401）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat"
    }, extra_headers={"Authorization": "Bearer invalid_token_12345"})
    check_status(401, resp.status_code, "无效 token")

    # ============================================
    # 第九部分：边界和异常情况
    # ============================================
    print_header("第九部分：边界和异常情况")

    # 测试 37: mode=no_trap 但传了 media_asset_id（应被忽略）
    print_test("no_trap 模式传 media_asset_id（应被忽略）")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "media_asset_id": test_media_id
    })
    if check_status(200, resp.status_code, "no_trap 带 media_asset_id"):
        data = resp.json()
        if data.get("existing_trap") is None:
            print_success("media_asset_id 被正确忽略")
        else:
            print_warning("media_asset_id 未被忽略")

    # 测试 38: user_location 只传 country
    print_test("user_location 只传 country")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "country": "JP"
        }
    })
    check_status(200, resp.status_code, "只传 country")

    # 测试 39: user_location 为空对象
    print_test("user_location 为空对象")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {}
    })
    # 应该成功，只是没有位置信息
    check_status(200, resp.status_code, "空 user_location")

    # 测试 40: preferences 为空对象
    print_test("preferences 为空对象")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "mouse",
        "preferences": {}
    })
    check_status(200, resp.status_code, "空 preferences")

    # 测试 41: null 值字段
    print_test("传 null 值的可选字段")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": None,
        "preferences": None
    })
    check_status(200, resp.status_code, "null 值字段")

    # 测试 42: 极长的字符串（country）
    print_test("极长的 country 字符串")
    resp = api_call("POST", "/trap-recommendations", {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "country": "A" * 1000
        }
    })
    # 可能返回 400 或成功，取决于验证
    if resp.status_code in [200, 400]:
        print_success(f"返回 {resp.status_code}（合理）")
        stats.passed += 1
    else:
        print_error(f"意外状态码 {resp.status_code}")
        stats.failed += 1

    # 测试 43: 重复请求（测试一致性）
    print_test("重复相同请求（测试一致性）")
    request_data = {
        "mode": "no_trap",
        "rodent_target": "rat",
        "user_location": {
            "country": "TW",
            "environment": "apartment"
        },
        "limit": 3
    }

    resp1 = api_call("POST", "/trap-recommendations", request_data)
    resp2 = api_call("POST", "/trap-recommendations", request_data)

    if resp1.status_code == 200 and resp2.status_code == 200:
        data1 = resp1.json()
        data2 = resp2.json()

        # 比较推荐数量
        len1 = len(data1.get('recommended_traps', []))
        len2 = len(data2.get('recommended_traps', []))

        if len1 == len2:
            print_success(f"两次请求返回相同数量的推荐 ({len1})")
            stats.passed += 1
        else:
            print_warning(f"两次请求返回不同数量: {len1} vs {len2}")
            stats.passed += 1  # 仍然算通过，因为推荐可能有随机性
    else:
        print_error("重复请求失败")
        stats.failed += 1

    # ============================================
    # 测试结果汇总
    # ============================================
    print_header("测试结果汇总")
    print()
    print(f"总测试数: {Colors.CYAN}{stats.total}{Colors.NC}")
    print(f"通过: {Colors.GREEN}{stats.passed}{Colors.NC}")
    print(f"失败: {Colors.RED}{stats.failed}{Colors.NC}")
    if stats.skipped > 0:
        print(f"跳过: {Colors.YELLOW}{stats.skipped}{Colors.NC}")
    print()

    pass_rate = (stats.passed / stats.total * 100) if stats.total > 0 else 0
    print(f"通过率: {Colors.CYAN}{pass_rate:.1f}%{Colors.NC}")
    print()

    if stats.failed == 0:
        print(f"{Colors.GREEN}╔{'═' * 68}╗{Colors.NC}")
        print(f"{Colors.GREEN}║{' ' * 24}所有测试通过！{' ' * 25}║{Colors.NC}")
        print(f"{Colors.GREEN}╚{'═' * 68}╝{Colors.NC}")
    else:
        print(f"{Colors.RED}╔{'═' * 68}╗{Colors.NC}")
        print(f"{Colors.RED}║{' ' * 22}有 {stats.failed} 个测试失败{' ' * 25}║{Colors.NC}")
        print(f"{Colors.RED}╚{'═' * 68}╝{Colors.NC}")

    print()
    print(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 返回退出码
    sys.exit(0 if stats.failed == 0 else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试被用户中断{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}测试发生异常: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
