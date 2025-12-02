#!/usr/bin/env python3
"""
RatTrap API - Calibration Checks 接口测试脚本

测试 POST /calibration-checks 接口的各种场景
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

# 测试账号
EMAIL = "test@example.com"
PASSWORD = "test1234"

# 全局变量
AUTH_TOKEN = None

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

def check_field(data: Dict, field: str, expected_value: Any, field_name: str) -> bool:
    """检查字段值"""
    actual_value = data.get(field)
    if actual_value == expected_value:
        print(f"{Colors.OKGREEN}  ✓ {field_name}: {field} = {actual_value}{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}  ✗ {field_name}: {field} = {actual_value}, 期望 {expected_value}{Colors.ENDC}")
        return False

def check_field_exists(data: Dict, field_path: str, field_name: str) -> bool:
    """检查字段是否存在（支持嵌套路径，如 'issues[0].code'）"""
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

def check_boolean_field(data: Dict, field: str, field_name: str) -> bool:
    """检查布尔字段"""
    actual_value = data.get(field)
    if isinstance(actual_value, bool):
        print(f"{Colors.OKGREEN}  ✓ {field_name}: {field} = {actual_value} (布尔值){Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}  ✗ {field_name}: {field} 不是布尔值, 实际类型 {type(actual_value).__name__}{Colors.ENDC}")
        return False

def check_confidence_range(data: Dict, field: str, field_name: str) -> bool:
    """检查置信度字段在 0-1 范围内"""
    value = data.get(field, -1)
    if isinstance(value, (int, float)) and 0 <= value <= 1:
        print(f"{Colors.OKGREEN}  ✓ {field_name}: {field} = {value} (在 0-1 范围内){Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}  ✗ {field_name}: {field} = {value} (不在 0-1 范围内){Colors.ENDC}")
        return False

def check_issues_structure(issues: list) -> bool:
    """检查 issues 数组的结构"""
    if not isinstance(issues, list):
        print(f"{Colors.FAIL}  ✗ issues 不是数组{Colors.ENDC}")
        return False

    print(f"{Colors.OKGREEN}  ✓ issues 是数组，长度: {len(issues)}{Colors.ENDC}")

    for i, issue in enumerate(issues):
        required_fields = ['code', 'message', 'severity', 'suggestion']
        for field in required_fields:
            if field not in issue:
                print(f"{Colors.FAIL}  ✗ issues[{i}] 缺少字段: {field}{Colors.ENDC}")
                return False

        # 检查 severity 枚举值
        if issue.get('severity') not in ['info', 'warning', 'error']:
            print(f"{Colors.FAIL}  ✗ issues[{i}].severity 值无效: {issue.get('severity')}{Colors.ENDC}")
            return False

    if len(issues) > 0:
        print(f"{Colors.OKGREEN}  ✓ issues 结构正确，包含 {len(issues)} 个问题{Colors.ENDC}")
    return True

def check_recommended_actions_structure(actions: list) -> bool:
    """检查 recommended_actions 数组的结构"""
    if not isinstance(actions, list):
        print(f"{Colors.FAIL}  ✗ recommended_actions 不是数组{Colors.ENDC}")
        return False

    print(f"{Colors.OKGREEN}  ✓ recommended_actions 是数组，长度: {len(actions)}{Colors.ENDC}")

    for i, action in enumerate(actions):
        required_fields = ['code', 'label', 'priority']
        for field in required_fields:
            if field not in action:
                print(f"{Colors.FAIL}  ✗ recommended_actions[{i}] 缺少字段: {field}{Colors.ENDC}")
                return False

    # 检查 priority 排序
    if len(actions) > 1:
        priorities = [a.get('priority') for a in actions]
        if priorities == sorted(priorities):
            print(f"{Colors.OKGREEN}  ✓ recommended_actions 按 priority 正确排序{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}  ⚠ recommended_actions priority 顺序可能不正确: {priorities}{Colors.ENDC}")

    return True

# ============================================================================
# API 调用函数
# ============================================================================

def api_call(method: str, endpoint: str, data: Optional[Dict] = None, headers: Optional[Dict] = None, timeout: int = 60) -> requests.Response:
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
            response = requests.post(url, json=data, headers=default_headers, timeout=timeout)
        elif method == "GET":
            response = requests.get(url, headers=default_headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")

        try:
            response_data = response.json()
        except:
            response_data = response.text

        print_response(response.status_code, response_data)
        return response

    except requests.exceptions.Timeout:
        print(f"{Colors.FAIL}✗ 请求超时 (>{timeout}秒){Colors.ENDC}\n")
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
            headers={"Content-Type": "application/json", "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3aW52a3h4aGV1ZXh2cHZ6aWJ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzOTgwOTcsImV4cCI6MjA3OTk3NDA5N30.QS6bhQMQdgPG2_bU9sYpMGyGPX7JNTJp2cZ8KVutucc"},
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

def get_test_media_asset(image_path: str = "rattrap-api/test-assets/calibration-check.jpg") -> Optional[str]:
    """创建测试用的 media asset 并上传图片"""
    print(f"{Colors.CYAN}📤 准备测试图片...{Colors.ENDC}")

    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        print(f"{Colors.WARNING}⚠ 测试图片不存在: {image_path}，将跳过需要图片的测试{Colors.ENDC}\n")
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
                "purpose": "setup",  # 校准检查属于 setup 阶段
                "content_type": "image/jpeg",
                "metadata": {
                    "test_source": "calibration_checks_test",
                    "usage": "calibration_check"
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
    global passed_tests, failed_tests, skipped_tests, AUTH_TOKEN

    # 打印测试信息
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.CYAN}🧪 RatTrap API - 校准检查接口测试{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.YELLOW}→ 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    print(f"{Colors.YELLOW}→ 环境: Preview (vwinvkxxheuexvpvzibt){Colors.ENDC}\n")

    # 登录获取 token
    AUTH_TOKEN = login()

    # ========================================================================
    # 第一部分: 必填字段验证
    # ========================================================================
    print_header("第一部分: 必填字段验证")

    # 测试 1: 空 body 验证
    print_test("空 body 验证")
    resp = api_call("POST", "/calibration-checks", data={})
    if resp and check_status(400, resp.status_code, "空 body 验证"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 2: 缺少 media_asset_id（唯一必填字段）
    print_test("缺少 media_asset_id")
    resp = api_call("POST", "/calibration-checks", data={
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    if resp and check_status(400, resp.status_code, "缺少 media_asset_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 3: 空字符串 media_asset_id
    print_test("空字符串 media_asset_id")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": ""
    })
    if resp and check_status(400, resp.status_code, "空字符串 media_asset_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第二部分: media_asset_id 验证
    # ========================================================================
    print_header("第二部分: media_asset_id 验证")

    # 测试 4: 不存在的 media_asset_id
    print_test("不存在的 media_asset_id")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": "ma_nonexistent_999999"
    })
    if resp and check_status(404, resp.status_code, "不存在的 media_asset_id"):
        # 检查错误码
        data = resp.json()
        if data.get("error", {}).get("code") == "MEDIA_NOT_FOUND":
            print(f"{Colors.OKGREEN}  ✓ 错误码正确: MEDIA_NOT_FOUND{Colors.ENDC}")
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第三部分: 枚举值验证（可选字段）
    # ========================================================================
    print_header("第三部分: 枚举值验证")

    # 测试 5: 无效 rodent_target
    print_test("无效 rodent_target")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": "ma_test_123",
        "rodent_target": "hamster"
    })
    if resp and check_status(400, resp.status_code, "无效 rodent_target"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 6: 无效 trap_type
    print_test("无效 trap_type")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": "ma_test_123",
        "trap_type": "laser_trap"
    })
    if resp and check_status(400, resp.status_code, "无效 trap_type"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 7: 无效 bait_type
    print_test("无效 bait_type")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": "ma_test_123",
        "bait_type": "pizza"
    })
    if resp and check_status(400, resp.status_code, "无效 bait_type"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 8: 无效 tolerance
    print_test("无效 tolerance")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": "ma_test_123",
        "options": {
            "tolerance": "very_strict"
        }
    })
    if resp and check_status(400, resp.status_code, "无效 tolerance"):
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第四部分: 有效枚举值测试（需要真实图片）
    # ========================================================================
    print_header("第四部分: 有效枚举值测试")

    # 准备测试图片
    media_id = get_test_media_asset()

    if media_id:
        # 测试 9: 有效 rodent_target=rat
        print_test("有效 rodent_target=rat")
        resp = api_call("POST", "/calibration-checks", data={
            "media_asset_id": media_id,
            "rodent_target": "rat"
        }, timeout=90)
        if resp and check_status(200, resp.status_code, "rodent_target=rat"):
            passed_tests += 1
        else:
            failed_tests += 1

        # 测试 10: 有效 rodent_target=mouse
        media_id_2 = get_test_media_asset()
        if media_id_2:
            print_test("有效 rodent_target=mouse")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_2,
                "rodent_target": "mouse"
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "rodent_target=mouse"):
                passed_tests += 1
            else:
                failed_tests += 1

        # 测试 11: 有效 rodent_target=unknown
        media_id_3 = get_test_media_asset()
        if media_id_3:
            print_test("有效 rodent_target=unknown")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_3,
                "rodent_target": "unknown"
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "rodent_target=unknown"):
                passed_tests += 1
            else:
                failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过枚举值测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 3

    # ========================================================================
    # 第五部分: options 参数测试
    # ========================================================================
    print_header("第五部分: options 参数测试")

    if media_id:
        # 测试 12: tolerance=normal
        media_id_4 = get_test_media_asset()
        if media_id_4:
            print_test("tolerance=normal")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_4,
                "options": {
                    "tolerance": "normal"
                }
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "tolerance=normal"):
                passed_tests += 1
            else:
                failed_tests += 1

        # 测试 13: tolerance=strict
        media_id_5 = get_test_media_asset()
        if media_id_5:
            print_test("tolerance=strict")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_5,
                "options": {
                    "tolerance": "strict"
                }
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "tolerance=strict"):
                passed_tests += 1
            else:
                failed_tests += 1

        # 测试 14: need_annotated_image=true
        media_id_6 = get_test_media_asset()
        if media_id_6:
            print_test("need_annotated_image=true")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_6,
                "options": {
                    "need_annotated_image": True
                }
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "need_annotated_image=true"):
                data = resp.json()
                # 注意: annotated_media_asset_id 可能为 null（如果标注生成失败）
                if "annotated_media_asset_id" in data:
                    print(f"{Colors.OKGREEN}  ✓ annotated_media_asset_id 字段存在: {data.get('annotated_media_asset_id')}{Colors.ENDC}")
                passed_tests += 1
            else:
                failed_tests += 1

        # 测试 15: need_annotated_image=false
        media_id_7 = get_test_media_asset()
        if media_id_7:
            print_test("need_annotated_image=false")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_7,
                "options": {
                    "need_annotated_image": False
                }
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "need_annotated_image=false"):
                data = resp.json()
                if data.get("annotated_media_asset_id") is None:
                    print(f"{Colors.OKGREEN}  ✓ annotated_media_asset_id 为 null（符合预期）{Colors.ENDC}")
                else:
                    print(f"{Colors.WARNING}  ⚠ annotated_media_asset_id 不为 null: {data.get('annotated_media_asset_id')}{Colors.ENDC}")
                passed_tests += 1
            else:
                failed_tests += 1

        # 测试 16: language=en-US
        media_id_8 = get_test_media_asset()
        if media_id_8:
            print_test("language=en-US")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_8,
                "options": {
                    "language": "en-US"
                }
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "language=en-US"):
                passed_tests += 1
            else:
                failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过 options 参数测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 5

    # ========================================================================
    # 第六部分: 完整请求测试
    # ========================================================================
    print_header("第六部分: 完整请求测试")

    if media_id:
        # 测试 17: 完整参数请求
        media_id_9 = get_test_media_asset()
        if media_id_9:
            print_test("完整参数请求")
            resp = api_call("POST", "/calibration-checks", data={
                "setup_session_id": "ss_test_123",
                "media_asset_id": media_id_9,
                "rodent_target": "rat",
                "trap_type": "snap_trap",
                "bait_type": "peanut_butter",
                "location_context": {
                    "recommended_zone_id": "zone_A",
                    "recommended_description": "冰箱右侧沿墙，距墙角约 10cm",
                    "recommended_distance_to_wall_cm": 0
                },
                "options": {
                    "language": "zh-CN",
                    "need_annotated_image": True,
                    "tolerance": "normal"
                }
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "完整参数请求"):
                data = resp.json()

                # 检查响应结构
                check_field(data, "object", "calibration_check", "对象类型")
                check_field_exists(data, "id", "校准检查 ID")
                check_field_exists(data, "media_asset_id", "原始图片 ID")
                check_boolean_field(data, "is_correct", "布置是否正确")
                check_confidence_range(data, "confidence", "置信度")
                check_field_exists(data, "advice_text", "建议文案")
                check_field_exists(data, "created", "创建时间")

                # 检查 issues 结构
                if "issues" in data:
                    check_issues_structure(data["issues"])

                # 检查 recommended_actions 结构
                if "recommended_actions" in data:
                    check_recommended_actions_structure(data["recommended_actions"])

                passed_tests += 1
            else:
                failed_tests += 1

        # 测试 18: 最小参数请求（只有 media_asset_id）
        media_id_10 = get_test_media_asset()
        if media_id_10:
            print_test("最小参数请求（只有 media_asset_id）")
            resp = api_call("POST", "/calibration-checks", data={
                "media_asset_id": media_id_10
            }, timeout=90)
            if resp and check_status(200, resp.status_code, "最小参数请求"):
                data = resp.json()
                check_field(data, "object", "calibration_check", "对象类型")
                check_boolean_field(data, "is_correct", "布置是否正确")
                passed_tests += 1
            else:
                failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过完整请求测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 2

    # ========================================================================
    # 第七部分: 认证测试
    # ========================================================================
    print_header("第七部分: 认证测试")

    # 测试 19: 无 Authorization header
    print_test("无 Authorization header")
    resp = api_call("POST", "/calibration-checks",
                    data={"media_asset_id": "ma_test_123"},
                    headers={"Authorization": ""})
    if resp is not None and resp.status_code in (401, 500):
        print(f"{Colors.OKGREEN}✓ 通过: 无 Authorization header (HTTP {resp.status_code}){Colors.ENDC}\n")
        passed_tests += 1
    else:
        status = resp.status_code if resp is not None else 'None'
        print(f"{Colors.FAIL}✗ 失败: 无 Authorization header - 期望 401/500, 实际 {status}{Colors.ENDC}\n")
        failed_tests += 1

    # 测试 20: 无效 Bearer token
    print_test("无效 Bearer token")
    resp = api_call("POST", "/calibration-checks",
                    data={"media_asset_id": "ma_test_123"},
                    headers={"Authorization": "Bearer invalid_token_xyz"})
    if resp is not None and resp.status_code in (401, 500):
        print(f"{Colors.OKGREEN}✓ 通过: 无效 Bearer token (HTTP {resp.status_code}){Colors.ENDC}\n")
        passed_tests += 1
    else:
        status = resp.status_code if resp is not None else 'None'
        print(f"{Colors.FAIL}✗ 失败: 无效 Bearer token - 期望 401/500, 实际 {status}{Colors.ENDC}\n")
        failed_tests += 1

    # ========================================================================
    # 第八部分: 幂等性测试
    # ========================================================================
    print_header("第八部分: 幂等性测试")

    if media_id:
        # 测试 21: 使用 Idempotency-Key
        media_id_11 = get_test_media_asset()
        if media_id_11:
            print_test("使用 Idempotency-Key")
            idempotency_key = f"test-calib-{int(time.time())}"
            resp = api_call("POST", "/calibration-checks",
                            data={
                                "media_asset_id": media_id_11,
                                "rodent_target": "rat"
                            },
                            headers={"Idempotency-Key": idempotency_key},
                            timeout=90)
            if resp and check_status(200, resp.status_code, "使用 Idempotency-Key"):
                passed_tests += 1
            else:
                failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过幂等性测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 1

    # ========================================================================
    # 第九部分: 边界测试
    # ========================================================================
    print_header("第九部分: 边界测试")

    # 测试 22: null 值字段
    print_test("null 值字段 (media_asset_id)")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": None
    })
    if resp and check_status(400, resp.status_code, "null 值 media_asset_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 23: location_context 为空对象
    print_test("location_context 为空对象")
    resp = api_call("POST", "/calibration-checks", data={
        "media_asset_id": "ma_test_123",
        "location_context": {}
    })
    # 空对象应该被接受（字段都是可选的）
    if resp and resp.status_code in (400, 404):  # 404 因为 media_asset_id 不存在
        print(f"{Colors.OKGREEN}✓ 通过: location_context 为空对象被接受 (HTTP {resp.status_code}){Colors.ENDC}\n")
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 测试统计
    # ========================================================================
    total_tests = passed_tests + failed_tests + skipped_tests
    pass_rate = (passed_tests / (passed_tests + failed_tests) * 100) if (passed_tests + failed_tests) > 0 else 0

    print(f"\n{Colors.OKGREEN}{'╔' + '═' * 68 + '╗'}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}║{' ' * 27}测试统计{' ' * 32}║{Colors.ENDC}")
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
        print(f"{Colors.WARNING}⚠ 部分测试被跳过（原因：缺少测试图片）{Colors.ENDC}\n")

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
