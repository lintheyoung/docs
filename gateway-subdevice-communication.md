# 子设备与网关设备通信架构

本文档描述 PestGG IoT 系统中子设备与网关设备的通信机制，以及如何通过 MQTT Topic 与用户 App 和 Supabase 后端进行数据交互。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              云端 (AWS + Supabase)                           │
│                                                                              │
│   ┌─────────────┐  登录/获取凭证   ┌─────────────┐                          │
│   │  Supabase   │◄────────────────│  User App   │                          │
│   │  (后端数据库) │   (仅登录时)     │  (Flutter)  │                          │
│   └──────▲──────┘                 └──────┬──────┘                          │
│          │                               │                                  │
│          │ IoT Rule                      │ MQTT over WebSocket (443)        │
│          │ (数据持久化)                   │ (实时通信)                        │
│          │                               │                                  │
│   ┌──────┴───────────────────────────────▼──────────────────────────────┐  │
│   │                      AWS IoT Core (MQTT Broker)                      │  │
│   │                                                                       │  │
│   │  Shadow Topics:                                                       │  │
│   │  • $aws/things/{thingName}/shadow/update (网关 Classic Shadow)       │  │
│   │  • $aws/things/{thingName}/shadow/name/{shadowName}/update           │  │
│   │    (子设备 Named Shadow)                                              │  │
│   │                                                                       │  │
│   │  Lifecycle Events (设备在线状态检测):                                  │  │
│   │  • $aws/events/presence/connected/{clientId}                          │  │
│   │  • $aws/events/presence/disconnected/{clientId}                       │  │
│   └───────────────────────────────▲───────────────────────────────────────┘  │
└───────────────────────────────────│─────────────────────────────────────────┘
                                    │ MQTT over TLS (8883)
                                    │ X.509 证书认证
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                              网关设备 (Gateway)                              │
│                                                                              │
│   • 拥有 AWS IoT 证书 (.cert.pem, .private.key)                             │
│   • 拥有网络连接 (WiFi/4G)                                                   │
│   • Thing Name: IoT-Gateway-XXXXXX                                           │
│   • 负责转发子设备数据和命令                                                  │
│   • Keep Alive: 30秒 (超时阈值: 45秒)                                        │
│                                                                              │
└───────────────────────────────────▲─────────────────────────────────────────┘
                                    │ 本地通信 (BLE/Zigbee/LoRa)
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                              子设备 (Sub-device)                             │
│                                                                              │
│   • 无 AWS 证书，无网络连接                                                  │
│   • 通过本地通信连接网关                                                      │
│   • Shadow Name: vibration-sensor-001, trap-device-002 等                   │
│   • 设备类型: 捕鼠器、振动传感器、温湿度传感器等                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 通信模式

### 设计原则

为降低通信成本，采用以下策略：

1. **App 仅在登录时与 Supabase 通信** - 获取用户信息和 AWS IoT 临时凭证
2. **实时数据通过 AWS IoT WebSocket 传输** - App 直连 AWS IoT Core，无需经过 Supabase
3. **数据持久化由 IoT Rule 异步处理** - Lambda 将数据写入 Supabase，不影响实时通信

### App 连接流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User App  │     │  Supabase   │     │ AWS Cognito │     │ AWS IoT Core│
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │  1. 登录请求       │                   │                   │
       │──────────────────►│                   │                   │
       │                   │                   │                   │
       │  2. 返回 JWT +     │                   │                   │
       │     设备列表       │                   │                   │
       │◄──────────────────│                   │                   │
       │                   │                   │                   │
       │  3. 获取 AWS 临时凭证                  │                   │
       │──────────────────────────────────────►│                   │
       │                   │                   │                   │
       │  4. 返回 AccessKey/SecretKey/Token    │                   │
       │◄──────────────────────────────────────│                   │
       │                   │                   │                   │
       │  5. WebSocket 连接 (MQTT over WSS)                        │
       │──────────────────────────────────────────────────────────►│
       │                   │                   │                   │
       │  6. 订阅设备 Shadow Topics                                │
       │──────────────────────────────────────────────────────────►│
       │                   │                   │                   │
       │  7. 实时接收设备数据 / 发送命令                            │
       │◄─────────────────────────────────────────────────────────►│
       │                   │                   │                   │
```

### 通信成本对比

| 通信方式 | 原方案 | 优化后 |
|---------|-------|--------|
| App ↔ Supabase | 每次操作都调用 | 仅登录时调用 |
| App ↔ AWS IoT | 无 | WebSocket 长连接 |
| 实时数据延迟 | 1-3秒 (经 Supabase) | < 100ms (直连) |
| 命令下发 | App → Supabase → Lambda → IoT | App → IoT (直接) |

## 通信链路

### 数据上报流程 (子设备 → App)

**实时路径** (低延迟):
```
子设备 → BLE → 网关 → MQTT → AWS IoT Core → WebSocket → User App
```

**持久化路径** (异步):
```
AWS IoT Core → IoT Rule → Lambda → Supabase
```

1. 子设备通过本地通信（BLE/Zigbee）将遥测数据发送给网关
2. 网关更新子设备的 Named Shadow reported 状态
3. AWS IoT Core 同时：
   - 通过 WebSocket 推送给已订阅的 App（实时）
   - 触发 IoT Rule，由 Lambda 写入 Supabase（持久化）

### 命令下发流程 (App → 子设备)

**优化后** (直连):
```
User App → WebSocket → AWS IoT Core → MQTT → 网关 → BLE → 子设备
```

1. App 直接通过 WebSocket 更新子设备的 Named Shadow desired 状态
2. AWS IoT Core 发布 Delta 消息到网关订阅的主题
3. 网关接收 Delta，通过本地通信转发给子设备
4. 子设备执行命令后，网关更新 Shadow reported 状态（ACK）
5. App 通过 WebSocket 实时收到 ACK

## App 接入 AWS IoT

### 获取临时凭证

App 登录后，调用 Supabase Edge Function 获取 AWS IoT 临时凭证：

```typescript
// Supabase Edge Function: get-aws-credentials
export async function handler(req: Request) {
  const user = await getAuthUser(req);

  // 使用 AWS STS AssumeRole 获取临时凭证
  const credentials = await sts.assumeRole({
    RoleArn: 'arn:aws:iam::123456789012:role/IoTAppRole',
    RoleSessionName: `user-${user.id}`,
    DurationSeconds: 3600  // 1小时有效期
  });

  return {
    accessKeyId: credentials.AccessKeyId,
    secretAccessKey: credentials.SecretAccessKey,
    sessionToken: credentials.SessionToken,
    expiration: credentials.Expiration,
    iotEndpoint: 'xxx.iot.ap-southeast-1.amazonaws.com'
  };
}
```

### App WebSocket 连接

```dart
// Flutter App 连接 AWS IoT
import 'package:aws_iot_device_sdk/aws_iot_device_sdk.dart';

class IoTService {
  late AWSIoTDevice _device;

  Future<void> connect(AWSCredentials credentials) async {
    _device = AWSIoTDevice(
      endpoint: 'xxx.iot.ap-southeast-1.amazonaws.com',
      clientId: 'app-user-${userId}',
      credentials: credentials,
      protocol: MqttProtocol.wss,  // WebSocket Secure
    );

    await _device.connect();

    // 订阅用户所有设备的 Shadow
    for (final device in userDevices) {
      await _subscribeToDevice(device);
    }
  }

  Future<void> _subscribeToDevice(Device device) async {
    // 订阅 Shadow 更新
    final topic = '\$aws/things/${device.thingName}/shadow/name/${device.shadowName}/update/documents';
    await _device.subscribe(topic, (message) {
      // 处理设备状态更新
      onDeviceUpdate(device.id, message);
    });
  }

  Future<void> sendCommand(Device device, Map<String, dynamic> command) async {
    // 直接更新 Shadow desired 状态
    final topic = '\$aws/things/${device.thingName}/shadow/name/${device.shadowName}/update';
    final payload = {
      'state': {
        'desired': {
          ...command,
          '_reqId': generateReqId(),
        }
      }
    };
    await _device.publish(topic, jsonEncode(payload));
  }
}
```

### IAM 策略配置

App 用户的 IAM 角色需要限制只能访问自己的设备：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect"],
      "Resource": "arn:aws:iot:*:*:client/app-user-${cognito-identity.amazonaws.com:sub}"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe"],
      "Resource": [
        "arn:aws:iot:*:*:topicfilter/$aws/things/*/shadow/name/*/update/documents"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Receive"],
      "Resource": [
        "arn:aws:iot:*:*:topic/$aws/things/*/shadow/name/*/update/documents"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish"],
      "Resource": [
        "arn:aws:iot:*:*:topic/$aws/things/*/shadow/name/*/update"
      ]
    }
  ]
}
```

## MQTT Topic 设计

### Shadow Topic 前缀

| Shadow 类型 | Topic 前缀 |
|------------|-----------|
| Classic Shadow (网关) | `$aws/things/{thingName}/shadow` |
| Named Shadow (子设备) | `$aws/things/{thingName}/shadow/name/{shadowName}` |

### 1. 设备端必须订阅的 Topics

设备连接后，**必须先订阅响应主题，再发布请求**，否则无法收到响应。

#### 网关 Classic Shadow

| 主题 | 用途 | 必须 |
|-----|------|-----|
| `{prefix}/update/accepted` | 更新成功响应 | ✅ |
| `{prefix}/update/rejected` | 更新失败响应 | ✅ |
| `{prefix}/update/delta` | 接收云端命令（desired 变化） | ✅ |
| `{prefix}/update/documents` | Shadow 完整文档变更通知 | 可选 |
| `{prefix}/get/accepted` | 获取 Shadow 成功响应 | ✅ |
| `{prefix}/get/rejected` | 获取 Shadow 失败响应 | ✅ |
| `{prefix}/delete/accepted` | 删除 Shadow 成功响应 | 可选 |
| `{prefix}/delete/rejected` | 删除 Shadow 失败响应 | 可选 |

#### 子设备 Named Shadow

网关需要为每个子设备订阅相同的主题模式：

| 主题 | 用途 | 必须 |
|-----|------|-----|
| `{prefix}/update/accepted` | 更新成功响应 | ✅ |
| `{prefix}/update/rejected` | 更新失败响应 | ✅ |
| `{prefix}/update/delta` | 接收云端命令 | ✅ |
| `{prefix}/update/documents` | Shadow 完整文档变更通知 | 可选 |
| `{prefix}/get/accepted` | 获取 Shadow 成功响应 | ✅ |
| `{prefix}/get/rejected` | 获取 Shadow 失败响应 | ✅ |

### 2. 设备端发布的 Topics

| 主题 | 用途 | 触发时机 |
|-----|------|---------|
| `{prefix}/update` | 上报设备状态 | 状态变化时 |
| `{prefix}/get` | 获取当前 Shadow | 设备启动/重连时 |
| `{prefix}/delete` | 删除 Shadow | 设备解绑时 |

### 3. App 端订阅的 Topics

App 通过 WebSocket 订阅设备状态变更：

| 主题 | 用途 |
|-----|------|
| `{prefix}/update/documents` | 接收设备状态完整更新 |
| `{prefix}/update/accepted` | 确认命令已被接收 |

### 4. App 端发布的 Topics

| 主题 | 用途 |
|-----|------|
| `{prefix}/update` | 发送命令（更新 desired 状态） |
| `{prefix}/get` | 获取设备当前状态 |

### 5. 生命周期事件 Topics

AWS IoT Core 自动发布设备连接/断开事件：

| 事件类型 | Topic |
|---------|-------|
| 设备连接 | `$aws/events/presence/connected/{clientId}` |
| 设备断开 | `$aws/events/presence/disconnected/{clientId}` |

### 6. Topic 完整示例

以网关 `IoT-Gateway-000011` 和子设备 `vibration-sensor-001` 为例：

**网关 Classic Shadow Topics**:
```
# 发布
$aws/things/IoT-Gateway-000011/shadow/update
$aws/things/IoT-Gateway-000011/shadow/get

# 订阅
$aws/things/IoT-Gateway-000011/shadow/update/accepted
$aws/things/IoT-Gateway-000011/shadow/update/rejected
$aws/things/IoT-Gateway-000011/shadow/update/delta
$aws/things/IoT-Gateway-000011/shadow/get/accepted
$aws/things/IoT-Gateway-000011/shadow/get/rejected
```

**子设备 Named Shadow Topics**:
```
# 发布 (网关代理)
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/update
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/get

# 订阅 (网关代理)
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/update/accepted
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/update/rejected
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/update/delta
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/get/accepted
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/get/rejected

# App 订阅
$aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/update/documents
```

---

## Shadow Topic 详细使用说明

以下详细说明每个 Shadow Topic 的使用场景、消息格式和代码示例。

### /update - 更新 Shadow 状态

**Topic**: `{ShadowTopicPrefix}/update`

**用途**: 设备上报状态 或 App/云端下发命令

**使用场景**:
1. 设备启动后上报初始状态
2. 设备状态变化时上报最新状态
3. App 发送命令给设备（更新 desired）
4. 设备执行命令后确认（更新 reported + lastAckedReqId）

**消息格式**:

设备上报状态（reported）:
```json
{
  "state": {
    "reported": {
      "connected": true,
      "battery": 95,
      "vibration_level": 2.3,
      "threshold": 5.0,
      "timestamp": 1702900060
    }
  }
}
```

App 下发命令（desired）:
```json
{
  "state": {
    "desired": {
      "action": "set_threshold",
      "threshold": 3.0,
      "_reqId": "cmd_1702900100_abc123"
    }
  }
}
```

设备确认命令（ACK）:
```json
{
  "state": {
    "reported": {
      "threshold": 3.0,
      "lastAckedReqId": "cmd_1702900100_abc123"
    },
    "desired": null
  }
}
```

**代码示例**:
```python
# 设备上报状态
def report_state(mqtt_client, thing_name, shadow_name, state):
    topic = f"$aws/things/{thing_name}/shadow/name/{shadow_name}/update"
    payload = {"state": {"reported": state}}
    mqtt_client.publish(topic, json.dumps(payload), qos=1)
```

---

### /update/accepted - 更新成功响应

**Topic**: `{ShadowTopicPrefix}/update/accepted`

**用途**: 确认 Shadow 更新成功

**使用场景**:
1. 设备上报状态后，确认云端已接收
2. App 发送命令后，确认 Shadow 已更新
3. 用于实现可靠的消息确认机制

**消息格式**:
```json
{
  "state": {
    "reported": {
      "battery": 95,
      "threshold": 3.0
    }
  },
  "metadata": {
    "reported": {
      "battery": {"timestamp": 1702900060},
      "threshold": {"timestamp": 1702900060}
    }
  },
  "version": 42,
  "timestamp": 1702900060
}
```

**代码示例**:
```python
# 订阅更新成功响应
def on_update_accepted(topic, payload):
    data = json.loads(payload)
    version = data.get('version')
    print(f"Shadow 更新成功，版本: {version}")

mqtt_client.subscribe(
    f"$aws/things/{thing_name}/shadow/name/{shadow_name}/update/accepted",
    callback=on_update_accepted
)
```

---

### /update/rejected - 更新失败响应

**Topic**: `{ShadowTopicPrefix}/update/rejected`

**用途**: 通知 Shadow 更新失败及原因

**使用场景**:
1. 消息格式错误
2. 版本冲突（并发更新）
3. Shadow 大小超限（8KB）
4. 权限不足

**消息格式**:
```json
{
  "code": 409,
  "message": "Version conflict",
  "timestamp": 1702900060,
  "clientToken": "token123"
}
```

**错误码说明**:

| code | 说明 |
|------|------|
| 400 | 请求格式错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | Shadow 不存在 |
| 409 | 版本冲突 |
| 413 | 请求体过大 |
| 500 | 服务器内部错误 |

**代码示例**:
```python
def on_update_rejected(topic, payload):
    error = json.loads(payload)
    print(f"Shadow 更新失败: {error['code']} - {error['message']}")

    if error['code'] == 409:
        # 版本冲突，重新获取最新状态后重试
        get_shadow()
```

---

### /update/delta - 接收云端命令

**Topic**: `{ShadowTopicPrefix}/update/delta`

**用途**: 通知设备 desired 和 reported 状态不一致，需要执行操作

**使用场景**:
1. App 发送命令后，设备接收待执行的操作
2. 设备重连后，获取离线期间的待处理命令
3. 实现命令下发和状态同步

**Delta 生成规则**:
- 仅包含 `desired` 和 `reported` 之间**不同**的属性
- 不包含两者**相同**的属性
- 不包含仅在 `reported` 中存在的属性
- 包含仅在 `desired` 中存在的属性

**消息格式**:
```json
{
  "version": 43,
  "timestamp": 1702900100,
  "state": {
    "action": "set_threshold",
    "threshold": 3.0,
    "_reqId": "cmd_1702900100_abc123"
  },
  "metadata": {
    "action": {"timestamp": 1702900100},
    "threshold": {"timestamp": 1702900100},
    "_reqId": {"timestamp": 1702900100}
  }
}
```

**代码示例**:
```python
def on_delta_received(topic, payload):
    delta = json.loads(payload)
    state = delta.get('state', {})
    req_id = state.get('_reqId')

    # 执行命令
    if state.get('action') == 'set_threshold':
        new_threshold = state.get('threshold')
        device.set_threshold(new_threshold)

        # 发送 ACK，清除 desired
        ack_payload = {
            "state": {
                "reported": {
                    "threshold": new_threshold,
                    "lastAckedReqId": req_id
                },
                "desired": {
                    "action": None,
                    "threshold": None,
                    "_reqId": None
                }
            }
        }
        mqtt_client.publish(update_topic, json.dumps(ack_payload))

# 订阅 delta（必须）
mqtt_client.subscribe(
    f"$aws/things/{thing_name}/shadow/name/{shadow_name}/update/delta",
    callback=on_delta_received
)
```

---

### /update/documents - Shadow 完整文档变更

**Topic**: `{ShadowTopicPrefix}/update/documents`

**用途**: 每次 Shadow 更新成功后，发布完整的 Shadow 文档

**使用场景**:
1. App 监听设备状态变化（推荐 App 订阅此主题）
2. 获取完整的 previous 和 current 状态对比
3. 实现状态变更日志记录

**消息格式**:
```json
{
  "previous": {
    "state": {
      "desired": {"threshold": 5.0},
      "reported": {"threshold": 5.0, "battery": 95}
    },
    "metadata": {...},
    "version": 42
  },
  "current": {
    "state": {
      "desired": {"threshold": 3.0},
      "reported": {"threshold": 5.0, "battery": 95}
    },
    "metadata": {...},
    "version": 43
  },
  "timestamp": 1702900100
}
```

**代码示例（App 端）**:
```dart
// Flutter App 订阅设备状态变更
void subscribeToDevice(String thingName, String shadowName) {
  final topic = '\$aws/things/$thingName/shadow/name/$shadowName/update/documents';

  mqttClient.subscribe(topic, (message) {
    final doc = jsonDecode(message);
    final currentState = doc['current']['state']['reported'];

    // 更新 UI
    setState(() {
      deviceBattery = currentState['battery'];
      deviceThreshold = currentState['threshold'];
      isConnected = currentState['connected'];
    });
  });
}
```

---

### /get - 获取当前 Shadow

**Topic**: `{ShadowTopicPrefix}/get`

**用途**: 请求获取当前完整的 Shadow 文档

**使用场景**:
1. 设备启动/重连后，获取最新状态和待处理命令
2. App 打开设备详情页时，获取当前状态
3. 状态同步和离线补偿

**消息格式**: 发布空消息或空 JSON `{}`

**代码示例**:
```python
# 设备启动时获取 Shadow
def on_connect():
    # 先订阅响应主题
    mqtt_client.subscribe(f"{shadow_prefix}/get/accepted", on_get_accepted)
    mqtt_client.subscribe(f"{shadow_prefix}/get/rejected", on_get_rejected)

    # 再发布 get 请求
    mqtt_client.publish(f"{shadow_prefix}/get", "{}")

def on_get_accepted(topic, payload):
    shadow = json.loads(payload)
    desired = shadow.get('state', {}).get('desired', {})
    reported = shadow.get('state', {}).get('reported', {})

    # 检查是否有待处理命令
    req_id = desired.get('_reqId')
    last_acked = reported.get('lastAckedReqId')

    if req_id and req_id != last_acked:
        # 有未处理的命令，执行它
        execute_command(desired)
```

---

### /get/accepted - 获取成功响应

**Topic**: `{ShadowTopicPrefix}/get/accepted`

**用途**: 返回完整的 Shadow 文档

**消息格式**:
```json
{
  "state": {
    "desired": {
      "threshold": 3.0,
      "_reqId": "cmd_1702900100_abc123"
    },
    "reported": {
      "threshold": 5.0,
      "battery": 95,
      "connected": true,
      "lastAckedReqId": "cmd_1702900000_xyz789"
    },
    "delta": {
      "threshold": 3.0,
      "_reqId": "cmd_1702900100_abc123"
    }
  },
  "metadata": {...},
  "version": 43,
  "timestamp": 1702900100
}
```

**注意**: 响应中包含 `delta` 字段，表示 desired 和 reported 的差异。

---

### /get/rejected - 获取失败响应

**Topic**: `{ShadowTopicPrefix}/get/rejected`

**用途**: 通知获取 Shadow 失败

**消息格式**:
```json
{
  "code": 404,
  "message": "No shadow exists with name: 'vibration-sensor-001'",
  "timestamp": 1702900100
}
```

**处理建议**:
- 404: Shadow 不存在，设备首次上报时会自动创建
- 401/403: 检查 IAM 权限配置

---

### /delete - 删除 Shadow

**Topic**: `{ShadowTopicPrefix}/delete`

**用途**: 删除设备的 Shadow

**使用场景**:
1. 设备解绑时清理 Shadow
2. 重置设备状态
3. 子设备从网关移除时

**消息格式**: 发布空消息或空 JSON `{}`

**注意**: 删除 Shadow 不会重置版本号为 0，下次创建时版本号继续递增。

**代码示例**:
```python
def unbind_subdevice(shadow_name):
    # 删除子设备 Shadow
    delete_topic = f"$aws/things/{thing_name}/shadow/name/{shadow_name}/delete"
    mqtt_client.publish(delete_topic, "{}")
```

---

### /delete/accepted - 删除成功响应

**Topic**: `{ShadowTopicPrefix}/delete/accepted`

**消息格式**:
```json
{
  "version": 43,
  "timestamp": 1702900100
}
```

---

### /delete/rejected - 删除失败响应

**Topic**: `{ShadowTopicPrefix}/delete/rejected`

**消息格式**:
```json
{
  "code": 404,
  "message": "No shadow exists with name: 'vibration-sensor-001'",
  "timestamp": 1702900100
}
```

## 设备在线状态检测

### 基于 AWS IoT Keep Alive 机制

使用 AWS IoT 内置的 Keep Alive 机制检测设备在线状态，无需自定义心跳协议。

**工作原理**：
- 设备连接时设置 Keep Alive 时间（如 30 秒）
- AWS IoT Core 在 **1.5 倍 Keep Alive 时间**（45 秒）内没有收到任何通信时，判定设备离线
- 设备离线时自动发布生命周期事件

### 监听生命周期事件

创建 IoT Rule 监听生命周期事件，更新数据库：

```sql
-- IoT Rule SQL
SELECT
  clientId,
  thingName,
  timestamp,
  eventType,
  disconnectReason,
  versionNumber
FROM '$aws/events/presence/+/{clientId}'
```

**连接事件消息**：
```json
{
  "clientId": "IoT-Gateway-000011",
  "thingName": "IoT-Gateway-000011",
  "timestamp": 1573002230757,
  "eventType": "connected",
  "sessionIdentifier": "00000000-0000-0000-0000-000000000000",
  "versionNumber": 0
}
```

**断开事件消息**：
```json
{
  "clientId": "IoT-Gateway-000011",
  "thingName": "IoT-Gateway-000011",
  "timestamp": 1573002340451,
  "eventType": "disconnected",
  "disconnectReason": "MQTT_KEEP_ALIVE_TIMEOUT",
  "clientInitiatedDisconnect": false,
  "versionNumber": 1
}
```

**断开原因说明**：

| disconnectReason | 说明 | 发送 LWT |
|-----------------|------|---------|
| `MQTT_KEEP_ALIVE_TIMEOUT` | Keep Alive 超时 | 是 |
| `CLIENT_INITIATED_DISCONNECT` | 客户端主动断开 | 否 |
| `CONNECTION_LOST` | 连接丢失 | 是 |
| `DUPLICATE_CLIENTID` | 客户端 ID 重复 | 是 |

## 子设备在线状态检测

子设备没有直接连接 AWS IoT，因此：
- **无法使用 MQTT LWT 机制**：子设备没有自己的 MQTT 连接，无法设置 Last Will and Testament
- **由网关维护在线状态**：子设备的 `connected` 属性表示与网关的本地连接状态（BLE/Zigbee）
- **网关负责更新 Shadow**：当子设备本地连接建立或断开时，网关更新其 Named Shadow

```json
// $aws/things/IoT-Gateway-000011/shadow/name/vibration-sensor-001/update
{
  "state": {
    "reported": {
      "connected": true,
      "battery": 78,
      "lastSeen": 1704355200
    }
  }
}
```

**处理网关异常断开**：

当网关异常断开时，其下所有子设备都应标记为离线。可以通过以下方式实现：

1. 网关的 MQTT LWT 触发生命周期事件
2. IoT Rule 监听网关断开事件
3. Lambda 函数批量更新该网关下所有子设备的 `connected` 状态为 `false`

## 消息格式

### 遥测数据 (Shadow Update)

```json
{
  "state": {
    "reported": {
      "deviceId": "09aa8ad8-f23e-4e75-bcbe-332efeb431ce",
      "gatewayId": "435204e6-21c9-447d-ab6f-888c99b91926",
      "connected": true,
      "battery": 95,
      "vibration_detected": false,
      "vibration_level": 2.3,
      "timestamp": 1702900060
    }
  }
}
```

### 命令下发 (App 直接发送)

```json
{
  "state": {
    "desired": {
      "action": "set_threshold",
      "vibration_threshold": 3.0,
      "_reqId": "cmd_1702900100_abc123"
    }
  }
}
```

### 命令确认 (ACK)

```json
{
  "state": {
    "reported": {
      "lastAckedReqId": "cmd_1702900100_abc123",
      "vibration_threshold": 3.0,
      "timestamp": 1702900105
    }
  }
}
```

## Keep Alive 配置

| 参数 | 值 | 说明 |
|-----|-----|------|
| Keep Alive | 30 秒 | MQTT 连接时设置 |
| 超时阈值 | 45 秒 | AWS IoT 自动计算 (1.5 × Keep Alive) |
| 离线判定 | 45 秒无通信 | 自动发布断开事件 |

## 设备标识说明

| 字段 | 网关 | 子设备 |
|------|------|--------|
| `thing_name` | AWS IoT Thing 名称 | 绑定后继承网关的 thing_name |
| `shadow_name` | 无（使用 Classic Shadow） | 唯一标识，绑定时生成 |
| `device_id` | Supabase UUID | Supabase UUID |
| AWS 证书 | 有 | 无 |

---

## 固件版本兼容性设计

当设备固件升级/降级时，Shadow 中的字段可能与设备当前固件版本不兼容。本章节描述如何通过**能力表**和**映射表**解决这个问题。

### 核心问题

同一硬件（如 A1）的不同固件版本，支持的功能不同：

| 固件版本 | 支持的功能 |
|---------|-----------|
| 1.0 | 红灯 |
| 1.1 | 红灯 + 绿灯 |
| 1.2 | 红灯 + 绿灯 + 蓝灯 |

如果 App 对 1.0 设备发送"绿灯亮"命令，设备无法理解，会导致失败或异常。

### 解决方案：5 张配置表

云端维护以下配置表，供网关和 App 查询使用。

---

### 表 1：设备能力表 (Device Capability)

> **设备每个版本能做什么**（供 App 画界面 + 网关判断支持）

```json
// Supabase: device_capabilities 表
{
  "hw_variant": "A1",
  "fw_version": "1.0",
  "capabilities": {
    "led_colors": ["red"],
    "buzzer": true,
    "threshold_range": [1, 10]
  }
}
```

| hw_variant | fw_version | led_colors | buzzer | threshold_range |
|------------|------------|------------|--------|-----------------|
| A1 | 1.0 | red | ✅ | 1-10 |
| A1 | 1.1 | red, green | ✅ | 1-20 |
| A1 | 1.2 | red, green, blue | ✅ | 1-100 |

**用途**：
- App 根据此表决定显示哪些控件
- 网关根据此表判断命令是否支持

---

### 表 2：App 版本能力表 (App Capability)

> **App 版本自己会什么**（决定 App 能画出哪些控件）

| app_version | supported_led_colors | has_buzzer_control | has_schedule |
|-------------|---------------------|-------------------|--------------|
| 1.0 | red | ✅ | ❌ |
| 2.0 | red, green, blue | ✅ | ✅ |

**用途**：
- App 启动时读取自身能力
- 与设备能力取交集，决定最终显示

---

### 表 3：界面显示规则

> **显示 = 设备能力 ∩ App 能力**

| 设备版本 | 设备支持 | App v2 支持 | App v2 实际显示 |
|---------|---------|-------------|----------------|
| 1.0 | red | red, green, blue | red |
| 1.1 | red, green | red, green, blue | red, green |
| 1.2 | red, green, blue | red, green, blue | red, green, blue |

**规则**：两边都有的功能才显示，避免显示不能用的按钮。

---

### 表 4：网关下发映射表 (Command Mapping)

> **同一个命令，不同版本的设备需要不同的下发格式**

```json
// Supabase: command_mappings 表
{
  "hw_variant": "A1",
  "fw_version": "1.1",
  "command": "SetLed",
  "params": {"color": "green", "on": true},
  "downlink_format": {"led": {"g": 1}}
}
```

| hw_variant | fw_version | 统一命令 (SetLed green on) | 设备能听懂的下发格式 |
|------------|------------|---------------------------|---------------------|
| A1 | 1.0 | green on | ❌ 不支持，不下发 |
| A1 | 1.1 | green on | `{"led":{"g":1}}` |
| A1 | 1.2 | green on | `{"led":{"color":"green","on":true}}` |

**用途**：
- 网关收到统一命令后，查此表翻译成设备能理解的格式
- 支持固件升级后字段名变化（如 `g` → `color`）

---

### 表 5：原因码表 (Reason Code)

> **失败/拒绝时的标准提示**

| reason_code | message_zh | message_en |
|-------------|-----------|------------|
| OK | 已执行 | Executed |
| NEED_UPGRADE | 当前设备版本不支持该功能，请升级固件 | Feature not supported, please upgrade firmware |
| PARAM_NOT_ALLOWED | 参数不支持 | Parameter not allowed |
| DEVICE_OFFLINE | 设备离线 | Device offline |
| TIMEOUT | 命令超时 | Command timeout |

---

### 完整流程示例

**场景**：App v2 对三台设备发送"绿灯亮"命令

| 设备 | 固件版本 |
|-----|---------|
| 设备1 | 1.0 |
| 设备2 | 1.1 |
| 设备3 | 1.2 |

#### Step 1: App 显示界面（查表1 + 表2 取交集）

| 设备 | 固件版本 | 设备支持 | App v2 支持 | 显示的按钮 |
|-----|---------|---------|-------------|-----------|
| 设备1 | 1.0 | red | red, green, blue | 红灯 |
| 设备2 | 1.1 | red, green | red, green, blue | 红灯, 绿灯 |
| 设备3 | 1.2 | red, green, blue | red, green, blue | 红灯, 绿灯, 蓝灯 |

> 设备1 界面上根本没有绿灯按钮，用户点不到。

#### Step 2: App 发送统一命令

```json
// App 发送（统一格式，不管设备版本）
{
  "state": {
    "desired": {
      "action": "SetLed",
      "color": "green",
      "on": true,
      "_reqId": "cmd_123"
    }
  }
}
```

#### Step 3: 网关判断支持（查表1）

| 设备 | 固件版本 | 支持 green？ | 网关决定 |
|-----|---------|-------------|---------|
| 设备1 | 1.0 | ❌ | 拒绝，返回 NEED_UPGRADE |
| 设备2 | 1.1 | ✅ | 继续处理 |
| 设备3 | 1.2 | ✅ | 继续处理 |

#### Step 4: 网关翻译下发（查表4）

| 设备 | 固件版本 | 翻译后下发 |
|-----|---------|-----------|
| 设备2 | 1.1 | `{"led":{"g":1}}` |
| 设备3 | 1.2 | `{"led":{"color":"green","on":true}}` |

#### Step 5: 返回结果给 App

```json
{
  "results": [
    {
      "device_id": "device-1-uuid",
      "success": false,
      "reason_code": "NEED_UPGRADE",
      "message": "当前设备版本不支持该功能，请升级固件"
    },
    {
      "device_id": "device-2-uuid",
      "success": true,
      "reason_code": "OK",
      "message": "已执行"
    },
    {
      "device_id": "device-3-uuid",
      "success": true,
      "reason_code": "OK",
      "message": "已执行"
    }
  ]
}
```

---

### 数据库 Schema

```sql
-- 设备能力表
CREATE TABLE device_capabilities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  hw_variant TEXT NOT NULL,           -- 硬件型号
  fw_version TEXT NOT NULL,           -- 固件版本
  capabilities JSONB NOT NULL,        -- 能力列表
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(hw_variant, fw_version)
);

-- 命令映射表
CREATE TABLE command_mappings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  hw_variant TEXT NOT NULL,
  fw_version TEXT NOT NULL,
  command TEXT NOT NULL,              -- 统一命令名
  params JSONB,                       -- 命令参数
  downlink_format JSONB NOT NULL,     -- 设备能理解的格式
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 原因码表
CREATE TABLE reason_codes (
  code TEXT PRIMARY KEY,
  message_zh TEXT NOT NULL,
  message_en TEXT NOT NULL
);

-- 示例数据
INSERT INTO device_capabilities (hw_variant, fw_version, capabilities) VALUES
('A1', '1.0', '{"led_colors": ["red"], "buzzer": true}'),
('A1', '1.1', '{"led_colors": ["red", "green"], "buzzer": true}'),
('A1', '1.2', '{"led_colors": ["red", "green", "blue"], "buzzer": true}');

INSERT INTO command_mappings (hw_variant, fw_version, command, params, downlink_format) VALUES
('A1', '1.1', 'SetLed', '{"color": "green", "on": true}', '{"led": {"g": 1}}'),
('A1', '1.2', 'SetLed', '{"color": "green", "on": true}', '{"led": {"color": "green", "on": true}}');

INSERT INTO reason_codes (code, message_zh, message_en) VALUES
('OK', '已执行', 'Executed'),
('NEED_UPGRADE', '当前设备版本不支持该功能，请升级固件', 'Feature not supported, please upgrade firmware'),
('PARAM_NOT_ALLOWED', '参数不支持', 'Parameter not allowed');
```

---

### 网关处理逻辑

```python
class CommandProcessor:
    def process_command(self, device, command, params):
        """处理统一命令"""
        hw_variant = device.hw_variant
        fw_version = device.fw_version

        # Step 1: 查能力表，判断是否支持
        capabilities = self.get_capabilities(hw_variant, fw_version)
        if not self.is_supported(capabilities, command, params):
            return {
                "success": False,
                "reason_code": "NEED_UPGRADE",
                "message": "当前设备版本不支持该功能，请升级固件"
            }

        # Step 2: 查映射表，翻译成设备能理解的格式
        downlink = self.get_downlink_format(hw_variant, fw_version, command, params)
        if not downlink:
            return {
                "success": False,
                "reason_code": "PARAM_NOT_ALLOWED",
                "message": "参数不支持"
            }

        # Step 3: 下发到设备
        self.send_to_device(device, downlink)

        return {
            "success": True,
            "reason_code": "OK",
            "message": "已执行"
        }

    def is_supported(self, capabilities, command, params):
        """检查能力是否支持"""
        if command == "SetLed":
            color = params.get("color")
            return color in capabilities.get("led_colors", [])
        return True

    def get_downlink_format(self, hw_variant, fw_version, command, params):
        """获取下发格式"""
        mapping = db.query(
            "SELECT downlink_format FROM command_mappings "
            "WHERE hw_variant = %s AND fw_version = %s AND command = %s AND params = %s",
            (hw_variant, fw_version, command, json.dumps(params))
        )
        return mapping.downlink_format if mapping else None
```

---

### App 端处理逻辑

```dart
class DeviceController {
  /// 获取设备能力（进入设备页面时调用）
  Future<DeviceCapabilities> getCapabilities(String deviceId) async {
    final device = await getDevice(deviceId);
    return await api.getCapabilities(device.hwVariant, device.fwVersion);
  }

  /// 计算可显示的功能（设备能力 ∩ App 能力）
  List<String> getDisplayableFeatures(DeviceCapabilities deviceCaps) {
    final appCaps = AppCapabilities.current; // App 自身能力

    // 取交集
    return deviceCaps.ledColors
        .where((color) => appCaps.supportedLedColors.contains(color))
        .toList();
  }

  /// 发送命令前检查
  Future<void> sendCommand(String deviceId, String command, Map params) async {
    final caps = await getCapabilities(deviceId);

    // 本地预检查（可选，网关会再检查一次）
    if (command == 'SetLed') {
      final color = params['color'];
      if (!caps.ledColors.contains(color)) {
        showError('该设备不支持此功能，请升级固件');
        return;
      }
    }

    // 发送统一命令
    final result = await api.sendCommand(deviceId, command, params);

    if (!result.success) {
      showError(result.message);
    }
  }
}
```

---

### 总结：分工职责

| 角色 | 职责 |
|-----|------|
| **云端/Supabase** | 维护能力表、映射表、原因码表 |
| **网关** | 查能力表判断支持 → 查映射表翻译下发 → 返回结果 |
| **App** | 查能力表画界面 → 发统一命令 → 显示结果 |
| **设备** | 只需理解自己版本的格式，无需关心兼容性 |

**核心原则**：
1. App 只说"我要什么"（统一命令），不说"你怎么做"
2. 网关负责翻译和兜底
3. 设备只需处理自己能理解的格式

## 参考文档

- [AWS IoT Device Shadow 通信](https://docs.aws.amazon.com/zh_cn/iot/latest/developerguide/device-shadow-comms-app.html)
- [AWS IoT 生命周期事件](https://docs.aws.amazon.com/zh_cn/iot/latest/developerguide/life-cycle-events.html)
- [AWS IoT WebSocket 连接](https://docs.aws.amazon.com/iot/latest/developerguide/protocols.html)
- [获取 AWS 临时凭证 API](./user-api/endpoint/get-aws-credentials.mdx)
