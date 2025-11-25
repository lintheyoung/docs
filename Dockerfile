# 第一阶段：构建文档
FROM node:20-alpine AS builder

RUN npm i -g mintlify

WORKDIR /docs
COPY . .

RUN mintlify build

# 第二阶段：运行服务
FROM node:20-alpine

WORKDIR /app

# 安装依赖
RUN npm init -y && npm i express express-basic-auth

# 复制构建好的静态文件
COPY --from=builder /docs/.mintlify/static ./static

# 创建服务器文件
RUN echo 'const express = require("express"); \
const basicAuth = require("express-basic-auth"); \
const app = express(); \
const users = {}; \
(process.env.USERS || "admin:admin123").split(",").forEach(u => { \
  const [name, pass] = u.split(":"); \
  users[name] = pass; \
}); \
app.use(basicAuth({ users, challenge: true, realm: "Docs" })); \
app.use(express.static("static")); \
app.listen(3000, "0.0.0.0", () => console.log("Docs running on http://0.0.0.0:3000"));' > server.js

# ============================================
# 默认账号密码（可通过 -e USERS 覆盖）
# 格式：用户名:密码,用户名2:密码2
# ============================================
ENV USERS="admin:admin123,reader:reader456"

EXPOSE 3000

CMD ["node", "server.js"]
