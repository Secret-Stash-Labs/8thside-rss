# 8th Side RSS Feed Generator

This project fetches event data from a Wizards of the Coast store page and generates an RSS feed.

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```
   - On Windows:
     ```
     venv\Scripts\activate
     ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```
   python -m playwright install
   ```

## Usage

Run the basic script to generate the RSS feed:

```
python feedgen-new.py
```

Or run the Playwright version which can handle JavaScript-rendered content:

```
python feedgen-playwright.py
```

### Command Line Options

- `--debug`: Enable debug output with detailed information about the scraping process
  ```
  python feedgen-playwright.py --debug
  ```

### Event Filtering

The script automatically filters out:
- Events outside the next 30 days
- MTG casual play events

Both scripts will create a `feed.rss` file in the project directory.

## Automated Setup

You can also use the setup script:

```
python setup.py
```

This will create and activate the virtual environment and install all dependencies.