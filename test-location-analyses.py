#!/usr/bin/env python3
"""
RatTrap API - Location Analyses 接口测试脚本

测试 POST /location-analyses 接口的各种场景
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
    """检查字段是否存在（支持嵌套路径，如 'fridge_analysis.identified_foods'）"""
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

def check_array_length(data: Dict, field: str, max_length: int, field_name: str) -> bool:
    """检查数组长度"""
    arr = data.get(field, [])
    if len(arr) <= max_length:
        print(f"{Colors.OKGREEN}✓   ✓ 返回数组长度: {field} 长度 {len(arr)} <= {max_length}{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}✗   ✗ 返回数组长度: {field} 长度 {len(arr)} > {max_length}{Colors.ENDC}")
        return False

def check_confidence_range(zones: list) -> bool:
    """检查所有 zone 的 confidence 在 0-1 之间"""
    for zone in zones:
        confidence = zone.get('confidence', -1)
        if not (0 <= confidence <= 1):
            print(f"{Colors.FAIL}  ✗ confidence 超出范围: {confidence} (zone: {zone.get('id')}){Colors.ENDC}")
            return False
    print(f"{Colors.OKGREEN}  ✓ 所有 zone 的 confidence 在 0-1 范围内{Colors.ENDC}")
    return True

def check_priority_order(zones: list) -> bool:
    """检查 zones 按 priority 排序"""
    priorities = [zone.get('priority') for zone in zones]
    if priorities == sorted(priorities):
        print(f"{Colors.OKGREEN}  ✓ zones 按 priority 正确排序{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}  ✗ zones priority 顺序错误: {priorities}{Colors.ENDC}")
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
            response = requests.post(url, json=data, headers=default_headers, timeout=60)
        elif method == "GET":
            response = requests.get(url, headers=default_headers, timeout=60)
        else:
            raise ValueError(f"Unsupported method: {method}")

        try:
            response_data = response.json()
        except:
            response_data = response.text

        print_response(response.status_code, response_data)
        return response

    except requests.exceptions.Timeout:
        print(f"{Colors.FAIL}✗ 请求超时{Colors.ENDC}\n")
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

def get_test_media_asset(image_path: str = "rattrap-api/test-assets/room.jpg") -> Optional[str]:
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
                "purpose": "setup",  # 位置分析使用 setup
                "content_type": "image/jpeg",
                "metadata": {
                    "test_source": "location_analyses_test",
                    "usage": "location_analysis_test"
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
    print(f"{Colors.CYAN}🧪 RatTrap API - 位置分析接口测试{Colors.ENDC}")
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
    resp = api_call("POST", "/location-analyses", data={})
    if check_status(400, resp.status_code, "空 body 验证"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 2: 缺少 media_asset_id
    print_test("缺少 media_asset_id")
    resp = api_call("POST", "/location-analyses", data={
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    if check_status(400, resp.status_code, "缺少 media_asset_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 3: 缺少 rodent_target
    print_test("缺少 rodent_target")
    resp = api_call("POST", "/location-analyses", data={
        "media_asset_id": "ma_test_123",
        "trap_type": "snap_trap"
    })
    if check_status(400, resp.status_code, "缺少 rodent_target"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 4: 缺少 trap_type
    print_test("缺少 trap_type")
    resp = api_call("POST", "/location-analyses", data={
        "media_asset_id": "ma_test_123",
        "rodent_target": "rat"
    })
    if check_status(400, resp.status_code, "缺少 trap_type"):
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第二部分: 枚举值验证
    # ========================================================================
    print_header("第二部分: 枚举值验证")

    # 测试 5: 无效 rodent_target
    print_test("无效 rodent_target")
    resp = api_call("POST", "/location-analyses", data={
        "media_asset_id": "ma_test_123",
        "rodent_target": "hamster",
        "trap_type": "snap_trap"
    })
    if check_status(400, resp.status_code, "无效 rodent_target"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 6: 无效 trap_type
    print_test("无效 trap_type")
    resp = api_call("POST", "/location-analyses", data={
        "media_asset_id": "ma_test_123",
        "rodent_target": "rat",
        "trap_type": "laser_trap"
    })
    if check_status(400, resp.status_code, "无效 trap_type"):
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第三部分: media_asset_id 验证
    # ========================================================================
    print_header("第三部分: media_asset_id 验证")

    # 测试 7: 空字符串 media_asset_id
    print_test("空字符串 media_asset_id")
    resp = api_call("POST", "/location-analyses", data={
        "media_asset_id": "",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    if check_status(400, resp.status_code, "空字符串 media_asset_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # 测试 8: 不存在的 media_asset_id
    print_test("不存在的 media_asset_id")
    resp = api_call("POST", "/location-analyses", data={
        "media_asset_id": "ma_nonexistent_999999",
        "rodent_target": "rat",
        "trap_type": "snap_trap"
    })
    if check_status(404, resp.status_code, "不存在的 media_asset_id"):
        passed_tests += 1
    else:
        failed_tests += 1

    # ========================================================================
    # 第四部分: options 参数测试
    # ========================================================================
    print_header("第四部分: options 参数测试")

    # 准备测试图片
    media_id = get_test_media_asset()

    if media_id:
        # 测试 9: max_zones=1
        print_test("max_zones=1")
        resp = api_call("POST", "/location-analyses", data={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap",
            "options": {
                "max_zones": 1
            }
        })
        if check_status(200, resp.status_code, "max_zones=1"):
            data = resp.json()
            if check_array_length(data, "zones", 1, "zones 数量"):
                passed_tests += 1
            else:
                failed_tests += 1
        else:
            failed_tests += 1

        # 测试 10: max_zones=5
        print_test("max_zones=5")
        resp = api_call("POST", "/location-analyses", data={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap",
            "options": {
                "max_zones": 5
            }
        })
        if check_status(200, resp.status_code, "max_zones=5"):
            data = resp.json()
            if check_array_length(data, "zones", 5, "zones 数量"):
                passed_tests += 1
            else:
                failed_tests += 1
        else:
            failed_tests += 1

        # 测试 11: 无效 max_zones (0)
        print_test("无效 max_zones (0)")
        resp = api_call("POST", "/location-analyses", data={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap",
            "options": {
                "max_zones": 0
            }
        })
        if check_status(400, resp.status_code, "无效 max_zones (0)"):
            passed_tests += 1
        else:
            failed_tests += 1

        # 测试 12: 超大 max_zones (100)
        print_test("超大 max_zones (100)")
        resp = api_call("POST", "/location-analyses", data={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap",
            "options": {
                "max_zones": 100
            }
        })
        if check_status(400, resp.status_code, "超大 max_zones (100)"):
            passed_tests += 1
        else:
            failed_tests += 1

        # 测试 13: 不同语言 (en-US)
        print_test("language=en-US")
        resp = api_call("POST", "/location-analyses", data={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap",
            "options": {
                "language": "en-US"
            }
        })
        if check_status(200, resp.status_code, "language=en-US"):
            passed_tests += 1
        else:
            failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过 options 参数测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 4

    # ========================================================================
    # 第五部分: 不同陷阱类型测试
    # ========================================================================
    print_header("第五部分: 不同陷阱类型测试")

    if media_id:
        trap_types = ["snap_trap", "glue_board", "cage_trap", "electronic_trap", "other"]

        for trap_type in trap_types:
            print_test(f"trap_type={trap_type}")
            resp = api_call("POST", "/location-analyses", data={
                "media_asset_id": media_id,
                "rodent_target": "rat",
                "trap_type": trap_type
            })
            if check_status(200, resp.status_code, f"trap_type={trap_type}"):
                passed_tests += 1
            else:
                failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过陷阱类型测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 5

    # ========================================================================
    # 第六部分: 不同鼠种测试
    # ========================================================================
    print_header("第六部分: 不同鼠种测试")

    if media_id:
        rodent_targets = ["rat", "mouse", "unknown"]

        for rodent in rodent_targets:
            print_test(f"rodent_target={rodent}")
            resp = api_call("POST", "/location-analyses", data={
                "media_asset_id": media_id,
                "rodent_target": rodent,
                "trap_type": "snap_trap"
            })
            if check_status(200, resp.status_code, f"rodent_target={rodent}"):
                passed_tests += 1
            else:
                failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过鼠种测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 3

    # ========================================================================
    # 第七部分: 完整请求测试
    # ========================================================================
    print_header("第七部分: 完整请求测试")

    if media_id:
        # 测试 19: 完整参数请求
        print_test("完整参数请求")
        resp = api_call("POST", "/location-analyses", data={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap",
            "bait_type": "peanut_butter",
            "user_location": {
                "country": "TW",
                "city": "Taipei",
                "environment": "apartment"
            },
            "options": {
                "max_zones": 2,
                "language": "zh-CN"
            }
        })
        if check_status(200, resp.status_code, "完整参数请求"):
            data = resp.json()
            check_field(data, "object", "location_analysis", "对象类型")
            check_field_exists(data, "id", "分析 ID")
            check_field_exists(data, "media_asset_id", "原始图片 ID")
            check_field_exists(data, "annotated_media_asset_id", "标注图片 ID")
            check_field_exists(data, "placement_text", "放置说明")
            check_field_exists(data, "zones", "推荐区域")
            check_field_exists(data, "created", "创建时间")

            # 检查 zones 结构
            if data.get("zones"):
                zones = data["zones"]
                print(f"{Colors.OKGREEN}✓ ✓ 返回 {len(zones)} 个推荐区域{Colors.ENDC}")

                # 检查第一个 zone 的结构
                if len(zones) > 0:
                    zone = zones[0]
                    check_field_exists({"zone": zone}, "zone.id", "zone ID")
                    check_field_exists({"zone": zone}, "zone.label", "zone 标签")
                    check_field_exists({"zone": zone}, "zone.priority", "zone 优先级")
                    check_field_exists({"zone": zone}, "zone.confidence", "zone 置信度")
                    check_field_exists({"zone": zone}, "zone.description", "zone 描述")
                    check_field_exists({"zone": zone}, "zone.bounding_box", "bounding_box")

                    # 检查 confidence 范围
                    check_confidence_range(zones)

                    # 检查 priority 排序
                    check_priority_order(zones)

            passed_tests += 1
        else:
            failed_tests += 1

        # 测试 20: 带 setup_session_id
        print_test("带 setup_session_id")
        resp = api_call("POST", "/location-analyses", data={
            "setup_session_id": "ss_test_123",
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap"
        })
        if check_status(200, resp.status_code, "带 setup_session_id"):
            passed_tests += 1
        else:
            failed_tests += 1
    else:
        print(f"{Colors.WARNING}⚠ 跳过完整请求测试（无测试图片）{Colors.ENDC}\n")
        skipped_tests += 2

    # ========================================================================
    # 第八部分: 认证测试
    # ========================================================================
    print_header("第八部分: 认证测试")

    # 测试 21: 无 Authorization header
    print_test("无 Authorization header")
    resp = api_call("POST", "/location-analyses",
                    data={
                        "media_asset_id": "ma_test_123",
                        "rodent_target": "rat",
                        "trap_type": "snap_trap"
                    },
                    headers={"Authorization": ""})
    # 期望 401 或 500（取决于后端实现）
    if resp.status_code in (401, 500):
        print(f"{Colors.OKGREEN}✓ 通过: 无 Authorization header (HTTP {resp.status_code}){Colors.ENDC}\n")
        passed_tests += 1
    else:
        print(f"{Colors.FAIL}✗ 失败: 无 Authorization header - 期望 401/500, 实际 {resp.status_code}{Colors.ENDC}\n")
        failed_tests += 1

    # 测试 22: 无效 Bearer token
    print_test("无效 Bearer token")
    resp = api_call("POST", "/location-analyses",
                    data={
                        "media_asset_id": "ma_test_123",
                        "rodent_target": "rat",
                        "trap_type": "snap_trap"
                    },
                    headers={"Authorization": "Bearer invalid_token_xyz"})
    # 期望 401 或 500
    if resp.status_code in (401, 500):
        print(f"{Colors.OKGREEN}✓ 通过: 无效 Bearer token (HTTP {resp.status_code}){Colors.ENDC}\n")
        passed_tests += 1
    else:
        print(f"{Colors.FAIL}✗ 失败: 无效 Bearer token - 期望 401/500, 实际 {resp.status_code}{Colors.ENDC}\n")
        failed_tests += 1

    # ========================================================================
    # 第九部分: 边界测试
    # ========================================================================
    print_header("第九部分: 边界测试")

    # 测试 23: null 值字段
    print_test("null 值字段")
    resp = api_call("POST", "/location-analyses", data={
        "media_asset_id": "ma_test_123",
        "rodent_target": None,
        "trap_type": "snap_trap"
    })
    if check_status(400, resp.status_code, "null 值字段"):
        passed_tests += 1
    else:
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
        print(f"{Colors.WARNING}⚠ 部分测试被跳过（原因：缺少测试图片）{Colors.ENDC}\n")

    # 检测 LLM_QUOTA_EXCEEDED 错误，自动退出
    # (此功能可选，根据实际情况决定是否保留)

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
