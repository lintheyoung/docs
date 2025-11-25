const express = require("express");
const basicAuth = require("express-basic-auth");
const { createProxyMiddleware } = require("http-proxy-middleware");
const { spawn } = require("child_process");

// 启动 mintlify dev
const mint = spawn("mintlify", ["dev", "--port", "3333"], {
  stdio: "inherit",
  shell: true
});

// 等待 mintlify 启动
setTimeout(() => {
  const app = express();

  // 解析账号密码
  const users = {};
  (process.env.USERS || "admin:admin123").split(",").forEach(u => {
    const [name, pass] = u.split(":");
    if (name && pass) users[name] = pass;
  });

  // 密码保护
  app.use(basicAuth({ users, challenge: true, realm: "Docs" }));

  // 代理到 mintlify dev
  app.use("/", createProxyMiddleware({
    target: "http://127.0.0.1:3333",
    changeOrigin: true,
    ws: true
  }));

  app.listen(3000, "0.0.0.0", () => {
    console.log("Protected docs running on http://0.0.0.0:3000");
  });
}, 10000);

// 处理退出
process.on("SIGTERM", () => { mint.kill(); process.exit(0); });
