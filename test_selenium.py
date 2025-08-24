from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

print("Summoning the Chrome spirit...")

# --- The Runes of Configuration ---
chrome_options = Options()
# This rune tells Chrome to run without a visible window (headless)
chrome_options.add_argument("--headless")
# This rune is often needed in Linux environments
chrome_options.add_argument("--no-sandbox")
# This rune helps prevent certain crashes
chrome_options.add_argument("--disable-dev-shm-usage")
# This rune points to the Chrome binary on Android
chrome_options.add_experimental_option("androidPackage", "com.android.chrome")

# --- The Path to Power ---
# Selenium 4 no longer needs the executable_path if chromedriver is in your $PATH
service = Service()

# --- The Final Conjuration ---
try:
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("The spirit has answered! Navigating to the arcane Google scrolls...")

    driver.get("https://www.google.com")
    print("Current Scroll Title:", driver.title)

except Exception as e:
    print(f"A disturbance in the ether! The spell failed: {e}")

finally:
    if 'driver' in locals():
        driver.quit()
        print("The spirit has been dismissed.")
