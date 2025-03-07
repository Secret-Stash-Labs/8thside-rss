import requests
from bs4 import BeautifulSoup
from feedgenerator import Rss201rev2Feed
import hashlib
from datetime import datetime, timedelta
import asyncio
from playwright.async_api import async_playwright
import time
import re
import argparse
import sys

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate RSS feed from event data.')
parser.add_argument('--debug', action='store_true', help='Enable debug output')
args = parser.parse_args()

# Debug mode flag
DEBUG = args.debug

# Create a new RSS feed
feed = Rss201rev2Feed(
    title="Event Feed",
    link="https://locator.wizards.com/store/14936",
    description="Feed of events",
)

# Calculate the date range: today to one month from now
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
one_month_later = today + timedelta(days=30)
print(f"Filtering events between {today.strftime('%Y-%m-%d')} and {one_month_later.strftime('%Y-%m-%d')}")

# First try with requests for efficiency, and fall back to Playwright if needed
async def main():
    try:
        # Set up headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        print("Using Playwright to fetch page content...")
        html_content = await fetch_with_playwright()
        
        # Save HTML content to file for debugging
        if DEBUG:
            with open('debug_page_content.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
                print("Saved page content to debug_page_content.html for inspection")
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Debug: Print all available classes in the document
        if DEBUG:
            all_classes = set()
            for tag in soup.find_all(True):
                if tag.has_attr('class'):
                    all_classes.update(tag.get('class'))
            print("Available classes in the document:", sorted(all_classes))
        
        # Try multiple selectors to find event containers
        event_containers = []
        
        # Original selector
        store_info_containers = soup.find_all(class_='store-info')
        if store_info_containers:
            if DEBUG:
                print(f"Found {len(store_info_containers)} containers with class 'store-info'")
            event_containers.extend(store_info_containers)
        
        # Try alternative selectors
        event_containers_alt1 = soup.find_all(class_='event-container')
        if event_containers_alt1 and DEBUG:
            print(f"Found {len(event_containers_alt1)} containers with class 'event-container'")
            event_containers.extend(event_containers_alt1)
            
        event_containers_alt2 = soup.find_all(class_='event-listing')
        if event_containers_alt2 and DEBUG:
            print(f"Found {len(event_containers_alt2)} containers with class 'event-listing'")
            event_containers.extend(event_containers_alt2)
            
        event_containers_alt3 = soup.find_all('div', {'data-testid': re.compile(r'event-*')})
        if event_containers_alt3 and DEBUG:
            print(f"Found {len(event_containers_alt3)} containers with data-testid matching 'event-*'")
            event_containers.extend(event_containers_alt3)

        # Look for any event-related elements
        event_related = [tag for tag in soup.find_all(True) if tag.has_attr('class') and 
                         any(cls for cls in tag.get('class') if 'event' in cls.lower())]
        if event_related and DEBUG:
            print(f"Found {len(event_related)} elements with 'event' in their class name")
            print("Sample class names:", [tag.get('class') for tag in event_related[:5]])
            event_containers.extend(event_related)
            
        # Check if we found any event containers
        if not event_containers:
            print("No event containers found using any selector.")
            if DEBUG:
                print("Checking for any calendar or schedule elements...")
                
                # Look for calendar or schedule elements
                calendar_elements = [tag for tag in soup.find_all(True) if tag.has_attr('class') and 
                                   any(cls for cls in tag.get('class') if 'calendar' in cls.lower() or 'schedule' in cls.lower())]
                if calendar_elements:
                    print(f"Found {len(calendar_elements)} calendar/schedule elements")
                    print("Sample class names:", [tag.get('class') for tag in calendar_elements[:5]])
        else:
            print(f"Found {len(event_containers)} event containers")
            
            if DEBUG:
                for i, container in enumerate(event_containers[:3]):  # Show first 3 for debugging
                    print(f"\nContainer {i+1} HTML structure:")
                    print(container.prettify()[:500] + "..." if len(container.prettify()) > 500 else container.prettify())
        
        # Process event containers if any were found
        if event_containers:
            process_event_containers(event_containers)

        # Write the RSS feed to a file 
        with open('feed.rss', 'w') as f:
            feed.write(f, 'utf-8')
            print("Successfully wrote feed.rss file")

    except Exception as e:
        print(f"Error: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()

def process_event_containers(event_containers):
    """Process the found event containers and extract event details."""
    print(f"Processing {len(event_containers)} event containers")
    
    events_found = 0
    events_added = 0
    events_filtered = 0
    events_skipped_casual = 0
    
    for i, container in enumerate(event_containers):
        # Create a dictionary to store event details
        event_details = {}
        
        # Extract store name with multiple possible selectors
        store_name_element = (container.find(class_='store-info__name') or 
                             container.find(class_='store-name') or
                             container.find('h2') or
                             container.find('h3'))
        if store_name_element:
            event_details["Store Name"] = store_name_element.text.strip()
        
        # Extract event name with multiple possible selectors - REQUIRED
        event_name_element = (container.find(class_='row no-gutters') or 
                             container.find(class_='event-title') or
                             container.find(class_='event-name') or
                             container.find('h4') or
                             container.find('h5'))
        if event_name_element:
            event_details["Event Name"] = event_name_element.text.strip()
        else:
            # Skip silently without printing
            continue
        
        # Skip MTG casual play events
        if any(casual_term in event_details["Event Name"].lower() for casual_term in 
              ['casual play', 'causal play', 'open play', 'casual mtg', 'play mtg']) or \
           'causal play for any mtg' in event_details["Event Name"].lower():
            events_skipped_casual += 1
            continue
        
        # Extract date information with multiple possible selectors - REQUIRED
        day_of_week = (container.find(class_='dayOfWeek text-center') or 
                      container.find(class_='day-of-week') or
                      container.find(string=re.compile(r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday', re.I)))
        month = (container.find(class_='month text-center') or 
                container.find(class_='month') or
                container.find(string=re.compile(r'January|February|March|April|May|June|July|August|September|October|November|December', re.I)))
        day = (container.find(class_='dayOfMonth text-center') or 
              container.find(class_='day-of-month') or
              container.find(class_='date') or
              container.find(string=re.compile(r'\b\d{1,2}\b')))
        
        # Extract date components
        if day_of_week:
            if isinstance(day_of_week, str):
                event_details["Day of Week"] = day_of_week.strip()
            else:
                event_details["Day of Week"] = day_of_week.text.strip()
        
        if month:
            if isinstance(month, str):
                event_details["Month"] = month.strip()
            else:
                event_details["Month"] = month.text.strip()
        
        if day:
            if isinstance(day, str):
                event_details["Day"] = day.strip()
            else:
                event_details["Day"] = day.text.strip()
        
        # Try to find a full date string if individual components weren't found
        if not all(key in event_details for key in ["Day of Week", "Month", "Day"]):
            date_pattern = re.compile(r'(?P<day_of_week>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s*(?P<day>\d{1,2})', re.I)
            date_text = container.get_text()
            date_match = date_pattern.search(date_text)
            
            if date_match:
                event_details["Day of Week"] = date_match.group('day_of_week')
                event_details["Month"] = date_match.group('month')
                event_details["Day"] = date_match.group('day')
        
        # Check if we have all REQUIRED date fields after attempts to extract
        if not all(key in event_details for key in ["Day of Week", "Month", "Day"]):
            # Skip silently without printing
            continue
        
        events_found += 1
        
        # Extract event cost with multiple possible selectors
        event_fee_element = (container.find(class_='event-fee') or 
                            container.find(class_='price') or
                            container.find(class_='cost') or
                            container.find(string=re.compile(r'\$\d+|\bfree\b', re.I)))
        if event_fee_element:
            if isinstance(event_fee_element, str):
                event_details["Event Cost"] = event_fee_element.strip()
            else:
                event_details["Event Cost"] = event_fee_element.text.strip()
        else:
            event_details["Event Cost"] = "Not specified"
        
        # Extract event time with multiple possible selectors
        event_time_element = (container.find(class_='event-time') or 
                             container.find(class_='time') or
                             container.find(string=re.compile(r'\d{1,2}:\d{2}(?:\s*[AP]M)?', re.I)))
        if event_time_element:
            if isinstance(event_time_element, str):
                event_details["Event Time"] = event_time_element.strip()
            else:
                event_details["Event Time"] = event_time_element.text.strip()
        else:
            event_details["Event Time"] = "12:00 PM"  # Default time if not found
        
        # Format the event for the feed
        try:
            # Format the datetime string
            try:
                event_datetime_str = f"{event_details['Day of Week']}, {event_details['Month']} {event_details['Day']}, {datetime.now().year} , {event_details['Event Time']}"
                event_datetime = datetime.strptime(event_datetime_str, "%A, %B %d, %Y , %I:%M %p")
            except ValueError:
                # Try alternate time format if the first fails
                event_datetime_str = f"{event_details['Day of Week']}, {event_details['Month']} {event_details['Day']}, {datetime.now().year} , 12:00 PM"
                event_datetime = datetime.strptime(event_datetime_str, "%A, %B %d, %Y , %I:%M %p")
                event_details["Event Time"] = "12:00 PM"  # Use default time
            
            # Check if the event is in January-March but we're currently in October-December
            # If so, the event is likely in the next year
            current_month = datetime.now().month
            event_month = event_datetime.month
            if current_month >= 10 and event_month <= 3:
                event_datetime = event_datetime.replace(year=datetime.now().year + 1)
            
            # Filter events by date range (today to one month from now)
            if event_datetime < today or event_datetime > one_month_later:
                # Skip silently without printing
                events_filtered += 1
                continue
            
            # Adjust timezone
            event_datetime = event_datetime - timedelta(hours=5)
            event_datetime_str = datetime.strftime(event_datetime,"%A, %B %d, %I:%M %p") 
            
            # Create a consistent string for GUID generation
            details_str = f"{event_details['Event Name']}-{event_details['Event Cost']}-{event_datetime_str}"
            guid = hashlib.md5(details_str.encode()).hexdigest()

            # Construct the HTML formatted message - no debug prints for HTML
            formatted_message = f"<p></p>"  # Empty paragraph for spacing
            formatted_message += f"<p><h2>{event_details['Event Name']}</h2></p>"
            formatted_message += f"<p><strong>Date and Time:</strong> {event_datetime_str}</p>"
            formatted_message += "<p><ul>"
            for key, value in event_details.items():
                if key not in ["Event Name", "Day of Week", "Month", "Day", "Event Time"]:
                    formatted_message += f"<li><strong>{key}</strong>: {value}</li>"
            formatted_message += "</ul></p>"
                    
            # Add the event details to the RSS feed
            feed.add_item(
                title=event_details.get("Event Name", ""),
                link="https://locator.wizards.com/store/14936",
                description=formatted_message,
                content=str(event_details),
                unique_id=guid
            )
            events_added += 1
            print(f"Added event: {event_details.get('Event Name', '')} on {event_datetime.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"Error processing event: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
    
    print(f"\nSummary: Found {events_found} valid events, filtered {events_filtered} by date, " +
          f"skipped {events_skipped_casual} casual play events, added {events_added} to feed")

async def fetch_with_playwright():
    """Fetch page content using Playwright when requests fails."""
    async with async_playwright() as p:
        print("Launching Playwright browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("Navigating to page...")
        await page.goto("https://locator.wizards.com/store/14936", wait_until="domcontentloaded")
        
        # Wait for content to load
        print("Waiting for page to load completely...")
        
        # Wait for the page to settle
        await page.wait_for_load_state('networkidle')
        
        # Wait a bit more to ensure JavaScript execution completes
        await asyncio.sleep(5)
        
        # Try to find event-related elements
        selectors_to_try = [
            '.store-info', 
            '.event-container', 
            '.event-listing', 
            '[data-testid*="event"]',
            '.calendar',
            '.schedule'
        ]
        
        found_selector = None
        for selector in selectors_to_try:
            try:
                if DEBUG:
                    print(f"Looking for selector: {selector}")
                count = await page.evaluate(f'document.querySelectorAll("{selector}").length')
                if DEBUG:
                    print(f"Found {count} elements with selector: {selector}")
                if count > 0:
                    found_selector = selector
                    break
            except Exception as e:
                if DEBUG:
                    print(f"Error checking selector {selector}: {e}")
        
        if found_selector:
            if DEBUG:
                print(f"Using selector: {found_selector}")
            # Wait explicitly for this selector
            try:
                await page.wait_for_selector(found_selector, timeout=10000)
            except:
                if DEBUG:
                    print(f"Timeout waiting for {found_selector}, but continuing anyway")
        
        # Take a screenshot for debugging
        if DEBUG:
            await page.screenshot(path="debug_screenshot.png")
            print("Saved screenshot to debug_screenshot.png")
        
        # Get the page content
        content = await page.content()
        
        await browser.close()
        print("Playwright browser closed")
        
        return content

if __name__ == "__main__":
    asyncio.run(main())
