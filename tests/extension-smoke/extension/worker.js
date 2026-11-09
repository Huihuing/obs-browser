chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message === "obs-extension-probe") respond("worker-ready");
});
