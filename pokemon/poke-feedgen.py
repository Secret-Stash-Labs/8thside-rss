import asyncio
from playwright.async_api import async_playwright
from feedgenerator import Rss201rev2Feed
import time
import hashlib
import re
from datetime import datetime, timedelta
import argparse
import sys

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate Pokemon RSS feed from event data.')
parser.add_argument('--debug', action='store_true', help='Enable debug output')
args = parser.parse_args()

# Debug mode flag
DEBUG = args.debug

# Create a new RSS feed
feed = Rss201rev2Feed(
    title="Pokemon Event Feed",
    link="https://events.pokemon.com/en-us/events?near=4232%20Fort%20St,%20Lincoln%20Park,%20MI%2048146,%20USA",
    description="Feed of Pokemon events",
)

# Calculate the date range: today to one month from now
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
one_month_later = today + timedelta(days=30)
print(f"Filtering Pokemon events between {today.strftime('%Y-%m-%d')} and {one_month_later.strftime('%Y-%m-%d')}")

async def main():
    try:
        print("Using Playwright to fetch Pokemon event data...")
        await fetch_and_process_events()

        # Write the RSS feed to a file 
        with open('pokemon/feed.rss', 'w') as f:
            feed.write(f, 'utf-8')
            print("Successfully wrote pokemon/feed.rss file")

    except Exception as e:
        print(f"Error: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()

async def fetch_and_process_events():
    """Fetch and process Pokemon event data using Playwright."""
    async with async_playwright() as p:
        print("Launching Playwright browser for Pokemon events...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("Navigating to Pokemon events page...")
        await page.goto("https://events.pokemon.com/en-us/events?near=4232%20Fort%20St,%20Lincoln%20Park,%20MI%2048146,%20USA", wait_until="domcontentloaded")
        
        # Wait for content to load
        print("Waiting for page to load completely...")
        await page.wait_for_load_state('networkidle')
        
        # Wait a bit more to ensure JavaScript execution completes
        await asyncio.sleep(5)
        
        # Wait for the event cards to load
        await page.wait_for_selector('.event-card', timeout=10000)
        
        # Scroll down to load all events
        await scroll_to_load_all_events(page)
        
        # Take a screenshot for debugging
        if DEBUG:
            await page.screenshot(path="debug_pokemon_screenshot.png")
            print("Saved screenshot to debug_pokemon_screenshot.png")
        
        # Process the event cards
        await process_event_cards(page, browser)
        
        await browser.close()
        print("Playwright browser closed")

async def scroll_to_load_all_events(page):
    """Scroll down to load all event cards."""
    print("Scrolling to load all events...")
    
    previous_height = 0
    current_height = await page.evaluate('document.body.scrollHeight')
    
    while previous_height < current_height:
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(2)  # Wait for content to load
        
        previous_height = current_height
        current_height = await page.evaluate('document.body.scrollHeight')
        
        if DEBUG:
            print(f"Scrolled: Previous height: {previous_height}, Current height: {current_height}")
    
    print("Finished scrolling. All events should be loaded.")

async def process_event_cards(page, browser):
    """Process all event cards on the page."""
    # Get all event card elements
    print("Finding 8th Side events on the page...")
    
    # Use a more reliable method to find 8th side events
    eighth_side_events = await page.evaluate('''
        () => {
            const events = [];
            const eventCards = document.querySelectorAll('.event-card');
            
            for (let i = 0; i < eventCards.length; i++) {
                const card = eventCards[i];
                const text = card.innerText || card.textContent;
                
                if (text.toLowerCase().includes('8th')) {
                    // Get the structured data from the card
                    const lines = text.split('\\n').filter(line => line.trim() !== '');
                    const dateText = lines[0] || '';
                    const distanceText = lines[1] || '';
                    const titleText = lines[2] || '';
                    
                    events.push({
                        index: i,
                        date: dateText.trim(),
                        distance: distanceText.trim(),
                        title: titleText.trim()
                    });
                }
            }
            return events;
        }
    ''')
    
    print(f"Found {len(eighth_side_events)} 8th side events")
    
    events_found = len(eighth_side_events)
    events_added = 0
    events_filtered = 0
    
    for event_data in eighth_side_events:
        try:
            event_date_str = event_data['date'].replace('color: #fff;', '').strip()
            event_title = event_data['title'].replace('color: #fff;', '').strip()
            
            if not event_title:
                event_title = "8th Side Pokemon Event"
            
            print(f"Processing event: {event_title} on {event_date_str}")
            
            # Extract date components from the date string (like "March 11, 2025 6:30PM")
            date_pattern = re.compile(r'([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\s+(\d{1,2}:\d{2}[AP]M)', re.IGNORECASE)
            date_match = date_pattern.search(event_date_str)
            
            if date_match:
                month, day, year, time_str = date_match.groups()
                event_month = month
                event_day = day
                event_year = year
                event_time = time_str
                
                try:
                    event_date = datetime.strptime(f"{month} {day}, {year} {time_str}", "%B %d, %Y %I:%M%p")
                    
                    # Filter events by date range (today to one month from now)
                    if event_date < today or event_date > one_month_later:
                        if DEBUG:
                            print(f"Skipping event outside date range: {event_title} on {event_date.strftime('%Y-%m-%d')}")
                        events_filtered += 1
                        continue
                    
                except ValueError:
                    if DEBUG:
                        print(f"Could not parse date for event: {event_title}, {event_date_str}")
                    # Default to today if we can't parse the date
                    event_date = datetime.now()
            else:
                # Couldn't extract date components, set default values
                event_time = "6:30PM" 
                event_date = datetime.now()
            
            # Rather than clicking on cards which causes DOM detachment issues,
            # we'll construct the URL based on the event data
            base_url = "https://events.pokemon.com/en-us/events/"
            event_url = f"{base_url}?near=4232%20Fort%20St,%20Lincoln%20Park,%20MI%2048146,%20USA"
            
            # Set default price if we can't extract it
            event_price = "$5.00"
            
            # Format the datetime string for display
            if date_match:
                event_datetime_str = f"{month} {day}, {year} {time_str}"
            else:
                event_datetime_str = event_date_str
            
            # Create a consistent string for GUID generation
            details_str = f"{event_title}-{event_datetime_str}-{event_price}"
            guid = hashlib.md5(details_str.encode()).hexdigest()
            
            # Construct the HTML formatted description
            formatted_description = f"""
            <h2>{event_title}</h2>
            <p><strong>Date and Time:</strong> {event_datetime_str}</p>
            <p><strong>Price:</strong> {event_price}</p>
            <p><strong>Location:</strong> 8th Side Games</p>
            <p><a href="{event_url}">Event Link</a></p>
            """
            
            # Add the item to the feed
            feed.add_item(
                title=event_title,
                link=event_url,
                description=formatted_description,
                content=f"{event_title}\nDate: {event_datetime_str}\nPrice: {event_price}\nLocation: 8th Side Games\nLink: {event_url}",
                unique_id=guid
            )
            events_added += 1
            print(f"Added event: {event_title}")
            
        except Exception as e:
            print(f"Error processing event: {str(e)}")
            if DEBUG:
                import traceback
                traceback.print_exc()
    
    print(f"\nSummary: Found {events_found} 8th side events, filtered {events_filtered} by date, added {events_added} to feed")

if __name__ == "__main__":
    asyncio.run(main())