# WeatherBot

A simple Discord bot that provides weather forecasts for specified cities and dates. Hosted on an AWS EC2 instance and runs continuously using `systemd`.

## Features
- Retrieves weather forecasts for specified locations and dates.
- Provides details such as temperature, condition, humidity, wind speed, and rain chance.
- Gives recommendations on whether the weather is suitable for golfing.
- Runs persistently on an AWS EC2 instance.

## Requirements
### Python Libraries
Install the required dependencies using:
```bash
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the project directory and add your Discord bot token:
```
DISCORD_TOKEN=your_discord_bot_token
```

### AWS EC2 Instance Setup
1. **Connect to EC2:**
   ```bash
   ssh -i /path/to/your-key.pem ubuntu@your-instance-ip
   ```
2. **Clone the repository:**
   ```bash
   git clone https://github.com/Thomas-Kulch/weather_bot.git
   cd weather_bot
   ```
3. **Set up a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Run the bot manually for testing:**
   ```bash
   python bot.py
   ```

## Running the Bot with Systemd (Auto-start on Reboot)
1. **Create a systemd service file:**
   ```bash
   sudo nano /etc/systemd/system/weather_bot.service
   ```
   Add the following content (update paths accordingly):
   ```ini
   [Unit]
   Description=WeatherBot Discord Bot
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/weather_bot
   ExecStart=/home/ubuntu/weather_bot/venv/bin/python /home/ubuntu/weather_bot/bot.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
2. **Reload systemd and enable the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable weatherbot
   sudo systemctl start weatherbot
   ```
3. **Check status:**
   ```bash
   sudo systemctl status weatherbot
   ```

## Updating the Bot
When making updates to the bot:
1. **Connect to EC2 and navigate to the project directory:**
   ```bash
   ssh -i /path/to/your-key.pem ubuntu@your-instance-ip
   cd weather_bot
   ```
2. **Pull the latest changes from GitHub:**
   ```bash
   git pull origin main
   ```
3. **Restart the bot:**
   ```bash
   sudo systemctl restart weatherbot
   ```

## Clearing the JSON Storage
To clear the tracked forecasts JSON file:
```bash
> /home/ubuntu/weather_bot/tracked_forecasts.json
```
Or replace it with an empty object:
```bash
echo "{}" > /home/ubuntu/weather_bot/tracked_forecasts.json
```

