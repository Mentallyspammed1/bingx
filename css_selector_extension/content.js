// A global variable to check if the script is active
let isScriptActive = true

// A global reference to the tooltip element
let tooltip = null

// The improved function to generate a CSS selector for an element
function getCSSSelector(element) {
  if (!(element instanceof Element)) {
    return
  }

  const path = []
  while (element.nodeType === Node.ELEMENT_NODE) {
    let selector = element.tagName.toLowerCase()

    // Check for ID
    if (element.id) {
      selector += `#${element.id}`
      path.unshift(selector)
      break
    }

    // Check for unique data attributes (e.g., data-testid)
    const dataAttributes = Object.values(element.dataset)
    for (const attr of dataAttributes) {
      if (document.querySelectorAll(`[data-${attr}]`).length === 1) {
        selector += `[data-${attr}]`
        path.unshift(selector)
        break
      }
    }
    if (path.length > 0) {
      break
    }

    // Check for unique class names
    const classNames = element.className.split(/\s+/).filter(cls => cls)
    if (classNames.length > 0) {
      const uniqueClass = classNames.find(cls => document.querySelectorAll(`.${cls}`).length === 1)
      if (uniqueClass) {
        selector += `.${uniqueClass}`
        path.unshift(selector)
        break
      }
    }

    // Fallback to :nth-child
    let sibling = element
    let nth = 1
    while (sibling.previousElementSibling) {
      sibling = sibling.previousElementSibling
      if (sibling.tagName.toLowerCase() === selector) {
        nth++
      }
    }
    if (nth > 1) {
      selector += `:nth-of-type(${nth})`
    }
    path.unshift(selector)
    element = element.parentElement
  }
  return path.join(' > ')
}

// Function to handle the click event
function handleClick(event) {
  event.preventDefault()
  event.stopPropagation()

  const selector = getCSSSelector(event.target)
  if (selector) {
    // Send the selector to the popup
    chrome.runtime.sendMessage({ action: 'selectorFound', selector: selector })

    // Show a tooltip on the page
    if (tooltip) {
      tooltip.remove()
    }
    tooltip = document.createElement('div')
    tooltip.style.cssText = `
      position: fixed;
      top: ${event.clientY + 10}px;
      left: ${event.clientX + 10}px;
      background-color: #2c3e50;
      color: white;
      padding: 8px 12px;
      border-radius: 4px;
      font-family: 'Courier New', Courier, monospace;
      font-size: 12px;
      z-index: 10000;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      max-width: 300px;
      white-space: pre-wrap;
      word-wrap: break-word;
    `
    tooltip.textContent = selector
    document.body.appendChild(tooltip)

    // Fade out the tooltip after a few seconds
    setTimeout(() => {
      tooltip.remove()
      tooltip = null
    }, 4000)
  }
}

// Function to enable the click listener
function enableClickListener() {
  if (!isScriptActive) {
    isScriptActive = true
    document.addEventListener('click', handleClick, true)
    document.addEventListener('contextmenu', handleClick, true) // Use contextmenu as an alternative if needed
    console.log('CSS Selector Finder enabled.')
  }
}

// Function to disable the click listener
function disableClickListener() {
  if (isScriptActive) {
    isScriptActive = false
    document.removeEventListener('click', handleClick, true)
    document.removeEventListener('contextmenu', handleClick, true)
    if (tooltip) {
      tooltip.remove()
      tooltip = null
    }
    console.log('CSS Selector Finder disabled.')
  }
}

// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'enable') {
    enableClickListener()
  } else if (request.action === 'disable') {
    disableClickListener()
  }
})

// Immediately enable the listener when the script is injected
enableClickListener()