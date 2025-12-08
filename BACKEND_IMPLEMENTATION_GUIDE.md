# 后端实现指南：Setup Session 完成时自动创建 Trap

> **文档目的**: 后端开发人员实现参考  
> **创建日期**: 2024-12-08  
> **更新日期**: 2024-12-08  
> **关联文档**: [BACKEND_API_CHANGES_FOR_SETUP_COMPLETION.md](./BACKEND_API_CHANGES_FOR_SETUP_COMPLETION.md)

---

## 一、变更概述

| 项目 | 内容 |
|------|------|
| **需要修改的 API** | `POST /setup-sessions/{id}` (Update Setup Session) |
| **需要废弃的 API** | `POST /create-trap-from-session` (标记为 Deprecated) |
| **变更类型** | 新增完成逻辑 |
| **核心功能** | 校准阶段完成时，**必须**同时创建 Trap 和 deployment Event |

---

## 二、新增请求字段

### trap_name

```json
{
  "calibration_data": {
    "media_asset_id": "ma_calib_xxx",
    "calibration_check_id": "cc_xxx",
    "is_correct": true,
    "skipped": false
  },
  "trap_name": "厨房陷阱1"  // ← 新增字段
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `trap_name` | string | **必填** | 校准阶段完成时必须提供，用于创建 Trap |

---

## 三、触发条件

当以下条件**同时满足**时，触发创建 Trap 逻辑：

```
1. session.current_stage == 'calibration'
2. request.calibration_data 存在
3. request.trap_name 存在且非空（trim 后 length > 0）
```

**注意**：`trap_name` 是必填字段，如果缺失则返回 `400 VALIDATION_ERROR`。

---

## 四、事务操作（原子性）

```sql
BEGIN;

-- 1. 幂等性检查
SELECT created_trap_id FROM setup_sessions WHERE id = $session_id;
-- 如果 created_trap_id 不为空，直接返回，不重复创建

-- 2. 创建 Trap
INSERT INTO traps (...) VALUES (...) RETURNING id;

-- 3. 更新 Session
UPDATE setup_sessions SET
  created_trap_id = $trap_id,
  current_stage = 'completed',
  calibration_data = $calibration_data,
  updated = NOW()
WHERE id = $session_id;

-- 4. 创建 deployment Event
INSERT INTO trap_events (...) VALUES (...);

COMMIT;
```

---

## 五、Trap 字段数据来源

| Trap 字段 | 数据来源 | 说明 |
|-----------|---------|------|
| `id` | 系统生成 | `trap_{timestamp}_{random}` |
| `name` | `request.trap_name` | 请求传入 |
| `trap_type` | `session.strategy_data.selected_trap_type` | 策略阶段 |
| `bait_type` | `session.strategy_data.selected_bait_type` | 策略阶段 |
| `rodent_target` | `session.rodent_target` | 识别阶段 |
| `location_desc` | `session.location_scout_data.location_description` | 位置阶段 |
| `deployment_media_id` | `request.calibration_data.media_asset_id` | 请求传入 |
| `last_check_media_id` | `request.calibration_data.media_asset_id` | 同上 |
| `status` | 固定值 | `"active"` |
| `last_checked_at` | 当前时间 | `NOW()` |
| `next_check_at` | 计算值 | `NOW() + recommended_interval_hours`（默认 24h）|
| `stats_catches` | 固定值 | `0` |
| `stats_misses` | 固定值 | `0` |
| `setup_session_id` | `session.id` | **新增列** |

### next_check_at 计算

```sql
next_check_at = NOW() + INTERVAL (
  COALESCE(
    (session.strategy_data->>'recommended_interval_hours')::int,
    24  -- 默认 24 小时
  )
) HOUR
```

---

## 六、deployment Event 字段

| Event 字段 | 数据来源 |
|-----------|---------|
| `id` | 系统生成 |
| `trap_id` | 新创建的 Trap ID |
| `event_type` | `"deployment"` |
| `media_id` | `calibration_data.media_asset_id` |
| `details` | 见下方 |
| `recorded_at` | Unix timestamp (秒) |
| `created` | Unix timestamp (秒) |

### details 结构

```json
{
  "setup_session_id": "ss_xxx",
  "trap_name": "厨房陷阱1",
  "location_desc": "厨房 - 沿墙角放置",
  "trap_type": "snap_trap",
  "bait_type": "peanut_butter",
  "rodent_target": "rat",
  "calibration_passed": true,
  "calibration_skipped": false,
  "notes": "初始部署"
}
```

---

## 七、数据库变更

```sql
-- 1. 新增列
ALTER TABLE traps 
ADD COLUMN IF NOT EXISTS setup_session_id VARCHAR(255);

-- 2. 唯一约束（幂等性保障）
ALTER TABLE traps 
ADD CONSTRAINT unique_user_setup_session_trap 
UNIQUE (user_id, setup_session_id);

-- 3. 索引
CREATE INDEX IF NOT EXISTS idx_traps_setup_session_id 
ON traps(setup_session_id);
```

---

## 八、数据完整性检查

在创建 Trap 前，验证以下字段存在：

| 检查项 | 来源 |
|--------|------|
| 目标鼠种 | `session.rodent_target` |
| 陷阱类型 | `session.strategy_data.selected_trap_type` |
| 诱饵类型 | `session.strategy_data.selected_bait_type` |
| 位置描述 | `session.location_scout_data.location_description` |
| 校准照片 | `request.calibration_data.media_asset_id` |
| 陷阱名称 | `request.trap_name` |

任何字段缺失时返回：

```json
{
  "error": {
    "type": "validation_error",
    "code": "INCOMPLETE_SESSION",
    "message": "Cannot complete setup: missing required data",
    "details": {
      "missing_fields": ["strategy_data.selected_trap_type"]
    }
  }
}
```

---

## 九、幂等性

- 检查 `session.created_trap_id` 是否已有值
- 如果有值，直接返回当前 Session，不重复创建 Trap
- 保证重复请求不会产生重复数据

---

## 十、错误码

| HTTP 状态码 | Error Code | 场景 |
|------------|------------|------|
| 400 | `VALIDATION_ERROR` | trap_name 为空字符串 |
| 400 | `INVALID_STAGE` | 当前阶段不是 calibration |
| 400 | `INCOMPLETE_SESSION` | 前置数据不完整 |
| 404 | `SESSION_NOT_FOUND` | 会话不存在 |
| 500 | `DATABASE_ERROR` | 数据库操作失败 |

---

## 十一、实现检查清单

- [ ] 新增 `trap_name` 参数处理
- [ ] 实现触发条件判断
- [ ] 实现幂等性检查（检查 created_trap_id）
- [ ] 实现数据完整性检查
- [ ] 使用 `selected_trap_type` 和 `selected_bait_type` 字段名
- [ ] 使用 `recommended_interval_hours` 计算 next_check_at（默认 24h）
- [ ] 事务中创建 Trap + 更新 Session + 创建 Event
- [ ] 添加 `traps.setup_session_id` 列和唯一约束
- [ ] 错误处理和日志

---

## 十二、测试用例

### 正常流程
```bash
POST /setup-sessions/ss_xxx
{
  "calibration_data": { "media_asset_id": "ma_xxx", "is_correct": true },
  "trap_name": "厨房陷阱1"
}
# 预期: 200, created_trap_id 有值
```

### 幂等性测试
```bash
# 重复发送相同请求
# 预期: 200, 不创建新 Trap, 返回已存在数据
```

### 缺少 trap_name
```bash
POST /setup-sessions/ss_xxx
{ "calibration_data": { "media_asset_id": "ma_xxx", "is_correct": true } }
# 预期: 400, VALIDATION_ERROR, "trap_name is required when completing setup"
```

---

## 十三、废弃 API 说明

`POST /create-trap-from-session` 接口已标记为 **Deprecated**，后端无需修改该接口，但需要：

1. 在日志中记录该接口的调用（方便追踪迁移进度）
2. 该接口仍可正常工作，保持向后兼容

---

**详细规范请参考**: [BACKEND_API_CHANGES_FOR_SETUP_COMPLETION.md](./BACKEND_API_CHANGES_FOR_SETUP_COMPLETION.md)
