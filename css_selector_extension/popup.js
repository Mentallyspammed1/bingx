document.addEventListener('DOMContentLoaded', () => {
  const toggleSwitch = document.getElementById('toggle-switch');
  const selectorDisplay = document.getElementById('selector-display');
  const copyButton = document.getElementById('copy-btn');

  // Request the current state from the background script
  chrome.runtime.sendMessage({ action: 'getState' }, (response) => {
    if (response) {
      toggleSwitch.checked = response.isEnabled;
      selectorDisplay.textContent = response.lastSelector || 'Click an element on the page...';
      if (response.lastSelector) {
        copyButton.style.display = 'inline-block';
      }
    }
  });

  // Handle the toggle switch change
  toggleSwitch.addEventListener('change', () => {
    const isEnabled = toggleSwitch.checked;
    chrome.runtime.sendMessage({ action: 'toggle', isEnabled: isEnabled });

    // Inject/remove the content script based on the toggle state
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length > 0) {
        const tabId = tabs[0].id;
        if (isEnabled) {
          chrome.scripting.executeScript({
            target: { tabId: tabId },
            files: ['content.js']
          });
        } else {
          // Send a message to the content script to remove event listeners
          chrome.tabs.sendMessage(tabId, { action: 'disable' });
        }
      }
    });
  });

  // Listen for messages from the content script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'selectorFound') {
      selectorDisplay.textContent = request.selector;
      copyButton.style.display = 'inline-block';
      // Save the last selector to the background script
      chrome.runtime.sendMessage({ action: 'saveSelector', selector: request.selector });
    }
  });

  // Copy button functionality
  copyButton.addEventListener('click', () => {
    const selector = selectorDisplay.textContent;
    if (selector) {
      navigator.clipboard.writeText(selector).then(() => {
        const originalText = copyButton.textContent;
        copyButton.textContent = 'Copied!';
        setTimeout(() => {
          copyButton.textContent = originalText;
        }, 1500);
      }).catch(err => {
        console.error('Failed to copy text: ', err);
      });
    }
  });
});