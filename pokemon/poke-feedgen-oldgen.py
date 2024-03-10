from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from feedgenerator import Rss201rev2Feed
import time
import hashlib
import chromedriver_autoinstaller
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import re



chrome_service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())

chrome_options = Options()
options = [
    "--headless",
    "--disable-gpu",
    "--window-size=1920,1200",
    "--ignore-certificate-errors",
    "--disable-extensions",
    "--no-sandbox",
    "--disable-dev-shm-usage"
]
for option in options:
    chrome_options.add_argument(option)

driver = webdriver.Chrome(service=chrome_service, options=chrome_options)


# Create a new RSS feed
feed = Rss201rev2Feed(
    title="Event Feed",
    link="https://events.pokemon.com/en-us/events?near=4232%20Fort%20St,%20Lincoln%20Park,%20MI%2048146,%20USA",
    description="Feed of events",
)

try:
    # Navigate to the URL
    driver.get("https://events.pokemon.com/en-us/events?near=4232%20Fort%20St,%20Lincoln%20Park,%20MI%2048146,%20USA")
    # Wait for the event cards to load
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'event-card')))


    # Find all event containers
    event_containers = driver.find_elements(By.CLASS_NAME, 'event-card')  # Adjust if necessary

    for i in range(len(event_containers)):
        # Since navigating to a new page will lose the context of the previous page,
        # we need to find the elements again each time we navigate back to the list of events
        event_cards = driver.find_elements(By.CLASS_NAME, 'event-card')
        if "8th" in event_cards[i].text.lower():
            lineSplit = event_cards[i].text.splitlines()
            
            print(lineSplit[0])
            print(lineSplit[2])

            # Click on the event card to navigate to the event page
            event_cards[i].click()
            eventUrl = driver.current_url
            print(eventUrl)

            # Wait for the new page to load
            time.sleep(5)  # adjust this value as needed

            source = driver.page_source

            dollar_values = re.findall(r'\$\d+(?:\.\d{2})?', source)

            # Print the found dollar values
            print(dollar_values[0])

            driver.back()
            time.sleep(5)
except:
    pass

finally:
    driver.quit()

# Write the RSS feed to a file 
# with open('feed.rss', 'w') as f:
#     feed.write(f, 'utf-8')