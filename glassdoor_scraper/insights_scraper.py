# insights_scraper.py
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scrape_glassdoor_insights(company: str, role: str) -> dict:
    search_company = company.replace(" ", "-")
    url = f"https://www.glassdoor.com/Reviews/{search_company}-reviews-SRCH_KE0,{len(company)}.htm"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="glassdoor_scraper/glassdoor_cookies.json",user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = await context.new_page()

        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(5000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Debug screenshot
            await page.screenshot(path="glassdoor_debug.png", full_page=True)

            # Extract reviews
            reviews = []
            review_blocks = (
                soup.select('span[data-test="reviewDescription"]') or
                soup.select('div[data-test="pros"]') or
                soup.select('div.gdReview')
            )
            for block in review_blocks[:5]:
                text = block.get_text(strip=True)
                if text:
                    reviews.append(text)

            await browser.close()

            return {
                "salary_range": "Coming soon...",
                "top_reviews": reviews,
                "interview_questions": [],
                "experience_path": []
            }

        except Exception as e:
            await browser.close()
            print(f"❌ Error scraping page: {e}")
            return {
                "salary_range": "Coming soon...",
                "top_reviews": [f"Scraping failed: {e}"],
                "interview_questions": [],
                "experience_path": []
            }

# Local test
if __name__ == "__main__":
    result = asyncio.run(scrape_glassdoor_insights("Google", "Software Engineer"))
    print(result)
