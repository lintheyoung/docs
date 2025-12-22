# PestGG IoT System Architecture Documentation

> Complete technical reference for the AWS IoT + Supabase integrated system

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technical Architecture](#2-technical-architecture)
3. [Device Lifecycle](#3-device-lifecycle)
4. [Factory Stage - Device Manufacturing](#4-factory-stage---device-manufacturing)
5. [User Stage - Device Binding & Activation](#5-user-stage---device-binding--activation)
6. [Operation Stage - Device Control & Telemetry](#6-operation-stage---device-control--telemetry)
7. [Device Sharing & Transfer](#7-device-sharing--transfer)
8. [Database Schema](#8-database-schema)
9. [Authentication & Permission System](#9-authentication--permission-system)
10. [API Reference](#10-api-reference)
11. [AWS CDK Infrastructure](#11-aws-cdk-infrastructure)
12. [Developer Quick Start](#12-developer-quick-start)

---

## 1. System Overview

### 1.1 System Purpose

PestGG is a smart pest control IoT system that enables:
- Factory batch device manufacturing and registration
- User device binding via activation codes
- Real-time device control via web interface
- Telemetry data collection and monitoring
- Multi-tenant device management with sharing/transfer capabilities

### 1.2 Core Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React + TypeScript | User Portal web application |
| **Backend API** | Supabase Edge Functions (Deno) | Business logic and API endpoints |
| **Database** | PostgreSQL 15 (Supabase) | Data persistence with RLS |
| **IoT Core** | AWS IoT Core | MQTT broker and device management |
| **Compute** | AWS Lambda (Node.js 20) | Device control and shadow projection |
| **Infrastructure** | AWS CDK (TypeScript) | Infrastructure as Code |
| **Auth** | Supabase Auth + AWS Cognito | User auth + IoT credentials |

### 1.3 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER PORTAL (React)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Device Mgmt  │  │ Trap Control │  │  Telemetry   │  │  Settings    │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼─────────────────┼─────────────────┼─────────────────┼────────────┘
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE EDGE FUNCTIONS                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ manufacturing-* │  │ user-device-*   │  │ device-share    │             │
│  │ (Factory APIs)  │  │ (Control APIs)  │  │ device-transfer │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
└───────────┼────────────────────┼────────────────────┼───────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE POSTGRESQL                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   devices   │  │   traps     │  │ telemetry   │  │  commands   │        │
│  │   (IoT)     │  │  (Business) │  │   _last     │  │  (History)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        AWS IoT Core                                  │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │   │ MQTT Broker │  │   Device    │  │  IoT Rules  │                 │   │
│  │   │  (WebSocket)│  │   Shadow    │  │  (Trigger)  │                 │   │
│  │   └─────────────┘  └──────┬──────┘  └──────┬──────┘                 │   │
│  └───────────────────────────┼────────────────┼─────────────────────────┘   │
│                              │                │                             │
│  ┌───────────────────────────┼────────────────┼─────────────────────────┐   │
│  │                     AWS Lambda              │                         │   │
│  │   ┌─────────────┐  ┌──────┴──────┐  ┌──────┴──────┐                  │   │
│  │   │ Authorizer  │  │  Control    │  │  Projector  │                  │   │
│  │   │   Lambda    │  │   Lambda    │  │   Lambda    │                  │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHYSICAL DEVICES                                  │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│   │    Gateway      │    │   Child Device  │    │   Child Device  │        │
│   │  (ESP32/Linux)  │◄──►│    (Sensor)     │    │    (Trap)       │        │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technical Architecture

### 2.1 Data Flow Overview

The system implements a **dual-path architecture** for optimal performance:

#### **Real-time Path (WebSocket/MQTT)**
- **Control Flow**: Web UI → MQTT/WebSocket → AWS IoT Core → Shadow Update → Device
- **Telemetry Flow**: Device → Shadow Update → AWS IoT Core → MQTT/WebSocket → Web UI
- **Latency**: <100ms
- **Use Case**: Real-time device control and monitoring

#### **Persistence Path (Event Sourcing)**
- **Data Flow**: Shadow Update → IoT Rule → Projector Lambda → Supabase
- **Latency**: 1-3 seconds
- **Use Case**: Historical data, analytics, audit logs

#### **Key Design Principle**
Web applications connect directly to AWS IoT Core via MQTT over WebSocket for real-time communication, while Projector Lambda asynchronously persists all state changes to Supabase for historical queries and business logic.

### 2.2 Device Shadow Architecture

AWS IoT Device Shadow is the core mechanism for device state management:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS IoT Device Shadow                        │
├─────────────────────────────────────────────────────────────────┤
│  {                                                              │
│    "state": {                                                   │
│      "desired": {        // Set by cloud/web                    │
│        "mode": "auto",                                          │
│        "trapState": "armed",                                    │
│        "sensitivity": 3,                                        │
│        "reqId": "abc123"  // Command tracking ID                │
│      },                                                         │
│      "reported": {       // Set by device                       │
│        "mode": "auto",                                          │
│        "trapState": "armed",                                    │
│        "sensitivity": 3,                                        │
│        "lastAckedReqId": "abc123",  // ACK for command          │
│        "batteryLevel": 85,                                      │
│        "timestamp": 1702900000                                  │
│      },                                                         │
│      "delta": {}         // Pending changes                     │
│    },                                                           │
│    "metadata": { ... },                                         │
│    "version": 42                                                │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Shadow Types

| Shadow Type | Topic Pattern | Use Case |
|-------------|---------------|----------|
| **Classic Shadow** | `$aws/things/{thingName}/shadow/...` | Gateway devices |
| **Named Shadow** | `$aws/things/{thingName}/shadow/name/{shadowName}/...` | Child devices under gateway |

### 2.4 Gateway-Child Device Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    AWS IoT Core                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                 Thing: "gateway:001"                          │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │ │
│  │  │  Classic Shadow │  │ Named Shadow:   │  │Named Shadow: │  │ │
│  │  │  (Gateway Self) │  │ "child:trap01"  │  │"child:sensor"│  │ │
│  │  └─────────────────┘  └─────────────────┘  └──────────────┘  │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│                     Physical Gateway Device                        │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │   Gateway (ESP32/Linux with MQTT Client)                      │ │
│  │   - Manages Classic Shadow for its own state                  │ │
│  │   - Manages Named Shadows for child devices                   │ │
│  │   - Communicates with children via BLE/Zigbee/LoRa            │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                              │                                     │
│           ┌──────────────────┼──────────────────┐                  │
│           ▼                  ▼                  ▼                  │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐          │
│   │ Child Device │   │ Child Device │   │ Child Device │          │
│   │   (Trap)     │   │  (Sensor)    │   │  (Camera)    │          │
│   └──────────────┘   └──────────────┘   └──────────────┘          │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Device Lifecycle

### 3.1 Complete Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEVICE LIFECYCLE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   FACTORY   │    │    USER     │    │  OPERATION  │    │  TRANSFER   │  │
│  │    STAGE    │───►│    STAGE    │───►│    STAGE    │───►│    STAGE    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        │                  │                  │                  │          │
│        ▼                  ▼                  ▼                  ▼          │
│  ┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐   │
│  │ Create    │      │ Bind with │      │ Control   │      │ Transfer  │   │
│  │ IoT Thing │      │ Activation│      │ Device    │      │ Ownership │   │
│  │           │      │ Code      │      │           │      │           │   │
│  │ Generate  │      │           │      │ Monitor   │      │ Share     │   │
│  │ Certs     │      │ Create    │      │ Telemetry │      │ Access    │   │
│  │           │      │ Ownership │      │           │      │           │   │
│  │ Create    │      │           │      │ Manage    │      │           │   │
│  │ Activation│      │ Setup     │      │ Traps     │      │           │   │
│  │ Code      │      │ Session   │      │           │      │           │   │
│  └───────────┘      └───────────┘      └───────────┘      └───────────┘   │
│                                                                             │
│  Device Status: registered → pending → active → (transferred)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Status Transitions

| From Status | To Status | Trigger | API |
|-------------|-----------|---------|-----|
| (none) | `registered` | Factory creates device | `manufacturing-create-devices` |
| `registered` | `pending` | User binds device | `user-device-bind` |
| `pending` | `active` | Device completes setup | `setup-sessions` |
| `active` | `active` | Ownership transfer | `device-transfer` |
| Any | `offline` | Connection timeout | Projector Lambda |

---

## 4. Factory Stage - Device Manufacturing

### 4.1 Batch Device Creation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FACTORY: BATCH DEVICE CREATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Admin User                  Edge Function              AWS IoT Core        │
│      │                           │                           │              │
│      │  POST /manufacturing-     │                           │              │
│      │  create-devices           │                           │              │
│      │  {                        │                           │              │
│      │    model: "RT-Pro-4G",    │                           │              │
│      │    count: 100,            │                           │              │
│      │    prefix: "RT4G"         │                           │              │
│      │  }                        │                           │              │
│      │──────────────────────────►│                           │              │
│      │                           │                           │              │
│      │                           │  1. Verify Admin Role     │              │
│      │                           │  ────────────────────     │              │
│      │                           │                           │              │
│      │                           │  2. Create Batch Record   │              │
│      │                           │  ────────────────────     │              │
│      │                           │                           │              │
│      │                           │  3. For each device:      │              │
│      │                           │  ────────────────────     │              │
│      │                           │                           │              │
│      │                           │  3a. CreateThing          │              │
│      │                           │─────────────────────────►│              │
│      │                           │         Thing Created     │              │
│      │                           │◄─────────────────────────│              │
│      │                           │                           │              │
│      │                           │  3b. CreateKeysAndCert    │              │
│      │                           │      (ECC P-256)          │              │
│      │                           │─────────────────────────►│              │
│      │                           │    Cert + Private Key     │              │
│      │                           │◄─────────────────────────│              │
│      │                           │                           │              │
│      │                           │  3c. AttachPolicy         │              │
│      │                           │─────────────────────────►│              │
│      │                           │                           │              │
│      │                           │  3d. AttachThingPrincipal │              │
│      │                           │─────────────────────────►│              │
│      │                           │                           │              │
│      │                           │  3e. GetIoTEndpoint       │              │
│      │                           │─────────────────────────►│              │
│      │                           │         Endpoint URL      │              │
│      │                           │◄─────────────────────────│              │
│      │                           │                           │              │
│      │                           │  4. Generate Activation   │              │
│      │                           │     Code (MODEL-XXXXXXXX) │              │
│      │                           │  ────────────────────     │              │
│      │                           │                           │              │
│      │                           │  5. Insert into devices   │              │
│      │                           │     table (with metadata) │              │
│      │                           │  ────────────────────     │              │
│      │                           │                           │              │
│      │                           │  6. Insert into           │              │
│      │                           │     device_activation_    │              │
│      │                           │     codes table           │              │
│      │                           │  ────────────────────     │              │
│      │                           │                           │              │
│      │   Response with device    │                           │              │
│      │   credentials (one-time)  │                           │              │
│      │◄──────────────────────────│                           │              │
│      │                           │                           │              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Key Files

| File | Purpose |
|------|---------|
| `supabase/functions/manufacturing-create-devices/index.ts` | Batch device creation |
| `supabase/functions/manufacturing-batches/index.ts` | Query batch records |
| `supabase/functions/manufacturing-activation-codes/index.ts` | Export activation codes (CSV) |
| `supabase/functions/_shared/aws-iot-client.ts` | AWS IoT API wrapper |

### 4.3 Certificate Generation

The system uses ECC P-256 certificates via CSR:

```typescript
// Certificate generation flow (aws-iot-client.ts)
async createCertificateFromCsr(csr: string) {
  // 1. Generate ECC P-256 key pair
  const keyPair = await crypto.subtle.generateKey(
    { name: 'ECDSA', namedCurve: 'P-256' },
    true,
    ['sign', 'verify']
  );

  // 2. Create Certificate Signing Request
  const csr = await this.generateCSR(keyPair, thingName);

  // 3. Submit CSR to AWS IoT
  const response = await this.callAWSIoT('CreateCertificateFromCsr', {
    certificateSigningRequest: csr,
    setAsActive: true
  });

  // 4. Return certificate + private key
  return {
    certificateArn: response.certificateArn,
    certificateId: response.certificateId,
    certificatePem: response.certificatePem,
    privateKey: privateKeyPem  // ONLY returned here, never stored
  };
}
```

### 4.4 Activation Code Format

```
Format: {MODEL}-{8-HEX-CHARS}
Example: RT4G-A3F2B1C9

Generation:
const activationCode = `${model.toUpperCase()}-${crypto.randomUUID().slice(0,8).toUpperCase()}`;
```

### 4.5 Device Metadata Storage

```json
{
  "thing_name": "RT4G:001",
  "type": "gateway",
  "model": "RT-Pro-4G",
  "status": "registered",
  "metadata": {
    "certificateArn": "arn:aws:iot:...:cert/...",
    "certificateId": "abc123...",
    "policyName": "IoTDevicePolicy",
    "iotEndpoint": "xxxx.iot.ap-southeast-1.amazonaws.com"
  }
}
```

> **Security Note**: Private keys are ONLY returned in the API response during device creation. They are never persisted in the database.

---

## 5. User Stage - Device Binding & Activation

### 5.1 Device Binding Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      USER: DEVICE BINDING                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User App               Edge Function              Database                 │
│      │                       │                        │                     │
│      │  POST /user-device-   │                        │                     │
│      │  bind                 │                        │                     │
│      │  {                    │                        │                     │
│      │    activation_code:   │                        │                     │
│      │    "RT4G-A3F2B1C9"    │                        │                     │
│      │  }                    │                        │                     │
│      │──────────────────────►│                        │                     │
│      │                       │                        │                     │
│      │                       │  1. Verify JWT         │                     │
│      │                       │  ─────────────         │                     │
│      │                       │                        │                     │
│      │                       │  2. Query activation   │                     │
│      │                       │     code               │                     │
│      │                       │───────────────────────►│                     │
│      │                       │    Code details        │                     │
│      │                       │◄───────────────────────│                     │
│      │                       │                        │                     │
│      │                       │  3. Verify code not    │                     │
│      │                       │     used               │                     │
│      │                       │  ─────────────         │                     │
│      │                       │                        │                     │
│      │                       │  4. Verify device not  │                     │
│      │                       │     bound to another   │                     │
│      │                       │     user               │                     │
│      │                       │───────────────────────►│                     │
│      │                       │    No owner found      │                     │
│      │                       │◄───────────────────────│                     │
│      │                       │                        │                     │
│      │                       │  5. Get user's         │                     │
│      │                       │     tenant_id          │                     │
│      │                       │───────────────────────►│                     │
│      │                       │    Tenant ID           │                     │
│      │                       │◄───────────────────────│                     │
│      │                       │                        │                     │
│      │                       │  6. Create device_     │                     │
│      │                       │     owners record      │                     │
│      │                       │───────────────────────►│                     │
│      │                       │                        │                     │
│      │                       │  7. Mark activation    │                     │
│      │                       │     code as used       │                     │
│      │                       │───────────────────────►│                     │
│      │                       │                        │                     │
│      │                       │  8. Update device      │                     │
│      │                       │     status to          │                     │
│      │                       │     'pending'          │                     │
│      │                       │───────────────────────►│                     │
│      │                       │                        │                     │
│      │   Success response    │                        │                     │
│      │◄──────────────────────│                        │                     │
│      │                       │                        │                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 AWS Credentials Acquisition

Before users can receive real-time MQTT updates, they need AWS temporary credentials:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   USER: GET AWS CREDENTIALS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User App          Edge Function       Cognito          IoT Core            │
│      │                  │                 │                │                │
│      │  POST /get-aws-  │                 │                │                │
│      │  credentials     │                 │                │                │
│      │  Authorization:  │                 │                │                │
│      │  Bearer <jwt>    │                 │                │                │
│      │─────────────────►│                 │                │                │
│      │                  │                 │                │                │
│      │                  │  1. Check cache │                │                │
│      │                  │  ─────────────  │                │                │
│      │                  │                 │                │                │
│      │                  │  [Cache Miss]   │                │                │
│      │                  │                 │                │                │
│      │                  │  2. GetId       │                │                │
│      │                  │────────────────►│                │                │
│      │                  │   Identity ID   │                │                │
│      │                  │◄────────────────│                │                │
│      │                  │                 │                │                │
│      │                  │  3. GetCredentialsForIdentity   │                │
│      │                  │────────────────►│                │                │
│      │                  │   Temp Creds    │                │                │
│      │                  │◄────────────────│                │                │
│      │                  │                 │                │                │
│      │                  │  4. AttachPolicy (first time)   │                │
│      │                  │─────────────────────────────────►│               │
│      │                  │                 │                │                │
│      │                  │  5. Save to cache               │                │
│      │                  │  ─────────────  │                │                │
│      │                  │                 │                │                │
│      │   Credentials    │                 │                │                │
│      │◄─────────────────│                 │                │                │
│      │                  │                 │                │                │
│      │                  │  [Cache Hit - subsequent calls] │                │
│      │                  │  Return cached  │                │                │
│      │                  │  credentials    │                │                │
│      │                  │  (< 100ms)      │                │                │
│      │                  │                 │                │                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Credential Response Format

```json
{
  "identityId": "ap-southeast-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "credentials": {
    "AccessKeyId": "ASIA...",
    "SecretKey": "...",
    "SessionToken": "...",
    "Expiration": 1702900000
  },
  "policyAttached": true,
  "policyName": "PestGG-User-MQTT-Policy",
  "fromCache": false
}
```

### 5.4 Setup Session Flow

After binding, devices go through a setup session:

```
Device Status: pending → active

Setup Session States:
1. awaiting_placement  - User selecting trap location
2. scanning            - Device scanning environment
3. calibrating         - Device calibrating sensors
4. awaiting_confirm    - Waiting for user confirmation
5. completed           - Setup complete, device active
```

---

## 6. Operation Stage - Device Control & Telemetry

### 6.1 Control Command Flow (Web → Device)

The system supports **two control paths**:

#### **Path 1: Direct MQTT Control (Recommended for Real-time)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              OPERATION: DIRECT MQTT CONTROL (Real-time)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Web UI          MQTT Client         AWS IoT Core         Device            │
│      │                │                    │                 │              │
│      │  1. User clicks│                    │                 │              │
│      │     "Turn On"  │                    │                 │              │
│      │  ──────────────│                    │                 │              │
│      │                │                    │                 │              │
│      │  2. Call       │                    │                 │              │
│      │     mqttClient.│                    │                 │              │
│      │     publishControl()                │                 │              │
│      │───────────────►│                    │                 │              │
│      │                │                    │                 │              │
│      │                │  3. Generate reqId │                 │              │
│      │                │     (for ACK)      │                 │              │
│      │                │  ──────────────    │                 │              │
│      │                │                    │                 │              │
│      │                │  4. PUBLISH        │                 │              │
│      │                │     Topic: $aws/things/{thing}/     │              │
│      │                │            shadow/update            │              │
│      │                │     Payload: {                      │              │
│      │                │       state: {                      │              │
│      │                │         desired: {                  │              │
│      │                │           power: "on",              │              │
│      │                │           req_id: "req_xxx"         │              │
│      │                │         }                           │              │
│      │                │       }                             │              │
│      │                │     }                               │              │
│      │                │───────────────────────────────────►│              │
│      │                │                    │                 │              │
│      │                │                    │  5. Update Shadow              │
│      │                │                    │     state.desired              │
│      │                │                    │  ──────────────│              │
│      │                │                    │                 │              │
│      │                │                    │  6. Publish delta              │
│      │                │                    │────────────────►│              │
│      │                │                    │                 │              │
│      │                │                    │                 │  7. Device   │
│      │                │                    │                 │     processes│
│      │                │                    │                 │     command  │
│      │                │                    │                 │  ────────────│
│      │                │                    │                 │              │
│      │                │                    │  8. Device updates             │
│      │                │                    │     state.reported             │
│      │                │                    │     (includes req_id as ACK)   │
│      │                │                    │◄────────────────│              │
│      │                │                    │                 │              │
│      │                │  9. Receive Shadow │                 │              │
│      │                │     update/documents                │              │
│      │◄───────────────│◄───────────────────│                 │              │
│      │                │                    │                 │              │
│      │  10. Match reqId                    │                 │              │
│      │      → Show "Command Executed"      │                 │              │
│      │  ──────────────                     │                 │              │
│      │                                                                       │
│  Latency: ~50-100ms (direct MQTT)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### **Path 2: HTTP API Control (Legacy, for server-side operations)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              OPERATION: HTTP API CONTROL (Server-side)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Client         Edge Function      Lambda         IoT Core      Device      │
│      │                │               │               │            │        │
│      │  POST /user-   │               │               │            │        │
│      │  device-control│               │               │            │        │
│      │───────────────►│               │               │            │        │
│      │                │               │               │            │        │
│      │                │  Verify JWT   │               │            │        │
│      │                │  + Permission │               │            │        │
│      │                │  ─────────────│               │            │        │
│      │                │               │               │            │        │
│      │                │  Call Control │               │            │        │
│      │                │  Lambda       │               │            │        │
│      │                │──────────────►│               │            │        │
│      │                │               │               │            │        │
│      │                │               │  Update Shadow│            │        │
│      │                │               │──────────────►│            │        │
│      │                │               │               │            │        │
│      │                │               │               │  Notify    │        │
│      │                │               │               │  Device    │        │
│      │                │               │               │───────────►│        │
│      │                │               │               │            │        │
│      │   {reqId}      │               │               │            │        │
│      │◄───────────────│◄──────────────│               │            │        │
│      │                                                              │        │
│  Latency: ~200-500ms (HTTP + Lambda cold start)                             │
│  Use Case: Scheduled tasks, batch operations, server-side automation        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Shadow Update Structure

```json
// Control Lambda updates desired state
{
  "state": {
    "desired": {
      "mode": "auto",
      "trapState": "armed",
      "reqId": "cmd_1702900000_abc123"
    }
  }
}

// Device receives delta and updates reported state
{
  "state": {
    "reported": {
      "mode": "auto",
      "trapState": "armed",
      "lastAckedReqId": "cmd_1702900000_abc123"  // ACK
    }
  }
}
```

### 6.3 Telemetry Flow (Device → Web)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   OPERATION: TELEMETRY FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Device         IoT Core          IoT Rule         Projector     Supabase   │
│      │              │                 │               │             │       │
│      │  Update      │                 │               │             │       │
│      │  Shadow      │                 │               │             │       │
│      │  reported    │                 │               │             │       │
│      │─────────────►│                 │               │             │       │
│      │              │                 │               │             │       │
│      │              │  Shadow Update  │               │             │       │
│      │              │  Document       │               │             │       │
│      │              │  Published      │               │             │       │
│      │              │────────────────►│               │             │       │
│      │              │                 │               │             │       │
│      │              │                 │  Trigger      │             │       │
│      │              │                 │  Lambda       │             │       │
│      │              │                 │──────────────►│             │       │
│      │              │                 │               │             │       │
│      │              │                 │               │  1. Parse   │       │
│      │              │                 │               │     topic   │       │
│      │              │                 │               │  ───────────│       │
│      │              │                 │               │             │       │
│      │              │                 │               │  2. Archive │       │
│      │              │                 │               │     to S3   │       │
│      │              │                 │               │  ───────────│       │
│      │              │                 │               │             │       │
│      │              │                 │               │  3. Update  │       │
│      │              │                 │               │     telemetry_last  │
│      │              │                 │               │─────────────────────►
│      │              │                 │               │             │       │
│      │              │                 │               │  4. Update  │       │
│      │              │                 │               │     device  │       │
│      │              │                 │               │     status  │       │
│      │              │                 │               │─────────────────────►
│      │              │                 │               │             │       │
│      │              │                 │               │  5. ACK     │       │
│      │              │                 │               │     command │       │
│      │              │                 │               │     if      │       │
│      │              │                 │               │     reqId   │       │
│      │              │                 │               │     present │       │
│      │              │                 │               │─────────────────────►
│      │              │                 │               │             │       │
│      │                                                              │       │
│      │     Web App receives real-time update via MQTT WebSocket     │       │
│      │◄──────────────────────────────────────────────────────────────       │
│      │                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

Note: The diagram above shows the persistence path. The real-time path is:
Device → Shadow Update → MQTT Broadcast → Web UI (subscribed to update/documents)
```

### 6.4 IoT Rule SQL

```sql
-- Classic Shadow Rule
SELECT
  encode(*, 'base64') as payload_b64,
  topic() as topic,
  topic(3) as thing_name
FROM '$aws/things/+/shadow/update/documents'

-- Named Shadow Rule
SELECT
  encode(*, 'base64') as payload_b64,
  topic() as topic,
  topic(3) as thing_name,
  topic(6) as shadow_name
FROM '$aws/things/+/shadow/name/+/update/documents'
```

### 6.5 Real-time MQTT Subscription (Web)

#### **MQTT Client Implementation**

```typescript
// user-portal/src/lib/mqtt-client.ts

// 1. Connect to AWS IoT Core via WebSocket
await mqttClient.connect();
// This internally:
// - Gets AWS credentials from Cognito
// - Generates SigV4-signed WebSocket URL
// - Establishes MQTT over WebSocket connection

// 2. Subscribe to device Shadow updates
const unsubscribe = await mqttClient.subscribeTelemetry(
  'RT4G:001',           // thingName
  undefined,            // shadowName (undefined = classic shadow)
  (reported) => {
    // This callback fires instantly when device updates Shadow
    console.log('Battery:', reported.battery);
    console.log('Temperature:', reported.temperature);

    // Update UI immediately
    updateDeviceUI(reported);
  }
);

// 3. Send control command
const { reqId } = await mqttClient.publishControl({
  thingName: 'RT4G:001',
  command: {
    power: 'on',
    mode: 'auto'
  }
});

// 4. Wait for ACK (device will include req_id in reported state)
// The subscribeTelemetry callback will receive the ACK
```

#### **Shadow Topic Subscription Strategy**

```typescript
// ❌ DON'T subscribe to update/accepted (only successful updates)
// ❌ DON'T subscribe to update/delta (only differences)
// ✅ DO subscribe to update/documents (complete previous + current state)

const topic = `$aws/things/${thingName}/shadow/update/documents`;

// Why update/documents?
// - Contains both previous and current state
// - Includes metadata and version
// - Captures ALL Shadow changes (from device AND cloud)
// - Perfect for detecting ACKs by comparing previous vs current
```

#### **Command ACK Detection**

```typescript
// When you send a command, you get a reqId
const { reqId, sentAt } = await mqttClient.publishControl({
  thingName: 'device-001',
  command: { trapState: 'armed' }
});

// Subscribe to Shadow updates
mqttClient.subscribeTelemetry('device-001', undefined, (reported) => {
  // Device includes req_id in reported state as ACK
  if (reported.req_id === reqId) {
    const latency = performance.now() - sentAt;
    console.log(`Command ACKed in ${latency}ms`);
    showSuccessNotification('Device armed successfully');
  }
});
```

### 6.6 MQTT WebSocket Connection

```typescript
// iot-signer.ts - SigV4 Signing
function getSignedWebSocketUrl(credentials: AWSCredentials): string {
  const endpoint = 'xxxx.iot.ap-southeast-1.amazonaws.com';
  const region = 'ap-southeast-1';
  const service = 'iotdevicegateway';

  // Create canonical request
  const canonicalUri = '/mqtt';
  const canonicalQuerystring = buildCanonicalQueryString(
    credentials.accessKeyId,
    region,
    service,
    datetime
  );

  // Calculate signature
  const signature = calculateSigV4Signature(...);

  // Build final URL
  // IMPORTANT: X-Amz-Security-Token added AFTER signature
  let url = `wss://${endpoint}${canonicalUri}?${canonicalQuerystring}&X-Amz-Signature=${signature}`;

  if (credentials.sessionToken) {
    url += `&X-Amz-Security-Token=${encodeURIComponent(credentials.sessionToken)}`;
  }

  return url;
}
```

---

## 7. Device Sharing & Transfer

### 7.1 Device Sharing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   DEVICE SHARING                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Owner App          Edge Function              Database                     │
│      │                   │                        │                         │
│      │  POST /device-    │                        │                         │
│      │  share            │                        │                         │
│      │  {                │                        │                         │
│      │    device_id,     │                        │                         │
│      │    target_email,  │                        │                         │
│      │    role: "viewer" │                        │                         │
│      │    | "editor"     │                        │                         │
│      │  }                │                        │                         │
│      │──────────────────►│                        │                         │
│      │                   │                        │                         │
│      │                   │  1. Verify caller      │                         │
│      │                   │     has can_share_     │                         │
│      │                   │     device permission  │                         │
│      │                   │───────────────────────►│                         │
│      │                   │                        │                         │
│      │                   │  2. Lookup target      │                         │
│      │                   │     user by email      │                         │
│      │                   │───────────────────────►│                         │
│      │                   │                        │                         │
│      │                   │  3. Create device_     │                         │
│      │                   │     shares record      │                         │
│      │                   │───────────────────────►│                         │
│      │                   │                        │                         │
│      │   Success         │                        │                         │
│      │◄──────────────────│                        │                         │
│      │                   │                        │                         │
└─────────────────────────────────────────────────────────────────────────────┘

Share Roles:
- viewer: Can view device status, cannot control
- editor: Can view and control device
```

### 7.2 Device Transfer Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   DEVICE TRANSFER                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step 1: Generate Transfer Code                                             │
│  ──────────────────────────────                                             │
│                                                                             │
│  Original Owner       Edge Function              Database                   │
│      │                     │                        │                       │
│      │  POST /device-      │                        │                       │
│      │  transfer           │                        │                       │
│      │  action: generate   │                        │                       │
│      │  device_id: xxx     │                        │                       │
│      │────────────────────►│                        │                       │
│      │                     │                        │                       │
│      │                     │  Generate 8-char code  │                       │
│      │                     │  (excludes 0/O/I/1)    │                       │
│      │                     │  ───────────────────   │                       │
│      │                     │                        │                       │
│      │                     │  Store pending         │                       │
│      │                     │  transfer (24h expiry) │                       │
│      │                     │───────────────────────►│                       │
│      │                     │                        │                       │
│      │  { code: "A3F2B5C9"}│                        │                       │
│      │◄────────────────────│                        │                       │
│      │                     │                        │                       │
│                                                                             │
│  Step 2: Accept Transfer                                                    │
│  ───────────────────────                                                    │
│                                                                             │
│  New Owner             Edge Function              Database                  │
│      │                     │                        │                       │
│      │  POST /device-      │                        │                       │
│      │  transfer           │                        │                       │
│      │  action: accept     │                        │                       │
│      │  code: "A3F2B5C9"   │                        │                       │
│      │────────────────────►│                        │                       │
│      │                     │                        │                       │
│      │                     │  1. Verify code valid  │                       │
│      │                     │     and not expired    │                       │
│      │                     │───────────────────────►│                       │
│      │                     │                        │                       │
│      │                     │  2. Delete old         │                       │
│      │                     │     device_owners      │                       │
│      │                     │───────────────────────►│                       │
│      │                     │                        │                       │
│      │                     │  3. Create new         │                       │
│      │                     │     device_owners      │                       │
│      │                     │───────────────────────►│                       │
│      │                     │                        │                       │
│      │                     │  4. Delete all         │                       │
│      │                     │     device_shares      │                       │
│      │                     │───────────────────────►│                       │
│      │                     │                        │                       │
│      │                     │  5. Mark transfer      │                       │
│      │                     │     completed          │                       │
│      │                     │───────────────────────►│                       │
│      │                     │                        │                       │
│      │   Transfer complete │                        │                       │
│      │◄────────────────────│                        │                       │
│      │                     │                        │                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Database Schema

### 8.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATABASE SCHEMA                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐        │
│  │   tenants    │◄────────│    users     │────────►│   profiles   │        │
│  │              │  1:N    │              │  1:1    │              │        │
│  │  id (PK)     │         │  id (PK)     │         │  id (PK/FK)  │        │
│  │  name        │         │  email       │         │  name        │        │
│  │  created_at  │         │  created_at  │         │  avatar_url  │        │
│  └──────┬───────┘         └──────────────┘         └──────────────┘        │
│         │                        │                                          │
│         │                        │                                          │
│         │ 1:N                    │ N:M                                      │
│         ▼                        ▼                                          │
│  ┌──────────────┐         ┌──────────────────┐                             │
│  │user_tenant_  │◄────────│                  │                             │
│  │   roles      │         │                  │                             │
│  │              │         │                  │                             │
│  │  user_id(FK) │         │                  │                             │
│  │  tenant_id(FK│         │                  │                             │
│  │  role        │         │                  │                             │
│  └──────────────┘         │                  │                             │
│         │                 │                  │                             │
│         │                 │                  │                             │
│         ▼                 ▼                  │                             │
│  ┌──────────────┐  ┌──────────────┐         │                             │
│  │   devices    │◄─│device_owners │         │                             │
│  │              │  │              │         │                             │
│  │  id (PK)     │  │  device_id   │         │                             │
│  │  thing_name  │  │  tenant_id   │         │                             │
│  │  type        │  │  acquired_at │         │                             │
│  │  model       │  └──────────────┘         │                             │
│  │  status      │         │                 │                             │
│  │  metadata    │         │                 │                             │
│  └──────┬───────┘         │                 │                             │
│         │                 │                 │                             │
│    ┌────┴────┬────────────┴─────┐           │                             │
│    │         │                  │           │                             │
│    ▼         ▼                  ▼           │                             │
│  ┌────────┐ ┌────────┐  ┌──────────────┐    │                             │
│  │ traps  │ │commands│  │device_shares │    │                             │
│  │        │ │        │  │              │    │                             │
│  │ device │ │ device │  │  device_id   │    │                             │
│  │ _id(FK)│ │ _id(FK)│  │  user_id     │    │                             │
│  │ name   │ │ command│  │  role        │    │                             │
│  │ status │ │ params │  └──────────────┘    │                             │
│  │ config │ │ status │                      │                             │
│  └────────┘ │ acked_ │                      │                             │
│             │ at     │                      │                             │
│             └────────┘                      │                             │
│                                             │                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │ telemetry_   │  │manufacturing_│  │device_activ- │                     │
│  │    last      │  │   batches    │  │ation_codes   │                     │
│  │              │  │              │  │              │                     │
│  │  device_id   │  │  batch_id    │  │ code (PK)    │                     │
│  │  shadow_name │  │  model       │  │ device_id    │                     │
│  │  reported    │  │  status      │  │ batch_id     │                     │
│  │  desired     │  │  created_    │  │ is_used      │                     │
│  │  updated_at  │  │  devices     │  │ used_at      │                     │
│  └──────────────┘  └──────────────┘  └──────────────┘                     │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐                                        │
│  │  cognito_    │  │  setup_      │                                        │
│  │  credentials │  │  sessions    │                                        │
│  │  _cache      │  │              │                                        │
│  │              │  │  device_id   │                                        │
│  │  user_id     │  │  state       │                                        │
│  │  identity_id │  │  data        │                                        │
│  │  credentials │  │  expires_at  │                                        │
│  │  expiration  │  └──────────────┘                                        │
│  └──────────────┘                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `devices` | All registered IoT devices | id, thing_name, type, model, status, metadata |
| `device_owners` | Device-tenant ownership | device_id, tenant_id, acquired_at |
| `device_shares` | Shared device access | device_id, user_id, role (viewer/editor) |
| `traps` | Business trap entities | device_id, name, status, location, config |
| `telemetry_last` | Latest device state | device_id, shadow_name, reported, desired |
| `commands` | Command history | device_id, command, params, status, acked_at |
| `manufacturing_batches` | Factory batch records | batch_id, model, status, created_devices |
| `device_activation_codes` | Activation codes | code, device_id, batch_id, is_used |
| `setup_sessions` | Device setup workflow | device_id, state, data, expires_at |
| `cognito_credentials_cache` | AWS credential cache | user_id, identity_id, credentials, expiration |

### 8.3 Key Database Functions

```sql
-- Check if user can manage device (owner/admin)
CREATE FUNCTION can_manage_device(p_device_id uuid) RETURNS boolean;

-- Get user's permission level for device
CREATE FUNCTION get_device_permission_level(p_device_id uuid)
RETURNS text; -- 'owner', 'editor', 'viewer', null

-- Check specific permission
CREATE FUNCTION check_device_permission(
  p_device_id uuid,
  p_required_level text
) RETURNS boolean;
```

---

## 9. Authentication & Permission System

### 9.1 Multi-Layer Authentication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   AUTHENTICATION LAYERS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Layer 1: Supabase JWT                                                      │
│  ─────────────────────                                                      │
│  - User authenticates via Supabase Auth                                     │
│  - JWT contains: user_id, email, role                                       │
│  - Edge Functions verify JWT via verifyAuth()                               │
│                                                                             │
│  Layer 2: Row Level Security (RLS)                                          │
│  ─────────────────────────────────                                          │
│  - PostgreSQL RLS policies enforce data access                              │
│  - Automatic filtering based on auth.uid()                                  │
│  - No data leakage even with direct SQL access                              │
│                                                                             │
│  Layer 3: Business Logic Permission                                         │
│  ────────────────────────────────                                           │
│  - Edge Functions check specific permissions:                               │
│    - can_manage_device() for control operations                             │
│    - check_device_permission() for granular access                          │
│    - Role checks for admin operations                                       │
│                                                                             │
│  Layer 4: AWS IoT Policy                                                    │
│  ───────────────────────                                                    │
│  - PestGG-User-MQTT-Policy attached to Cognito Identity                     │
│  - Controls MQTT topic access                                               │
│  - Enforces IoT resource authorization                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Permission Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PERMISSION LEVELS                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tenant Level:                                                              │
│  ─────────────                                                              │
│  owner  > admin  > member                                                   │
│    │        │        │                                                      │
│    │        │        └─ View own data                                       │
│    │        └────────── Manage tenant devices                               │
│    └─────────────────── Full tenant control + billing                       │
│                                                                             │
│  Device Level:                                                              │
│  ─────────────                                                              │
│  owner  > editor > viewer                                                   │
│    │        │        │                                                      │
│    │        │        └─ View device status                                  │
│    │        └────────── Control device + view                               │
│    └─────────────────── Full control + share + transfer                     │
│                                                                             │
│  Permission Capabilities:                                                   │
│  ────────────────────────                                                   │
│  ┌────────────────┬────────┬────────┬────────┐                              │
│  │ Action         │ Owner  │ Editor │ Viewer │                              │
│  ├────────────────┼────────┼────────┼────────┤                              │
│  │ View Status    │   ✓    │   ✓    │   ✓    │                              │
│  │ Control Device │   ✓    │   ✓    │   ✗    │                              │
│  │ Share Device   │   ✓    │   ✗    │   ✗    │                              │
│  │ Transfer Device│   ✓    │   ✗    │   ✗    │                              │
│  │ Delete Device  │   ✓    │   ✗    │   ✗    │                              │
│  └────────────────┴────────┴────────┴────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Auth Implementation Pattern

```typescript
// Shared auth pattern (auth.ts)
export async function verifyAuth(req: Request) {
  const authHeader = req.headers.get('Authorization');
  if (!authHeader) {
    throw new AppError(ErrorCodes.UNAUTHORIZED, 'Missing authorization', 401);
  }

  const token = authHeader.replace('Bearer ', '');
  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  const { data: { user }, error } = await supabase.auth.getUser(token);
  if (error || !user) {
    throw new AppError(ErrorCodes.UNAUTHORIZED, 'Invalid token', 401);
  }

  return { user, supabase };
}

// Permission check pattern
async function checkDevicePermission(
  supabase: SupabaseClient,
  deviceId: string,
  requiredLevel: 'viewer' | 'editor' | 'owner'
) {
  const { data, error } = await supabase
    .rpc('check_device_permission', {
      p_device_id: deviceId,
      p_required_level: requiredLevel
    });

  if (!data) {
    throw new AppError(ErrorCodes.PERMISSION_DENIED, 'Insufficient permissions', 403);
  }
}
```

---

## 10. API Reference

### 10.1 Factory Stage APIs

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/manufacturing-create-devices` | POST | Batch create devices | Admin |
| `/manufacturing-batches` | GET | Query batch records | Admin |
| `/manufacturing-activation-codes` | GET | Export codes (CSV) | Admin |

### 10.2 User Stage APIs

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/user-device-bind` | POST | Bind device with code | User |
| `/get-aws-credentials` | POST | Get IoT credentials | User |
| `/setup-sessions` | POST/GET | Manage setup flow | User |

### 10.3 Operation Stage APIs

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/user-device-control` | POST | Send control command | Owner/Editor |
| `/send-command` | POST | Legacy control API | Owner/Editor |
| `/device-share` | POST | Share device access | Owner |
| `/device-transfer` | POST | Transfer ownership | Owner |

### 10.4 Request/Response Examples

**Batch Create Devices:**
```json
// POST /manufacturing-create-devices
{
  "model": "RT-Pro-4G",
  "count": 10,
  "prefix": "RT4G"
}

// Response
{
  "batch_id": "batch_1702900000",
  "devices": [
    {
      "thing_name": "RT4G:001",
      "activation_code": "RT4G-A3F2B1C9",
      "certificate_pem": "-----BEGIN CERTIFICATE-----...",
      "private_key": "-----BEGIN EC PRIVATE KEY-----...",
      "iot_endpoint": "xxxx.iot.ap-southeast-1.amazonaws.com"
    }
  ]
}
```

**User Device Control:**
```json
// POST /user-device-control
{
  "thing_name": "RT4G:001",
  "command": "setMode",
  "params": {
    "mode": "auto",
    "sensitivity": 3
  }
}

// Response
{
  "success": true,
  "reqId": "cmd_1702900000_abc123"
}
```

---

## 11. AWS CDK Infrastructure

### 11.1 Stack Structure

```
cloud-iot/
├── bin/
│   └── app.ts              # CDK app entry point
├── lib/
│   ├── api-stack.ts        # API Gateway + Lambdas
│   ├── cognito-stack.ts    # Cognito Identity Pool
│   └── iot-stack.ts        # IoT Core resources
└── lambdas/
    ├── authorizer/         # JWT validation Lambda
    ├── control/            # Device control Lambda
    └── projector/          # Shadow projection Lambda
```

### 11.2 IoT Stack Resources

```typescript
// iot-stack.ts creates:

// 1. S3 Archive Bucket
const archiveBucket = new s3.Bucket(this, 'ArchiveBucket', {});

// 2. Projector Lambda
const projector = new nodefn.NodejsFunction(this, 'ProjectorFn', {
  entry: 'lambdas/projector/handler.ts',
  runtime: lambda.Runtime.NODEJS_20_X,
  environment: {
    ARCHIVE_BUCKET: archiveBucket.bucketName,
    SUPABASE_URL: process.env.SUPABASE_URL,
    SUPABASE_SERVICE_ROLE: process.env.SUPABASE_SERVICE_ROLE
  }
});

// 3. IoT Policies
const userMqttPolicy = new iot.CfnPolicy(this, 'PestGGUserMqttPolicy', {
  policyName: 'PestGG-User-MQTT-Policy',
  policyDocument: {
    Statement: [
      { Effect: 'Allow', Action: 'iot:Connect', Resource: '*' },
      { Effect: 'Allow', Action: ['iot:Publish', 'iot:Receive'], Resource: '*' },
      { Effect: 'Allow', Action: 'iot:Subscribe', Resource: '*' }
    ]
  }
});

// 4. IoT Rules (Classic + Named Shadow)
const classicRule = new iot.CfnTopicRule(this, 'ShadowClassicToLambda', {
  topicRulePayload: {
    sql: "SELECT ... FROM '$aws/things/+/shadow/update/documents'",
    actions: [{ lambda: { functionArn: projector.functionArn } }]
  }
});

const namedRule = new iot.CfnTopicRule(this, 'ShadowNamedToLambda', {
  topicRulePayload: {
    sql: "SELECT ... FROM '$aws/things/+/shadow/name/+/update/documents'",
    actions: [{ lambda: { functionArn: projector.functionArn } }]
  }
});
```

### 11.3 Deployment

```bash
# Deploy to staging
cd cloud-iot
npm run cdk deploy -- --all --context env=staging

# Deploy to production
npm run cdk deploy -- --all --context env=production
```

---

## 12. Developer Quick Start

### 12.1 Development Environment Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd AWS-Template

# 2. Install dependencies
npm install
cd supabase/functions && deno cache deps.ts
cd ../..
cd cloud-iot && npm install
cd ..
cd user-portal && npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Start Supabase locally
supabase start

# 5. Start Edge Functions
supabase functions serve --env-file .env

# 6. Start User Portal
cd user-portal && npm run dev
```

### 12.2 Adding a New Edge Function

```bash
# 1. Create function directory
mkdir -p supabase/functions/my-new-function

# 2. Create index.ts with standard pattern
cat > supabase/functions/my-new-function/index.ts << 'EOF'
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { corsHeaders, handleCorsPreFlight } from '../_shared/cors.ts';
import { verifyAuth } from '../_shared/auth.ts';
import { AppError, ErrorCodes } from '../_shared/errors.ts';

serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return handleCorsPreFlight();
  }

  try {
    const { user, supabase } = await verifyAuth(req);

    // Your business logic here

    return new Response(JSON.stringify({ success: true }), {
      headers: { ...corsHeaders(), 'Content-Type': 'application/json' }
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: error instanceof AppError ? error.statusCode : 500,
      headers: { ...corsHeaders(), 'Content-Type': 'application/json' }
    });
  }
});
EOF

# 3. Deploy
supabase functions deploy my-new-function
```

### 12.3 Adding Device Control Command

```typescript
// 1. Update Control Lambda (lambdas/control/handler.ts)
// Add command validation if needed

// 2. Update user-device-control Edge Function
// Add any business logic validation

// 3. Update frontend API client
// user-portal/src/lib/api.ts
export const sendCommand = async (
  thingName: string,
  command: string,
  params: object
) => {
  return api.post('/user-device-control', {
    thing_name: thingName,
    command,
    params
  });
};
```

### 12.4 Key Files Reference

| File | Purpose |
|------|---------|
| `supabase/functions/_shared/auth.ts` | JWT verification |
| `supabase/functions/_shared/aws-iot-client.ts` | AWS IoT API wrapper |
| `supabase/functions/_shared/cors.ts` | CORS handling |
| `supabase/functions/_shared/errors.ts` | Error types |
| `lambdas/control/handler.ts` | Device control Lambda |
| `lambdas/projector/handler.ts` | Shadow projection Lambda |
| `user-portal/src/lib/mqtt-client.ts` | MQTT WebSocket client |
| `user-portal/src/lib/api.ts` | API client |
| `cloud-iot/lib/iot-stack.ts` | IoT infrastructure |

---

## Appendix A: Troubleshooting

### A.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| MQTT connection fails | Invalid credentials or expired | Refresh AWS credentials via `/get-aws-credentials` |
| Shadow update not reflected | Projector Lambda error | Check CloudWatch Logs for projector |
| Command not ACKed | Device offline or shadow desync | Check device connection and shadow state |
| Permission denied | Missing RLS policy or role | Verify user role and device ownership |

### A.2 Debug Logging

```typescript
// Enable verbose logging in Edge Functions
console.log('[FunctionName] Step description:', { data });

// Check Supabase logs
supabase functions logs my-function --tail

// Check AWS Lambda logs
aws logs tail /aws/lambda/ProjectorFn --follow
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Thing** | AWS IoT representation of a physical device |
| **Shadow** | JSON document representing device state |
| **Classic Shadow** | Default shadow for a Thing |
| **Named Shadow** | Additional shadow with custom name |
| **Gateway** | Device that manages child devices |
| **Child Device** | Device managed by a gateway via Named Shadow |
| **Activation Code** | One-time code for user device binding |
| **Tenant** | Organization/account that owns devices |
| **RLS** | Row Level Security in PostgreSQL |

---

*Document Version: 1.0*
*Last Updated: December 2024*
*Generated for PestGG IoT System*
