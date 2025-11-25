# Mintlify 文档 + 密码保护
FROM node:20-alpine

WORKDIR /app

# 安装 mintlify CLI 和依赖
RUN npm i -g mintlify && \
    npm init -y && \
    npm i express express-basic-auth http-proxy-middleware

# 复制文档源文件
COPY . .

# ============================================
# 默认账号密码（可通过 -e USERS 覆盖）
# 格式：用户名:密码,用户名2:密码2
# ============================================
ENV USERS="admin:admin123,reader:reader456"

EXPOSE 3000

CMD ["node", "server.js"]
