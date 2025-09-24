#!/bin/bash

# Daily Menu Telegram Sender
# This script generates today's menu message and sends it to Telegram
# Requires environment variables: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    print_error "TELEGRAM_BOT_TOKEN environment variable is not set"
    print_warning "Please set it in your .env file or export it:"
    print_warning "export TELEGRAM_BOT_TOKEN='your_bot_token_here'"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    print_error "TELEGRAM_CHAT_ID environment variable is not set"
    print_warning "Please set it in your .env file or export it:"
    print_warning "export TELEGRAM_CHAT_ID='your_chat_id_here'"
    exit 1
fi

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    print_status "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
else
    print_warning "No .env file found, using system environment variables"
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed or not in PATH"
    print_warning "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if menu JSON file exists
MENU_JSON_PATH="${MENU_JSON_PATH:-2025_q4_menu_fixed.json}"
if [ ! -f "$MENU_JSON_PATH" ]; then
    print_error "Menu JSON file not found: $MENU_JSON_PATH"
    print_warning "Please run the menu parser first or set MENU_JSON_PATH environment variable"
    exit 1
fi

print_status "Starting daily menu generation and Telegram posting..."

# Generate today's menu message
print_status "Generating today's menu message..."
TEMP_MESSAGE_FILE=$(mktemp)
uv run python daily_menu_message.py --telegram --output-file "$TEMP_MESSAGE_FILE"

# Check if message was generated successfully
if [ ! -s "$TEMP_MESSAGE_FILE" ]; then
    print_error "Failed to generate menu message"
    rm -f "$TEMP_MESSAGE_FILE"
    exit 1
fi

# Read the message content
MESSAGE=$(cat "$TEMP_MESSAGE_FILE")
print_status "Message generated successfully:"
echo "----------------------------------------"
echo "$MESSAGE"
echo "----------------------------------------"

# Send to Telegram
print_status "Sending message to Telegram..."

# Escape the message for JSON (handle quotes and newlines)
ESCAPED_MESSAGE=$(echo "$MESSAGE" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')

# Send the message
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
        \"chat_id\": \"$TELEGRAM_CHAT_ID\",
        \"text\": \"$ESCAPED_MESSAGE\",
        \"parse_mode\": \"HTML\"
    }")

# Check if the request was successful
if echo "$RESPONSE" | grep -q '"ok":true'; then
    print_status "Message sent to Telegram successfully! 🎉"
else
    print_error "Failed to send message to Telegram"
    print_error "Response: $RESPONSE"
    rm -f "$TEMP_MESSAGE_FILE"
    exit 1
fi

# Clean up
rm -f "$TEMP_MESSAGE_FILE"

print_status "Daily menu script completed successfully!"
