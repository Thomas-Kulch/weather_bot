"""
Test file for bot
"""
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import datetime
import requests
import uuid
import json
import atexit

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
API_KEY = os.getenv('API_KEY')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store weather requests {"forecast_id": {"city": city, "date": date_str, "channel_id": channel_id}}
tracked_forecasts = {}


def parse_date(date_str):
    """Try parsing the date in multiple formats."""
    date_formats = [
        "%Y-%m-%d",  # YYYY-MM-DD
        "%m/%d/%Y",  # MM/DD/YYYY
    ]
    for fmt in date_formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        "Invalid date format. Please use one of the following formats: YYYY-MM-DD, MM/DD/YYYY")

def user_response(city, date, condition, max_temp, min_temp, avg_temp, humidity, rain_chance, wind_speed):
    base_response = f"📅 Weather forecast for **{city.capitalize()}** on **{date}**:\n🌤 {condition}\n🌡 High: {max_temp}°F | Low: {min_temp}°F\n**Humidity:** {humidity}%\n**Wind:** {wind_speed}mph\n**Chance of rain:** {rain_chance}%"
    good_weather = ["Sunny", "Partly Cloudy", "Overcast", "Mist"] # list of good conditions
    decent_weather = ["Cloudy", "Fog", "Patchy light drizzle", "Light drizzle"]
    weather_response = ""

    if avg_temp >= 60 and condition in good_weather and rain_chance < 40 and wind_speed < 15 and humidity < 85:
        weather_response = f"\n**Overview:** It's a perfect day for golf!\n\n"
    elif condition in decent_weather and avg_temp >= 50 and wind_speed > 8:
        weather_response = f"\n**Overview:** It's a decent day for golf.\n\n"
    elif rain_chance > 50:
        weather_response = f"\n**Overview:** It's going to be rainy. Not great golfing weather.\n\n"
    elif avg_temp < 45:
        weather_response = f"\n**Overview:** It's too cold to golf.\n\n"
    elif avg_temp < 60 and wind_speed > 10:
        weather_response = f"\n**Overview:** It's going to be a bit chilly, but golfing is possible.\n\n"
    elif avg_temp > 80 and humidity >= 85:
        weather_response = f"\n**Overview:** It's going to be very hot and humid.\n\n"
    elif wind_speed > 20:
        weather_response = f"\n**Overview:** It's going to be very windy.\n\n"

    return base_response + weather_response

def save_forecasts():
    with open("tracked_forecasts.json", "w") as f:
        json.dump(tracked_forecasts, f)

def load_forecasts():
    global tracked_forecasts
    if os.path.exists("tracked_forecasts.json"):
        with open("tracked_forecasts.json", "r") as f:
            try:
                tracked_forecasts = json.load(f)
            except json.JSONDecodeError:
                # If the file is empty or malformed, set tracked_forecasts to an empty dictionary
                tracked_forecasts = {}

def save_on_exit():
    save_forecasts()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    load_forecasts()  # Load forecasts from file when the bot starts

@bot.command(name='forecast', help='Responds with the forecast for the inputted location and date.')
async def forecast(ctx, city: str, date: str):
    """User calls !forecast <city> <date>, and the bot will track and update daily"""
    try:
        # Validate and parse date
        forecast_date = parse_date(date)
        today = datetime.date.today()
        if forecast_date < today or (forecast_date - today).days > 14:
            await ctx.send("You can only request forecasts for the next 14 days.")
            return

        # Generate a unique ID for this forecast
        forecast_id = str(uuid.uuid4())

        # Store the forecast request in the dictionary
        # Store the date as a string in a consistent format
        tracked_forecasts[forecast_id] = {
            "city": city,
            "date": forecast_date.strftime("%Y-%m-%d"),
            "channel_id": ctx.channel.id
        }

        # Fetch the weather forecast immediately after storing the request
        url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={city}&dt={forecast_date.strftime('%Y-%m-%d')}&aqi=no&alerts=no"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            forecast_day = data["forecast"]["forecastday"][0]  # Since we asked for a specific date
            condition = forecast_day["day"]["condition"]["text"]
            max_temp = forecast_day["day"]["maxtemp_f"]
            min_temp = forecast_day["day"]["mintemp_f"]
            wind_speed = forecast_day["day"]["maxwind_mph"]
            avg_temp = forecast_day["day"]["avgtemp_f"]
            humidity = forecast_day["day"]["avghumidity"]
            rain_chance = forecast_day["day"]["daily_chance_of_rain"]

            #insert response variable call here and pass condition variables
            give_response = user_response(city, date, condition, max_temp, min_temp, avg_temp, humidity, rain_chance, wind_speed)

            # Send the weather forecast immediately to the same channel
            await ctx.send(give_response)
        else:
            await ctx.send(f"Failed to fetch weather data for {city.capitalize()} on {date}.")
            # Remove the forecast from tracking if we couldn't get data
            del tracked_forecasts[forecast_id]

    except ValueError as e:
        await ctx.send(str(e))


@bot.command(name='update', help='Updates the weather forecast for all stored cities and dates.')
async def update(ctx):
    """User calls !update, and the bot will send weather updates for all stored cities and dates."""
    if not tracked_forecasts:
        await ctx.send("No weather forecasts are being tracked at the moment.")
        return

    today = datetime.date.today()
    to_remove = []  # Keep track of records to remove

    # Create a compiled message with all forecasts
    message = "📋 **Weather Updates For All Tracked Locations:**\n\n"

    for forecast_id, request in tracked_forecasts.items():
        city = request["city"]
        date_str = request["date"]  # This is now stored as a string

        # Parse the stored date string
        forecast_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

        # Skip forecasts with past dates
        if forecast_date < today:
            to_remove.append(forecast_id)
            message += f"• **{city.capitalize()}** on **{date_str}** - REMOVED (past date)\n"
            continue  # Skip past forecasts

        # Get forecast from Weather API
        url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={city}&dt={date_str}&aqi=no&alerts=no"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            forecast_day = data["forecast"]["forecastday"][0]  # Since we asked for a specific date
            condition = forecast_day["day"]["condition"]["text"]
            max_temp = forecast_day["day"]["maxtemp_f"]
            min_temp = forecast_day["day"]["mintemp_f"]
            wind_speed = forecast_day["day"]["maxwind_mph"]
            avg_temp = forecast_day["day"]["avgtemp_f"]
            humidity = forecast_day["day"]["avghumidity"]
            rain_chance = forecast_day["day"]["daily_chance_of_rain"]

            # Add this forecast to the compiled message
            message += user_response(city, date_str, condition, max_temp, min_temp, avg_temp, humidity, rain_chance, wind_speed)

        else:
            message += f"• **{city.capitalize()}** on **{date_str}** - Failed to fetch weather data.\n"

    # Remove past forecasts
    for forecast_id in to_remove:
        del tracked_forecasts[forecast_id]

    # Send the compiled message
    await ctx.send(message)


@bot.command(name='remove', help='Removes a tracked forecast by city and date.')
async def remove_forecast(ctx, city: str, date: str):
    """Removes a specific forecast from tracking by city and date."""
    # Try to parse the date
    try:
        remove_date = parse_date(date)
        remove_date_str = remove_date.strftime("%Y-%m-%d")
    except ValueError as e:
        await ctx.send(str(e))
        return

    # Find matching forecasts
    found = False
    for forecast_id, request in list(tracked_forecasts.items()):
        if request["city"].lower() == city.lower() and request["date"] == remove_date_str:
            del tracked_forecasts[forecast_id]
            found = True

    if found:
        await ctx.send(f"Removed forecast for **{city.capitalize()}** on **{date}** from tracking.")
    else:
        await ctx.send(f"No forecast found for **{city.capitalize()}** on **{date}**.")

atexit.register(save_on_exit)
bot.run(TOKEN)