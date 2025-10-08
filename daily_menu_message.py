#!/usr/bin/env python3
"""
Daily Menu Message Generator

This script generates a daily menu message for social media or notifications.
It can be used in GitHub Actions or run locally with environment variables.

Usage:
    python daily_menu_message.py [--date YYYY-MM-DD] [--output-file output.txt]

Environment Variables:
    MENU_JSON_PATH: Path to the menu JSON file (default: 2025_q4_menu.json)
    MENU_BASE_URL: Base URL for the menu website (default: https://joaoqalves.github.io/menu-stnico)
"""

import json
import os
import sys
from datetime import date, datetime
import argparse
from pathlib import Path

# Load environment variables from .env file for local development
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass  # load_env.py not available, use system environment variables

def load_menu_data(json_path):
    """Load menu data from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Menu file not found: {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in menu file: {e}")
        sys.exit(1)

def load_holiday_data(json_path):
    """Load holiday data from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Holiday file not found: {json_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in holiday file: {e}")
        return None

def check_holiday(target_date, holiday_data):
    """Check if a date is a holiday and return holiday information."""
    if not holiday_data or 'holidays' not in holiday_data:
        return None
    
    target_date_str = target_date.isoformat()
    
    for holiday in holiday_data['holidays']:
        if holiday['date'] == target_date_str:
            return holiday
    
    return None

def is_school_closed(target_date, holiday_data):
    """Check if school is closed on a given date."""
    holiday = check_holiday(target_date, holiday_data)
    if holiday:
        return holiday.get('school_closed', False)
    return False

def find_menu_for_date(menu_data, target_date):
    """Find the menu that contains the target date within its week ranges."""
    target_date_str = target_date.isoformat()
    
    for week_menu in menu_data:
        for week_range in week_menu['weeks']:
            if week_range['start'] <= target_date_str <= week_range['end']:
                return week_menu
    return None

def get_weekday_name_ca(date_obj):
    """Get Catalan weekday name for a date."""
    day_names = ['Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres']
    return day_names[date_obj.weekday()]

def is_date_within_quarterly_range(target_date, menu_data):
    """Check if a date falls within the quarterly menu range."""
    all_dates = []
    for week_menu in menu_data:
        for week_range in week_menu['weeks']:
            all_dates.append(week_range['start'])
            all_dates.append(week_range['end'])
    
    if not all_dates:
        return False
    
    start_date = min(all_dates)
    end_date = max(all_dates)
    target_date_str = target_date.isoformat()
    return start_date <= target_date_str <= end_date

def generate_daily_message(target_date, menu_data, base_url, format_for_telegram=False, holiday_data=None):
    """Generate the daily menu message."""
    day_name = get_weekday_name_ca(target_date)
    date_str = target_date.strftime('%d/%m/%Y')
    
    # Check if this is a holiday first
    holiday = check_holiday(target_date, holiday_data)
    if holiday:
        holiday_type_info = holiday_data.get('holiday_types', {}).get(holiday['type'], {})
        emoji = holiday_type_info.get('emoji', '🎉')
        holiday_name = holiday.get('name', 'Festiu')
        
        if format_for_telegram:
            return f"{emoji} <b>Avui ({day_name} {date_str}) és {holiday_name}.</b>\n\n{holiday.get('description', '')}\n\nSi voleu saber més, visiteu {base_url}"
        else:
            return f"{emoji} Avui ({day_name} {date_str}) és {holiday_name}.\n\n{holiday.get('description', '')}\n\nSi voleu saber més, visiteu {base_url}"
    
    # Find menu for this date
    week_menu = find_menu_for_date(menu_data, target_date)
    if not week_menu or day_name not in week_menu['days']:
        # Check if this is a bank holiday or missing menu
        if is_date_within_quarterly_range(target_date, menu_data):
            if format_for_telegram:
                return f"🍽️ <b>Avui ({day_name} {date_str}) és dia de lliure disposició.</b>\n\nSi voleu saber més, visiteu {base_url}"
            else:
                return f"Avui ({day_name} {date_str}) és dia de lliure disposició.\n\nSi voleu saber més, visiteu {base_url}"
        else:
            if format_for_telegram:
                return f"🍽️ <b>Avui ({day_name} {date_str}) no hi ha menú disponible.</b>\n\nSi voleu saber més, visiteu {base_url}"
            else:
                return f"Avui ({day_name} {date_str}) no hi ha menú disponible.\n\nSi voleu saber més, visiteu {base_url}"
    
    # Get the day's menu
    day_menu = week_menu['days'][day_name]
    
    # Build the message
    if format_for_telegram:
        message_parts = [f"🍽️ <b>Avui el menú del dia és ({day_name} {date_str}):</b>"]
        message_parts.append("")
        
        if day_menu.get('entrant'):
            message_parts.append(f"🥗 <b>Primer:</b> {day_menu['entrant']}")
        
        if day_menu.get('main'):
            message_parts.append(f"🍖 <b>Segon:</b> {day_menu['main']}")
        
        if day_menu.get('dessert'):
            message_parts.append(f"🍰 <b>Postre:</b> {day_menu['dessert']}")
        
        message_parts.append("")
        message_parts.append(f"ℹ️ Si voleu saber més, visiteu {base_url}")
    else:
        message_parts = [f"Avui el menú del dia és ({day_name} {date_str}):"]
        message_parts.append("")
        
        if day_menu.get('entrant'):
            message_parts.append(f"Primer: {day_menu['entrant']}")
        
        if day_menu.get('main'):
            message_parts.append(f"Segon: {day_menu['main']}")
        
        if day_menu.get('dessert'):
            message_parts.append(f"Postre: {day_menu['dessert']}")
        
        message_parts.append("")
        message_parts.append(f"Si voleu saber més, visiteu {base_url}")
    
    return "\n".join(message_parts)

def main():
    parser = argparse.ArgumentParser(description='Generate daily menu message')
    parser.add_argument('--date', type=str, help='Target date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--output-file', type=str, help='Output file path (default: stdout)')
    parser.add_argument('--json-path', type=str, help='Path to menu JSON file')
    parser.add_argument('--holiday-path', type=str, help='Path to holiday JSON file')
    parser.add_argument('--base-url', type=str, help='Base URL for the menu website')
    parser.add_argument('--telegram', action='store_true', help='Format message for Telegram with HTML and emojis')
    
    args = parser.parse_args()
    
    # Parse target date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = date.today()
    
    # Get configuration from environment variables or arguments
    json_path = args.json_path or os.getenv('MENU_JSON_PATH', '2025_q4_menu.json')
    base_url = args.base_url or os.getenv('MENU_BASE_URL', 'https://joaoqalves.github.io/menu-stnico')
    holiday_path = args.holiday_path or os.getenv('HOLIDAY_JSON_PATH', 'holidays_2025_2026.json')
    
    # Load menu data
    menu_data = load_menu_data(json_path)
    
    # Load holiday data
    holiday_data = load_holiday_data(holiday_path)
    
    # Check if school is closed
    if is_school_closed(target_date, holiday_data):
        holiday = check_holiday(target_date, holiday_data)
        holiday_name = holiday.get('name', 'Festiu') if holiday else 'Festiu'
        print(f"School is closed today ({target_date.strftime('%d/%m/%Y')}) - {holiday_name}")
        print("Skipping message generation.")
        sys.exit(2)  # Exit code 2 indicates school is closed
    
    # Generate message
    message = generate_daily_message(target_date, menu_data, base_url, format_for_telegram=args.telegram, holiday_data=holiday_data)
    
    # Output message
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(message)
        print(f"Message written to: {args.output_file}")
    else:
        print(message)

if __name__ == "__main__":
    main()
