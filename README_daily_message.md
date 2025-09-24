# Daily Menu Message Generator

This script generates daily menu messages for social media or notifications. It's designed to work both locally and in GitHub Actions.

## Features

- ✅ Generates daily menu messages in Catalan
- ✅ Handles bank holidays (dia de lliure disposició)
- ✅ Handles missing menu data
- ✅ Environment variable support for configuration
- ✅ Command-line interface with flexible options
- ✅ GitHub Actions ready

## Usage

### Basic Usage

```bash
# Generate message for today
uv run python daily_menu_message.py

# Generate message for a specific date
uv run python daily_menu_message.py --date 2025-09-29

# Save message to file
uv run python daily_menu_message.py --output-file daily_menu.txt

# Format for Telegram (with HTML and emojis)
uv run python daily_menu_message.py --telegram --output-file daily_menu.txt
```

### Command Line Options

- `--date YYYY-MM-DD`: Target date (default: today)
- `--output-file PATH`: Save message to file (default: stdout)
- `--json-path PATH`: Path to menu JSON file
- `--base-url URL`: Base URL for the menu website
- `--telegram`: Format message for Telegram with HTML and emojis

### Environment Variables

For local development, create a `.env` file:

```bash
# Copy the example file
cp env.example .env

# Edit with your values
nano .env
```

Environment variables:

- `MENU_JSON_PATH`: Path to the menu JSON file (default: `2025_q4_menu_fixed.json`)
- `MENU_BASE_URL`: Base URL for the menu website (default: `https://joaoqalves.github.io/menu-stnico`)

## Example Output

### Normal Menu Day

```
Avui el menú del dia és (Dilluns 29/09/2025):

Primer: Trinxat de col i patates
Segon: Estofat de vedella amb bolets
Postre: Fruita

Si voleu saber més, visiteu https://joaoqalves.github.io/menu-stnico
```

### Telegram Formatted (with --telegram flag)

```
🍽️ <b>Avui el menú del dia és (Dilluns 29/09/2025):</b>

🥗 <b>Primer:</b> Trinxat de col i patates
🍖 <b>Segon:</b> Estofat de vedella amb bolets
🍰 <b>Postre:</b> Fruita

ℹ️ Si voleu saber més, visiteu https://joaoqalves.github.io/menu-stnico
```

### Bank Holiday

```
Avui (Dilluns 15/09/2025) és dia de lliure disposició.

Si voleu saber més, visiteu https://joaoqalves.github.io/menu-stnico
```

### Missing Menu

```
Avui (Divendres 15/08/2025) no hi ha menú disponible.

Si voleu saber més, visiteu https://joaoqalves.github.io/menu-stnico
```

## GitHub Actions

The included workflow (`.github/workflows/daily-menu.yml`) runs every weekday at 8:00 AM UTC and:

1. Generates the latest menu data
2. Creates a daily message
3. Saves it as an artifact

### Setting up GitHub Actions

1. **Create a Telegram Bot:**

   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Use `/newbot` command and follow instructions
   - Save the bot token you receive

2. **Get your Chat ID:**

   - Start a conversation with your bot
   - Send any message to the bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your chat ID in the response

3. **Add secrets to GitHub repository:**

   - Go to Settings → Secrets and variables → Actions
   - Add these secrets:
     - `TELEGRAM_BOT_TOKEN`: Your bot token from BotFather
     - `TELEGRAM_CHAT_ID`: Your chat ID (can be a group ID or user ID)

4. The workflow will run automatically on weekdays and post to Telegram
5. You can manually trigger it from the Actions tab

### Telegram Message Format

The messages will be posted with HTML formatting support. The bot will automatically:

- Format the menu items with proper line breaks
- Handle special characters correctly
- Include the website link for more information

## Local Development

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Create environment file:

   ```bash
   cp env.example .env
   # Edit .env with your values
   ```

3. Run the script:

   ```bash
   # Generate message only
   uv run python daily_menu_message.py

   # Generate and send to Telegram
   ./send_daily_menu.sh
   ```

## Bash Script for Telegram

The `send_daily_menu.sh` script provides a convenient way to generate and send today's menu to Telegram:

### Features

- ✅ Automatically generates today's menu message
- ✅ Formats message for Telegram with HTML and emojis
- ✅ Sends to Telegram using Bot API
- ✅ Colored output for better visibility
- ✅ Error handling and validation
- ✅ Environment variable support

### Usage

1. **Set up environment variables:**

   ```bash
   cp env.example .env
   # Edit .env with your Telegram credentials
   ```

2. **Run the script:**

   ```bash
   ./send_daily_menu.sh
   ```

3. **Test the script:**
   ```bash
   ./test_telegram_script.sh
   ```

### Required Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your bot token from BotFather
- `TELEGRAM_CHAT_ID`: Your chat ID or group ID
- `MENU_JSON_PATH`: Path to menu JSON file (optional, defaults to `2025_q4_menu_fixed.json`)
- `MENU_BASE_URL`: Base URL for the menu website (optional)

## Files

- `daily_menu_message.py`: Main Python script
- `send_daily_menu.sh`: Bash script for Telegram posting
- `test_telegram_script.sh`: Test script for validation
- `load_env.py`: Environment variable loader for local development
- `env.example`: Example environment configuration
- `.github/workflows/daily-menu.yml`: GitHub Actions workflow
- `README_daily_message.md`: This documentation
