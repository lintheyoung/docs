#!/usr/bin/env python3
"""
RatTrap API - 诱饵推荐接口测试脚本
测试端点: POST /bait-recommendations
覆盖正常场景、边界条件、错误处理

使用方法:
1. 直接运行测试脚本（会自动使用 Preview 环境测试账号登录）
   - 邮箱: test@example.com
   - 密码: test1234
   - 自动获取 JWT Token 并打印到控制台
2. 运行: python3 test-bait-recommendations.py
3. 可选配置:
   - 修改 TEST_EMAIL/TEST_PASSWORD 使用不同账号

测试覆盖:
- 必填字段验证
- 枚举值验证
- limit 参数边界测试
- standard 模式测试（标准推荐）
- from_fridge 模式测试（冰箱识别）
- preferences 组合测试（用户偏好）
- 认证和权限测试
- 边界和异常情况
"""

import requests
import json
import sys
import os
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
        response = requests.request(method, url, json=data, headers=headers, timeout=180)
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

def check_error_code(data: Dict, expected_code: str) -> bool:
    """检查错误码"""
    actual_code = data.get('error', {}).get('code', '')
    if actual_code == expected_code:
        print(f"{Colors.GREEN}✓ 正确返回错误码: {expected_code}{Colors.NC}")
        return True
    else:
        print(f"{Colors.RED}✗ 错误码不匹配 - 期望 {expected_code}, 实际 {actual_code}{Colors.NC}")
        return False

def login() -> str:
    """登录并获取 JWT Token"""
    print_header("🔐 自动登录获取 JWT Token")
    print_info(f"邮箱: {TEST_EMAIL}")
    print_info(f"密码: {TEST_PASSWORD}")
    print()

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
        timeout=30
    )

    if response.status_code == 200:
        token = response.json()["access_token"]
        print_success("登录成功！")
        print_info(f"Token: {token[:50]}...")
        return token
    else:
        print_error(f"登录失败: {response.status_code}")
        print(response.text)
        sys.exit(1)

def get_test_media_asset() -> Optional[str]:
    """通过 media-assets 接口上传测试图片并获取 media_asset_id"""
    print_info("通过 media-assets 接口上传测试图片...")

    # 查找测试图片
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "rattrap-api", "test-assets", "fridge.jpg")

    if not os.path.exists(image_path):
        print_warning(f"测试图片不存在: {image_path}")
        print_warning("创建临时测试图片...")
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='blue')
            temp_path = '/tmp/test_fridge_image.jpg'
            img.save(temp_path)
            image_path = temp_path
        except ImportError:
            print_error("PIL 库未安装，无法创建临时图片")
            return None

    try:
        # 步骤1: 创建 media asset 资源
        response = requests.post(
            f"{BASE_URL}/media-assets",
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "purpose": "check",  # 使用 check 而非 bait
                "content_type": "image/jpeg",
                "metadata": {
                    "test_source": "bait_recommendations_test",
                    "usage": "from_fridge_mode_test"
                }
            },
            timeout=30
        )

        if response.status_code != 200:
            print_error(f"创建媒体资源失败: {response.status_code}")
            print(response.text)
            return None

        data = response.json()
        media_id = data.get('id')
        upload_url = data.get('upload_url')

        print_success(f"创建媒体资源成功: {media_id}")

        # 步骤2: 上传图片到预签名URL
        with open(image_path, 'rb') as f:
            upload_response = requests.put(
                upload_url,
                headers={"Content-Type": "image/jpeg"},
                data=f,
                timeout=30
            )

        if upload_response.status_code in [200, 204]:
            print_success(f"图片上传成功: {media_id}")
            return media_id
        else:
            print_error(f"图片上传失败: {upload_response.status_code}")
            return None

    except Exception as e:
        print_error(f"上传图片过程出错: {e}")
        return None

# ==================== 测试函数 ====================

def test_required_fields():
    """测试必填字段验证"""
    print_section("📋 第一部分: 必填字段验证")

    # 测试 1: 空 body
    print_test("空 body 验证")
    resp = api_call("POST", "/bait-recommendations", data={})
    check_status(400, resp.status_code, "空 body 验证")

    # 测试 2: 缺少 mode
    print_test("缺少 mode")
    resp = api_call("POST", "/bait-recommendations", data={
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    check_status(400, resp.status_code, "缺少 mode")

    # 测试 3: 缺少 rodent_target
    print_test("缺少 rodent_target")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "trap_type": "snap_trap"
    })
    check_status(400, resp.status_code, "缺少 rodent_target")

    # 测试 4: 缺少 trap_type
    print_test("缺少 trap_type")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat"
    })
    check_status(400, resp.status_code, "缺少 trap_type")

    # 测试 5: from_fridge 模式缺少 media_asset_id
    print_test("from_fridge 模式缺少 media_asset_id")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "from_fridge",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    check_status(400, resp.status_code, "from_fridge 模式缺少 media_asset_id")

def test_enum_validation():
    """测试枚举值验证"""
    print_section("🔢 第二部分: 枚举值验证")

    # 测试 6: 无效 mode
    print_test("无效 mode")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "invalid_mode",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    check_status(400, resp.status_code, "无效 mode")

    # 测试 7: 无效 rodent_target
    print_test("无效 rodent_target")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "hamster",
        "trap_type": "snap_trap"
    })
    check_status(400, resp.status_code, "无效 rodent_target")

    # 测试 8: 无效 trap_type
    print_test("无效 trap_type")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "laser_trap"
    })
    check_status(400, resp.status_code, "无效 trap_type")

def test_limit_parameter():
    """测试 limit 参数"""
    print_section("🔢 第三部分: limit 参数测试")

    # 测试 9: limit=0
    print_test("limit=0 返回错误")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "limit": 0
    })
    check_status(400, resp.status_code, "limit=0 返回错误")

    # 测试 10: 负数 limit
    print_test("负数 limit")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "limit": -1
    })
    check_status(400, resp.status_code, "负数 limit")

    # 测试 11: limit=1
    print_test("limit=1")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "limit": 1
    })
    if check_status(200, resp.status_code, "limit=1"):
        data = resp.json()
        # 检查 alternative_baits 数组长度不超过 limit-1
        alt_count = len(data.get('alternative_baits', []))
        if alt_count <= 0:
            print_success(f"  ✓ 返回数组长度: alternative_baits 长度 {alt_count} <= 0")
        else:
            print_error(f"  ✗ 返回数组长度: alternative_baits 长度 {alt_count} > 0")

    # 测试 12: limit=5
    print_test("limit=5")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "limit": 5
    })
    if check_status(200, resp.status_code, "limit=5"):
        data = resp.json()
        alt_count = len(data.get('alternative_baits', []))
        if alt_count <= 4:
            print_success(f"  ✓ 返回数组长度: alternative_baits 长度 {alt_count} <= 4")
        else:
            print_error(f"  ✗ 返回数组长度: alternative_baits 长度 {alt_count} > 4")

    # 测试 13: 默认 limit
    print_test("默认 limit")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    if check_status(200, resp.status_code, "默认 limit"):
        data = resp.json()
        alt_count = len(data.get('alternative_baits', []))
        if alt_count <= 2:  # 默认 limit=3, alternative_baits 最多 2 个
            print_success(f"  ✓ 返回数组长度: alternative_baits 长度 {alt_count} <= 2")

def test_standard_mode():
    """测试 standard 模式"""
    print_section("🎯 第四部分: standard 模式测试")

    # 测试 14: 最简请求
    print_test("standard 最简请求")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    if check_status(200, resp.status_code, "standard 最简请求"):
        data = resp.json()
        check_field(data, "object", "bait_recommendation_result", "对象类型")
        check_field(data, "mode", "standard", "模式")
        check_field(data, "rodent_target", "rat", "目标鼠种")
        check_field_exists(data, "primary_bait", "主推荐诱饵")
        check_field_exists(data, "created", "创建时间")

        # 检查 fridge_analysis 应该为 null
        if data.get("fridge_analysis") is None:
            print_success("✓ fridge_analysis 为 null（符合 standard 模式）")

    # 测试 15: rodent_target=mouse
    print_test("rodent_target=mouse")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "mouse",
        "trap_type": "snap_trap"
    })
    if check_status(200, resp.status_code, "rodent_target=mouse"):
        data = resp.json()
        check_field(data, "rodent_target", "mouse", "目标鼠种")

    # 测试 16: rodent_target=unknown
    print_test("rodent_target=unknown")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "unknown",
        "trap_type": "snap_trap"
    })
    # unknown 应该被接受（与 trap-recommendations 不同）
    check_status(200, resp.status_code, "rodent_target=unknown")

    # 测试 17: 所有 trap_type
    trap_types = ["snap_trap", "glue_board", "cage_trap", "electronic_trap", "other"]
    for trap_type in trap_types:
        print_test(f"trap_type={trap_type}")
        resp = api_call("POST", "/bait-recommendations", data={
            "mode": "standard",
            "rodent_target": "rat",
            "trap_type": trap_type
        })
        check_status(200, resp.status_code, f"trap_type={trap_type}")

def test_user_location():
    """测试用户位置参数"""
    print_section("🌍 第五部分: 用户位置测试")

    # 测试 22: 带 user_location
    print_test("带 user_location")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "user_location": {
            "country": "TW",
            "city": "Taipei",
            "environment": "apartment"
        }
    })
    check_status(200, resp.status_code, "带 user_location")

    # 测试 23: 只传 country
    print_test("只传 country")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "user_location": {
            "country": "US"
        }
    })
    check_status(200, resp.status_code, "只传 country")

    # 测试 24: 空 user_location
    print_test("空 user_location")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "user_location": {}
    })
    check_status(200, resp.status_code, "空 user_location")

def test_preferences():
    """测试用户偏好"""
    print_section("⚙️ 第六部分: preferences 组合测试")

    # 测试 25: avoid_perishable=true
    print_test("avoid_perishable=true")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "preferences": {
            "avoid_perishable": True
        }
    })
    if check_status(200, resp.status_code, "avoid_perishable=true"):
        data = resp.json()
        # 检查推荐的诱饵 spoilage_risk 不是 high
        spoilage_risk = data.get('primary_bait', {}).get('spoilage_risk')
        if spoilage_risk != 'high':
            print_success(f"✓ 未推荐高腐败风险诱饵（符合 avoid_perishable）: {spoilage_risk}")

    # 测试 26: has_children_or_pets=true
    print_test("has_children_or_pets=true")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "preferences": {
            "has_children_or_pets": True
        }
    })
    check_status(200, resp.status_code, "has_children_or_pets=true")

    # 测试 27: 组合 preferences
    print_test("组合 preferences")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "mouse",
        "trap_type": "cage_trap",
        "preferences": {
            "avoid_perishable": True,
            "has_children_or_pets": True,
            "easy_to_clean": True
        }
    })
    check_status(200, resp.status_code, "组合 preferences")

    # 测试 28: 空 preferences
    print_test("空 preferences")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "preferences": {}
    })
    check_status(200, resp.status_code, "空 preferences")

def test_from_fridge_mode():
    """测试 from_fridge 模式"""
    print_section("📷 第七部分: from_fridge 模式测试")

    # 获取测试图片的 media_asset_id
    media_id = get_test_media_asset()

    if not media_id:
        print_warning("无法获取测试图片 ID，跳过 from_fridge 模式测试")
        stats.skipped += 3
        return

    # 测试 29: from_fridge 基本请求
    print_test("from_fridge 基本请求")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "from_fridge",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "media_asset_id": media_id
    })
    if check_status(200, resp.status_code, "from_fridge 基本请求"):
        data = resp.json()
        check_field(data, "mode", "from_fridge", "模式")
        check_field_exists(data, "fridge_analysis", "冰箱分析结果")

        # 检查 fridge_analysis 结构
        if data.get("fridge_analysis"):
            check_field_exists(data, "fridge_analysis.media_asset_id", "media_asset_id")
            check_field_exists(data, "fridge_analysis.detected_foods", "detected_foods")

    # 测试 30: from_fridge 带 user_location
    print_test("from_fridge 带 user_location")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "from_fridge",
        "rodent_target": "mouse",
        "trap_type": "cage_trap",
        "media_asset_id": media_id,
        "user_location": {
            "country": "TW",
            "city": "Kaohsiung"
        }
    })
    check_status(200, resp.status_code, "from_fridge 带 user_location")

    # 测试 31: 空字符串 media_asset_id
    print_test("空字符串 media_asset_id")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "from_fridge",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "media_asset_id": ""
    })
    check_status(400, resp.status_code, "空字符串 media_asset_id")

    # 测试 32: 不存在的 media_asset_id
    print_test("不存在的 media_asset_id")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "from_fridge",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "media_asset_id": "ma_nonexistent_12345"
    })
    check_status(404, resp.status_code, "不存在的 media_asset_id")

def test_authentication():
    """测试认证和权限"""
    print_section("🔐 第八部分: 认证和权限测试")

    # 测试 33: 无 Authorization header
    print_test("无 Authorization header（应返回 401）")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    }, use_auth=False)
    check_status(401, resp.status_code, "无 Authorization header")

    # 测试 34: 无效的 Bearer token
    print_test("无效的 Bearer token（应返回 401）")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    }, extra_headers={"Authorization": "Bearer invalid_token_12345"})
    check_status(401, resp.status_code, "无效 token")

def test_edge_cases():
    """测试边界和异常情况"""
    print_section("🔍 第九部分: 边界和异常测试")

    # 测试 35: 完整请求（所有可选参数）
    print_test("完整请求")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "user_location": {
            "country": "TW",
            "city": "Taipei",
            "environment": "apartment"
        },
        "preferences": {
            "avoid_perishable": True,
            "has_children_or_pets": True,
            "easy_to_clean": True,
            "avoid_smelly_bait": True
        },
        "limit": 5
    })
    check_status(200, resp.status_code, "完整请求")

    # 测试 36: null 值字段
    print_test("null 值字段")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "user_location": None,
        "preferences": None
    })
    check_status(200, resp.status_code, "null 值字段")

    # 测试 37: 超大 limit
    print_test("超大 limit (1000)")
    resp = api_call("POST", "/bait-recommendations", data={
        "mode": "standard",
        "rodent_target": "rat",
        "trap_type": "snap_trap",
        "limit": 1000
    })
    # 应该返回 200 或 400，取决于后端实现
    if resp.status_code in [200, 400]:
        print_success(f"✓ 通过: 超大 limit (HTTP {resp.status_code})")
        stats.passed += 1

def print_summary():
    """打印测试统计摘要"""
    print()
    print(f"{Colors.GREEN}{'╔' + '═' * 68 + '╗'}{Colors.NC}")
    print(f"{Colors.GREEN}║{'测试统计':^66}║{Colors.NC}")
    print(f"{Colors.GREEN}{'╠' + '═' * 68 + '╣'}{Colors.NC}")
    print(f"{Colors.GREEN}║{Colors.NC}  总测试数: {Colors.CYAN}{stats.total}{Colors.NC}")
    print(f"{Colors.GREEN}║{Colors.NC}  通过: {Colors.GREEN}{stats.passed}{Colors.NC}")
    print(f"{Colors.GREEN}║{Colors.NC}  失败: {Colors.RED}{stats.failed}{Colors.NC}")

    if stats.skipped > 0:
        print(f"{Colors.GREEN}║{Colors.NC}  跳过: {Colors.YELLOW}{stats.skipped}{Colors.NC}")

    pass_rate = (stats.passed / stats.total * 100) if stats.total > 0 else 0
    print(f"{Colors.GREEN}║{Colors.NC}  通过率: {Colors.CYAN}{pass_rate:.1f}%{Colors.NC}")
    print(f"{Colors.GREEN}{'╚' + '═' * 68 + '╝'}{Colors.NC}")
    print()

    if stats.failed == 0:
        print(f"{Colors.GREEN}{'╔' + '═' * 68 + '╗'}{Colors.NC}")
        print(f"{Colors.GREEN}║{'所有测试通过！':^58}║{Colors.NC}")
        print(f"{Colors.GREEN}{'╚' + '═' * 68 + '╝'}{Colors.NC}")
    else:
        print(f"{Colors.RED}{'╔' + '═' * 68 + '╗'}{Colors.NC}")
        print(f"{Colors.RED}║{f'有 {stats.failed} 个测试失败':^60}║{Colors.NC}")
        print(f"{Colors.RED}{'╚' + '═' * 68 + '╝'}{Colors.NC}")

def main():
    """主函数"""
    global AUTH_TOKEN

    print_header("🧪 RatTrap API - 诱饵推荐接口测试")
    print_info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"环境: Preview (vwinvkxxheuexvpvzibt)")
    print()

    # 登录获取 Token
    AUTH_TOKEN = login()

    try:
        # 执行所有测试
        test_required_fields()
        test_enum_validation()
        test_limit_parameter()
        test_standard_mode()
        test_user_location()
        test_preferences()
        test_from_fridge_mode()
        test_authentication()
        test_edge_cases()

    except KeyboardInterrupt:
        print()
        print_warning("测试被用户中断")
        print_summary()
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        print_summary()
        sys.exit(1)

    # 打印测试摘要
    print_summary()

    # 根据测试结果返回退出码
    sys.exit(0 if stats.failed == 0 else 1)

if __name__ == "__main__":
    main()
