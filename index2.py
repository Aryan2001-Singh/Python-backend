from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import csv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://www.kogenie.com", "https://kogenie.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class AdRequest(BaseModel):
    url: str
    gender: str
    ageGroup: str

async def scrape_amazon_product(url: str):
    """
    Scrapes product details from an Amazon product page.
    """
    try:
        custom_headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=custom_headers)
        soup = BeautifulSoup(response.text, "lxml")

        # Scrape product details
        title_element = soup.select_one('#productTitle')
        title = title_element.text.strip() if title_element else 'No title available'

        rating_element = soup.select_one('#acrPopover')
        rating_text = rating_element.attrs.get('title', '') if rating_element else None
        rating = rating_text.replace('out of 5 stars', '').strip() if rating_text else None

        price_element = soup.select_one('span.a-price span.a-offscreen')
        price = price_element.text.strip() if price_element else None

        image_element = soup.select_one("#landingImage")
        image = image_element.attrs.get('src') if image_element else None

        description_element = soup.select_one('#feature-bullets')
        description = description_element.text.strip() if description_element else None

        # Get brand name from the URL or title
        brand_name = url.split('//')[1].split('/')[0].replace('www.amazon', 'Amazon')

        # Save to CSV if needed
        product_data = {
            "title": title,
            "rating": rating,
            "price": price,
            "image": image,
            "description": description,
            "url": url
        }
        save_to_csv(product_data)

        return {
            'brandName': brand_name,
            'productName': title,
            'productDescription': description or 'No description available',
            'productImage': image,
            'productPrice': price,
            'productRating': rating
        }

    except Exception as error:
        print(f'Error scraping product data: {str(error)}')
        raise HTTPException(status_code=500, detail='Failed to scrape the product data')

def save_to_csv(data, filename="product_details.csv"):
    """
    Saves the scraped product details to a CSV file.
    """
    headers = ["Title", "Rating", "Price", "Image URL", "Description", "Product URL"]
    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow([
            data["title"], 
            data["rating"], 
            data["price"], 
            data["image"], 
            data["description"], 
            data["url"]
        ])

def get_target_description(gender: str, age_group: str) -> str:
    descriptions = {
        'female': {
            '9-18': 'The ad should appeal to young girls with a focus on fun, color, and trendy designs.',
            '18-25': 'The ad should emphasize style, comfort, and empowerment, as young women in this age group often look for products that complement their personal style and lifestyle.',
            '25-40': 'For women in this age group, the ad should focus on a balance of comfort, elegance, and professional appeal.',
            '40-60': 'The ad should emphasize comfort, sophistication, and practicality, appealing to women who value quality and timeless style.',
            '60+': 'The ad should highlight comfort, elegance, and the products ability to bring relaxation and ease to daily life.'
        },
        'male': {
            '9-18': 'The ad should appeal to young boys or teens, focusing on energy, coolness, and modern trends.',
            '18-25': 'The ad should focus on style, confidence, and boldness, appealing to young men who are exploring their identity and fashion preferences.',
            '25-40': 'For men in this age group, the ad should emphasize practicality, style, and versatility.',
            '40-60': 'The ad should appeal to men with a focus on quality, durability, and classic style, suitable for both personal and professional settings.',
            '60+': 'The ad should highlight comfort, ease of use, and thoughtful gifts for loved ones.'
        },
        'others': {
            '*': 'The ad should emphasize inclusivity, comfort, and a sense of belonging, appealing to individuals of diverse identities who value style and self-expression across all age groups.'
        }
    }

    if gender == 'others':
        return descriptions['others']['*']
    return descriptions.get(gender, {}).get(age_group, '')

def generate_simple_ad(product_data, gender, age_group):
    """
    Generates a simple ad based on product data and target audience.
    """
    target_desc = get_target_description(gender, age_group)
    rating_text = f" Rated {product_data['productRating']} stars!" if product_data['productRating'] else ""

    # Basic template for ad generation
    ad_templates = [
        f"Discover {product_data['productName']}! {rating_text} Available now at {product_data['productPrice']}.",
        f"Introducing the amazing {product_data['productName']} - perfect for you! {rating_text}",
        f"Don't miss out on {product_data['productName']}! Get yours at {product_data['productPrice']}.",
        f"Experience the excellence of {product_data['productName']}! {rating_text}",
        f"Transform your life with {product_data['productName']}! Now only {product_data['productPrice']}!"
    ]

    import random
    base_ad = random.choice(ad_templates)

    # Add a targeted message based on gender and age group
    if target_desc:
        base_ad += f"\n{target_desc}"

    return base_ad

@app.post("/createAd")
async def create_ad(request: AdRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="No URL provided")

    try:
        print(f'Received URL: {request.url}')

        # Scrape product data using the Amazon scraper
        product_data = await scrape_amazon_product(request.url)
        print(f'Scraped Product Data: {product_data}')

        # Generate ad copy using our simple generator
        ad_copy = generate_simple_ad(product_data, request.gender, request.ageGroup)

        return {
            **product_data,
            'adCopy': ad_copy
        }

    except Exception as error:
        print(f'Error generating ad: {str(error)}')
        raise HTTPException(status_code=500, detail=f"Error generating ad: {str(error)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv('PORT', 5001)))