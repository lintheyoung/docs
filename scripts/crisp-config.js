// Crisp 自定义配置
// 文档: https://docs.crisp.chat/guides/chatbox-sdks/web-sdk/

// 等待 Crisp 加载完成
window.CRISP_READY_TRIGGER = function() {
  // 设置用户信息 (如果有)
  // $crisp.push(["set", "user:email", ["user@example.com"]]);
  // $crisp.push(["set", "user:nickname", ["John Doe"]]);

  // 设置自定义数据
  // $crisp.push(["set", "session:data", [[["plan", "pro"], ["source", "docs"]]]]);

  // 设置聊天框位置 (left 或 right)
  // $crisp.push(["config", "position:reverse", [true]]); // 移到左边

  // 设置颜色主题
  // $crisp.push(["config", "color:theme", ["green"]]);

  // 隐藏默认欢迎消息
  // $crisp.push(["config", "hide:on:away", [true]]);

  // 自动打开聊天框
  // $crisp.push(["do", "chat:open"]);

  // 发送自动消息
  // $crisp.push(["do", "message:show", ["text", "有什么可以帮助您的？"]]);

  console.log("Crisp 已加载并配置完成");
};

// 监听事件示例
// $crisp.push(["on", "chat:opened", function() {
//   console.log("聊天框已打开");
// }]);

// $crisp.push(["on", "message:received", function(data) {
//   console.log("收到消息:", data);
// }]);
