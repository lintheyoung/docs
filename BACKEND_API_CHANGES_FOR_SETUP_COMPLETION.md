# 后端 API 修改需求文档

> **文档目的**: 供后端开发同学参考，实现 Setup Session 完成时自动创建 Trap 和 deployment Event 的功能  
> **创建日期**: 2024-12-08  
> **更新日期**: 2024-12-08  
> **优先级**: 高  
> **前置依赖**: 现有的 setup-sessions、traps、trap-events API

---

## 一、需求概述

### 1.1 业务背景

当用户完成布防会话（Setup Session）的最后一个阶段（校准 calibration）时，系统需要：

1. **创建 Trap（陷阱）实体** - 持久化用户设置的陷阱信息
2. **更新 Setup Session** - 关联新创建的 trap_id，标记会话完成
3. **创建 Trap Event (deployment)** - 记录首次部署事件，作为陷阱生命周期的起点

### 1.2 核心要求

| 要求 | 说明 |
|------|------|
| **原子性** | 三个操作必须在同一数据库事务中完成 |
| **幂等性** | 重复请求不会创建重复的 Trap |
| **数据完整性** | 使用前序阶段收集的数据填充 Trap 字段 |

---

## 二、API 变更清单

### 2.1 变更概述

| API | 端点 | 变更类型 | 说明 |
|-----|------|---------|------|
| **Update Setup Session** | `POST /setup-sessions/{id}` | **修改** | 校准完成时必须同时创建 Trap |
| **Create Trap From Session** | `POST /create-trap-from-session` | **废弃** | 标记为 Deprecated，保持向后兼容 |
| Create Trap | `POST /traps` | 无变更 | 由上述 API 内部调用 |
| Create Trap Event | `POST /trap-events` | 无变更 | 由上述 API 内部调用 |

### 2.2 废弃说明

`POST /create-trap-from-session` 接口已标记为 **Deprecated**：
- 该接口仍可正常工作，保持向后兼容
- 新代码应使用 `POST /setup-sessions/{id}` 并传入 `trap_name`
- 建议在日志中记录该接口调用，方便追踪迁移进度

---

## 三、Update Setup Session 完成逻辑

### 3.1 端点

```
POST /setup-sessions/{session_id}
```

### 3.2 请求头

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

### 3.3 请求体 - 完成阶段

```json
{
  "calibration_data": {
    "media_asset_id": "ma_calib_1234567890",
    "calibration_check_id": "cc_1234567890",
    "is_correct": true,
    "skipped": false
  },
  "trap_name": "厨房陷阱1"
}
```

### 3.4 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `calibration_data` | object | ✅ | 校准阶段数据 |
| `calibration_data.media_asset_id` | string | ✅ | 校准照片 ID（用作 deployment_media_id） |
| `calibration_data.calibration_check_id` | string | ❌ | 校准检查 API 返回的 ID |
| `calibration_data.is_correct` | boolean | ✅ | 是否通过校准 |
| `calibration_data.skipped` | boolean | ❌ | 是否跳过校准（用户选择"先用这样"） |
| `trap_name` | string | ✅ | 陷阱名称（**必填**） |

> **注意**: `trap_name` 是**新增字段**，在提交 `calibration_data` 时**必须**同时提供。其他阶段（identification、strategy、location）更新时不需要此字段。

### 3.5 触发完成逻辑的条件

当以下条件**同时满足**时，触发完成逻辑：

```
1. session.current_stage == 'calibration'
2. request.calibration_data 存在
3. request.trap_name 存在且非空（去除首尾空格后）
```

**注意**：`trap_name` 是必填字段，如果缺失则返回 `400 VALIDATION_ERROR`。

### 3.6 成功响应 (200 OK)

```json
{
  "id": "ss_1702012345678_000001",
  "object": "setup_session",
  "current_stage": "completed",
  "created_trap_id": "trap_1702012345678",
  "rodent_target": "rat",
  "identification_data": {
    "media_asset_id": "ma_ident_xxx",
    "confirmed_rodent_target": "rat"
  },
  "strategy_data": {
    "selected_trap_type": "snap",
    "selected_bait_type": "peanut_butter",
    "recommended_interval_hours": 24
  },
  "location_scout_data": {
    "media_asset_id": "ma_loc_xxx",
    "room_type": "kitchen",
    "location_description": "厨房 - 沿墙角放置"
  },
  "calibration_data": {
    "media_asset_id": "ma_calib_xxx",
    "calibration_check_id": "cc_xxx",
    "is_correct": true,
    "skipped": false
  },
  "metadata": {
    "source": "mobile_app"
  },
  "created": 1702012345,
  "updated": 1702012999
}
```

### 3.7 幂等响应 (200 OK)

如果 `session.created_trap_id` 已有值，直接返回当前 Session，**不重复创建** Trap：

```json
{
  "id": "ss_1702012345678_000001",
  "object": "setup_session",
  "current_stage": "completed",
  "created_trap_id": "trap_1702012345678",
  // ... 其他字段保持不变
}
```

### 3.8 错误响应

**400 Bad Request - 参数验证失败**

```json
{
  "error": {
    "type": "validation_error",
    "code": "VALIDATION_ERROR",
    "message": "trap_name is required when completing setup",
    "param": "trap_name"
  }
}
```

**400 Bad Request - 阶段不正确**

```json
{
  "error": {
    "type": "validation_error",
    "code": "INVALID_STAGE",
    "message": "Cannot complete setup: current stage is 'location', expected 'calibration'"
  }
}
```

**400 Bad Request - 数据不完整**

```json
{
  "error": {
    "type": "validation_error",
    "code": "INCOMPLETE_SESSION",
    "message": "Cannot complete setup: missing required data",
    "details": {
      "missing_fields": [
        "strategy_data.selected_trap_type",
        "location_scout_data.location_description"
      ]
    }
  }
}
```

**404 Not Found - 会话不存在**

```json
{
  "error": {
    "type": "not_found_error",
    "code": "SESSION_NOT_FOUND",
    "message": "Setup session not found"
  }
}
```

**500 Internal Server Error - 数据库错误**

```json
{
  "error": {
    "type": "internal_error",
    "code": "DATABASE_ERROR",
    "message": "Failed to complete setup session"
  }
}
```

---

## 四、Trap 实体创建规范

### 4.1 字段填充规则（方式 B）

| Trap 字段 | 数据来源 | 计算规则 |
|-----------|---------|---------|
| `id` | 系统生成 | `trap_{timestamp}_{random}` |
| `object` | 固定值 | `"trap"` |
| `user_id` | 当前用户 | 从认证 token 获取 |
| `name` | `request.trap_name` | 直接使用 |
| `location_desc` | `session.location_scout_data.location_description` | 直接使用 |
| `trap_type` | `session.strategy_data.selected_trap_type` | 直接使用 |
| `bait_type` | `session.strategy_data.selected_bait_type` | 直接使用 |
| `rodent_target` | `session.rodent_target` | 直接使用 |
| `status` | 固定值 | `"active"` |
| `deployment_media_id` | `request.calibration_data.media_asset_id` | 直接使用 |
| `last_check_media_id` | `request.calibration_data.media_asset_id` | 与 deployment 相同 |
| `last_checked_at` | 当前时间 | `NOW()` |
| `next_check_at` | 计算值 | 见下方 |
| `stats_catches` | 固定值 | `0` |
| `stats_misses` | 固定值 | `0` |
| `metadata` | 组合 | 继承 session.metadata + setup_session_id |
| `setup_session_id` | `session.id` | **新增列** |
| `created` | 当前时间 | `NOW()` |
| `updated` | 当前时间 | `NOW()` |

### 4.2 next_check_at 计算规则

**方式 B（新逻辑）**：使用 `recommended_interval_hours`

```sql
-- interval_hours 来自 strategy_data.recommended_interval_hours
-- 如果没有该字段，默认使用 24 小时

next_check_at = NOW() + INTERVAL (
  COALESCE(
    (session.strategy_data->>'recommended_interval_hours')::int,
    24
  )
) HOUR
```

**方式 A（现有逻辑）**：固定 7 天

```sql
-- 现有 create-trap-from-session 的逻辑保持不变
next_check_at = NOW() + INTERVAL '7 days'
```

### 4.3 两种方式的 next_check_at 对比

| 方式 | 计算规则 | 默认值 | 说明 |
|------|---------|--------|------|
| 方式 A (create-trap-from-session) | 固定值 | 7 天 | 现有逻辑，保持不变 |
| 方式 B (update-setup-session) | recommended_interval_hours | 24 小时 | 新逻辑，更灵活 |

### 4.4 Trap 创建 SQL 示例（方式 B）

```sql
INSERT INTO traps (
  id,
  object,
  user_id,
  name,
  location_desc,
  trap_type,
  bait_type,
  rodent_target,
  status,
  deployment_media_id,
  last_check_media_id,
  last_checked_at,
  next_check_at,
  stats_catches,
  stats_misses,
  metadata,
  setup_session_id,
  created,
  updated
) VALUES (
  'trap_1702012345678',
  'trap',
  'user_xxx',
  '厨房陷阱1',
  '厨房 - 沿墙角放置',
  'snap',
  'peanut_butter',
  'rat',
  'active',
  'ma_calib_xxx',
  'ma_calib_xxx',
  NOW(),
  NOW() + INTERVAL '24 hours',  -- 使用 recommended_interval_hours
  0,
  0,
  '{"source": "mobile_app", "setup_session_id": "ss_xxx"}'::jsonb,
  'ss_xxx',  -- 新增列
  NOW(),
  NOW()
);
```

---

## 五、Trap Event (deployment) 创建规范

### 5.1 字段填充规则

| Event 字段 | 数据来源 | 说明 |
|-----------|---------|------|
| `id` | 系统生成 | `event_{timestamp}_{random}` |
| `object` | 固定值 | `"trap_event"` |
| `trap_id` | 新创建的 Trap | trap.id |
| `event_type` | 固定值 | `"deployment"` |
| `media_id` | `calibration_data.media_asset_id` | 部署照片 |
| `details` | 组合对象 | 见下方结构 |
| `recorded_at` | 当前时间戳 | Unix timestamp (秒) |
| `created` | 当前时间戳 | Unix timestamp (秒) |

### 5.2 details 字段结构

```json
{
  "setup_session_id": "ss_1702012345678_000001",
  "trap_name": "厨房陷阱1",
  "location_desc": "厨房 - 沿墙角放置",
  "trap_type": "snap",
  "bait_type": "peanut_butter",
  "rodent_target": "rat",
  "calibration_passed": true,
  "calibration_skipped": false,
  "notes": "初始部署"
}
```

### 5.3 Event 创建 SQL 示例

```sql
INSERT INTO trap_events (
  id,
  object,
  trap_id,
  event_type,
  media_id,
  details,
  recorded_at,
  created
) VALUES (
  'event_1702012345678',
  'trap_event',
  'trap_1702012345678',
  'deployment',
  'ma_calib_xxx',
  '{
    "setup_session_id": "ss_xxx",
    "trap_name": "厨房陷阱1",
    "location_desc": "厨房 - 沿墙角放置",
    "trap_type": "snap",
    "bait_type": "peanut_butter",
    "rodent_target": "rat",
    "calibration_passed": true,
    "calibration_skipped": false,
    "notes": "初始部署"
  }'::jsonb,
  EXTRACT(EPOCH FROM NOW())::bigint,
  EXTRACT(EPOCH FROM NOW())::bigint
);
```

---

## 六、数据库变更

### 6.1 traps 表新增列

```sql
-- 新增 setup_session_id 列
ALTER TABLE traps 
ADD COLUMN IF NOT EXISTS setup_session_id VARCHAR(255);

-- 为 setup_session_id 创建索引
CREATE INDEX IF NOT EXISTS idx_traps_setup_session_id 
ON traps(setup_session_id);
```

### 6.2 唯一约束（幂等性保障）

```sql
-- 确保每个 setup_session 只能通过方式 B 创建一个 trap
-- 注意：只约束 setup_session_id 不为空的情况
ALTER TABLE traps 
ADD CONSTRAINT unique_user_setup_session_trap 
UNIQUE (user_id, setup_session_id);

-- 注意：方式 A 创建的 Trap，setup_session_id 存在 metadata 中，不受此约束影响
```

### 6.3 外键约束（可选）

```sql
-- setup_sessions.created_trap_id 引用 traps.id
ALTER TABLE setup_sessions
ADD CONSTRAINT fk_setup_sessions_created_trap
FOREIGN KEY (created_trap_id) REFERENCES traps(id)
ON DELETE SET NULL;

-- trap_events.trap_id 引用 traps.id
ALTER TABLE trap_events
ADD CONSTRAINT fk_trap_events_trap
FOREIGN KEY (trap_id) REFERENCES traps(id)
ON DELETE CASCADE;
```

---

## 七、事务处理逻辑

### 7.1 事务流程

```sql
BEGIN;

-- 1. 幂等性检查
SELECT created_trap_id FROM setup_sessions WHERE id = $session_id;
-- 如果 created_trap_id 不为空，COMMIT 并返回已存在的数据

-- 2. 创建 Trap
INSERT INTO traps (...) VALUES (...) RETURNING id;

-- 3. 更新 Setup Session
UPDATE setup_sessions 
SET 
  created_trap_id = $trap_id,
  current_stage = 'completed',
  calibration_data = $calibration_data,
  updated = NOW()
WHERE id = $session_id;

-- 4. 创建 deployment Event
INSERT INTO trap_events (...) VALUES (...);

COMMIT;
```

### 7.2 错误处理

```sql
-- 如果任何步骤失败
ROLLBACK;
-- 返回错误响应
```

### 7.3 存储过程实现

```sql
-- 创建存储过程以确保事务原子性
CREATE OR REPLACE FUNCTION complete_setup_session(
  p_session_id VARCHAR,
  p_user_id VARCHAR,
  p_trap_name VARCHAR,
  p_calibration_data JSONB
) RETURNS JSONB AS $$
DECLARE
  v_session RECORD;
  v_trap_id VARCHAR;
  v_event_id VARCHAR;
  v_now TIMESTAMP := NOW();
  v_now_epoch BIGINT := EXTRACT(EPOCH FROM NOW())::bigint;
  v_interval_hours INT;
  v_next_check_at TIMESTAMP;
BEGIN
  -- 1. 查询并锁定 Session
  SELECT * INTO v_session
  FROM setup_sessions
  WHERE id = p_session_id AND user_id = p_user_id
  FOR UPDATE;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'SESSION_NOT_FOUND';
  END IF;
  
  -- 2. 阶段检查
  IF v_session.current_stage != 'calibration' THEN
    RAISE EXCEPTION 'INVALID_STAGE: %', v_session.current_stage;
  END IF;
  
  -- 3. 幂等性检查
  IF v_session.created_trap_id IS NOT NULL THEN
    RETURN to_jsonb(v_session);
  END IF;
  
  -- 4. 计算检查间隔（使用 recommended_interval_hours）
  v_interval_hours := COALESCE(
    (v_session.strategy_data->>'recommended_interval_hours')::int,
    24  -- 默认 24 小时
  );
  v_next_check_at := v_now + (v_interval_hours || ' hours')::interval;
  
  -- 5. 生成 IDs
  v_trap_id := 'trap_' || EXTRACT(EPOCH FROM v_now)::bigint || '_' || floor(random() * 1000000)::int;
  v_event_id := 'event_' || EXTRACT(EPOCH FROM v_now)::bigint || '_' || floor(random() * 1000000)::int;
  
  -- 6. 创建 Trap（使用 selected_trap_type 和 selected_bait_type）
  INSERT INTO traps (
    id, object, user_id, name, location_desc, trap_type, bait_type,
    rodent_target, status, deployment_media_id, last_check_media_id,
    last_checked_at, next_check_at, stats_catches, stats_misses,
    metadata, setup_session_id, created, updated
  ) VALUES (
    v_trap_id,
    'trap',
    p_user_id,
    p_trap_name,
    v_session.location_scout_data->>'location_description',
    v_session.strategy_data->>'selected_trap_type',
    v_session.strategy_data->>'selected_bait_type',
    v_session.rodent_target,
    'active',
    p_calibration_data->>'media_asset_id',
    p_calibration_data->>'media_asset_id',
    v_now,
    v_next_check_at,
    0,
    0,
    jsonb_build_object(
      'source', COALESCE(v_session.metadata->>'source', 'mobile_app'),
      'setup_session_id', p_session_id
    ),
    p_session_id,
    v_now,
    v_now
  );
  
  -- 7. 更新 Session
  UPDATE setup_sessions SET
    created_trap_id = v_trap_id,
    current_stage = 'completed',
    calibration_data = p_calibration_data,
    updated = v_now_epoch
  WHERE id = p_session_id;
  
  -- 8. 创建 deployment Event
  INSERT INTO trap_events (
    id, object, trap_id, event_type, media_id, details, recorded_at, created
  ) VALUES (
    v_event_id,
    'trap_event',
    v_trap_id,
    'deployment',
    p_calibration_data->>'media_asset_id',
    jsonb_build_object(
      'setup_session_id', p_session_id,
      'trap_name', p_trap_name,
      'location_desc', v_session.location_scout_data->>'location_description',
      'trap_type', v_session.strategy_data->>'selected_trap_type',
      'bait_type', v_session.strategy_data->>'selected_bait_type',
      'rodent_target', v_session.rodent_target,
      'calibration_passed', COALESCE((p_calibration_data->>'is_correct')::boolean, false),
      'calibration_skipped', COALESCE((p_calibration_data->>'skipped')::boolean, false),
      'notes', '初始部署'
    ),
    v_now_epoch,
    v_now_epoch
  );
  
  -- 9. 返回更新后的 Session
  SELECT to_jsonb(s.*) INTO v_session
  FROM setup_sessions s
  WHERE s.id = p_session_id;
  
  RETURN v_session;
  
EXCEPTION
  WHEN OTHERS THEN
    RAISE;
END;
$$ LANGUAGE plpgsql;
```

---

## 八、数据验证规则

### 8.1 完成前的数据完整性检查

在执行方式 B 完成逻辑前，验证 Session 包含所有必要数据：

| 检查项 | 来源字段 | 验证规则 |
|--------|---------|---------|
| 目标鼠种 | `session.rodent_target` | 非空 |
| 陷阱类型 | `session.strategy_data.selected_trap_type` | 非空 |
| 诱饵类型 | `session.strategy_data.selected_bait_type` | 非空 |
| 位置描述 | `session.location_scout_data.location_description` | 非空 |
| 校准照片 | `request.calibration_data.media_asset_id` | 非空 |
| 陷阱名称 | `request.trap_name` | 非空，去除首尾空格后长度 > 0 |

### 8.2 验证失败的错误响应

```json
{
  "error": {
    "type": "validation_error",
    "code": "INCOMPLETE_SESSION",
    "message": "Cannot complete setup: missing required data",
    "details": {
      "missing_fields": [
        "strategy_data.selected_trap_type",
        "location_scout_data.location_description"
      ]
    }
  }
}
```

---

## 九、Session 各阶段数据结构参考

### 9.1 identification_data

```json
{
  "media_asset_id": "ma_ident_xxx",
  "ai_result": {
    "rodent_type": "rat",
    "confidence": 0.92,
    "evidence_found": ["droppings", "gnaw_marks"]
  },
  "confirmed_rodent_target": "rat"
}
```

### 9.2 strategy_data

```json
{
  "selected_trap_type": "snap",
  "selected_bait_type": "peanut_butter",
  "trap_recommendation_id": "tr_xxx",
  "bait_recommendation_id": "br_xxx",
  "recommended_interval_hours": 24
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `selected_trap_type` | string | ✅ | 用户选择的陷阱类型 |
| `selected_bait_type` | string | ✅ | 用户选择的诱饵类型 |
| `trap_recommendation_id` | string | ❌ | 陷阱推荐 API 返回的 ID |
| `bait_recommendation_id` | string | ❌ | 诱饵推荐 API 返回的 ID |
| `recommended_interval_hours` | number | ❌ | 推荐检查间隔（小时），默认 24 |

### 9.3 location_scout_data

```json
{
  "media_asset_id": "ma_loc_xxx",
  "location_analysis_id": "la_xxx",
  "room_type": "kitchen",
  "selected_recommendation_id": "rec_001",
  "selected_location_title": "沿墙角放置",
  "location_description": "厨房 - 沿墙角放置"
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `media_asset_id` | string | ✅ | 房间照片 ID |
| `location_analysis_id` | string | ❌ | 位置分析 API 返回的 ID |
| `room_type` | string | ❌ | 房间类型 |
| `selected_recommendation_id` | string | ❌ | 用户选择的建议 ID |
| `selected_location_title` | string | ❌ | 选择的位置标题 |
| `location_description` | string | ✅ | 完整位置描述（用于 Trap.location_desc） |

### 9.4 calibration_data

```json
{
  "media_asset_id": "ma_calib_xxx",
  "calibration_check_id": "cc_xxx",
  "is_correct": true,
  "skipped": false,
  "attempts": 1
}
```

---

## 十、测试用例

### 10.1 正常完成流程（方式 B）

```bash
# 请求
curl -X POST "https://xxx.supabase.co/functions/v1/setup-sessions/ss_xxx" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "calibration_data": {
      "media_asset_id": "ma_calib_123",
      "is_correct": true
    },
    "trap_name": "厨房陷阱1"
  }'

# 预期响应 (200)
{
  "id": "ss_xxx",
  "current_stage": "completed",
  "created_trap_id": "trap_xxx",
  ...
}
```

### 10.2 只提交 calibration_data（不触发方式 B）

```bash
# 请求 - 没有 trap_name
curl -X POST "https://xxx.supabase.co/functions/v1/setup-sessions/ss_xxx" \
  -H "Authorization: Bearer {token}" \
  -d '{"calibration_data": {"media_asset_id": "ma_xxx", "is_correct": true}}'

# 预期响应 (200)
# stage 变为 completed，但 created_trap_id 为 null
{
  "id": "ss_xxx",
  "current_stage": "completed",
  "created_trap_id": null,  // 没有创建 Trap
  ...
}

# 前端之后可以使用方式 A (create-trap-from-session) 创建 Trap
```

### 10.3 幂等性测试 - 重复请求

```bash
# 第一次请求 - 成功创建
# 第二次请求 - 相同内容
# 预期: 返回 200，不创建新 Trap，返回已存在的数据
```

### 10.4 缺少 trap_name 但想使用方式 B

```bash
# 如果前端想使用方式 B 但忘记传 trap_name
# 当前设计：不会报错，只是不触发方式 B

# 如果需要报错提示，可以在前端处理
```

### 10.5 阶段不正确

```bash
# 当 session.current_stage = 'location' 时发送完成请求

# 预期响应 (400)
{
  "error": {
    "code": "INVALID_STAGE",
    "message": "Cannot complete setup: current stage is 'location', expected 'calibration'"
  }
}
```

### 10.6 前置数据不完整

```bash
# 当 strategy_data.selected_trap_type 为空时

# 预期响应 (400)
{
  "error": {
    "code": "INCOMPLETE_SESSION",
    "message": "Cannot complete setup: missing strategy_data.selected_trap_type"
  }
}
```

---

## 十一、实现检查清单

### 后端开发

- [ ] **保留** `create-trap-from-session` 接口（方式 A）不变
- [ ] **修改** `setup-sessions` 接口，添加方式 B 完成逻辑
- [ ] 添加 `trap_name` 参数处理（新增字段）
- [ ] 实现幂等性检查逻辑（检查 created_trap_id）
- [ ] 实现数据完整性检查（验证必填字段）
- [ ] 使用 `selected_trap_type` 和 `selected_bait_type` 字段
- [ ] 使用 `recommended_interval_hours` 计算 next_check_at（默认 24 小时）
- [ ] 创建 `complete_setup_session` 存储过程（或在 Function 中实现事务）
- [ ] 添加错误处理和日志

### 数据库

- [ ] 添加 `traps.setup_session_id` 列
- [ ] 添加唯一约束 `unique_user_setup_session_trap`
- [ ] 创建索引 `idx_traps_setup_session_id`
- [ ] 创建存储过程（如果使用）

### 测试

- [ ] 单元测试：方式 B 正常完成流程
- [ ] 单元测试：方式 A 仍然正常工作
- [ ] 单元测试：幂等性（重复请求）
- [ ] 单元测试：各种错误场景
- [ ] 集成测试：完整的 Setup Session 流程

---

## 十二、问答 FAQ

### Q1: 方式 A 和方式 B 可以混用吗？

A: 可以。如果用户完成 calibration 阶段时没有传 `trap_name`，Session 会变成 `completed` 但没有创建 Trap。之后仍然可以使用方式 A (`create-trap-from-session`) 来创建 Trap。

### Q2: 为什么方式 B 的 next_check_at 用 24 小时，方式 A 用 7 天？

A: 方式 B 使用 `recommended_interval_hours`，这是 AI 根据诱饵类型推荐的检查间隔。方式 A 是现有逻辑，保持 7 天不变以确保向后兼容。

### Q3: 字段名是 `trap_type` 还是 `selected_trap_type`？

A: 在 `strategy_data` 中使用 **`selected_trap_type`** 和 **`selected_bait_type`**。在 `traps` 表中使用 `trap_type` 和 `bait_type`（没有 selected_ 前缀）。

### Q4: 如何区分方式 A 和方式 B 创建的 Trap？

A: 
- 方式 A：`setup_session_id` 存在 `metadata.source_session_id` 中，`traps.setup_session_id` 列为空
- 方式 B：`traps.setup_session_id` 列有值

### Q5: 幂等性检查是基于什么？

A: 基于 `session.created_trap_id` 字段。如果该字段已有值，说明已经通过方式 B 创建过 Trap，直接返回不重复创建。

### Q6: 如果 recommended_interval_hours 没有值怎么办？

A: 使用默认值 **24 小时**。

### Q7: trap_name 有长度限制吗？

A: 建议限制在 100 字符以内，可以在数据库层面做 `VARCHAR(100)` 约束。

---

## 十三、联系方式

如有疑问，请联系：

- **前端负责人**: [填写]
- **产品负责人**: [填写]
- **相关文档**: 
  - [SETUP_SESSION_API_IMPLEMENTATION.md](./SETUP_SESSION_API_IMPLEMENTATION.md)
  - [SETUP_COMPLETION_TRAP_CREATION.md](./SETUP_COMPLETION_TRAP_CREATION.md)
