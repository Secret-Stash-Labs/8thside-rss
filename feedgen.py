from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from feedgenerator import Rss201rev2Feed
import time
import hashlib
# Set up the WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

# Create a new RSS feed
feed = Rss201rev2Feed(
    title="Event Feed",
    link="https://locator.wizards.com/store/14936",
    description="Feed of events",
)

try:
    # Navigate to the URL
    driver.get("https://locator.wizards.com/store/14936")
    time.sleep(5)  # Wait for the page to load

    # Find all event containers
    event_containers = driver.find_elements(By.CLASS_NAME, 'store-info')  # Adjust if necessary

    for container in event_containers:
        # Find all child elements
        child_elements = container.find_elements(By.XPATH, './/*')

        # Create a dictionary to store the event details
        event_details = {}

        for element in child_elements:
            # Get class name of each child element
            class_name = element.get_attribute('class')
            text = element.text

            if class_name == "store-info__name":
                event_details["Store Name"] = text
            elif class_name == "event-fee":
                event_details["Event Cost"] = text
            elif class_name == "event-time":
                event_details["Event Time"] = text
            elif class_name == "row no-gutters":
                event_details["Event Name"] = text
            elif class_name == "dayOfWeek text-center":
                event_details["Day of Week"] = text
            elif class_name == "month text-center":
                event_details["Month"] = text
            elif class_name == "dayOfMonth text-center":
                event_details["Day"] = text
                
            guid = hashlib.md5(''.join(event_details.values()).encode()).hexdigest()
            event_details["Guid"] = guid

        # Add the event details to the RSS feed
        feed.add_item(
            title=event_details.get("Event Name", ""),
            link="https://locator.wizards.com/store/14936",
            description=str(event_details),
        )
        
        

finally:
    driver.quit()

# Write the RSS feed to a file 
with open('feed.rss', 'w') as f:
    feed.write(f, 'utf-8')