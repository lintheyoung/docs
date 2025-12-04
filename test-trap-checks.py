#!/usr/bin/env python3
"""
RatTrap API - Trap Checks (AI 智能巡检) 接口测试脚本

测试 POST /trap-checks 接口的各种场景：
- 捕获分析 (check_type="catch")
- 空陷阱诊断 (check_type="empty")
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Optional

# ============================================================================
# 配置
# ============================================================================

BASE_URL = "https://vwinvkxxheuexvpvzibt.supabase.co/functions/v1"
AUTH_URL = "https://vwinvkxxheuexvpvzibt.supabase.co/auth/v1/token?grant_type=password"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3aW52a3h4aGV1ZXh2cHZ6aWJ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzOTgwOTcsImV4cCI6MjA3OTk3NDA5N30.QS6bhQMQdgPG2_bU9sYpMGyGPX7JNTJp2cZ8KVutucc"

# 测试账号
EMAIL = "test@example.com"
PASSWORD = "test1234"

# 全局变量
AUTH_TOKEN = None
TEST_TRAP_ID = None

# ANSI 颜色代码
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CYAN = '\033[36m'
    MAGENTA = '\033[35m'
    YELLOW = '\033[33m'

# ============================================================================
# 辅助函数
# ============================================================================

def print_header(text: str):
    """打印测试区块标题"""
    print(f"\n{Colors.MAGENTA}{'─' * 70}{Colors.ENDC}")
    print(f"{Colors.MAGENTA}📋 {text}{Colors.ENDC}")
    print(f"{Colors.MAGENTA}{'─' * 70}{Colors.ENDC}\n")

def print_test(name: str):
    """打印测试用例名称"""
    print(f"{Colors.OKBLUE}[测试 {test_counter[0]}] {name}{Colors.ENDC}")
    test_counter[0] += 1

def print_request(method: str, url: str, data: Optional[Dict] = None):
    """打印请求信息"""
    print(f"{Colors.YELLOW}{'━' * 70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}📤 请求{Colors.ENDC}")
    print(f"{Colors.YELLOW}方法: {Colors.ENDC}{method}")
    print(f"{Colors.YELLOW}URL: {Colors.ENDC}{url}")
    if data:
        print(f"{Colors.YELLOW}Body:{Colors.ENDC}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"{Colors.YELLOW}{'━' * 70}{Colors.ENDC}")

def print_response(status_code: int, data: Any):
    """打印响应信息"""
    print(f"{Colors.CYAN}📥 响应{Colors.ENDC}")
    print(f"{Colors.CYAN}状态码: {Colors.ENDC}{status_code}")
    print(f"{Colors.CYAN}Body:{Colors.ENDC}")
    if isinstance(data, dict):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)
    print(f"{Colors.CYAN}{'━' * 70}{Colors.ENDC}\n")

def check_status(expected: int, actual: int, test_name: str) -> bool:
    """检查 HTTP 状态码"""
    if actual == expected:
        print(f"{Colors.OKGREEN}✓ 通过: {test_name} (HTTP {actual}){Colors.ENDC}\n")
        return True
    else:
        print(f"{Colors.FAIL}✗ 失败: {test_name} - 期望 {expected}, 实际 {actual}{Colors.ENDC}\n")
        return False

def check_field_exists(data: Dict, field_path: str, field_name: str) -> bool:
    """检查字段是否存在（支持嵌套路径）"""
    keys = field_path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            print(f"{Colors.FAIL}  ✗ {field_name}: {field_path} 不存在{Colors.ENDC}")
            return False

    print(f"{Colors.OKGREEN}  ✓ {field_name}: {field_path} 存在{Colors.ENDC}")
    return True

def check_field_type(data: Dict, field: str, expected_type: type, field_name: str) -> bool:
    """检查字段类型"""
    actual_value = data.get(field)
    if isinstance(actual_value, expected_type):
        print(f"{Colors.OKGREEN}  ✓ {field_name}: {field} 类型正确 ({expected_type.__name__}){Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}  ✗ {field_name}: {field} 类型错误, 期望 {expected_type.__name__}, 实际 {type(actual_value).__name__}{Colors.ENDC}")
        return False

def check_url_format(url: str, field_name: str) -> bool:
    """检查 URL 格式"""
    if url and url.startswith("https://") and "supabase.co/storage" in url:
        print(f"{Colors.OKGREEN}  ✓ {field_name}: URL 格式正确{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}  ✗ {field_name}: URL 格式错误 - {url}{Colors.ENDC}")
        return False

# ============================================================================
# API 调用函数
# ============================================================================

def api_call(method: str, endpoint: str, data: Optional[Dict] = None, headers: Optional[Dict] = None) -> requests.Response:
    """统一的 API 调用函数"""
    url = f"{BASE_URL}{endpoint}"
    default_headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    if headers:
        default_headers.update(headers)

    print_request(method, url, data)

    try:
        if method == "POST":
            response = requests.post(url, json=data, headers=default_headers, timeout=120)
        elif method == "GET":
            response = requests.get(url, headers=default_headers, timeout=120)
        else:
            raise ValueError(f"Unsupported method: {method}")

        try:
            response_data = response.json()
        except:
            response_data = response.text

        print_response(response.status_code, response_data)
        return response

    except requests.exceptions.Timeout:
        print(f"{Colors.FAIL}✗ 请求超时（AI 分析可能需要较长时间）{Colors.ENDC}\n")
        return None
    except Exception as e:
        print(f"{Colors.FAIL}✗ 请求失败: {e}{Colors.ENDC}\n")
        return None

def login() -> str:
    """自动登录获取 JWT token"""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.CYAN}🔐 自动登录获取 JWT Token{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}→ 邮箱: {EMAIL}{Colors.ENDC}")
    print(f"{Colors.YELLOW}→ 密码: {PASSWORD}{Colors.ENDC}\n")

    try:
        response = requests.post(
            AUTH_URL,
            json={"email": EMAIL, "password": PASSWORD},
            headers={"Content-Type": "application/json", "apikey": ANON_KEY},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"{Colors.OKGREEN}✓ 登录成功！{Colors.ENDC}")
            print(f"{Colors.YELLOW}→ Token: {token[:50]}...{Colors.ENDC}\n")
            return token
        else:
            print(f"{Colors.FAIL}✗ 登录失败: {response.status_code}{Colors.ENDC}")
            print(response.text)
            sys.exit(1)

    except Exception as e:
        print(f"{Colors.FAIL}✗ 登录异常: {e}{Colors.ENDC}")
        sys.exit(1)

def get_test_media_asset(image_path: str) -> Optional[str]:
    """创建测试用的 media asset 并上传图片"""
    print(f"{Colors.CYAN}📤 准备测试图片: {image_path}...{Colors.ENDC}")

    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        print(f"{Colors.WARNING}⚠ 测试图片不存在: {image_path}{Colors.ENDC}\n")
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
                "purpose": "check",  # trap-checks 使用 check
                "content_type": "image/jpeg",
                "metadata": {
                    "test_source": "trap_checks_test"
                }
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"{Colors.FAIL}✗ 创建媒体资源失败: {response.status_code}{Colors.ENDC}")
            print(response.text)
            return None

        media_data = response.json()
        media_id = media_data.get("id")
        upload_url = media_data.get("upload_url")

        print(f"{Colors.OKGREEN}✓ 创建媒体资源成功: {media_id}{Colors.ENDC}")

        # 步骤2: 上传图片到预签名 URL
        with open(image_path, 'rb') as f:
            upload_response = requests.put(
                upload_url,
                headers={"Content-Type": "image/jpeg"},
                data=f,
                timeout=30
            )

        if upload_response.status_code in (200, 201, 204):
            print(f"{Colors.OKGREEN}✓ 图片上传成功{Colors.ENDC}\n")
            return media_id
        else:
            print(f"{Colors.FAIL}✗ 图片上传失败: {upload_response.status_code}{Colors.ENDC}")
            return None

    except Exception as e:
        print(f"{Colors.FAIL}✗ 准备测试图片失败: {e}{Colors.ENDC}\n")
        return None

def get_or_create_test_trap() -> Optional[str]:
    """获取或创建测试用陷阱"""
    print(f"{Colors.CYAN}📍 获取或创建测试陷阱...{Colors.ENDC}")

    try:
        # 先尝试获取陷阱列表
        response = requests.get(
            f"{BASE_URL}/traps",
            headers={
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            traps = data.get("data", [])
            if len(traps) > 0:
                trap_id = traps[0].get("id")
                print(f"{Colors.OKGREEN}✓ 使用现有陷阱: {trap_id}{Colors.ENDC}\n")
                return trap_id

        # 如果没有陷阱，创建一个（需要先创建 setup session）
        print(f"{Colors.YELLOW}→ 没有现有陷阱，需要先创建...{Colors.ENDC}")
        print(f"{Colors.WARNING}⚠ 请手动在系统中创建至少一个陷阱用于测试{Colors.ENDC}\n")
        return None

    except Exception as e:
        print(f"{Colors.FAIL}✗ 获取陷阱失败: {e}{Colors.ENDC}\n")
        return None

# ============================================================================
# 测试用例
# ============================================================================

# 测试计数器
test_counter = [1]
passed_tests = 0
failed_tests = 0
skipped_tests = 0

def run_tests():
    """运行所有测试"""
    global passed_tests, failed_tests, skipped_tests, AUTH_TOKEN, TEST_TRAP_ID

    # 打印测试信息
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.CYAN}🧪 RatTrap API - AI 智能巡检接口测试{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}→ 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    print(f"{Colors.YELLOW}→ 环境: Preview (lrsppxarhxvxcflougbp){Colors.ENDC}\n")

    # 登录获取 token
    AUTH_TOKEN = login()

    # 获取测试用陷阱
    TEST_TRAP_ID = get_or_create_test_trap()

    # ========================================================================
    # 第一部分: 必填字段验证
    # ========================================================================
    print_header("第一部分: 必填字段验证")

    # 测试 1: 空 body 验证
    print_test("空 body 验证")
    resp = api_call("POST", "/trap-checks", data={})
    if check_status(400, resp.status_code, "空 body 验证"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 2: 缺少 trap_id
    print_test("缺少 trap_id")
    resp = api_call("POST", "/trap-checks", data={
        "media_asset_id": "65190ea0-6ddd-4de3-8eff-1503d59d6f4d",
        "check_type": "catch"
    })
    if check_status(400, resp.status_code, "缺少 trap_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 3: 缺少 media_asset_id
    print_test("缺少 media_asset_id")
    resp = api_call("POST", "/trap-checks", data={
        "trap_id": "3c175d6d-d5af-4070-b73a-c9a5ab8e37e7",
        "check_type": "catch"
    })
    if check_status(400, resp.status_code, "缺少 media_asset_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 4: 缺少 check_type
    print_test("缺少 check_type")
    resp = api_call("POST", "/trap-checks", data={
        "trap_id": "3c175d6d-d5af-4070-b73a-c9a5ab8e37e7",
        "media_asset_id": "65190ea0-6ddd-4de3-8eff-1503d59d6f4d"
    })
    if check_status(400, resp.status_code, "缺少 check_type"):
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第二部分: 枚举值验证
    # ========================================================================
    print_header("第二部分: 枚举值验证")

    # 测试 5: 无效 check_type
    print_test("无效 check_type")
    resp = api_call("POST", "/trap-checks", data={
        "trap_id": "3c175d6d-d5af-4070-b73a-c9a5ab8e37e7",
        "media_asset_id": "65190ea0-6ddd-4de3-8eff-1503d59d6f4d",
        "check_type": "invalid_type"
    })
    if check_status(400, resp.status_code, "无效 check_type"):
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第三部分: ID 验证
    # ========================================================================
    print_header("第三部分: ID 验证")

    # 测试 6: 不存在的 trap_id
    print_test("不存在的 trap_id")
    resp = api_call("POST", "/trap-checks", data={
        "trap_id": "00000000-0000-0000-0000-000000000000",
        "media_asset_id": "65190ea0-6ddd-4de3-8eff-1503d59d6f4d",
        "check_type": "catch"
    })
    if check_status(404, resp.status_code, "不存在的 trap_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 7: 不存在的 media_asset_id
    print_test("不存在的 media_asset_id")
    if TEST_TRAP_ID:
        resp = api_call("POST", "/trap-checks", data={
            "trap_id": TEST_TRAP_ID,
            "media_asset_id": "99999999-9999-9999-9999-999999999999",
            "check_type": "catch"
        })
        if check_status(404, resp.status_code, "不存在的 media_asset_id"):
            passed_tests += 1
        else:
            failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过测试（无测试陷阱）{Colors.ENDC}\n")
        skipped_tests += 1

    # ========================================================================
    # 第四部分: 捕获分析 (check_type="catch")
    # ========================================================================
    print_header("第四部分: 捕获分析 (check_type=\"catch\")")

    if TEST_TRAP_ID:
        # 准备��试图片（假设有捕获老鼠的图片）
        catch_image_path = "rattrap-api/test-assets/catch-rat.jpg"
        media_id_catch = get_test_media_asset(catch_image_path)

        if media_id_catch:
            # 测试 8: 捕获分析成功响应
            print_test("捕获分析成功响应")
            print(f"{Colors.YELLOW}⚠ 注意：AI 分析可能需要 10-20 秒...{Colors.ENDC}")
            resp = api_call("POST", "/trap-checks", data={
                "trap_id": TEST_TRAP_ID,
                "media_asset_id": media_id_catch,
                "check_type": "catch"
            })
            if resp and check_status(200, resp.status_code, "捕获分析成功响应"):
                data = resp.json()
                # 检查响应字段
                check_field_exists(data, "check_type", "check_type")
                check_field_exists(data, "rodent_identification", "rodent_identification")
                check_field_exists(data, "should_blur", "should_blur")
                check_field_exists(data, "safety_guide", "safety_guide")
                check_field_exists(data, "achievement_summary", "achievement_summary")

                # 检查 URL 和 ID（如果需要模糊）
                if data.get("should_blur"):
                    if check_field_exists(data, "blurred_image_url", "blurred_image_url"):
                        check_url_format(data.get("blurred_image_url"), "blurred_image_url")
                    check_field_exists(data, "blurred_media_asset_id", "blurred_media_asset_id")

                passed_tests += 1
            else:
                failed_tests += 1
        else:
            print(f"{Colors.WARNING}⚠ 跳过捕获分析测试（无捕获图片：{catch_image_path}）{Colors.ENDC}\n")
            skipped_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过捕获分析测试（无测试陷阱）{Colors.ENDC}\n")
        skipped_tests += 1

    # ========================================================================
    # 第五部分: 空陷阱诊断 (check_type="empty")
    # ========================================================================
    print_header("第五部分: 空陷阱诊断 (check_type=\"empty\")")

    if TEST_TRAP_ID:
        # 准备测试图片（空陷阱图片）
        empty_image_path = "rattrap-api/test-assets/empty-trap.jpg"
        media_id_empty = get_test_media_asset(empty_image_path)

        if media_id_empty:
            # 测试 9: 空陷阱诊断成功响应
            print_test("空陷阱诊断成功响应")
            print(f"{Colors.YELLOW}⚠ 注意：AI 分析可能需要 5-15 秒...{Colors.ENDC}")
            resp = api_call("POST", "/trap-checks", data={
                "trap_id": TEST_TRAP_ID,
                "media_asset_id": media_id_empty,
                "check_type": "empty"
            })
            if resp and check_status(200, resp.status_code, "空陷阱诊断成功响应"):
                data = resp.json()
                # 检查响应字段
                check_field_exists(data, "check_type", "check_type")
                check_field_exists(data, "diagnosis", "diagnosis")
                check_field_exists(data, "diagnosis.scenario", "scenario")
                check_field_exists(data, "diagnosis.bait_status", "bait_status")
                check_field_exists(data, "diagnosis.trigger_status", "trigger_status")
                check_field_exists(data, "recommendations", "recommendations")
                check_field_exists(data, "recommendations.next_check_hours", "next_check_hours")

                # 检查标注图 URL 和 ID（如果有）
                if data.get("annotated_image_url"):
                    check_url_format(data.get("annotated_image_url"), "annotated_image_url")
                if data.get("annotated_media_asset_id"):
                    check_field_exists(data, "annotated_media_asset_id", "annotated_media_asset_id")

                passed_tests += 1
            else:
                failed_tests += 1
        else:
            print(f"{Colors.WARNING}⚠ 跳过空陷阱诊断测试（无空陷阱图片：{empty_image_path}）{Colors.ENDC}\n")
            skipped_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过空陷阱诊断测试（无测试陷阱）{Colors.ENDC}\n")
        skipped_tests += 1

    # ========================================================================
    # 第六部分: 认证测试
    # ========================================================================
    print_header("第六部分: 认证测试")

    # 测试 10: 无 Authorization header
    print_test("无 Authorization header")
    resp = api_call("POST", "/trap-checks",
                    data={
                        "trap_id": "3c175d6d-d5af-4070-b73a-c9a5ab8e37e7",
                        "media_asset_id": "65190ea0-6ddd-4de3-8eff-1503d59d6f4d",
                        "check_type": "catch"
                    },
                    headers={"Authorization": ""})
    if resp and resp.status_code in (401, 403):
        print(f"{Colors.OKGREEN}✓ 通过: 无 Authorization header (HTTP {resp.status_code}){Colors.ENDC}\n")
        passed_tests += 1
    else:
        print(f"{Colors.FAIL}✗ 失败: 无 Authorization header{Colors.ENDC}\n")
        failed_tests += 1

    # 测试 11: 无效 Bearer token
    print_test("无效 Bearer token")
    resp = api_call("POST", "/trap-checks",
                    data={
                        "trap_id": "3c175d6d-d5af-4070-b73a-c9a5ab8e37e7",
                        "media_asset_id": "65190ea0-6ddd-4de3-8eff-1503d59d6f4d",
                        "check_type": "catch"
                    },
                    headers={"Authorization": "Bearer invalid_token_xyz"})
    if resp and resp.status_code in (401, 403):
        print(f"{Colors.OKGREEN}✓ 通过: 无效 Bearer token (HTTP {resp.status_code}){Colors.ENDC}\n")
        passed_tests += 1
    else:
        print(f"{Colors.FAIL}✗ 失败: 无效 Bearer token{Colors.ENDC}\n")
        failed_tests += 1

    # ========================================================================
    # 测试统计
    # ========================================================================
    total_tests = passed_tests + failed_tests + skipped_tests
    pass_rate = (passed_tests / (passed_tests + failed_tests) * 100) if (passed_tests + failed_tests) > 0 else 0

    print(f"\n{Colors.OKGREEN}{'╔' + '═' * 68 + '╗'}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}║{' ' * 27}测试统计{' ' * 39}║{Colors.ENDC}")
    print(f"{Colors.OKGREEN}╠{'═' * 68}╣{Colors.ENDC}")
    print(f"{Colors.OKGREEN}║{Colors.ENDC}  总测试数: {Colors.CYAN}{total_tests}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}║{Colors.ENDC}  通过: {Colors.OKGREEN}{passed_tests}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}║{Colors.ENDC}  失败: {Colors.FAIL}{failed_tests}{Colors.ENDC}")
    if skipped_tests > 0:
        print(f"{Colors.OKGREEN}║{Colors.ENDC}  跳过: {Colors.WARNING}{skipped_tests}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}║{Colors.ENDC}  通过率: {Colors.CYAN}{pass_rate:.1f}%{Colors.ENDC}")
    print(f"{Colors.OKGREEN}╚{'═' * 68}╝{Colors.ENDC}\n")

    if failed_tests == 0 and skipped_tests == 0:
        print(f"{Colors.OKGREEN}╔{'═' * 68}╗{Colors.ENDC}")
        print(f"{Colors.OKGREEN}║{' ' * 25}所有测试通过！{' ' * 27}║{Colors.ENDC}")
        print(f"{Colors.OKGREEN}╚{'═' * 68}╝{Colors.ENDC}\n")
    elif skipped_tests > 0:
        print(f"{Colors.WARNING}⚠ 部分测试被跳过（原因：缺少测试陷阱或测试图片）{Colors.ENDC}\n")

# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    try:
        run_tests()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠ 测试被用户中断{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.FAIL}✗ 测试执行异常: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
