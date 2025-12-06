#!/usr/bin/env python3
"""测试 location-analyses 和 location-annotations 接口"""

import os
# 清除代理
for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(k, None)

import requests
import json
import uuid

# 配置
BASE_URL = "https://vwinvkxxheuexvpvzibt.supabase.co/functions/v1"
AUTH_URL = "https://vwinvkxxheuexvpvzibt.supabase.co/auth/v1"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3aW52a3h4aGV1ZXh2cHZ6aWJ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzOTgwOTcsImV4cCI6MjA3OTk3NDA5N30.QS6bhQMQdgPG2_bU9sYpMGyGPX7JNTJp2cZ8KVutucc"
TEST_IMAGE = "rattrap-api/test-assets/room.jpg"
OUTPUT_DIR = "/tmp"

# 创建无代理的 session
session = requests.Session()
session.trust_env = False  # 禁用从环境变量读取代理

def login():
    """自动登录获取 JWT"""
    email = "test@example.com"
    password = "test1234"

    resp = session.post(
        f"{AUTH_URL}/token?grant_type=password",
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password}
    )
    if resp.status_code != 200:
        print(f"❌ 登录失败: {resp.status_code} {resp.text}")
        return None
    token = resp.json().get("access_token")
    print(f"✅ 登录成功: {email}")
    return token

def upload_image(token, image_path):
    """上传图片并返回 media_asset_id"""
    # 1. 创建 media asset
    resp = session.post(
        f"{BASE_URL}/media-assets",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"purpose": "setup", "content_type": "image/jpeg", "metadata": {}}
    )
    if resp.status_code != 200:
        print(f"❌ 创建 media asset 失败: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    media_id = data["id"]
    upload_url = data["upload_url"]
    print(f"✅ 创建 media asset: {media_id}")

    # 2. 上传图片
    with open(image_path, "rb") as f:
        resp = session.put(upload_url, headers={"Content-Type": "image/jpeg"}, data=f)
    if resp.status_code not in [200, 201]:
        print(f"❌ 上传图片失败: {resp.status_code}")
        return None
    print(f"✅ 图片上传成功")
    return media_id

def test_location_analyses(token, media_id):
    """测试 location-analyses 接口"""
    print("\n" + "="*50)
    print("测试 location-analyses (文字建议接口)")
    print("="*50)

    # 正常请求
    print("\n[1] 正常请求 - 所有必填字段")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"loc-analysis-{uuid.uuid4()}"
        },
        json={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap"
        },
        timeout=60
    )
    print(f"状态码: {resp.status_code}")
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    if resp.status_code == 200:
        print(f"✅ 成功 - 返回 {len(data.get('recommendations', []))} 条建议")

    # 边界测试: 缺少 media_asset_id
    print("\n[2] 边界测试 - 缺少 media_asset_id")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"rodent_target": "rat", "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 缺少 rodent_target
    print("\n[3] 边界测试 - 缺少 rodent_target")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": media_id, "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 缺少 trap_type
    print("\n[4] 边界测试 - 缺少 trap_type")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": media_id, "rodent_target": "rat"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 无效的 media_asset_id
    print("\n[5] 边界测试 - 无效的 media_asset_id")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": "invalid_id", "rodent_target": "rat", "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 无效的 rodent_target
    print("\n[6] 边界测试 - 无效的 rodent_target")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": media_id, "rodent_target": "invalid", "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 无效的 trap_type
    print("\n[7] 边界测试 - 无效的 trap_type")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": media_id, "rodent_target": "rat", "trap_type": "invalid"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 无 Authorization
    print("\n[8] 边界测试 - 无 Authorization header")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Content-Type": "application/json"},
        json={"media_asset_id": media_id, "rodent_target": "rat", "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}")

    # 测试所有 rodent_target 枚举值
    print("\n[9] 枚举测试 - rodent_target: mouse")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Idempotency-Key": f"loc-{uuid.uuid4()}"},
        json={"media_asset_id": media_id, "rodent_target": "mouse", "trap_type": "snap_trap"},
        timeout=60
    )
    print(f"状态码: {resp.status_code}")

    print("\n[10] 枚举测试 - rodent_target: unknown")
    resp = session.post(
        f"{BASE_URL}/location-analyses",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Idempotency-Key": f"loc-{uuid.uuid4()}"},
        json={"media_asset_id": media_id, "rodent_target": "unknown", "trap_type": "glue_board"},
        timeout=60
    )
    print(f"状态码: {resp.status_code}")

def test_location_annotations(token, media_id):
    """测试 location-annotations 接口"""
    print("\n" + "="*50)
    print("测试 location-annotations (标注图接口)")
    print("="*50)

    # 正常请求
    print("\n[1] 正常请求 - 所有必填字段")
    resp = session.post(
        f"{BASE_URL}/location-annotations",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"loc-annot-{uuid.uuid4()}"
        },
        json={
            "media_asset_id": media_id,
            "rodent_target": "rat",
            "trap_type": "snap_trap"
        },
        timeout=90
    )
    print(f"状态码: {resp.status_code}")
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if resp.status_code == 200 and data.get("annotated_image_url"):
        url = data["annotated_image_url"]
        print(f"✅ 成功 - 标注了 {data.get('annotation_count', '?')} 个位置")
        # 下载标注图片
        img_resp = session.get(url)
        if img_resp.status_code == 200:
            output_path = f"{OUTPUT_DIR}/annotated_location.jpg"
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
            print(f"✅ 标注图片已保存到: {output_path}")

    # 边界测试: 缺少 media_asset_id
    print("\n[2] 边界测试 - 缺少 media_asset_id")
    resp = session.post(
        f"{BASE_URL}/location-annotations",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"rodent_target": "rat", "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 缺少 rodent_target
    print("\n[3] 边界测试 - 缺少 rodent_target")
    resp = session.post(
        f"{BASE_URL}/location-annotations",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": media_id, "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 缺少 trap_type
    print("\n[4] 边界测试 - 缺少 trap_type")
    resp = session.post(
        f"{BASE_URL}/location-annotations",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": media_id, "rodent_target": "rat"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 无效的 media_asset_id
    print("\n[5] 边界测试 - 无效的 media_asset_id")
    resp = session.post(
        f"{BASE_URL}/location-annotations",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"media_asset_id": "invalid_id", "rodent_target": "rat", "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}, 错误码: {resp.json().get('error', {}).get('code')}")

    # 边界测试: 无 Authorization
    print("\n[6] 边界测试 - 无 Authorization header")
    resp = session.post(
        f"{BASE_URL}/location-annotations",
        headers={"Content-Type": "application/json"},
        json={"media_asset_id": media_id, "rodent_target": "rat", "trap_type": "snap_trap"}
    )
    print(f"状态码: {resp.status_code}")

    # 测试可选字段
    print("\n[7] 测试可选字段 - bait_type, user_location, options")
    resp = session.post(
        f"{BASE_URL}/location-annotations",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"loc-annot-{uuid.uuid4()}"
        },
        json={
            "media_asset_id": media_id,
            "rodent_target": "mouse",
            "trap_type": "glue_board",
            "bait_type": "peanut_butter",
            "user_location": {"country": "TW", "city": "Taipei", "environment": "apartment"},
            "options": {"language": "zh-CN"}
        },
        timeout=90
    )
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        if data.get("annotated_image_url"):
            img_resp = session.get(data["annotated_image_url"])
            if img_resp.status_code == 200:
                output_path = f"{OUTPUT_DIR}/annotated_location_mouse.jpg"
                with open(output_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"✅ 标注图片已保存到: {output_path}")

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("="*50)
    print("位置分析接口测试")
    print("="*50)

    # 登录
    token = login()
    if not token:
        return

    # 上传测试图片
    media_id = upload_image(token, TEST_IMAGE)
    if not media_id:
        return

    # 测试两个接口
    test_location_analyses(token, media_id)
    test_location_annotations(token, media_id)

    print("\n" + "="*50)
    print("测试完成")
    print("="*50)

if __name__ == "__main__":
    main()
