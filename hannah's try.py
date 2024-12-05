from playwright.async_api import async_playwright
import pandas as pd
import re

# Define the URL
url = 'https://stats.protriathletes.org/race/im-hawaii/2023/results'

def seconds_from_run_time(time):
    # Remove the unnecessary text from the scrapped data
    # Map the filtered times from strings to integers
    time = re.sub(r"\n\(\d+\)", "", time).split(":")
    time = list(map(lambda x: 0 if "-" in x else int(x), time))

    if len(time) == 0:
        return 0
    
    hours = 0
    mins  = 0
    secs  = 0

    if len(time) > 2:
        hours = int(time[0]) * 3600
        mins  = int(time[1]) * 60
        secs  = int(time[2])
    else:
        mins  = int(time[0]) * 60
        secs  = int(time[1])

    return hours + mins + secs

    
def handle_row_data(row):
    temp_row = []
    temp_row.append(row[0])
    temp_row.append(row[1])
    temp_row.append(seconds_from_run_time(row[2]))
    temp_row.append(seconds_from_run_time(row[4]))

    # Combine the T1 times and T2 times to get the Total Transition Time
    T1 = seconds_from_run_time(row[3])
    T2 = seconds_from_run_time(row[5])

    temp_row.append(T1 + T2)

    temp_row.append(seconds_from_run_time(row[6]))
    temp_row.append(seconds_from_run_time(row[7]))
    temp_row.append(0.0 if "-" in row[8] else float(row[8]))
    return temp_row


# Function to scrape the table data using Playwright
async def scrape_table_data():
    async with async_playwright() as p:
        # Launch the browser (headless mode)
        browser = await p.chromium.launch(headless=True)  # Set headless=False if you want to see the browser
        page = await browser.new_page()
        
        # Navigate to the URL
        await page.goto(url, wait_until='domcontentloaded')  # Wait until the DOM is fully loaded
        
        # Wait for the table to appear using the provided selector
        await page.wait_for_selector('#content-fade > div > div.w-100.mx-auto.max-w-1000.race-results > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > div.race-results-container > table', timeout=60000)
        
        # Extract the headers from the first row (nth-child(1))
        header_row = await page.query_selector('#content-fade > div > div.w-100.mx-auto.max-w-1000.race-results > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > div.race-results-container > table > tbody > tr:nth-child(1)')
        header_cells = await header_row.query_selector_all('th, td')  # Extract both <th> and <td> for the headers
        headers_text = [await cell.inner_text() for cell in header_cells]
        
        # Rename the first header to 'Ranking' and second header to 'Name'
        if len(headers_text) > 1:
            headers_text[0] = 'Ranking'  # Rename the first header
            headers_text[1] = 'Name'     # Rename the second header
            headers_text[5] = 'Total Transition Time' # Create the Total Transition Time Column
            headers_text.remove("T1") # Remove the T1 row since it's unneeded

        # Extract the table rows
        table = await page.query_selector('#content-fade > div > div.w-100.mx-auto.max-w-1000.race-results > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > div.race-results-container > table')
        rows = await table.query_selector_all('tr')
        data = []
        
        for row in rows[1:]:  # Skip the header row
            cols = await row.query_selector_all('td')
            if len(cols) > 0:  # Skip empty rows or malformed rows
                row_data = [await col.inner_text() for col in cols]
                row_data = handle_row_data(row_data)
                data.append(row_data)
        
        # Create a DataFrame from the extracted data
        df = pd.DataFrame(data, columns=headers_text)
        
        # Close the browser
        await browser.close()
        
        return df

async def main():
    # Since we are in an interactive environment, we can just `await` directly
    df = await scrape_table_data()

    # Set pandas options to display all rows in the DataFrame
    pd.set_option('display.max_rows', None)  # Display all rows
    pd.set_option('display.max_columns', None)  # Display all columns (if necessary)
    pd.set_option('display.width', None)  # Let pandas decide the width of the display

    # Display the full DataFrame
    df