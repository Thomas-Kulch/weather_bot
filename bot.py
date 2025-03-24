"""
Bot main file
Update this with comments on what everything does. Make sure we know exactly what every line does

Essential files for AWS are this, .env, tracked_forecasts.json, and err.log
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
    base_response = (
        f"📅 **Weather Forecast for {city.capitalize()} on {date}:**\n"
        f"🔹 **Condition:** {condition}\n"
        f"🌡 **Temperature:** High: {max_temp}°F | Low: {min_temp}°F | Avg: {avg_temp}°F\n"
        f"💧 **Humidity:** {humidity}%\n"
        f"💨 **Wind Speed:** {wind_speed} mph\n"
        f"🌧 **Chance of Rain:** {rain_chance}%"
    )

    # Weather categories
    good_weather = ["Sunny", "Partly Cloudy", "Overcast", "Mist"]
    decent_weather = ["Cloudy", "Fog", "Patchy light drizzle", "Light drizzle"]

    # Determine golfing suitability
    if avg_temp >= 60 and condition in good_weather and rain_chance < 40 and wind_speed < 15 and humidity < 85:
        overview = "🏌️ **Perfect day for golf!**"
    elif condition in decent_weather and avg_temp >= 55 and wind_speed > 10:
        overview = "⛳ **Decent golfing weather. A little windy.**"
    elif rain_chance > 50:
        overview = "☔ **Expect rain. Poor golfing weather.**"
    elif avg_temp < 45:
        overview = "❄️ **Too cold to golf.**"
    elif avg_temp < 65 and wind_speed > 10:
        overview = "🌬 **A bit chilly, but playable.**"
    elif avg_temp > 80 and humidity >= 85:
        overview = "🔥 **Hot and humid—stay hydrated!**"
    elif wind_speed > 20:
        overview = "💨 **Very windy conditions.**"

    return f"{base_response}\n\n{overview}\n\n"


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


@bot.command(name='forecast',
             help='Responds with the forecast for the inputted location and date. Use quotes for multi-word cities: !forecast "New York" 2025-03-24')
async def forecast(ctx, *, args):
    """User calls !forecast <city> <date>, and the bot will track and update daily
    For multi-word cities, use quotes: !forecast "New York" 2025-03-24"""
    try:
        # Split the arguments into city and date
        # This will properly handle quoted city names with spaces
        parts = args.split()
        if len(parts) < 2:
            await ctx.send("Please provide both a city and a date. Example: !forecast 'New York' 2025-03-24")
            return

        # Check if the city is in quotes
        if parts[0].startswith('"') or parts[0].startswith("'"):
            # Find the closing quote
            city_parts = []
            for i, part in enumerate(parts):
                city_parts.append(part.strip('"\''))
                if part.endswith('"') or part.endswith("'"):
                    date = ' '.join(parts[i + 1:])
                    break
                if i == len(parts) - 2:  # If we're at the second-to-last part
                    date = parts[-1]
                    break
            city = ' '.join(city_parts)
        else:
            # Handle case where city doesn't have quotes - assume it's a single word
            city = parts[0]
            date = ' '.join(parts[1:])

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

            # insert response variable call here and pass condition variables
            give_response = user_response(city, date, condition, max_temp, min_temp, avg_temp, humidity, rain_chance,
                                          wind_speed)

            # Send the weather forecast immediately to the same channel
            await ctx.send(give_response)
            # Save forecasts after adding a new one
            save_forecasts()
        else:
            await ctx.send(f"Failed to fetch weather data for {city.capitalize()} on {date}.")
            # Remove the forecast from tracking if we couldn't get data
            del tracked_forecasts[forecast_id]

    except ValueError as e:
        await ctx.send(str(e))
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")


@bot.command(name='weather', help='Updates the weather forecast for all stored cities and dates.')
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
            message += user_response(city, date_str, condition, max_temp, min_temp, avg_temp, humidity, rain_chance,
                                     wind_speed)

        else:
            message += f"• **{city.capitalize()}** on **{date_str}** - Failed to fetch weather data.\n"

    # Remove past forecasts
    for forecast_id in to_remove:
        del tracked_forecasts[forecast_id]

    # Save forecasts after removing past ones
    save_forecasts()

    # Send the compiled message
    await ctx.send(message)


@bot.command(name='remove',
             help='Removes a tracked forecast by city and date. Use quotes for multi-word cities: !remove "New York" 2025-03-24')
async def remove_forecast(ctx, *, args):
    """Removes a specific forecast from tracking by city and date.
    For multi-word cities, use quotes: !remove "New York" 2025-03-24"""
    try:
        # Split the arguments into city and date
        parts = args.split()
        if len(parts) < 2:
            await ctx.send("Please provide both a city and a date. Example: !remove 'New York' 2025-03-24")
            return

        # Check if the city is in quotes
        if parts[0].startswith('"') or parts[0].startswith("'"):
            # Find the closing quote
            city_parts = []
            for i, part in enumerate(parts):
                city_parts.append(part.strip('"\''))
                if part.endswith('"') or part.endswith("'"):
                    date = ' '.join(parts[i + 1:])
                    break
                if i == len(parts) - 2:  # If we're at the second-to-last part
                    date = parts[-1]
                    break
            city = ' '.join(city_parts)
        else:
            # Handle case where city doesn't have quotes - assume it's a single word
            city = parts[0]
            date = ' '.join(parts[1:])

        # Try to parse the date
        remove_date = parse_date(date)
        remove_date_str = remove_date.strftime("%Y-%m-%d")

        # Find matching forecasts
        found = False
        for forecast_id, request in list(tracked_forecasts.items()):
            if request["city"].lower() == city.lower() and request["date"] == remove_date_str:
                del tracked_forecasts[forecast_id]
                found = True

        if found:
            await ctx.send(f"Removed forecast for **{city.capitalize()}** on **{date}** from tracking.")
            save_forecasts()  # Save after removing
        else:
            await ctx.send(f"No forecast found for **{city.capitalize()}** on **{date}**.")
    except ValueError as e:
        await ctx.send(str(e))
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")


atexit.register(save_on_exit)
bot.run(TOKEN)