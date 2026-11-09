document.documentElement.dataset.obsProbeContent = "yes";
chrome.runtime.sendMessage("obs-extension-probe").then((reply) => {
  if (reply === "worker-ready") document.documentElement.dataset.obsProbeWorker = "yes";
});
