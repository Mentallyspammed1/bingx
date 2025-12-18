let isEnabled = false
let lastSelector = null

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'toggle') {
    isEnabled = request.isEnabled
  } else if (request.action === 'saveSelector') {
    lastSelector = request.selector
  } else if (request.action === 'getState') {
    sendResponse({ isEnabled: isEnabled, lastSelector: lastSelector })
  }
})