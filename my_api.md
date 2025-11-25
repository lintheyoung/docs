https://gemini.google.com/share/4ac74f72f871（完整的逻辑流程）

![image-20251125134826854](https://pub-6c1e280a27614b05891bfd818585735e.r2.dev/dedeblog/2025/11/image-20251125134826854.webp)

https://gemini.google.com/share/3f347f1c563f（模拟的UI操作）

![image-20251125135044698](https://pub-6c1e280a27614b05891bfd818585735e.r2.dev/dedeblog/2025/11/image-20251125135044698.webp)

## 一、这条“放置新陷阱”流程中会用到的所有 API（概览）

全部按 Stripe 风格的 REST 资源命名，`snake_case` 字段，`/v1/...` 前缀。

### 1. 会话 & 媒体 & 结果资源

1. `POST /v1/setup-sessions`
    创建一次布防会话（用户点「＋新布防」）
2. `POST /v1/setup-sessions/{id}`
    更新会话：写入 identification/strategy/location/calibration 阶段数据
3. `POST /v1/setup-sessions/{id}/create-trap`
    从一个完成了各阶段数据的 session 中，创建真正的 `trap`
4. `POST /v1/media-assets`
    为用户拍的每一张照片创建媒体记录（返回上传信息 + `media_asset_id`）

------

### 2. 智能推荐 / 分析类（你新强调的几类 AI 能力）

1. `POST /v1/trap-recommendations`
    👉 根据：**用户所在地区 + 家中目标鼠种 + 用户偏好**
    返回“推荐购买哪些捕鼠器”的列表（用于 `TRAP_RECOMMENDATION` 页面）
2. `POST /v1/bait-recommendations`
    👉 根据：**地区 + 目标鼠种 + 用户已有/推荐 trap 类型 + 用户家中可用食物信息（可选）**
    返回“最适合的诱饵列表”（`BAIT_CHECK` 页面不再是固定花生酱）
3. `POST /v1/location-analyses`
    👉 输入：**房间全景的 `media_asset_id` + session 信息**
    输出：
   - 最佳放置位置的**文字描述**（描述放哪里、靠什么、朝向如何）
   - 一张**带标注的图片**（服务器生成并保存，返回一个新的 `annotated_media_asset_id`）
4. `POST /v1/calibration-checks`
    👉 输入：**用户拍的“已布置好的陷阱”照片 `media_asset_id` + session 中 trap/bait/rodent 信息**
    输出：
   - `is_correct`：布置是否合格
   - 如果不合格：具体问题、需要怎么调整（文本说明）
   - 可选：矫正建议的标注图 `annotated_media_asset_id`

> 这里已经包含了你说的逻辑：
>
> - 并不“故意失败”
> - AI 会真的判断是否 OK
> - 如果失败，可以重试一次；如果还是不行，用户可以选 **重新摆放**（再调用一次）或 **跳过**（直接创建 trap，但可能标记 calibration_confidence 较低——这是实现细节）。

------

### 3. 落地实体 & 事件 & Dashboard

1. `GET /v1/traps`
    列出当前用户的陷阱（Dashboard 列表）
2. `GET /v1/traps/{id}`
    获取单个陷阱详情（详情页）
3. `POST /v1/trap-events`
    创建陷阱事件：布防完成、检查、捕获、补饵等（在布防完成时会用一次）

> 以上 3 个，是用户完成布防后在 Dashboard / 详情页看到数据的来源。

------

## 二、按用户操作顺序，重新梳理整个流程用到的 API

下面是从「点击＋」开始，到「布防完成」为止，一步一步的 API 调用轨迹（含分支逻辑）。

------

### 0️⃣ 用户点击「＋ 新布防」

**UI：** Dashboard → 右下角「＋」

#### ✅ API：

1. `POST /v1/setup-sessions`
   - 创建一条新的布防会话
   - 初始 `current_stage = "identification"`
   - 返回 `setup_session_id = ss_xxx`
   - 前端在后续所有步骤都带上 `ss_xxx`

------

下面是 `POST /v1/setup-sessions` 的完整接口 spec

------

# POST `/v1/setup-sessions`

创建一条新的 **布防会话（setup session）**。
 每当用户在 App 内点击「＋ 新布防」时，都应该调用这个接口。

一个 setup session 表示从「开始诊断家里老鼠」到「布置好一个新陷阱」的整条引导流程的状态容器。后续步骤（物种识别、工具策略、诱饵推荐、位置侦查、校准）都会基于这条会话更新。

------

## 请求概览（Summary）

- **HTTP 方法：** `POST`
- **URL：** `/v1/setup-sessions`
- **认证：** 需要，`Authorization: Bearer <token>`
- **幂等性：** 支持，建议对可能重试的调用传 `Idempotency-Key` 头
- **返回：** 一个 `setup_session` 对象

------

## 请求头（Request Headers）

| Header            | 必填 | 说明                                                      |
| ----------------- | ---- | --------------------------------------------------------- |
| `Authorization`   | 是   | `Bearer <access_token>`                                   |
| `Content-Type`    | 否   | 推荐 `application/json`                                   |
| `Idempotency-Key` | 否   | 客户端生成的唯一键，用于避免重复创建会话                  |
| `RatTrap-Version` | 否   | API 版本（类似 Stripe-Version，可选），例如：`2024-11-22` |

> **建议：**
>  对于“用户点了一次＋按钮，但网络可能重试”的场景，**强烈建议**带上 `Idempotency-Key`，避免重复创建多个会话。

------

## 请求体参数（Request Body Parameters）

> 风格参考 Stripe：少、精、可选。
>  大多数信息（如用户 ID / tenant）从认证上下文中推导，不需要前端传。

请求体为 JSON（也可以兼容 form-urlencoded，但这里按 JSON 描述）：

| 字段名                  | 类型   | 必填 | 说明                                                         |
| ----------------------- | ------ | ---- | ------------------------------------------------------------ |
| `source`                | string | 否   | 会话来源，用于统计。推荐值：`"mobile_app"`、`"web_app"` 等。 |
| `initial_rodent_target` | string | 否   | 如果前端在开启会话前就已经大致知道是 rat/mouse，可提前传：`"rat"` / `"mouse"` / `"unknown"`。通常可以留空，由后续步骤确定。 |
| `user_location_hint`    | object | 否   | 提供地区提示，用于后续推荐 trap / bait。比如：`{"country": "TW", "city": "Taipei"}`。如不传可由后端从用户 profile / IP 推断。 |
| `metadata`              | object | 否   | 自定义键值对，不参与业务逻辑，仅用于标记该会话。键和值均为字符串。 |

### 字段示例

```json
{
  "source": "mobile_app",
  "initial_rodent_target": "unknown",
  "user_location_hint": {
    "country": "TW",
    "city": "Taipei"
  },
  "metadata": {
    "started_from": "dashboard_fab",
    "campaign": "winter_2024"
  }
}
```

> 所有字段都是可选的。
>  最常见的调用其实可以是一个**空 body**：`POST /v1/setup-sessions {}`。

------

## 响应（Response）

成功时返回一个 `setup_session` 对象：

### 字段说明

| 字段名                 | 类型           | 说明                                                         |
| ---------------------- | -------------- | ------------------------------------------------------------ |
| `id`                   | string         | Setup session 的 ID，带前缀，比如：`ss_12345`。              |
| `object`               | string         | 恒为 `"setup_session"`。                                     |
| `current_stage`        | string         | 当前布防阶段。初始为 `"identification"`。枚举：`identification` / `strategy` / `location` / `calibration` / `completed`。 |
| `is_completed`         | boolean        | 是否已经完成整个布防流程。创建时为 `false`。                 |
| `created_trap_id`      | string or null | 如果该会话最终创建了一个 `trap`，这里会填入 `trap` 的 ID；刚创建时为 `null`。 |
| `rodent_target`        | string or null | 当前判定的目标鼠类（便捷字段），可能为：`"rat"` / `"mouse"` / `"unknown"`；初始为 `null`，后续会在识别阶段被填充。 |
| `identification_data`  | object or null | 物种鉴定阶段的原始数据（AI 结果 + 用户回答）。创建时为空。   |
| `strategy_data`        | object or null | 工具 & 诱饵策略数据。                                        |
| `location_scout_data`  | object or null | 位置侦查结果（文字描述、标注图等）。                         |
| `calibration_data`     | object or null | 校准尝试记录（每次拍照的结果、建议等）。                     |
| `location_media_id`    | string or null | 房间全景图的 `media_asset` ID。                              |
| `calibration_media_id` | string or null | 最近一次校准图片的 `media_asset` ID。                        |
| `metadata`             | object         | 调用时传入的元数据（键值对）。                               |
| `created`              | integer        | 创建时间，Unix 时间戳（秒）。                                |
| `updated`              | integer        | 最近一次更新时间，Unix 时间戳（秒）。                        |

### 成功响应示例

```json
{
  "id": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",
  "object": "setup_session",
  "current_stage": "identification",
  "is_completed": false,
  "created_trap_id": null,
  "rodent_target": null,
  "identification_data": null,
  "strategy_data": null,
  "location_scout_data": null,
  "calibration_data": null,
  "location_media_id": null,
  "calibration_media_id": null,
  "metadata": {
    "started_from": "dashboard_fab",
    "campaign": "winter_2024"
  },
  "created": 1764038400,
  "updated": 1764038400
}
```

------

## 错误（Errors）

所有错误都返回标准 Stripe 风格的 error envelope：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "some_code",
    "message": "Human readable message",
    "param": "field_name",
    "doc_url": "https://docs.rattrap.ai/errors#some_code"
  }
}
```

### 可能的错误类型

| HTTP 状态码 | `error.type`            | `code` 示例                     | 说明                                           |
| ----------- | ----------------------- | ------------------------------- | ---------------------------------------------- |
| `400`       | `invalid_request_error` | `invalid_initial_rodent_target` | `initial_rodent_target` 不是 rat/mouse/unknown |
| `401`       | `authentication_error`  | `invalid_api_key`               | 未提供合法的 `Authorization` 头                |
| `403`       | `authorization_error`   | `not_allowed`                   | 当前用户无权限在该 tenant 下创建会话           |
| `409`       | `idempotency_error`     | `idempotency_key_in_use`        | 同一个 `Idempotency-Key` 与之前请求参数不一致  |
| `429`       | `rate_limit_error`      | `too_many_requests`             | 请求频率限制                                   |
| `500`       | `api_error`             | `internal_error`                | 服务器内部错误                                 |

### 错误示例：无效参数

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "invalid_initial_rodent_target",
    "message": "initial_rodent_target must be one of 'rat', 'mouse', or 'unknown'.",
    "param": "initial_rodent_target",
    "doc_url": "https://docs.rattrap.ai/errors#invalid_initial_rodent_target"
  }
}
```

------

## 幂等性（Idempotency）

对于“点击按钮发起”的操作，如果客户端可能因为网络重试同一个请求，建议使用 `Idempotency-Key`。

- **推荐：** 在用户每次点击「＋ 新布防」时，客户端生成一个 UUID：
  - `Idempotency-Key: rattrap-setup-<uuid>`
- 如果同一个 key 被重复发送，并且请求体完全相同：
  - 服务器应返回第一次创建的那条 `setup_session`
- 如果请求体不同：
  - 返回 409 冲突，`error.type = "idempotency_error"`

------

## 示例请求（Examples）

### cURL

```bash
curl https://api.rattrap.ai/v1/setup-sessions \
  -u sk_test_XXX: \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: rattrap-setup-550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "source": "mobile_app",
    "user_location_hint": {
      "country": "TW",
      "city": "Taipei"
    },
    "metadata": {
      "started_from": "dashboard_fab"
    }
  }'
```

### JavaScript（Node / Edge Function 客户端伪代码）

```js
const res = await fetch("https://api.rattrap.ai/v1/setup-sessions", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${accessToken}`,
    "Content-Type": "application/json",
    "Idempotency-Key": `rattrap-setup-${crypto.randomUUID()}`
  },
  body: JSON.stringify({
    source: "mobile_app",
    user_location_hint: {
      country: "TW",
      city: "Taipei"
    },
    metadata: {
      started_from: "dashboard_fab"
    }
  })
});

const session = await res.json();
// session.id === "ss_..."
```





### 1️⃣ 物种识别阶段（ID_START / ID_SIZE / GEO）

你这块的业务逻辑没变，只是会进到不同问答，但最终的关键是 **得到 rodent_target = rat/mouse/unknown**。

#### 1.1 用户回答完问题（“有黑影？多大？纯猜测？地理推断？”）

**UI：** `ID_START` / `ID_SIZE` / `ID_GEO_RESULT`

#### ✅ API：

1. `POST /v1/setup-sessions/{ss_id}`
   - 写入 `identification_data`：
     - `rodent_target`（rat/mouse/unknown）
     - 可能有 `confidence` 和用户回答
   - 将 `current_stage` 设为 `"strategy"`

> 到此：我们知道「家里是 Rat 还是 Mouse」，下面所有推荐（trap & bait）都会基于这个。

------

好，下面是 **`POST /v1/setup-sessions/{id}`（在物种识别阶段使用）** 的完整接口 spec，用 Stripe 的风格来写。

这个接口本质上是：**更新一个布防会话对象**。
 在当前阶段，我们主要用它来写入 **`identification_data` + `rodent_target` + 推进 `current_stage`**。

> 未来同一个接口也会被 strategy / location / calibration 阶段复用，但这里会把「识别阶段」相关字段单独讲清楚。

------

# POST `/v1/setup-sessions/{id}`

更新一个已有的 **布防会话（setup session）**。

在「物种识别阶段」里，当用户完成了：

- 是否看到黑影（ID_START）
- 大小判断（ID_SIZE）
- 或地理推断（ID_GEO_RESULT）

前端应调用本接口，将识别结果写入：

- `identification_data`（详细信息）
- `rodent_target`（方便后续使用）
- `current_stage`（通常从 `identification` 进入 `strategy`）

------

## 请求概览（Summary）

- **HTTP 方法：** `POST`
- **URL：** `/v1/setup-sessions/{id}`
- **认证：** 需要，`Authorization: Bearer <token>`
- **幂等性：** 建议对“同一步骤可能重试”的调用使用 `Idempotency-Key`
- **返回：** 更新后的 `setup_session` 对象

------

## 路径参数（Path Parameters）

| 参数名 | 类型   | 说明                                             |
| ------ | ------ | ------------------------------------------------ |
| `id`   | string | 要更新的 setup session ID，例如：`ss_1Qy8u8C...` |

------

## 请求头（Request Headers）

| Header            | 必填 | 说明                                              |
| ----------------- | ---- | ------------------------------------------------- |
| `Authorization`   | 是   | `Bearer <access_token>`                           |
| `Content-Type`    | 否   | 推荐 `application/json`                           |
| `Idempotency-Key` | 否   | 用于保证重试安全；例如用户在 ID_SIZE 页面重复提交 |
| `RatTrap-Version` | 否   | API 版本号（日期），如 `2024-11-22`               |

------

## 请求体参数（Request Body Parameters）

> 本接口是“通用更新接口”，但这里**重点描述识别阶段相关字段**。
>  所有字段都为**可选**，只会更新你传入的那些。

### 识别阶段相关字段（Identification Stage）

| 字段名                | 类型    | 必填 | 说明                                                         |
| --------------------- | ------- | ---- | ------------------------------------------------------------ |
| `rodent_target`       | string  | 否   | 识别出的目标鼠类：`"rat"` / `"mouse"` / `"unknown"`。在物种识别阶段，这是最关键字段。 |
| `identification_data` | object  | 否   | 物种识别阶段的详细信息（问卷 + AI 推断）。会整体覆盖原字段。 |
| `advance_to_strategy` | boolean | 否   | 如果为 `true`，后端会将 `current_stage` 自动推进到 `"strategy"`（仅当当前为 `"identification"` 时）。 |

#### `rodent_target` 取值

- `"rat"`：大鼠（例如沟鼠、大褐家鼠等）
- `"mouse"`：小家鼠
- `"unknown"`：尚不确定（例如证据不足）

#### `identification_data` 建议结构（示例）

后端不会强制规定字段结构，只要是 JSON 即可。但推荐形如：

```json
{
  "source": "shadow_and_size",      // or "geo_only", "evidence_photo"
  "answers": {
    "saw_shadow": true,
    "bigger_than_can": true
  },
  "ai_inference": {
    "rodent_target": "rat",
    "confidence": 0.86
  },
  "notes": "User reported seeing a large shadow in the kitchen at night."
}
```

> 注意：`identification_data` 为整块对象更新：
>  不传则不变；传则替换原有内容（Stripe 风格的“字段整体替换”）。

------

### 其它通用可选字段（为未来阶段保留）

> 这些字段在**识别阶段可以不传**，列出来是为了完整性。

| 字段名                | 类型   | 必填 | 说明                                                         |
| --------------------- | ------ | ---- | ------------------------------------------------------------ |
| `strategy_data`       | object | 否   | 工具 & 诱饵策略数据（在后续阶段使用）。                      |
| `location_scout_data` | object | 否   | 位置侦查结果（在 location 阶段使用）。                       |
| `calibration_data`    | object | 否   | 校准尝试结果（在 calibration 阶段使用）。                    |
| `metadata`            | object | 否   | 自定义键值对。新对象会与原有 metadata **合并**（浅合并），同名键覆盖。 |

------

## 请求示例（Examples）

### 示例 1：用户通过影子大小判断为大鼠（Rat），并进入下一阶段

用户操作路径：
 ID_START → 看到黑影 → ID_SIZE → 比可乐罐大 → 点击「继续」。

```http
POST /v1/setup-sessions/ss_1Qy8u8CZ7aQp98Xb5WJtR3 HTTP/1.1
Authorization: Bearer sk_test_xxx
Content-Type: application/json
Idempotency-Key: rattrap-identification-3d8cc2f0-1e9f-4c5b-90f9-dcb8a467c777
{
  "rodent_target": "rat",
  "identification_data": {
    "source": "shadow_and_size",
    "answers": {
      "saw_shadow": true,
      "bigger_than_can": true
    },
    "ai_inference": {
      "rodent_target": "rat",
      "confidence": 0.9
    }
  },
  "advance_to_strategy": true,
  "metadata": {
    "entry_flow": "shadow_size_flow"
  }
}
```

### 示例 2：用户选择“纯猜测”，通过地理推断判定为 Rat，但暂不推进阶段

用户可能还要上传痕迹照片，这时可以只先写入 `identification_data` 而不推进阶段。

```json
{
  "rodent_target": "rat",
  "identification_data": {
    "source": "geo_only",
    "geo_hint": {
      "country": "TW",
      "city": "Taipei"
    },
    "ai_inference": {
      "rodent_target": "rat",
      "confidence": 0.7
    }
  },
  "advance_to_strategy": false
}
```

------

## 响应（Response）

成功时返回**更新后的** `setup_session` 对象（字段结构与 `POST /v1/setup-sessions` 一致）。

### 成功响应示例

```json
{
  "id": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",
  "object": "setup_session",
  "current_stage": "strategy",          // 已推进到 strategy 阶段
  "is_completed": false,
  "created_trap_id": null,

  "rodent_target": "rat",

  "identification_data": {
    "source": "shadow_and_size",
    "answers": {
      "saw_shadow": true,
      "bigger_than_can": true
    },
    "ai_inference": {
      "rodent_target": "rat",
      "confidence": 0.9
    }
  },

  "strategy_data": null,
  "location_scout_data": null,
  "calibration_data": null,

  "location_media_id": null,
  "calibration_media_id": null,

  "metadata": {
    "started_from": "dashboard_fab",
    "entry_flow": "shadow_size_flow"
  },

  "created": 1764038400,
  "updated": 1764038455
}
```

------

## 行为规则（Stage & 字段更新规则）

1. **只更新传入的字段**
   - 未在请求体中出现的字段一律保持不变。
   - `identification_data` / `strategy_data` / `location_scout_data` / `calibration_data` **按字段整体替换**。
2. **`advance_to_strategy` 行为**
   - 如果 `advance_to_strategy = true` 且当前 `current_stage = "identification"`：
      → 后端会将 `current_stage` 更新为 `"strategy"`。
   - 如果当前 `current_stage != "identification"`：
      → 忽略该标志（不报错，但不推进阶段），保持幂等简洁。
3. **`rodent_target` 是个“便利字段”**
   - 建议总是与 `identification_data.ai_inference.rodent_target` 保持一致，以免混乱。
   - 如果未传 `rodent_target`，后端不会尝试从 `identification_data` 自动推断，避免隐式行为。

------

## 错误（Errors）

错误响应使用统一的 `error` 包裹结构：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "some_code",
    "message": "Human readable message",
    "param": "field_name",
    "doc_url": "https://docs.rattrap.ai/errors#some_code"
  }
}
```

### 典型错误列表

| HTTP 状态码 | `error.type`            | `code`                     | 说明                                                         |
| ----------- | ----------------------- | -------------------------- | ------------------------------------------------------------ |
| `400`       | `invalid_request_error` | `invalid_rodent_target`    | `rodent_target` 不是 `rat/mouse/unknown` 之一                |
| `400`       | `invalid_request_error` | `invalid_stage_transition` | 当前阶段不是 `identification` 却试图推进到 strategy（如果你想严格限制的话，可以用这个） |
| `404`       | `invalid_request_error` | `setup_session_not_found`  | 找不到指定 ID 的 session                                     |
| `401`       | `authentication_error`  | `invalid_api_key`          | 未认证或 token 无效                                          |
| `403`       | `authorization_error`   | `not_allowed`              | 用户无权访问该 session                                       |
| `409`       | `idempotency_error`     | `idempotency_key_in_use`   | 同一个 Idempotency-Key 的请求体不一致                        |
| `429`       | `rate_limit_error`      | `too_many_requests`        | 请求过于频繁                                                 |
| `500`       | `api_error`             | `internal_error`           | 服务器内部错误                                               |

### 错误示例：无效的 rodent_target

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "invalid_rodent_target",
    "message": "rodent_target must be one of 'rat', 'mouse', or 'unknown'.",
    "param": "rodent_target",
    "doc_url": "https://docs.rattrap.ai/errors#invalid_rodent_target"
  }
}
```

------

## 幂等性说明（Idempotency）

在识别阶段，前端很可能会因为网络抖动或用户重复点击按钮而重试提交：

- 建议使用：`Idempotency-Key: rattrap-identification-<uuid>`。
- 如果在给定的 `Idempotency-Key` 下，请求体完全相同：
  - 服务器应返回第一次的结果（并保证不重复写入副作用，如重复事件）。
- 如果同一个 `Idempotency-Key` 下请求体不同：
  - 返回 409 错误，`error.type = "idempotency_error"`。

------

## 小结

- `POST /v1/setup-sessions/{id}` 是一个 **“通用更新会话”接口**，
- 在「物种识别阶段」我们用它来：
  - 写入 `rodent_target`
  - 写入 `identification_data`
  - 选择性地推进 `current_stage → "strategy"`（通过 `advance_to_strategy`）

------



### 2️⃣ 工具策略阶段（STRATEGY_CAM & TRAP_RECOMMENDATION）

#### 2.1 STRATEGY_CAM：用户是否已有捕鼠器？

**UI：** 拍现有捕鼠器 / 或点击“没有，跳过”

------

#### 🔹 分支 A：用户有捕鼠器 → 拍照并分析是否适合

1. 用户拍摄工具照片。
2. `POST /v1/media-assets`
   - purpose: `"setup"`
   - 返回 `media_asset_id = ma_tool`
3. Edge Function / 后端内部调用 AI 识别工具类型（可以封装在下一步 API）
4. `POST /v1/trap-recommendations`（*已有捕鼠器路径，可以复用这个接口*）
   - 请求体里包含：
     - `mode: "existing_trap"`
     - `rodent_target`
     - `media_asset_id = ma_tool`
     - `user_location`（城市/国家）
   - 返回：
     - 识别出的 `trap_type`（snap/glue/...）
     - `is_suitable`（是否适合当前 rodent）
     - 如果不适合，可以顺便返回推荐的新 trap 列表
5. `POST /v1/setup-sessions/{ss_id}`
   - 更新 `strategy_data`：
     - `trap_detected_type`
     - `trap_is_suitable`
     - `tool_media_id = ma_tool`
   - `current_stage` 仍 `"strategy"`

> 前端根据 `trap_is_suitable`：
>
> - 适合 → 进入诱饵推荐（3️⃣）
> - 不适合 → 也可以进入“推荐购买”页展示替代方案（直接用 4 步的 response）

------

#### 🔹 分支 B：用户没有捕鼠器 → 直接去购买推荐（TRAP_RECOMMENDATION）

**UI：** “知道了，我家没有工具”

1. `POST /v1/trap-recommendations`
   - `mode: "no_trap"`
   - 输入：
     - `rodent_target`
     - `user_location`
     - 用户偏好（如不想杀生、预算等）
   - 输出：
     - 对当前地区 & 鼠种**最适合的 trap 列表**
     - 每条带：类型、推荐理由、适用场景、优缺点等
2. `POST /v1/setup-sessions/{ss_id}`
   - 更新：`strategy_data.trap_recommendations`（方便日志 & 分析）
   - 可选：标记 `"flow_variant": "no_existing_trap"`

**用户点击「知道了，我去买」：**

1. `POST /v1/setup-sessions/{ss_id}/complete`
   - `is_completed = true`
   - `current_stage = "completed"`

> 这条支线到此结束：**没有创建 trap**，只是帮助用户做采购决策。

------

太棒，这一块就是整个“工具策略阶段”的大脑接口。下面是 **`POST /v1/trap-recommendations`** 的完整 spec，用 Stripe 式风格来写。

------

# POST `/v1/trap-recommendations`

根据 **用户所在地区 + 目标鼠种 + 用户是否已有捕鼠器 +（可选）工具照片 + 用户偏好**，返回一组**捕鼠器策略推荐**。

- 当 `mode = "existing_trap"` 时：
   → 识别用户现有工具的类型，并评估是否适合当前 rodent。
   → 如不适合，同时给出购买建议列表。
- 当 `mode = "no_trap"` 时：
   → 只基于 rodent + 地区 + 偏好，推荐购买哪些 trap。

------

## 请求概览（Summary）

- **HTTP 方法：** `POST`
- **URL：** `/v1/trap-recommendations`
- **认证：** 需要，`Authorization: Bearer <token>`
- **幂等性：** 推荐对“同一次推荐请求”使用 `Idempotency-Key`
- **返回：** 一个 `trap_recommendation_result` 对象

------

## 请求头（Request Headers）

| Header            | 必填 | 说明                                                 |
| ----------------- | ---- | ---------------------------------------------------- |
| `Authorization`   | 是   | `Bearer <access_token>`                              |
| `Content-Type`    | 否   | 推荐 `application/json`                              |
| `Idempotency-Key` | 否   | 可选，但建议使用（尤其是上传图片后紧接着的推荐请求） |
| `RatTrap-Version` | 否   | API 版本（日期字符串），例如：`2024-11-22`           |

------

## 请求体参数（Request Body Parameters）

请求体为 JSON。

### 通用字段

| 字段名          | 类型   | 必填 | 说明                                                         |
| --------------- | ------ | ---- | ------------------------------------------------------------ |
| `mode`          | string | 是   | 推荐模式：`"existing_trap"` 或 `"no_trap"`。                 |
| `rodent_target` | string | 是   | 目标鼠种：`"rat"` / `"mouse"` / `"unknown"`。                |
| `user_location` | object | 否   | 用户所在地区，用于选型。建议至少包含 `country`，可选城市等。 |
| `preferences`   | object | 否   | 用户偏好，用于过滤方案（如预算、人道不杀等）。               |
| `limit`         | int    | 否   | 返回推荐 trap 的最大数量，默认 3，最大 10。                  |

#### `user_location` 建议结构

```json
"user_location": {
  "country": "TW",
  "city": "Taipei",
  "environment": "apartment"   // 可选：apartment / house / farm / warehouse ...
}
```

#### `preferences` 建议结构（示例）

```json
"preferences": {
  "avoid_killing": false,        // true 表示希望人道捕捉，不杀生
  "has_children_or_pets": true,  // 家中有小孩/宠物 -> 避免暴露式弹簧夹
  "budget_level": "medium",      // low / medium / high
  "noise_sensitive": true,       // 对咔哒声、电击声敏感
  "maintenance_tolerance": "low" // low / medium / high：能接受的维护频率
}
```

> 所有偏好字段都是可选的，未提供时使用默认策略。

------

### `mode = "existing_trap"` 额外字段

当用户已经拍摄了一个现有捕鼠器的照片，并希望系统识别 & 判断是否适用时使用。

| 字段名           | 类型   | 必填 | 说明                                                  |
| ---------------- | ------ | ---- | ----------------------------------------------------- |
| `mode`           | string | 是   | 必须为 `"existing_trap"`                              |
| `media_asset_id` | string | 是   | 现有捕鼠器照片的 `media_assets` ID，例如 `"ma_123"`。 |

> `media_asset_id` 来自之前调用 `POST /v1/media-assets` 的返回值。

------

### `mode = "no_trap"` 额外字段

当用户没有任何工具，或者你只是想帮他选购新工具时使用。

| 字段名 | 类型   | 必填 | 说明               |
| ------ | ------ | ---- | ------------------ |
| `mode` | string | 是   | 必须为 `"no_trap"` |

> 其它字段：`rodent_target` / `user_location` / `preferences` 等，跟通用字段一样。

------

## 请求示例（Examples）

### 示例 1：用户有现有捕鼠器（已拍照）

```http
POST /v1/trap-recommendations HTTP/1.1
Authorization: Bearer sk_test_xxx
Content-Type: application/json
Idempotency-Key: trap-strategy-existing-8e2ac0bd-3e1a-4d8f-9cbb-5c34b2c3a111
{
  "mode": "existing_trap",
  "rodent_target": "rat",
  "media_asset_id": "ma_1PpTqQx2YwZv9kLb",
  "user_location": {
    "country": "TW",
    "city": "Taipei",
    "environment": "apartment"
  },
  "preferences": {
    "avoid_killing": false,
    "has_children_or_pets": true,
    "budget_level": "medium"
  },
  "limit": 3
}
```

### 示例 2：用户没有工具，直接请求购买推荐

```json
{
  "mode": "no_trap",
  "rodent_target": "mouse",
  "user_location": {
    "country": "TW",
    "city": "Taichung"
  },
  "preferences": {
    "avoid_killing": true,
    "budget_level": "high"
  },
  "limit": 5
}
```

------

## 响应结构（Response Structure）

成功时返回一个 `trap_recommendation_result` 对象。

### 顶层字段

| 字段名              | 类型           | 说明                                                         |
| ------------------- | -------------- | ------------------------------------------------------------ |
| `object`            | string         | 恒为 `"trap_recommendation_result"`。                        |
| `mode`              | string         | 请求时的模式：`"existing_trap"` 或 `"no_trap"`。             |
| `rodent_target`     | string         | 回显或修正后的 rodent 目标。                                 |
| `user_location`     | object         | 回显的地区信息（可能包含后端推断出的补充字段）。             |
| `preferences`       | object         | 回显的偏好。                                                 |
| `existing_trap`     | object or null | 当 `mode = "existing_trap"` 时，包含对现有工具的识别和适用性分析；否则为 null。 |
| `recommended_traps` | array          | 推荐的 trap 列表，每条为一个 `trap_product` 对象。           |
| `created`           | int            | 推荐生成时间，Unix 时间戳（秒）。                            |

------

### `existing_trap` 对象（仅 `mode="existing_trap"` 时有）

| 字段名              | 类型    | 说明                                                         |
| ------------------- | ------- | ------------------------------------------------------------ |
| `object`            | string  | `"existing_trap_analysis"`                                   |
| `media_asset_id`    | string  | 用户上传的工具图片 ID。                                      |
| `detected_type`     | string  | 识别出的陷阱类型：`"snap_trap"` / `"glue_board"` / `"cage_trap"` / `"electronic_trap"` / `"other"`。 |
| `is_suitable`       | boolean | 是否适合当前 rodent_target + 用户环境。                      |
| `suitability_score` | number  | 0–1 之间的评分，用于前端展示信心条。                         |
| `notes`             | string  | 给用户的解释，例如“这是一种传统弹簧夹，对大鼠效果很好，但需要注意放置位置和安全性”。 |

> 如果识别不出类型，可以返回 `detected_type = "other"` 且 `is_suitable = false`，并通过 `recommended_traps` 提供替代方案。

------

### `recommended_traps` 列表 & `trap_product` 对象

每一条推荐 trap 用一个 `trap_product` 对象表示。

| 字段名                   | 类型           | 说明                                                         |
| ------------------------ | -------------- | ------------------------------------------------------------ |
| `object`                 | string         | `"trap_product"`                                             |
| `id`                     | string         | 内部商品 ID，前缀如 `trp_`。                                 |
| `trap_type`              | string         | 与枚举对应：`"snap_trap"` / `"glue_board"` / `"cage_trap"` / `"electronic_trap"` / `"other"`。 |
| `label`                  | string         | 用于 UI 的短标题，例如 `"大号强力弹簧夹"`。                  |
| `description`            | string         | 人类可读描述（优点/适用场景）。                              |
| `for_rodent`             | string         | 推荐适用于 `"rat"` / `"mouse"` / `"both"`。                  |
| `suitability_score`      | number         | 0–1，越高越匹配当前 rodent & 环境 & 偏好。                   |
| `safety_level`           | string         | `"low"` / `"medium"` / `"high"`，用于有小孩/宠物场景。       |
| `maintenance_level`      | string         | `"low"` / `"medium"` / `"high"`，维护频率和复杂度。          |
| `price_band`             | string         | `"low"` / `"medium"` / `"high"`，价格档位。                  |
| `recommended_reason`     | string         | 一句话解释为什么推荐：例 `"对大鼠击杀率高，适合厨房和车库。"` |
| `not_recommended_reason` | string or null | 若该 trap 是“作为参考但不推荐”，可填原因；通常推荐列表里不需要。 |
| `purchase_hints`         | object         | 购买引导信息（可包含平台名/搜索关键词等）。                  |

示例 `purchase_hints`：

```json
"purchase_hints": {
  "search_keywords": "大号 强力 老鼠夹 金属",
  "preferred_platforms": ["local_hardware_store", "online_marketplace"],
  "estimated_price_range": "NT$150–300"
}
```

------

## 成功响应示例

### 1）`mode = "existing_trap"`：识别出用户现有工具可用 & 提供备选方案

```json
{
  "object": "trap_recommendation_result",
  "mode": "existing_trap",
  "rodent_target": "rat",
  "user_location": {
    "country": "TW",
    "city": "Taipei",
    "environment": "apartment"
  },
  "preferences": {
    "avoid_killing": false,
    "has_children_or_pets": true,
    "budget_level": "medium"
  },

  "existing_trap": {
    "object": "existing_trap_analysis",
    "media_asset_id": "ma_1PpTqQx2YwZv9kLb",
    "detected_type": "snap_trap",
    "is_suitable": true,
    "suitability_score": 0.92,
    "notes": "识别为大号弹簧老鼠夹，对成年的大褐家鼠效果良好。请注意放置位置，避免儿童和宠物接触。"
  },

  "recommended_traps": [
    {
      "object": "trap_product",
      "id": "trp_snap_heavy_01",
      "trap_type": "snap_trap",
      "label": "大号强力弹簧夹",
      "description": "适合厨房和车库，对大鼠击杀率高，成本低。",
      "for_rodent": "rat",
      "suitability_score": 0.95,
      "safety_level": "medium",
      "maintenance_level": "low",
      "price_band": "low",
      "recommended_reason": "与您现有工具类型一致，方便一次购买多只备用。",
      "not_recommended_reason": null,
      "purchase_hints": {
        "search_keywords": "大号 强力 老鼠夹 金属",
        "preferred_platforms": ["online_marketplace"],
        "estimated_price_range": "NT$150–300"
      }
    }
  ],

  "created": 1764038500
}
```

### 2）`mode = "no_trap"`：用户没有工具，生成购买列表

```json
{
  "object": "trap_recommendation_result",
  "mode": "no_trap",
  "rodent_target": "mouse",
  "user_location": {
    "country": "TW",
    "city": "Taichung"
  },
  "preferences": {
    "avoid_killing": true,
    "budget_level": "high"
  },

  "existing_trap": null,

  "recommended_traps": [
    {
      "object": "trap_product",
      "id": "trp_cage_humane_01",
      "trap_type": "cage_trap",
      "label": "人道捕鼠笼",
      "description": "不伤害老鼠，适合室内使用。需要将捕获的老鼠带离住宅区放生。",
      "for_rodent": "mouse",
      "suitability_score": 0.91,
      "safety_level": "high",
      "maintenance_level": "medium",
      "price_band": "medium",
      "recommended_reason": "符合您“不杀生”的偏好，并且适合台湾常见的小家鼠。",
      "not_recommended_reason": null,
      "purchase_hints": {
        "search_keywords": "捕鼠笼 人道 小号",
        "preferred_platforms": ["online_marketplace"],
        "estimated_price_range": "NT$300–600"
      }
    }
  ],

  "created": 1764038600
}
```

------

## 错误（Errors）

错误结构沿用统一格式：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "some_code",
    "message": "Human readable message",
    "param": "field_name",
    "doc_url": "https://docs.rattrap.ai/errors#some_code"
  }
}
```

### 典型错误

| HTTP 状态码 | `error.type`            | `code`                    | 说明                                             |
| ----------- | ----------------------- | ------------------------- | ------------------------------------------------ |
| `400`       | `invalid_request_error` | `invalid_mode`            | `mode` 不是 `existing_trap` 或 `no_trap`         |
| `400`       | `invalid_request_error` | `invalid_rodent_target`   | `rodent_target` 非 `rat/mouse/unknown`           |
| `400`       | `invalid_request_error` | `media_asset_id_required` | `mode="existing_trap"` 却未提供 `media_asset_id` |
| `400`       | `invalid_request_error` | `invalid_media_asset`     | 指定的 `media_asset_id` 不存在或不属于当前用户   |
| `400`       | `invalid_request_error` | `invalid_limit`           | `limit` 超出允许范围                             |
| `401`       | `authentication_error`  | `invalid_api_key`         | Auth 无效                                        |
| `403`       | `authorization_error`   | `not_allowed`             | 用户无权访问该媒体资产等                         |
| `429`       | `rate_limit_error`      | `too_many_requests`       | 调用过于频繁                                     |
| `500`       | `api_error`             | `internal_error`          | 服务端错误                                       |
| `502`       | `api_error`             | `ai_provider_unavailable` | 下游 AI 服务暂时不可用                           |

### 错误示例：缺少 `media_asset_id`

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "media_asset_id_required",
    "message": "media_asset_id is required when mode is 'existing_trap'.",
    "param": "media_asset_id",
    "doc_url": "https://docs.rattrap.ai/errors#media_asset_id_required"
  }
}
```

------

## 幂等性说明（Idempotency）

- 推荐在以下场景使用 `Idempotency-Key`：
  - 用户刚拍完照片，前端自动发起推荐请求，但网络可能重试；
  - 用户在 TRAP_RECOMMENDATION 页面下拉刷新，但你希望保持结果一致。
- 策略：
  - 同一个 `Idempotency-Key` + 完全相同的请求体 → 返回第一次的计算结果；
  - 如果请求体不同 → 返回 409 `idempotency_error`。

------

如果你愿意，下一步我们可以继续写：

- `POST /v1/bait-recommendations`（对应 BAIT_CHECK / BAIT_CAM），或者
- `POST /v1/location-analyses`（房间全景 → 文字描述 + 标注图）。



### 3️⃣ 诱饵推荐阶段（BAIT_CHECK / BAIT_CAM）

你现在希望：这一步不是固定“花生酱”，而是一个基于地区 & 鼠种 & trap 类型的**动态 bait 推荐**接口。

#### 3.1 BAIT_CHECK：推荐最适合的诱饵（不再固定 peanut butter）

**场景前提：**
 已经确定：用户有一个可用的 trap（可能是已有、也可能是你推荐用户刚买回来之后重新走流程时指定的 trap）。

1. `POST /v1/bait-recommendations`
   - 输入：
     - `rodent_target`
     - `trap_type`
     - `user_location`
     - （可选）用户标记家中是否有冷藏条件、家中常见食物类型等
   - 输出：
     - 主推荐：比如 `bait_type = "peanut_butter"` 或 `"bacon"` / `"nuts"` 等
     - 备选列表：第二第三推荐
     - 每种诱饵的说明 & 检查周期建议
2. `POST /v1/setup-sessions/{ss_id}`
   - 更新 `strategy_data`：
     - `bait_primary`：接口返回的主推荐
     - `bait_candidates`：其它候选
   - `current_stage` 仍 `"strategy"`

**UI：** 在 BAIT_CHECK 页面显示主推荐 & 候选。

- 如果用户点击「我家有这个」：
  - 不额外调用 API，只需：
    - 把 `bait_type` 定为主推荐
    - （可以在下一步统一 `POST /setup-sessions/{id}` 写入 bait 最终选择）
- 如果用户点击「我家没有，帮我找替代」：
  - 进入 BAIT_CAM → 扫冰箱

------

#### 3.2 BAIT_CAM（扫描冰箱）：基于家中食物重新推荐 bait

1. 用户拍摄冰箱 / 储物柜内部
2. `POST /v1/media-assets`
   - purpose: `"setup"`
   - 返回 `media_asset_id = ma_pantry`
3. `POST /v1/bait-recommendations`
   - 此次请求加参数：
     - `mode: "from_fridge"`
     - `media_asset_id = ma_pantry`
   - 后端内部 AI 分析冰箱里的食物，找出哪些适合作为诱饵
   - 返回：
     - `bait_type`：从冰箱中选出的最佳诱饵类型（比如 `"bacon"`）
     - 推荐理由 + 使用注意事项
4. `POST /v1/setup-sessions/{ss_id}`
   - 更新：
     - `strategy_data.bait_type` = 冰箱中选出的结果
     - `strategy_data.bait_source` = `"from_fridge"`
     - `strategy_data.bait_fridge_media_id` = ma_pantry

> 之后 UI 显示 `BAIT_ALT_RESULT`，用户点「使用此诱饵」即可，**不需要再调 API**，直接跳到位置侦查。

------



- **BAIT_CHECK：** 基于 rodent + trap + 地区 → 动态推荐主诱饵 + 候选
- **BAIT_CAM：** 用户拍冰箱 → 从家里现有食物里挑一款最适合的诱饵

------

# POST `/v1/bait-recommendations`

根据 **目标鼠种、陷阱类型、用户所在地区、用户偏好**，以及（可选）**冰箱照片**，返回适合作为诱饵的推荐方案。

- 当 `mode = "standard"`（默认）时：
   → 基于 rodent + trap + location + 偏好，推荐一组通用诱饵方案（主推荐 + 候选）。
- 当 `mode = "from_fridge"` 时：
   → 基于用户拍摄的冰箱 / 储物柜内部照片，从中筛选出最适合做诱饵的现有食物。

------

## 请求概览（Summary）

- **HTTP 方法：** `POST`
- **URL：** `/v1/bait-recommendations`
- **认证：** 必需，`Authorization: Bearer <token>`
- **幂等性：** 推荐，尤其是 `from_fridge` 模式（图片分析可能重试）
- **返回：** 一个 `bait_recommendation_result` 对象

------

## 请求头（Request Headers）

| Header            | 必填 | 说明                         |
| ----------------- | ---- | ---------------------------- |
| `Authorization`   | 是   | `Bearer <access_token>`      |
| `Content-Type`    | 否   | 推荐 `application/json`      |
| `Idempotency-Key` | 否   | 客户端生成，用于防止重复计算 |
| `RatTrap-Version` | 否   | API 版本（如 `2024-11-22`）  |

------

## 请求体参数（Request Body Parameters）

请求体为 JSON。

### 通用字段

| 字段名          | 类型   | 必填 | 说明                                                         |
| --------------- | ------ | ---- | ------------------------------------------------------------ |
| `mode`          | string | 否   | 推荐模式，默认为 `"standard"`。可选值：`"standard"` / `"from_fridge"`。 |
| `rodent_target` | string | 是   | 目标鼠种：`"rat"` / `"mouse"` / `"unknown"`。                |
| `trap_type`     | string | 否   | 当前使用的陷阱类型，影响诱饵选择策略。枚举：`"snap_trap"` / `"glue_board"` / `"cage_trap"` / `"electronic_trap"` / `"other"`。 |
| `user_location` | object | 否   | 用户所在地区信息（温度、气候、当地常见食物等会影响诱饵表现）。 |
| `preferences`   | object | 否   | 用户偏好相关设置。                                           |
| `limit`         | int    | 否   | 返回诱饵候选数量，默认 3，最大 10。                          |

#### `user_location` 示例结构

```json
"user_location": {
  "country": "TW",
  "city": "Taipei",
  "environment": "apartment"   // 可选: apartment/house/farm/warehouse ...
}
```

#### `preferences` 示例结构

```json
"preferences": {
  "avoid_smelly_bait": false,           // 不喜欢异味太重
  "avoid_perishable": true,             // 不想用容易腐烂的肉类
  "has_children_or_pets": true,         // 有小孩或宠物 -> 避免散落小块
  "easy_to_clean": true,                // 偏好不太黏、清理方便的
  "available_food_profile": {           // 用户自己勾选的可能已有食物（可选）
    "has_peanut_butter": false,
    "has_nuts": true,
    "has_bacon": false,
    "has_cheese": true
  }
}
```

> 所有字段都是可选的，未提供时由后端用默认策略。

------

### `mode = "standard"` 用法（BAIT_CHECK）

**场景：** 用户有一个 trap，App 想先给出“理想世界”的诱饵推荐（不一定用户家里有）。

必要字段：

| 字段名          | 必填 | 说明                                 |
| --------------- | ---- | ------------------------------------ |
| `mode`          | 否   | 可不传，默认 `"standard"`            |
| `rodent_target` | 是   | 必须                                 |
| `trap_type`     | 否   | 建议传，有则更精准                   |
| 其它字段        | 否   | `user_location` / `preferences` 可选 |

请求示例：

```json
{
  "mode": "standard",
  "rodent_target": "rat",
  "trap_type": "snap_trap",
  "user_location": {
    "country": "TW",
    "city": "Taipei"
  },
  "preferences": {
    "avoid_perishable": true,
    "has_children_or_pets": true,
    "available_food_profile": {
      "has_peanut_butter": false,
      "has_nuts": true,
      "has_cheese": true
    }
  },
  "limit": 3
}
```

------

### `mode = "from_fridge"` 用法（BAIT_CAM）

**场景：** 用户点击「没有这个，帮我在冰箱里找」，拍摄冰箱/储物柜内部照片。

额外字段：

| 字段名           | 类型   | 必填 | 说明                                                 |
| ---------------- | ------ | ---- | ---------------------------------------------------- |
| `mode`           | string | 是   | 必须为 `"from_fridge"`                               |
| `media_asset_id` | string | 是   | 冰箱照片在 `media_assets` 表中的 ID，例如 `ma_123`。 |

其余字段 `rodent_target` / `trap_type` / `user_location` / `preferences` 与标准模式相同、可选但强烈推荐。

请求示例：

```json
{
  "mode": "from_fridge",
  "rodent_target": "rat",
  "trap_type": "snap_trap",
  "media_asset_id": "ma_1PkAbC23xyz",
  "user_location": {
    "country": "TW",
    "city": "Kaohsiung"
  },
  "preferences": {
    "avoid_perishable": false,
    "avoid_smelly_bait": false
  },
  "limit": 3
}
```

------

## 响应结构（Response）

成功时返回一个 `bait_recommendation_result` 对象。

### 顶层字段

| 字段名              | 类型           | 说明                                             |
| ------------------- | -------------- | ------------------------------------------------ |
| `object`            | string         | 恒为 `"bait_recommendation_result"`              |
| `mode`              | string         | `"standard"` 或 `"from_fridge"`                  |
| `rodent_target`     | string         | 回显或修正后的 rodent_target                     |
| `trap_type`         | string         | 回显或推断出的 trap_type                         |
| `user_location`     | object         | 回显位置（可能包含后端推断补充）                 |
| `preferences`       | object         | 回显偏好设置                                     |
| `primary_bait`      | object         | 主推荐诱饵，一个 `bait_option` 对象              |
| `alternative_baits` | array          | 候补诱饵列表，元素为 `bait_option` 对象          |
| `fridge_analysis`   | object or null | 仅 `mode="from_fridge"` 时存在，包含冰箱分析结果 |
| `created`           | integer        | 推荐生成时间，Unix 时间戳（秒）                  |

------

### `bait_option` 对象

代表一条具体的诱饵推荐。

| 字段名                       | 类型            | 说明                                                         |
| ---------------------------- | --------------- | ------------------------------------------------------------ |
| `object`                     | string          | `"bait_option"`                                              |
| `id`                         | string          | 内部 ID，前缀如 `bait_peanut_butter`                         |
| `bait_type`                  | string          | 与 DB 中 enum 对齐：`"peanut_butter"`, `"cheese"`, `"bacon"`, `"chocolate"`, `"nuts"`, `"grain"`, `"other"`, `"custom"` |
| `label`                      | string          | 面向用户显示的名称，如 `"花生酱"` / `"香肠/培根"`            |
| `description`                | string          | 说明/优点，例如“高油脂、高香味，对大鼠极具吸引力，且粘性强不易被偷走。” |
| `for_rodent`                 | string          | `"rat"` / `"mouse"` / `"both"`                               |
| `recommended_for_trap_types` | array of string | 适配的 trap 类型列表，例如 `["snap_trap", "cage_trap"]`      |
| `suitability_score`          | number          | 0–1 之间，适配度评分                                         |
| `recommended_interval_hours` | integer         | 推荐的检查/更换间隔（小时），通常来自 `maintenance_rules`。  |
| `spoilage_risk`              | string          | `"low"` / `"medium"` / `"high"`，腐败/变质风险。             |
| `safety_notes`               | string          | 安全提示，如“避免在儿童可触及区域使用含花生成分的诱饵，可能引发过敏。” |
| `usage_tips`                 | string          | 使用技巧，如“涂抹少量在触发踏板背面，并让老鼠必须用力啃咬才能取到。” |
| `source`                     | string          | `"ideal"` / `"from_fridge"` / `"user_available"` 等（用于区分推荐来源） |

------

### `fridge_analysis` 对象（`mode = "from_fridge"` 时）

| 字段名           | 类型   | 说明                                              |
| ---------------- | ------ | ------------------------------------------------- |
| `object`         | string | `"fridge_analysis"`                               |
| `media_asset_id` | string | 用户拍摄的冰箱照片 ID                             |
| `detected_foods` | array  | 识别出来的食物列表（结构可以较简单）              |
| `chosen_food_id` | string | 被选为诱饵的食物 ID（对应 detected_foods 里的项） |

`detected_foods` 示例元素（可选）：

```json
{
  "id": "food_sausage_01",
  "label": "香肠",
  "category": "meat",
  "confidence": 0.93
}
```

> 这部分主要是为了在 BAIT_ALT_RESULT 页面展示“我在你冰箱里发现了香肠/培根，最适合做诱饵”。

------

## 成功响应示例

### 1）`mode = "standard"`：推荐理想诱饵列表（BAIT_CHECK）

```json
{
  "object": "bait_recommendation_result",
  "mode": "standard",
  "rodent_target": "rat",
  "trap_type": "snap_trap",

  "user_location": {
    "country": "TW",
    "city": "Taipei"
  },

  "preferences": {
    "avoid_perishable": true,
    "has_children_or_pets": true
  },

  "primary_bait": {
    "object": "bait_option",
    "id": "bait_peanut_butter",
    "bait_type": "peanut_butter",
    "label": "花生酱",
    "description": "高油脂、高香味，对大褐家鼠吸引力强，且粘性好，不易被叼走。",
    "for_rodent": "rat",
    "recommended_for_trap_types": ["snap_trap", "cage_trap"],
    "suitability_score": 0.96,
    "recommended_interval_hours": 72,
    "spoilage_risk": "medium",
    "safety_notes": "若家中有花生过敏者，请避免在暴露区域使用。",
    "usage_tips": "只需米粒大小的一点，涂在踏板前缘内侧，让老鼠必须逗留啃咬。",
    "source": "ideal"
  },

  "alternative_baits": [
    {
      "object": "bait_option",
      "id": "bait_nuts_mixed",
      "bait_type": "nuts",
      "label": "混合坚果",
      "description": "对大鼠和小鼠都具有吸引力，耐放，适合忙碌家庭。",
      "for_rodent": "both",
      "recommended_for_trap_types": ["snap_trap", "cage_trap"],
      "suitability_score": 0.88,
      "recommended_interval_hours": 168,
      "spoilage_risk": "low",
      "safety_notes": "注意坚果碎片不要撒得太散，避免老鼠吃到却不触发陷阱。",
      "usage_tips": "可用一小块坚果压在踏板边缘，或用牙签扎住以防被轻易拖走。",
      "source": "user_available"
    }
  ],

  "fridge_analysis": null,
  "created": 1764038800
}
```

### 2）`mode = "from_fridge"`：从冰箱中选出最佳诱饵（BAIT_CAM）

```json
{
  "object": "bait_recommendation_result",
  "mode": "from_fridge",
  "rodent_target": "rat",
  "trap_type": "snap_trap",

  "user_location": {
    "country": "TW",
    "city": "Kaohsiung"
  },

  "preferences": {
    "avoid_perishable": false
  },

  "primary_bait": {
    "object": "bait_option",
    "id": "bait_bacon",
    "bait_type": "bacon",
    "label": "香肠 / 培根类肉制品",
    "description": "高蛋白、高油脂，对肉食偏好的沟鼠吸引力极强。",
    "for_rodent": "rat",
    "recommended_for_trap_types": ["snap_trap", "cage_trap"],
    "suitability_score": 0.95,
    "recommended_interval_hours": 24,
    "spoilage_risk": "high",
    "safety_notes": "避免在高温环境放置超过 24 小时，以免腐败产生异味和卫生风险。",
    "usage_tips": "切成小块并用细绳或牙签固定在踏板上，防止被整块拖走。",
    "source": "from_fridge"
  },

  "alternative_baits": [],

  "fridge_analysis": {
    "object": "fridge_analysis",
    "media_asset_id": "ma_1PkAbC23xyz",
    "detected_foods": [
      {
        "id": "food_sausage_01",
        "label": "香肠",
        "category": "meat",
        "confidence": 0.93
      },
      {
        "id": "food_bread_01",
        "label": "吐司面包",
        "category": "grain",
        "confidence": 0.81
      }
    ],
    "chosen_food_id": "food_sausage_01"
  },

  "created": 1764038900
}
```

------

## 错误（Errors）

和前面接口一样，错误使用统一的 envelope：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "some_code",
    "message": "Human readable message",
    "param": "field_name",
    "doc_url": "https://docs.rattrap.ai/errors#some_code"
  }
}
```

### 常见错误列表

| HTTP 状态码 | `error.type`            | `code`                    | 说明                                         |
| ----------- | ----------------------- | ------------------------- | -------------------------------------------- |
| `400`       | `invalid_request_error` | `invalid_mode`            | `mode` 不是 `standard` / `from_fridge`       |
| `400`       | `invalid_request_error` | `invalid_rodent_target`   | `rodent_target` 非 `rat/mouse/unknown`       |
| `400`       | `invalid_request_error` | `media_asset_id_required` | `mode="from_fridge"` 却没传 `media_asset_id` |
| `400`       | `invalid_request_error` | `invalid_media_asset`     | 冰箱照片不存在或不属于当前用户               |
| `400`       | `invalid_request_error` | `invalid_trap_type`       | `trap_type` 不在支持列表内                   |
| `400`       | `invalid_request_error` | `invalid_limit`           | `limit` 小于 1 或大于 10                     |
| `401`       | `authentication_error`  | `invalid_api_key`         | 未认证                                       |
| `403`       | `authorization_error`   | `not_allowed`             | 无权访问该 `media_asset`                     |
| `429`       | `rate_limit_error`      | `too_many_requests`       | 调用过于频繁                                 |
| `500`       | `api_error`             | `internal_error`          | 服务端错误                                   |
| `502`       | `api_error`             | `ai_provider_unavailable` | 下游 AI 分析服务不可用                       |

错误示例：`mode="from_fridge"` 但未提供 `media_asset_id`：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "media_asset_id_required",
    "message": "media_asset_id is required when mode is 'from_fridge'.",
    "param": "media_asset_id",
    "doc_url": "https://docs.rattrap.ai/errors#media_asset_id_required"
  }
}
```

------

## 幂等性（Idempotency）

- 推荐对这类“计算型接口”使用 `Idempotency-Key`：
  - 用户在 BAIT_CHECK 页面点击重试 / 下拉刷新；
  - 用户在 BAIT_CAM 拍完冰箱后网络抖动重复发起请求。

策略：

- 同一个 `Idempotency-Key` + 完全相同请求体 → 返回第一次的结果。
- 同一个键但请求体不同 → 返回 409 `idempotency_error`。

------

这样，BAIT_CHECK / BAIT_CAM 阶段用到的 `POST /v1/bait-recommendations` 就完整定义好了。
 接下来如果你愿意，我们可以继续写下一个关键 AI 接口：

- `POST /v1/location-analyses`（房间全景 → 文字描述 + 标注图），
   或者直接跳到
- `POST /v1/calibration-checks`（布置完成后的校准判断）。



### 4️⃣ 位置侦查阶段（LOC_CAM：AI 给文字 + 标注图）

你补充了一点：

> AI 不仅返回最佳位置坐标，还会生成一张**带标注的图片**，以及详细的文字描述。

#### 4.1 用户拍摄房间全景（LOC_CAM）

1. 用户拍房间全景
2. `POST /v1/media-assets`
   - purpose: `"setup"`
   - 返回 `media_asset_id = ma_room`
3. 后端请 AI 分析，**通过统一接口封装：**
4. `POST /v1/location-analyses`
   - 输入：
     - `setup_session_id = ss_xxx`
     - `media_asset_id = ma_room`
     - `rodent_target`
     - `trap_type`
     - `bait_type`
   - 内部行为：
     - AI 分析房间结构，找最佳放置区域
     - 生成：
       - 文字描述（例：“沿厨房冰箱右侧靠墙，距墙角约 10cm，陷阱垂直于墙放置，诱饵朝向墙角”）
       - 在原图上绘制标注框，产生一张新图片，保存到 `media_assets`：
         - `annotated_media_asset_id = ma_room_annotated`
   - 输出：
     - 一段 `placement_text`
     - `annotated_media_asset_id`
     - 可选：结构化的 `zones`（bounding boxes）
5. `POST /v1/setup-sessions/{ss_id}`
   - 更新：
     - `location_media_id = ma_room`
     - `location_scout_data`：
       - 包含 `placement_text`, `annotated_media_asset_id`, `zones` 等
     - `current_stage = "location"`

> 前端 LOC_RESULT 页面：
>
> - 显示 AI 返回的文字描述
> - 显示带标注的图片（通过 `annotated_media_asset_id` 对应的 URL）
>    用户现实中照着去放，放好后点「我放好了，去检查」，进入校准阶段。

------

好，这一段就是「帮用户看房间、标位置」的核心接口。下面是 **`POST /v1/location-analyses`** 的完整 spec，用你现在的业务逻辑 + Stripe 风格整合写出来。

------

# POST `/v1/location-analyses`

对用户拍摄的 **房间全景照片** 进行视觉分析，找出 **最佳放置陷阱的位置**，并生成：

- 用自然语言描述的**放置说明**（placement_text）
- 一张**带标注的图片**（在原图上标出推荐区域），对应一个新的 `media_asset`
- 可选的结构化区域数据（bounding boxes / zones）供前端高级可视化使用

该接口通常在布防流程中的 **位置侦查阶段（LOC_CAM）** 调用。

------

## 请求概览（Summary）

- **HTTP 方法：** `POST`
- **URL：** `/v1/location-analyses`
- **认证：** 必需，`Authorization: Bearer <token>`
- **幂等性：** 建议使用 `Idempotency-Key`
- **返回：** 一个 `location_analysis` 对象

------

## 请求头（Request Headers）

| Header            | 必填 | 说明                                         |
| ----------------- | ---- | -------------------------------------------- |
| `Authorization`   | 是   | `Bearer <access_token>`                      |
| `Content-Type`    | 否   | 推荐 `application/json`                      |
| `Idempotency-Key` | 否   | 可选，但建议使用（同一张房间图的分析可重用） |
| `RatTrap-Version` | 否   | API 版本（如 `2024-11-22`）                  |

------

## 请求体参数（Request Body Parameters）

请求体为 JSON。

| 字段名             | 类型   | 必填 | 说明                                                         |
| ------------------ | ------ | ---- | ------------------------------------------------------------ |
| `setup_session_id` | string | 否   | 关联的布防会话 ID（`ss_xxx`）。建议传，便于审计和后续关联。  |
| `media_asset_id`   | string | 是   | 房间全景照片的 `media_assets.id`，例如 `"ma_room_123"`。     |
| `rodent_target`    | string | 否   | 当前目标鼠种：`"rat"` / `"mouse"` / `"unknown"`。用于选择更偏隐蔽或更靠近墙角的策略。 |
| `trap_type`        | string | 否   | 准备使用的陷阱类型：`"snap_trap"` / `"glue_board"` / `"cage_trap"` / `"electronic_trap"` / `"other"`。不同工具对位置有略微不同要求。 |
| `bait_type`        | string | 否   | 计划使用的诱饵类型：如 `"peanut_butter"` / `"bacon"` 等，可用于微调推荐。 |
| `user_location`    | object | 否   | 地区环境信息（国家/城市/环境），可用于微调建议。             |
| `options`          | object | 否   | 高级选项，如是否需要多候选点位等。                           |

### 字段细节

#### `user_location` 示例结构

```json
"user_location": {
  "country": "TW",
  "city": "Taipei",
  "environment": "apartment"   // apartment / house / warehouse / restaurant_kitchen ...
}
```

#### `options` 示例结构

```json
"options": {
  "max_zones": 2,                 // 返回几个推荐点位，默认 2，最大 5
  "need_heatmap": false,          // 未来扩展，例如返回热力图
  "language": "zh-CN"             // placement_text 的语言，默认跟用户设置一致
}
```

> 大部分情况下，你可以只传：`setup_session_id` + `media_asset_id` + `rodent_target` + `trap_type`。

------

## 请求示例（Example Request）

```http
POST /v1/location-analyses HTTP/1.1
Authorization: Bearer sk_test_xxx
Content-Type: application/json
Idempotency-Key: loc-analysis-7f9b4bde-47c2-4ff0-9b0c-eed1d72ff001
{
  "setup_session_id": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",
  "media_asset_id": "ma_room_1PpTqQx2YwZv9kLb",
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
}
```

------

## 响应结构（Response）

成功时返回一个 `location_analysis` 对象。

### 顶层字段

| 字段名                     | 类型           | 说明                                                    |
| -------------------------- | -------------- | ------------------------------------------------------- |
| `object`                   | string         | 恒为 `"location_analysis"`                              |
| `id`                       | string         | 本次分析结果的 ID（可选，有则便于追踪），例如 `loc_123` |
| `setup_session_id`         | string or null | 回显输入的会话 ID                                       |
| `media_asset_id`           | string         | 原始房间照片的 `media_asset_id`                         |
| `annotated_media_asset_id` | string         | 标注后的图片 `media_asset_id`（服务端生成的一张新图）   |
| `rodent_target`            | string         | 回显/修正的目标鼠种                                     |
| `trap_type`                | string or null | 回显陷阱类型                                            |
| `bait_type`                | string or null | 回显诱饵类型                                            |
| `placement_text`           | string         | 可直接展示给用户的**详细文字说明**，引导如何放置陷阱。  |
| `zones`                    | array          | 推荐放置区域的结构化描述列表。                          |
| `notes`                    | string or null | 额外说明，如“房间内可用位置较少，建议考虑移动杂物”。    |
| `created`                  | integer        | 分析生成时间，Unix 时间戳（秒）。                       |

------

### `zones` 元素结构（推荐放置区域）

每个元素代表一个候选区域 / 点位。

| 字段名                | 类型           | 说明                                                     |
| --------------------- | -------------- | -------------------------------------------------------- |
| `id`                  | string         | 区域 ID，例如 `"zone_A"`                                 |
| `label`               | string         | 短标签，如 `"推荐点位 A"`                                |
| `priority`            | integer        | 优先级，1 为最高。                                       |
| `confidence`          | number         | 0–1 之间，AI 对这个点位的信心。                          |
| `description`         | string         | 对该点位的自然语言说明。                                 |
| `bounding_box`        | object         | 在图片中的矩形区域，用于在前端画框。                     |
| `distance_to_wall_cm` | number or null | 建议陷阱距离墙面的距离（厘米），适用时返回。             |
| `orientation_hint`    | string or null | 用于说明陷阱应该如何朝向，比如 `"bait_towards_corner"`。 |

`bounding_box` 示例：

```json
"bounding_box": {
  "x": 0.15,   // 左上角 x，归一化到 0–1
  "y": 0.55,   // 左上角 y
  "width": 0.20,
  "height": 0.18
}
```

------

## 成功响应示例

```json
{
  "object": "location_analysis",
  "id": "loc_1RasJr2f9hQe8KmN",
  "setup_session_id": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",

  "media_asset_id": "ma_room_1PpTqQx2YwZv9kLb",
  "annotated_media_asset_id": "ma_room_annotated_9DzXcP4v",

  "rodent_target": "rat",
  "trap_type": "snap_trap",
  "bait_type": "peanut_butter",

  "placement_text": "建议将老鼠夹放置在冰箱右侧沿墙根位置，距离墙角约 10 厘米，夹子垂直于墙摆放，诱饵一端朝向墙角。请确保陷阱紧贴墙面，并避免被垃圾桶或杂物挡住。",

  "zones": [
    {
      "id": "zone_A",
      "label": "推荐点位 A",
      "priority": 1,
      "confidence": 0.93,
      "description": "冰箱右侧墙角附近，靠近电线和小孔洞，是老鼠常走的贴墙路线。",
      "bounding_box": {
        "x": 0.62,
        "y": 0.48,
        "width": 0.18,
        "height": 0.20
      },
      "distance_to_wall_cm": 0,
      "orientation_hint": "trap_perpendicular_to_wall_bait_towards_corner"
    },
    {
      "id": "zone_B",
      "label": "备选点位 B",
      "priority": 2,
      "confidence": 0.78,
      "description": "水槽下方橱柜前的墙根位置，适合作为第二个陷阱或备用位置。",
      "bounding_box": {
        "x": 0.15,
        "y": 0.60,
        "width": 0.20,
        "height": 0.15
      },
      "distance_to_wall_cm": 0,
      "orientation_hint": "trap_parallel_to_wall"
    }
  ],

  "notes": "房间整体较整洁，可优先在冰箱附近放置第一个陷阱。",
  "created": 1764039000
}
```

> 前端 LOC_RESULT 页面可以：
>
> - 用 `placement_text` 做主要说明；
> - 用 `annotated_media_asset_id` 加载那张带红框的图；
> - 可选：根据 `zones.bounding_box` 在客户端加动画框 / 点击交互。

------

## 错误（Errors）

错误响应采用统一的 error envelope 格式：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "some_code",
    "message": "Human readable message",
    "param": "field_name",
    "doc_url": "https://docs.rattrap.ai/errors#some_code"
  }
}
```

### 常见错误列表

| HTTP 状态码 | `error.type`            | `code`                    | 说明                                          |
| ----------- | ----------------------- | ------------------------- | --------------------------------------------- |
| `400`       | `invalid_request_error` | `media_asset_id_required` | 未提供 `media_asset_id`                       |
| `400`       | `invalid_request_error` | `invalid_media_asset`     | 图片不存在或不属于当前用户                    |
| `400`       | `invalid_request_error` | `invalid_rodent_target`   | `rodent_target` 非 `rat/mouse/unknown`        |
| `400`       | `invalid_request_error` | `invalid_trap_type`       | `trap_type` 不在支持列表                      |
| `400`       | `invalid_request_error` | `invalid_options`         | `options` 中某些值越界（比如 max_zones 超限） |
| `401`       | `authentication_error`  | `invalid_api_key`         | 未认证 / token 无效                           |
| `403`       | `authorization_error`   | `not_allowed`             | 无权访问该媒体资源 / 会话                     |
| `404`       | `invalid_request_error` | `setup_session_not_found` | `setup_session_id` 不存在（如果传了的话）     |
| `429`       | `rate_limit_error`      | `too_many_requests`       | 调用频率过高                                  |
| `500`       | `api_error`             | `internal_error`          | 服务端错误                                    |
| `502`       | `api_error`             | `ai_provider_unavailable` | 下游视觉模型不可用                            |

### 错误示例：缺少 `media_asset_id`

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "media_asset_id_required",
    "message": "media_asset_id is required to run a location analysis.",
    "param": "media_asset_id",
    "doc_url": "https://docs.rattrap.ai/errors#media_asset_id_required"
  }
}
```

------

## 幂等性说明（Idempotency）

- 建议对「同一房间照片 + 同一上下文」的分析使用相同 `Idempotency-Key`：
  - 比如：同一张 `media_asset_id`，用户在前端刷新 LOC_RESULT 页面时重试。
- 行为建议：
  - 相同 `Idempotency-Key` + 完全一致的请求体 → 返回第一次生成的结果（避免重复调用 AI，节约成本）。
  - 相同 key 但请求体不同 → 返回 409 `idempotency_error`。

------

有了这个接口：

- 第 4 步 `POST /v1/location-analyses` 负责“看图 + 标注 +文字生成”
- 第 5 步 `POST /v1/setup-sessions/{ss_id}` 把 `location_media_id` 和 `location_scout_data`（含 `placement_text` & `annotated_media_asset_id` & `zones`）写回 session

下一步如果你愿意，我们可以继续做最后一块关键 AI 接口：

> `POST /v1/calibration-checks` —— 用户已经放好陷阱，拍近景照片，AI 评估是否放对，给出调整建议。



### 5️⃣ 校准阶段（CALIB_CAM：可能一次成功，也可能多次重试）

你新增逻辑：

- AI 会**真实判断**是否放好；
- 如果 OK：直接过
- 如果不 OK：提示问题，用户可以重拍一次
- 如果连续失败，用户可以选择：
  - 再次重新摆放 & 再拍
  - **或者直接跳过**（带着问题创建 trap）

#### 5.1 用户拍摄布置完成的陷阱（第一次 / N 次）

1. 用户在 CALIB_CAM 页面拍照
2. `POST /v1/media-assets`
   - purpose: `"setup"` 或 `"check"`（看你怎么区分）
   - 返回 `media_asset_id = ma_calib_n`
3. 请求 AI 校验这次布置：
4. `POST /v1/calibration-checks`
   - 输入：
     - `setup_session_id = ss_xxx`
     - `media_asset_id = ma_calib_n`
     - `rodent_target`
     - `trap_type`
     - `bait_type`
        -（可选）`location_context`（上一阶段的 `location_scout_data`）
   - 输出：
     - `is_correct: true/false`
     - `issues: [...]`（如：距离墙 8cm，角度偏差等）
     - `advice_text`：改进建议
     - 可选：`annotated_media_asset_id`：在图片上画出问题点
5. 把此次校准尝试记录进 session：
6. `POST /v1/setup-sessions/{ss_id}`
   - 更新：
     - `calibration_media_id = ma_calib_n`（可以永远保持最新一次成功/最近一次尝试）
     - 在 `calibration_data.attempts` 数组中 append 一条记录：
       - `{ media_id, is_correct, issues, advice_text, annotated_media_asset_id }`
     - `current_stage = "calibration"`

------

#### 5.2 按 AI 判定结果分支

##### ✅ 如果 `is_correct = true`：

- UI：直接展示 “完美部署”等文案（你的 `CALIB_SUCCESS`），
- 点击「完成布防」时，进入创建 trap 阶段（见第 6️⃣ 节）。

##### ❌ 如果 `is_correct = false`：

- UI：展示 AI 提示问题 + 改进建议（`CALIB_FAIL` 画面）
- 用户有两种选择：

1. **“调整后重拍”** → 回到 CALIB_CAM，重新拍 → 重复 16~~18~~判断
2. **“跳过，先用这样”** → 虽然失败，但用户觉得 OK：
   - 不再重试，直接继续到创建 trap（标记校准不完美）
   - 可在第 6 步创建 trap 时，把 `calibration_data` 的状态一起传入，
      后端可以设一个字段 `calibration_quality = "failed_but_accepted"` 之类。

> 无论成功还是“失败但跳过”，接下来都会调用 **同一个创建 trap 的 API**。

------

好，这一块就是“AI 帮你检查有没有真的放对”的核心接口。下面是 **`POST /v1/calibration-checks`** 的完整 spec，用和前面一致的 Stripe 风格来写。

------

# POST `/v1/calibration-checks`

对用户拍的**已布置好的陷阱近景照片**进行校准检查，判断：

- 这次布置是否**合格**（`is_correct`）
- 如果不合格，**具体有哪些问题**（距离墙太远、方向反了、诱饵放错等）
- 给出清晰的**调整建议文案**（`advice_text`）
- 可选地返回一张**标注问题点的图片**（`annotated_media_asset_id`）

该接口支持**多次重试**：用户可以“调整后重拍”，每次都调用一次校验。

------

## 请求概览（Summary）

- **HTTP 方法：** `POST`
- **URL：** `/v1/calibration-checks`
- **认证：** 必需，`Authorization: Bearer <token>`
- **幂等性：** 建议使用 `Idempotency-Key`，尤其是在网络不稳定时
- **返回：** 一个 `calibration_check` 对象

------

## 请求头（Request Headers）

| Header            | 必填 | 说明                                             |
| ----------------- | ---- | ------------------------------------------------ |
| `Authorization`   | 是   | `Bearer <access_token>`                          |
| `Content-Type`    | 否   | 推荐 `application/json`                          |
| `Idempotency-Key` | 否   | 可选，但建议在“同一次拍照请求可能重试”的场景使用 |
| `RatTrap-Version` | 否   | API 版本（如 `2024-11-22`）                      |

------

## 请求体参数（Request Body Parameters）

请求体为 JSON。

| 字段名             | 类型   | 必填 | 说明                                                         |
| ------------------ | ------ | ---- | ------------------------------------------------------------ |
| `setup_session_id` | string | 否   | 关联的布防会话 ID（`ss_xxx`）。建议传，方便写入 session。    |
| `media_asset_id`   | string | 是   | 本次校准照片的 `media_assets.id`（近景照片），如 `"ma_calib_1"`。 |
| `rodent_target`    | string | 否   | 目标鼠种：`"rat"` / `"mouse"` / `"unknown"`。                |
| `trap_type`        | string | 否   | 当前使用的陷阱类型：`"snap_trap"` / `"glue_board"` / `"cage_trap"` / `"electronic_trap"` / `"other"`。 |
| `bait_type`        | string | 否   | 当前使用的诱饵类型：`"peanut_butter"` / `"bacon"` / `"nuts"` / `"grain"` / ... |
| `location_context` | object | 否   | 上一阶段的位置推荐上下文，例如 `location_scout_data` 的子集。 |
| `options`          | object | 否   | 高级选项，如是否需要生成标注图、语言等。                     |

### `location_context` 示例结构（可选）

你可以直接把上一阶段 `location_scout_data` 中的核心内容传过来，方便 AI 对比：

```json
"location_context": {
  "recommended_zone_id": "zone_A",
  "recommended_description": "冰箱右侧沿墙，距墙角约 10cm，夹子垂直于墙。",
  "recommended_distance_to_wall_cm": 0
}
```

> 该字段是完全可选的，如果不传，AI 就仅凭当前照片来做判断。

### `options` 示例结构（可选）

```json
"options": {
  "language": "zh-CN",            // 返回文案语言，默认跟用户设置
  "need_annotated_image": true,   // 是否生成标注问题点的图片（默认 true）
  "tolerance": "normal"           // normal / strict：对“完美度”的容忍度
}
```

------

## 请求示例（Example Request）

```http
POST /v1/calibration-checks HTTP/1.1
Authorization: Bearer sk_test_xxx
Content-Type: application/json
Idempotency-Key: calib-check-4a5b8ff9-1b58-4402-b5e5-b2ecb0e5bb10
{
  "setup_session_id": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",
  "media_asset_id": "ma_calib_1PpTqQx2YwZv9kLb",
  "rodent_target": "rat",
  "trap_type": "snap_trap",
  "bait_type": "peanut_butter",
  "location_context": {
    "recommended_zone_id": "zone_A",
    "recommended_description": "冰箱右侧沿墙，距墙角约 10cm，夹子垂直于墙。",
    "recommended_distance_to_wall_cm": 0
  },
  "options": {
    "language": "zh-CN",
    "need_annotated_image": true,
    "tolerance": "normal"
  }
}
```

------

## 响应结构（Response）

成功时返回一个 `calibration_check` 对象。

### 顶层字段

| 字段名                     | 类型           | 说明                                                         |
| -------------------------- | -------------- | ------------------------------------------------------------ |
| `object`                   | string         | 恒为 `"calibration_check"`                                   |
| `id`                       | string         | 校准检查结果 ID，如 `calib_123`（可用于审计/重放）。         |
| `setup_session_id`         | string or null | 回显输入的 session ID。                                      |
| `media_asset_id`           | string         | 本次检查使用的原始图片 ID。                                  |
| `annotated_media_asset_id` | string or null | 标注问题点/确认 OK 的图片 `media_asset_id`，如果生成了的话。 |
| `rodent_target`            | string or null | 回显目标鼠种。                                               |
| `trap_type`                | string or null | 回显陷阱类型。                                               |
| `bait_type`                | string or null | 回显诱饵类型。                                               |
| `is_correct`               | boolean        | 布置是否合格。                                               |
| `confidence`               | number         | 0–1，AI 对 `is_correct` 判定的信心。                         |
| `placement_match_score`    | number or null | 0–1，与推荐位置/理想规范的匹配度。                           |
| `issues`                   | array          | 校准问题列表，若 `is_correct=true` 可为空数组。              |
| `advice_text`              | string         | 面向用户的综合建议文案（可以直接显示在 CALIB_FAIL / CALIB_SUCCESS 底部弹窗）。 |
| `recommended_actions`      | array          | 结构化的“下一步动作建议”（例如“向墙根推近 5cm”、“翻转陷阱”等）。 |
| `created`                  | integer        | 本次校准结果生成时间，Unix 时间戳（秒）。                    |

------

### `issues` 元素结构

每个 issue 表示一个具体的问题（比如“距离墙太远”、“角度不对”、“诱饵朝向错了”）。

| 字段名       | 类型           | 说明                                                         |
| ------------ | -------------- | ------------------------------------------------------------ |
| `code`       | string         | 机器可读问题码，如 `"too_far_from_wall"` / `"wrong_orientation"` / `"bait_position_suboptimal"` 等。 |
| `message`    | string         | 给开发者/日志用的简短描述。                                  |
| `severity`   | string         | `"info"` / `"warning"` / `"error"`，严重程度。               |
| `param`      | string or null | 可选，指向相关的“概念参数”，如 `"distance_to_wall"`。        |
| `metrics`    | object or null | 相关的定量信息，比如实际距离 vs 推荐距离。                   |
| `suggestion` | string         | 针对该问题的单条建议文案（例如“把陷阱再向墙根推近 5 厘米。”）。 |

`metrics` 例子：

```json
"metrics": {
  "distance_to_wall_cm": 8,
  "recommended_max_distance_cm": 1,
  "angle_deviation_deg": 25
}
```

------

### `recommended_actions` 元素结构（可选增强）

类似“可执行的 checklist”，你可以在前端展示为 bullet list。

| 字段名     | 类型   | 说明                                           |
| ---------- | ------ | ---------------------------------------------- |
| `code`     | string | 如 `"move_closer_to_wall"` / `"rotate_trap"`。 |
| `label`    | string | 短文案，如 `"把陷阱推到紧贴墙面"`。            |
| `details`  | string | 更详细的说明。                                 |
| `priority` | int    | 排序权重，1 为最高。                           |

------

## 成功响应示例

### 示例 1：布置不正确（CALIB_FAIL 场景）

```json
{
  "object": "calibration_check",
  "id": "calib_1SgF3zD8wQpR6NmK",
  "setup_session_id": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",

  "media_asset_id": "ma_calib_1PpTqQx2YwZv9kLb",
  "annotated_media_asset_id": "ma_calib_annotated_7YzXcP4v",

  "rodent_target": "rat",
  "trap_type": "snap_trap",
  "bait_type": "peanut_butter",

  "is_correct": false,
  "confidence": 0.94,
  "placement_match_score": 0.42,

  "issues": [
    {
      "code": "too_far_from_wall",
      "message": "The trap is placed too far away from the wall.",
      "severity": "error",
      "param": "distance_to_wall",
      "metrics": {
        "distance_to_wall_cm": 8,
        "recommended_max_distance_cm": 1
      },
      "suggestion": "将陷阱继续向墙根推进，尽量贴紧墙面摆放。"
    },
    {
      "code": "suboptimal_orientation",
      "message": "The bait is not oriented towards the wall.",
      "severity": "warning",
      "param": "orientation",
      "metrics": {
        "angle_deviation_deg": 20
      },
      "suggestion": "调整夹子方向，让诱饵一端朝向墙角或老鼠常出的缝隙。"
    }
  ],

  "advice_text": "AI 发现当前陷阱距离墙大约 8 公分，老鼠更喜欢紧贴墙根移动，这样的距离可能会被直接绕过。建议将陷阱推到紧贴墙根摆放，并把诱饵一端朝向墙角或缝隙，然后重新拍一张照片让我再次检查。",
  
  "recommended_actions": [
    {
      "code": "move_closer_to_wall",
      "label": "把陷阱推到紧贴墙面",
      "details": "将陷阱整体向墙根推进，直至夹子底座完全贴紧踢脚线。",
      "priority": 1
    },
    {
      "code": "rotate_trap",
      "label": "调整夹子方向",
      "details": "旋转陷阱，让诱饵一端朝向墙角或鼠洞方向。",
      "priority": 2
    }
  ],

  "created": 1764039200
}
```

在这个情况下：

- UI 可以进入 `CALIB_FAIL` 状态；
- 展示 `advice_text` + issues 列表（或只显示第一条建议）；
- 用户可以点击「调整后重拍」→ 再次拍照 → 再调用此接口。

------

### 示例 2：布置正确（CALIB_SUCCESS 场景）

```json
{
  "object": "calibration_check",
  "id": "calib_1SgF3zD8wQpR6NmK_ok",
  "setup_session_id": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",

  "media_asset_id": "ma_calib_2_ok",
  "annotated_media_asset_id": "ma_calib_2_ok_annotated",

  "rodent_target": "rat",
  "trap_type": "snap_trap",
  "bait_type": "peanut_butter",

  "is_correct": true,
  "confidence": 0.89,
  "placement_match_score": 0.91,

  "issues": [],

  "advice_text": "很好！陷阱已经紧贴墙根摆放，方向也正确，诱饵朝向墙角，这样可以最大化老鼠经过时被触发的概率。接下来只需要按 App 提醒定期检查和补充诱饵即可。",

  "recommended_actions": [
    {
      "code": "set_reminder",
      "label": "按提示定期检查陷阱",
      "details": "建议每 2–3 天查看一次陷阱，及时处理捕获和补充诱饵。",
      "priority": 1
    }
  ],

  "created": 1764039300
}
```

在这时：

- UI 可以显示“完美部署”绿条（`CALIB_SUCCESS`）；
- 用户点击「完成布防」后，前端去调用创建 trap 的接口（我们下一阶段定义的 `/v1/setup-sessions/{id}/create-trap`）。

------

## 错误（Errors）

统一的错误结构：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "some_code",
    "message": "Human readable message",
    "param": "field_name",
    "doc_url": "https://docs.rattrap.ai/errors#some_code"
  }
}
```

### 常见错误列表

| HTTP 状态码 | `error.type`            | `code`                    | 说明                                       |
| ----------- | ----------------------- | ------------------------- | ------------------------------------------ |
| `400`       | `invalid_request_error` | `media_asset_id_required` | 未提供 `media_asset_id`                    |
| `400`       | `invalid_request_error` | `invalid_media_asset`     | 指定的 `media_asset_id` 不存在或无访问权限 |
| `400`       | `invalid_request_error` | `invalid_rodent_target`   | `rodent_target` 非 `rat/mouse/unknown`     |
| `400`       | `invalid_request_error` | `invalid_trap_type`       | `trap_type` 不支持                         |
| `400`       | `invalid_request_error` | `invalid_options`         | `options` 某些字段值非法                   |
| `401`       | `authentication_error`  | `invalid_api_key`         | 未认证或 token 无效                        |
| `403`       | `authorization_error`   | `not_allowed`             | 无权访问该媒体或会话                       |
| `404`       | `invalid_request_error` | `setup_session_not_found` | 指定的 `setup_session_id` 不存在（若传入） |
| `429`       | `rate_limit_error`      | `too_many_requests`       | 调用过于频繁                               |
| `500`       | `api_error`             | `internal_error`          | 服务端内部错误                             |
| `502`       | `api_error`             | `ai_provider_unavailable` | 下游 AI 视觉服务不可用                     |

错误示例：缺少 `media_asset_id`：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "media_asset_id_required",
    "message": "media_asset_id is required to run a calibration check.",
    "param": "media_asset_id",
    "doc_url": "https://docs.rattrap.ai/errors#media_asset_id_required"
  }
}
```

------

## 幂等性说明（Idempotency）

- 推荐在以下场景使用 `Idempotency-Key`：
  - 用户在同一张校准照片提交时，网络重试；
  - 前端不小心连续发送两次相同的校准请求。

行为建议：

- 相同 `Idempotency-Key` + 完全一致的请求体：
   → 返回第一次校验的结果（避免重复向 AI 调用）。
- 相同 key 但请求体不同：
   → 返回 `409`，`error.type = "idempotency_error"`。

------

这样，校准阶段的 `POST /v1/calibration-checks` 就完整定义好了，可以完美对接你前端的：

- `CALIB_CAM` 拍照
- `CALIB_FAIL`：展示具体 issues + 建议
- `CALIB_SUCCESS`：展示“完美部署”

下一步如果你想，我们可以继续把最后一步：

> ```
> POST /v1/setup-sessions/{ss_id}/create-trap
> ```

也按 Stripe 风格写完整 spec，把 **session → trap 实体 + trap_events** 的落地逻辑封装成一个清晰的 RPC。



### 6️⃣ 创建 Trap 实体 + 记录事件 + 回到 Dashboard

当用户在 “校准成功” 或 “失败但选择跳过” 画面点击「完成布防」：

#### 6.1 从 session 创建 trap 实体

1. `POST /v1/setup-sessions/{ss_id}/create-trap`

- 后端行为：
  1. 读取该 session 的：
     - `identification_data.rodent_target`
     - `strategy_data.trap_detected_type / bait_type`
     - `location_scout_data`（可用于填充 `location_desc`）
     - `calibration_data`（setup 成功情况）
     - `calibration_media_id` & `location_media_id`
  2. 在 `traps` 表插入新记录：
     - `trap_type` / `bait_type` / `rodent_target`
     - `deployment_media_id`（可选：用 `calibration_media_id` 或 `location_media_id`）
     - `last_check_media_id` = `calibration_media_id`
     - `last_checked_at = now()`
     - `status = "active"`
  3. 触发器自动计算 `next_check_at`（用 `trap_type` & `bait_type`）
  4. 在 `trap_events` 里插入一条事件：
     - `event_type = "maintenance"` 或 `"deployment"`
     - `details.action = "deployment_completed"`
  5. 更新 `setup_sessions`：
     - `created_trap_id = trap_id`
     - `is_completed = true`
     - `current_stage = "completed"`
- 返回：
  - 新建 `trap` 对象 `{ id: "trap_xxx", object: "trap", ... }`

> 至此，“新陷阱”在数据层已经存在。

------

#### 6.2 Dashboard 刷新显示新陷阱

1. `GET /v1/traps?status=active&limit=...`
    或：

- `GET /v1/trap-dashboard`（如果你用视图）

前端用它来刷新 Dashboard 列表，展示刚创建的 Trap 卡片：

- `name` / `location_desc`
- `trap_type` / `bait_type`
- `next_check_at` → 显示为「X 天后检查」
- `stats_catches = 0`

------

下面把第 6 步相关的两个接口都用 Stripe 风格完整梳理出来：

- `POST /v1/setup-sessions/{id}/create-trap`（**从会话创建 trap 实体 + 写事件 + 更新 session**）
- `GET /v1/traps`（**在 Dashboard 拉取 active traps 列表**）

------

# 1️⃣ POST `/v1/setup-sessions/{id}/create-trap`

从一个已经走完布防流程的 **setup session** 中，创建一条真正的 **Trap 实体**，并写入初始事件，更新会话状态。

通常在前端：

- CALIB_SUCCESS（校准成功）点击「完成布防」
- 或 CALIB_FAIL（用户选择“跳过，先用这样”）点击「完成布防」

时调用。

------

## 概览（Summary）

- **HTTP 方法：** `POST`
- **URL：** `/v1/setup-sessions/{id}/create-trap`
- **语义：** 以 RPC 形式“提交会话”，生成一条 `trap`
- **认证：** 必需，`Authorization: Bearer <token>`
- **幂等性：** 强烈建议使用 `Idempotency-Key`
- **返回：** 一个 `trap` 对象

------

## 路径参数（Path Parameters）

| 参数名 | 类型   | 说明                                                        |
| ------ | ------ | ----------------------------------------------------------- |
| `id`   | string | 要提交的 setup session ID，例如 `ss_1Qy8u8CZ7aQp98Xb5WJtR3` |

------

## 请求头（Request Headers）

| Header            | 必填 | 说明                                  |
| ----------------- | ---- | ------------------------------------- |
| `Authorization`   | 是   | `Bearer <access_token>`               |
| `Content-Type`    | 否   | 推荐 `application/json`               |
| `Idempotency-Key` | 否   | 强烈建议，用来防止重复创建同一个 trap |
| `RatTrap-Version` | 否   | API 版本（如 `2024-11-22`）           |

------

## 请求体参数（Request Body Parameters）

> 大部分信息从 `setup_sessions` 派生，因此请求体非常轻量。
>  所有字段都是 **可选**，主要用于覆盖/补充从 session 中推断出的信息。

| 字段名                 | 类型   | 必填 | 说明                                                         |
| ---------------------- | ------ | ---- | ------------------------------------------------------------ |
| `name`                 | string | 否   | Trap 在 UI 中显示的名称。若不传，后端可根据位置自动生成，如 `"厨房 - 冰箱右侧"`。 |
| `location_desc`        | string | 否   | 位置描述。若不传，后端可从 `location_scout_data.placement_text` 或 zones 的描述中提炼。 |
| `metadata`             | object | 否   | 附加元数据（字符串键值对），用于分析或内部标记。             |
| `status`               | string | 否   | 初始状态，默认 `"active"`。仅高级用例需要修改。可选：`"active"` / `"warning"` / `"inactive"`。 |
| `calibration_override` | object | 否   | （可选）覆盖/精简传入校准结果，用于记住“失败但用户接受”的状态。也可以完全依赖 session 中的 `calibration_data`。 |

### `calibration_override` 建议结构（可选）

```json
"calibration_override": {
  "quality": "failed_but_accepted"  // "passed" / "failed_but_accepted"
}
```

> 通常情况下你可以 **不传** `calibration_override`，
>  后端可以直接从 `setup_sessions.calibration_data` 内部推断出最后一次尝试是否通过，并仅作为分析字段记录在 `trap_events.details` 或 `trap.metadata` 中。

------

## 后端内部行为（Server-side Behaviour）

调用成功时，后端会做：

1. **读取 setup_session：**
   - `identification_data` → `rodent_target`
   - `strategy_data` → `trap_type` / `bait_type` / bait 来源等
   - `location_scout_data` → 推荐位置描述，可用于 `location_desc`
   - `location_media_id` → 房间图
   - `calibration_data` + `calibration_media_id` → 最后一次布置检查
   - 如果已有 `created_trap_id`，则视为已经创建过（见幂等性逻辑）
2. **在 `traps` 表中插入一条记录：**
   - `trap_type`
   - `bait_type`
   - `rodent_target`
   - `status`（默认 `"active"`，可被请求体覆盖）
   - `name` / `location_desc`（来自请求体或 session 衍生）
   - `deployment_media_id`（通常可以用 `calibration_media_id`；如果不存在，则退化为 `location_media_id`）
   - `last_check_media_id = calibration_media_id`（若存在）
   - `last_checked_at = now()`
   - `stats_catches = 0`
   - `stats_misses = 0`
   - `next_check_at` 会通过 DB 触发器 `auto_update_next_check_at()` 根据 `trap_type` + `bait_type` 自动计算。
3. **在 `trap_events` 新增一条 “部署完成” 事件：**
   - `event_type = "maintenance"` 或 `"deployment"`（可按你的事件枚举实际选择）
   - `details` 包含：
     - `action: "deployment_completed"`
     - `setup_session_id`
     - `calibration_summary`（比如 `"passed"` / `"failed_but_accepted"` 等）
   - `media_id = calibration_media_id`（如有）
4. **更新 setup_session：**
   - `created_trap_id = trap.id`
   - `is_completed = true`
   - `current_stage = "completed"`

------

## 响应（Response）

成功时返回新创建的 `trap` 对象。

### `trap` 对象字段（对外视图）

| 字段名                | 类型            | 说明                                                         |
| --------------------- | --------------- | ------------------------------------------------------------ |
| `id`                  | string          | Trap ID，前缀推荐为 `trap_`，例如 `trap_1RasJr2...`          |
| `object`              | string          | 恒为 `"trap"`                                                |
| `name`                | string          | UI 中显示名称                                                |
| `location_desc`       | string or null  | 位置描述                                                     |
| `trap_type`           | string or null  | `snap_trap` / `glue_board` / `cage_trap` / `electronic_trap` / `other` |
| `bait_type`           | string or null  | `peanut_butter` / `bacon` / ...                              |
| `rodent_target`       | string or null  | `rat` / `mouse` / `unknown`                                  |
| `status`              | string          | `active` / `warning` / `triggered_caught` / ...              |
| `deployment_media_id` | string or null  | 布防基准图的 media ID                                        |
| `last_check_media_id` | string or null  | 最近一次检查图的 media ID                                    |
| `last_checked_at`     | integer or null | Unix 时间戳（秒）                                            |
| `next_check_at`       | integer or null | Unix 时间戳（秒），由规则引擎计算                            |
| `stats_catches`       | integer         | 初始为 `0`                                                   |
| `stats_misses`        | integer         | 初始为 `0`                                                   |
| `metadata`            | object          | 用户自定义元数据（若存储）                                   |
| `created`             | integer         | 创建时间（秒）                                               |
| `updated`             | integer         | 最近更新时间（秒）                                           |

> 注意：这里的字段是 API 视图，不必与 DB 字段一一对应，但语义上保持一致。

------

### 成功响应示例

```json
{
  "id": "trap_1RasJr2f9hQe8KmN",
  "object": "trap",

  "name": "厨房 - 冰箱右侧",
  "location_desc": "冰箱右侧沿墙根，距墙角约 10cm，夹子垂直于墙，诱饵朝向墙角。",

  "trap_type": "snap_trap",
  "bait_type": "peanut_butter",
  "rodent_target": "rat",
  "status": "active",

  "deployment_media_id": "ma_calib_2_ok",
  "last_check_media_id": "ma_calib_2_ok",
  "last_checked_at": 1764039300,
  "next_check_at": 1764298500,

  "stats_catches": 0,
  "stats_misses": 0,

  "metadata": {
    "created_from_session": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",
    "calibration_quality": "passed"
  },

  "created": 1764039300,
  "updated": 1764039300
}
```

------

## 幂等性（Idempotency）

> 非常关键：防止重复创建 trap。

推荐策略：

- 前端在用户点击「完成布防」时生成一个 UUID：
  - `Idempotency-Key: trap-create-<setup_session_id>-<uuid>`
- 如果同一个 `setup_session_id` 之前已经调用成功且 `created_trap_id` 已存在：
  - 服务端应**返回同一条 trap** 对象，而不是再插一条新 trap。
- 如果使用了相同的 `Idempotency-Key`，但请求体不同：
  - 返回 `409`，`error.type = "idempotency_error"`。

------

## 错误（Errors）

错误响应统一格式：

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "some_code",
    "message": "Human readable message",
    "param": "field_name",
    "doc_url": "https://docs.rattrap.ai/errors#some_code"
  }
}
```

常见错误：

| HTTP 状态码 | `type`                  | `code`                    | 说明                                                         |
| ----------- | ----------------------- | ------------------------- | ------------------------------------------------------------ |
| `400`       | `invalid_request_error` | `setup_session_not_ready` | 该 session 还没走完必要阶段（缺少 rodent/trap/bait 等）      |
| `400`       | `invalid_request_error` | `trap_already_created`    | 该 session 已经有 `created_trap_id`，不能再次创建（在无幂等头时保护） |
| `404`       | `invalid_request_error` | `setup_session_not_found` | 指定 ID 的 session 不存在或不归当前用户所有                  |
| `401`       | `authentication_error`  | `invalid_api_key`         | 未认证                                                       |
| `403`       | `authorization_error`   | `not_allowed`             | 无权访问该 session                                           |
| `409`       | `idempotency_error`     | `idempotency_key_in_use`  | 同一 Idempotency-Key 请求体不一致                            |
| `500`       | `api_error`             | `internal_error`          | 服务器内部错误                                               |

------

# 2️⃣ GET `/v1/traps`（Dashboard 列表）

创建完 trap 以后，Dashboard 需要**刷新列表**，展示所有 active traps（或根据过滤条件），这可以通过一个标准的列表接口完成。

你可以有两种实现：

- 直接列出 `traps`：`GET /v1/traps`
- 或者对 `trap_dashboard` 视图做一层封装：`GET /v1/trap-dashboard`

我们先定义一个通用的、Stripe 风格的列表接口：**`GET /v1/traps`**。

------

## 概览（Summary）

- **HTTP 方法：** `GET`
- **URL：** `/v1/traps`
- **语义：** 列出当前用户/租户下的 traps（支持状态筛选、分页）
- **返回：** `list` 对象，`data` 内为多个 `trap` 对象

------

## 查询参数（Query Parameters）

| 参数名           | 类型   | 必填 | 说明                                                         |
| ---------------- | ------ | ---- | ------------------------------------------------------------ |
| `status`         | string | 否   | 按状态过滤：如 `"active"` / `"inactive"` / `"warning"`。可以支持逗号分隔多值：`status=active,warning`。 |
| `limit`          | int    | 否   | 每页数量，默认 10，最大 100。                                |
| `starting_after` | string | 否   | 用于向后分页的游标（上一页最后一个 trap 的 ID）。            |
| `ending_before`  | string | 否   | 用于向前分页的游标。                                         |
| `tenant_id`      | string | 否   | （可选）指定某个 tenant 下的 traps，仅在多租户后台工具中用；普通用户一般不用传。 |

------

## 响应（Response）

响应采用 Stripe 样式的 list envelope：

| 字段名     | 类型   | 说明                        |
| ---------- | ------ | --------------------------- |
| `object`   | string | `"list"`                    |
| `url`      | string | 本次请求的 URL（不含 host） |
| `has_more` | bool   | 是否还有下一页              |
| `data`     | array  | `trap` 对象数组             |

每个 `trap` 对象结构与上面 `create-trap` 返回的 `trap` 对象一致。

------

### 示例请求

```http
GET /v1/traps?status=active&limit=10 HTTP/1.1
Authorization: Bearer sk_test_xxx
```

------

### 示例响应

```json
{
  "object": "list",
  "url": "/v1/traps?status=active&limit=10",
  "has_more": false,
  "data": [
    {
      "id": "trap_1RasJr2f9hQe8KmN",
      "object": "trap",

      "name": "厨房 - 冰箱右侧",
      "location_desc": "冰箱右侧沿墙根，距墙角约 10cm，夹子垂直于墙，诱饵朝向墙角。",

      "trap_type": "snap_trap",
      "bait_type": "peanut_butter",
      "rodent_target": "rat",
      "status": "active",

      "deployment_media_id": "ma_calib_2_ok",
      "last_check_media_id": "ma_calib_2_ok",
      "last_checked_at": 1764039300,
      "next_check_at": 1764298500,

      "stats_catches": 3,
      "stats_misses": 1,

      "metadata": {
        "created_from_session": "ss_1Qy8u8CZ7aQp98Xb5WJtR3",
        "calibration_quality": "passed"
      },

      "created": 1764039300,
      "updated": 1764300000
    }
  ]
}
```

> Dashboard 刷新时，只需要：
>
> - 调用 `GET /v1/traps?status=active&limit=20`
> - 用返回的 `trap` 列表渲染你的卡片（名称/位置/倒计时/统计等）

------

