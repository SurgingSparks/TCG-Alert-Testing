import os
import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import asyncio
import re

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Store previously seen products to avoid duplicate alerts
known_products = set()

def get_bigw_pokemon_products():
    """Scrape BIG W website for Pokémon TCG products"""
    url = "https://www.bigw.com.au/search/?text=pokemon+trading+card+game"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        products = []
        
        # This selector might need adjustment based on BIG W's actual HTML structure
        product_cards = soup.select('.product-tile')  # Update this based on inspection
        
        for card in product_cards:
            try:
                title = card.select_one('.product-title').get_text(strip=True)
                price = card.select_one('.price').get_text(strip=True)
                link = "https://www.bigw.com.au" + card.select_one('a')['href']
                availability = card.select_one('.stock-availability').get_text(strip=True) if card.select_one('.stock-availability') else "Unknown"
                
                # Extract set information from title (simplistic approach)
                set_name = "Unknown Set"
                if "booster" in title.lower():
                    set_name = "Booster Pack"
                elif "etb" in title.lower() or "elite trainer box" in title.lower():
                    set_name = "Elite Trainer Box"
                # Add more set detection as needed
                
                products.append({
                    'title': title,
                    'price': price,
                    'link': link,
                    'availability': availability,
                    'set': set_name
                })
            except Exception as e:
                print(f"Error parsing product: {e}")
                continue
                
        return products
    except Exception as e:
        print(f"Error scraping BIG W: {e}")
        return []

@tasks.loop(minutes=5)  # Check every 5 minutes
async def check_stock():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Channel not found!")
        return
    
    print("Checking BIG W for Pokémon TCG products...")
    products = get_bigw_pokemon_products()
    
    new_products = []
    for product in products:
        product_id = f"{product['title']}-{product['price']}"
        if product_id not in known_products and "out of stock" not in product['availability'].lower():
            known_products.add(product_id)
            new_products.append(product)
    
    if new_products:
        message = "**New Pokémon TCG products available at BIG W!**\n\n"
        for product in new_products:
            message += (
                f"**{product['title']}**\n"
                f"Price: {product['price']}\n"
                f"Status: {product['availability']}\n"
                f"Link: {product['link']}\n"
                f"Set: {product['set']}\n\n"
            )
        
        # Split message if too long (Discord has a 2000 character limit)
        if len(message) > 1900:
            parts = [message[i:i+1900] for i in range(0, len(message), 1900)]
            for part in parts:
                await channel.send(part)
                await asyncio.sleep(1)  # Avoid rate limiting
        else:
            await channel.send(message)
    else:
        print("No new products found.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    check_stock.start()

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)