const API_CONFIG = {
  imageProcessing: "http://localhost:8001",
  verification: "http://localhost:8002",
};

function showNotification(message, type = "info") {
  console.log(`${type.toUpperCase()}: ${message}`);
  // TODO: Implement actual notifications
}

function formatFileSize(bytes) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

document.addEventListener("DOMContentLoaded", function () {
  console.log("Web interface loaded");
  // TODO: Add actual initialization logic
});
