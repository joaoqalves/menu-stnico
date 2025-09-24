import opendataloader_pdf
import json
import os
import re
from datetime import date, datetime, timedelta
import click
from icalendar import Calendar, Event
import pytz

def normalize_text(text: str) -> str:
    """
    Normalize capitalization: first letter uppercase, rest lowercase,
    keep accents intact.
    """
    text = text.strip("- ").strip()
    if not text:
        return text
    return text[0].upper() + text[1:].lower()

def parse_weeks(weeks_str: str, year: int):
    """
    Parse strings like 'Del 9 al 12/09 Del 6 al 10/10' or 'Del 29 al 3/10'
    into structured dates with YYYY-MM-DD format.
    Handles cross-month ranges where start_day > end_day.
    """
    # Academic year assumption
    result = []
    pattern = r"Del (\d{1,2}) al (\d{1,2})/(\d{2})"
    for start_day, end_day, month in re.findall(pattern, weeks_str):
        start_day = int(start_day)
        end_day = int(end_day)
        month = int(month)
        year = year if month >= 7 else year + 1
        
        # Handle cross-month ranges (e.g., "Del 29 al 3/10" means Sep 29 to Oct 3)
        if start_day > end_day:
            # Start date is in the previous month
            if month == 1:
                start_month = 12
                start_year = year - 1
            else:
                start_month = month - 1
                start_year = year
            
            start = date(start_year, start_month, start_day).isoformat()
            end = date(year, month, end_day).isoformat()
        else:
            # Normal case: both dates in the same month
            start = date(year, month, start_day).isoformat()
            end = date(year, month, end_day).isoformat()
        
        result.append({"start": start, "end": end})
    return result

def parse_menu(json_data):
    # Find the table node
    table = next(kid for kid in json_data["kids"] if kid["type"] == "table")
    
    # Get header row -> days of week
    header_row = table["rows"][0]
    days = []
    for cell in header_row["cells"][1:]:  # skip "SETMANA"
        if cell["kids"]:
            days.append(normalize_text(cell["kids"][0]["content"]))
        else:
            days.append(None)
    
    menus = []
    # Iterate over remaining rows
    for row in table["rows"][1:]:
        week_cell = row["cells"][0]
        if not week_cell["kids"]:
            continue
        
        # Week range(s)
        weeks_str = " ".join([kid["content"] for kid in week_cell["kids"] if "content" in kid])
        # Use current year as default, could be made configurable
        current_year = date.today().year
        weeks = parse_weeks(weeks_str, current_year)
        
        # Menus for each weekday
        week_menu = {"weeks": weeks, "days": {}}
        for i, cell in enumerate(row["cells"][1:]):  # skip first column
            if not days[i]:
                continue
            meals = []
            for kid in cell.get("kids", []):
                if kid["type"] == "list":
                    for item in kid["list items"]:
                        meals.append(normalize_text(item["content"]))
            if meals:
                week_menu["days"][days[i]] = {
                    "entrant": meals[0] if len(meals) > 0 else None,
                    "main": meals[1] if len(meals) > 1 else None,
                    "dessert": meals[2] if len(meals) > 2 else None,
                    "raw": meals
                }
        menus.append(week_menu)
    
    return menus

def save_menu_json(menu_data, output_path: str):
    """Save menu data to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(menu_data, f, indent=2, ensure_ascii=False)

def generate_ics_calendar(menu_data, output_path: str):
    """Generate ICS calendar file from menu data."""
    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//Menustnico//Menu Parser//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    
    # Set timezone
    madrid_tz = pytz.timezone('Europe/Madrid')
    
    # Day names in Catalan for calendar (keeping original language)
    day_mapping = {
        'Dilluns': 'Dilluns',
        'Dimarts': 'Dimarts', 
        'Dimecres': 'Dimecres',
        'Dijous': 'Dijous',
        'Divendres': 'Divendres'
    }
    
    for week_menu in menu_data:
        for week_range in week_menu['weeks']:
            start_date = datetime.fromisoformat(week_range['start'])
            end_date = datetime.fromisoformat(week_range['end'])
            
            # Create events for each day in the range
            current_date = start_date
            while current_date <= end_date:
                # Only create events for weekdays (Monday to Friday)
                if current_date.weekday() < 5:  # 0=Monday, 4=Friday
                    # Get the day name in Catalan
                    day_names = ['Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres']
                    day_name_ca = day_names[current_date.weekday()]
                    
                    # Check if we have menu data for this day
                    if day_name_ca in week_menu['days']:
                        day_menu = week_menu['days'][day_name_ca]
                        
                        # Create event
                        event = Event()
                        
                        # Event title
                        day_name_ca = day_mapping.get(day_name_ca, day_name_ca)
                        event.add('summary', f'Menú Sant Nicolau - {day_name_ca}')
                        
                        # Event description with structured meal information
                        description_parts = []
                        if day_menu.get('entrant'):
                            description_parts.append(f"Entrant: {day_menu['entrant']}")
                        if day_menu.get('main'):
                            description_parts.append(f"Principal: {day_menu['main']}")
                        if day_menu.get('dessert'):
                            description_parts.append(f"Postre: {day_menu['dessert']}")
                        
                        event.add('description', '\n'.join(description_parts))
                        
                        # Event timing (1 PM for 1 hour)
                        event_start = madrid_tz.localize(
                            current_date.replace(hour=13, minute=0, second=0, microsecond=0)
                        )
                        event_end = event_start + timedelta(hours=1)
                        
                        event.add('dtstart', event_start)
                        event.add('dtend', event_end)
                        event.add('dtstamp', datetime.now(madrid_tz))
                        
                        # Add location
                        event.add('location', 'Centre Escolar Sant Nicolau, Sabadell')
                        
                        # Add to calendar
                        cal.add_component(event)
                
                # Move to next day
                current_date += timedelta(days=1)
    
    # Save calendar to file
    with open(output_path, 'wb') as f:
        f.write(cal.to_ical())

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

def get_previous_weekday(date_obj):
    """Get the previous weekday (skip weekends)."""
    prev_date = date_obj - timedelta(days=1)
    if prev_date.weekday() == 6:  # Sunday
        prev_date = prev_date - timedelta(days=2)  # Go to Friday
    return prev_date

def get_next_weekday(date_obj):
    """Get the next weekday (skip weekends)."""
    next_date = date_obj + timedelta(days=1)
    if next_date.weekday() == 5:  # Saturday
        next_date = next_date + timedelta(days=2)  # Go to Monday
    return next_date

def generate_html_pages(menu_data, json_filename, ics_filename):
    """Generate HTML pages for the menu."""
    madrid_tz = pytz.timezone('Europe/Madrid')
    today = datetime.now(madrid_tz).date()
    
    # Get menu for today
    today_menu = find_menu_for_date(menu_data, today)
    today_day_name = get_weekday_name_ca(today)
    
    # Generate main index.html
    index_html = f"""<!DOCTYPE html>
<html lang="ca">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Menú Sant Nicolau</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
         .menu-card {{
             background: white;
             border-radius: 15px;
             padding: 20px;
             margin-bottom: 20px;
             box-shadow: 0 10px 30px rgba(0,0,0,0.2);
             transition: transform 0.3s ease;
         }}
         
         .menu-card:hover {{
             transform: translateY(-5px);
         }}
         
         .menu-header {{
             display: flex;
             justify-content: space-between;
             align-items: center;
             margin-bottom: 15px;
             border-bottom: 2px solid #f0f0f0;
             padding-bottom: 10px;
         }}
         
         .menu-card h2 {{
             color: #667eea;
             margin: 0;
             font-size: 1.3rem;
         }}
         
         .nav-buttons {{
             display: flex;
             gap: 8px;
             margin-top: 20px;
             justify-content: center;
         }}
         
         .nav-btn {{
             background: #667eea;
             color: white;
             border: none;
             padding: 10px 16px;
             border-radius: 20px;
             cursor: pointer;
             font-size: 0.9rem;
             transition: background 0.3s ease;
             flex: 1;
             max-width: 100px;
         }}
         
         .nav-btn:hover {{
             background: #5a6fd8;
         }}
         
         .nav-btn:disabled {{
             background: #ccc;
             cursor: not-allowed;
         }}
         
         .nav-btn.today {{
             background: #28a745;
             max-width: 80px;
         }}
         
         .nav-btn.today:hover {{
             background: #218838;
         }}
         
         .share-section {{
             text-align: center;
             margin-top: 30px;
         }}
         
         .share-btn {{
             display: inline-block;
             background: #17a2b8;
             color: white;
             padding: 15px 30px;
             text-decoration: none;
             border-radius: 25px;
             font-weight: bold;
             transition: background 0.3s ease;
             margin: 10px;
             border: none;
             cursor: pointer;
             font-size: 1rem;
         }}
         
         .share-btn:hover {{
             background: #138496;
         }}
         
         .menu-item {{
             margin-bottom: 8px;
             padding: 8px 12px;
             background: #f8f9fa;
             border-radius: 6px;
             border-left: 3px solid #667eea;
             font-size: 0.95rem;
         }}
         
         .menu-item strong {{
             color: #495057;
             display: inline;
             margin-right: 8px;
         }}
        
        .no-menu {{
            text-align: center;
            color: #6c757d;
            font-style: italic;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px dashed #dee2e6;
        }}
        
        .download-section {{
            text-align: center;
            margin-top: 30px;
        }}
        
        .download-btn {{
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: background 0.3s ease;
            margin: 10px;
        }}
        
        .download-btn:hover {{
            background: #218838;
        }}
        
        .nav {{
            text-align: center;
            margin-top: 30px;
        }}
        
        .nav a {{
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            margin: 0 10px;
            transition: background 0.3s ease;
        }}
        
        .nav a:hover {{
            background: rgba(255,255,255,0.3);
        }}
        
         @media (max-width: 600px) {{
             .container {{
                 padding: 15px;
             }}
             
             .header h1 {{
                 font-size: 2rem;
             }}
             
             .menu-card {{
                 padding: 15px;
             }}
             
             .nav-buttons {{
                 margin-top: 15px;
                 gap: 6px;
             }}
             
             .nav-btn {{
                 padding: 12px 16px;
                 font-size: 0.9rem;
                 max-width: 90px;
             }}
             
             .nav-btn.today {{
                 max-width: 70px;
             }}
             
             .share-btn {{
                 display: block;
                 margin: 10px auto;
                 width: 100%;
                 max-width: 300px;
                 padding: 18px 30px;
                 font-size: 1.1rem;
             }}
             
             .download-btn {{
                 display: block;
                 margin: 10px auto;
                 width: 100%;
                 max-width: 300px;
                 padding: 18px 30px;
                 font-size: 1.1rem;
             }}
         }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍽️ Menú Sant Nicolau</h1>
        </div>
        
         <div class="menu-card">
             <div class="menu-header">
                 <h2>📅 {today_day_name} - {today.strftime('%d/%m/%Y')}</h2>
             </div>
             <div id="current-date" data-current-date="{today.isoformat()}">
                 <div id="menu-content">
                     {generate_menu_html(today_menu, today_day_name, today, menu_data)}
                 </div>
                 <div class="nav-buttons">
                     <button class="nav-btn" onclick="changeDate(-1)">← Anterior</button>
                     <button class="nav-btn today" onclick="goToToday()">Avui</button>
                     <button class="nav-btn" onclick="changeDate(1)">Següent →</button>
                 </div>
             </div>
         </div>
        
        <div class="share-section">
            <button class="share-btn" onclick="shareMenu()">
                📤 Compartir
            </button>
        </div>
        
        <div class="download-section">
            <a href="{ics_filename}" class="download-btn" download>
                📅 Descarregar Calendari (.ics)
            </a>
        </div>
        
         <div class="nav">
             <a href="sobre.html">Sobre</a>
         </div>
     </div>
     
     <script>
         // Menu data for navigation
         const menuData = {json.dumps(menu_data, ensure_ascii=False)};
         const originalToday = new Date('{today.isoformat()}');
         
         // Get quarterly date range
         const quarterlyRange = (() => {{
             const allDates = [];
             for (const weekMenu of menuData) {{
                 for (const weekRange of weekMenu.weeks) {{
                     allDates.push(weekRange.start, weekRange.end);
                 }}
             }}
             return allDates.length > 0 ? {{
                 start: allDates.reduce((min, date) => date < min ? date : min),
                 end: allDates.reduce((max, date) => date > max ? date : max)
             }} : null;
         }})();
         
         function isDateWithinQuarterlyRange(date) {{
             if (!quarterlyRange) return false;
             const dateStr = date.toISOString().split('T')[0];
             return quarterlyRange.start <= dateStr && dateStr <= quarterlyRange.end;
         }}
         
         function changeDate(direction) {{
             const currentDateElement = document.getElementById('current-date');
             const currentDate = new Date(currentDateElement.dataset.currentDate);
             
             // Calculate new date
             let newDate = new Date(currentDate);
             if (direction === -1) {{
                 newDate.setDate(newDate.getDate() - 1);
                 // Skip weekends going backwards
                 if (newDate.getDay() === 0) {{ // Sunday
                     newDate.setDate(newDate.getDate() - 2); // Go to Friday
                 }}
             }} else {{
                 newDate.setDate(newDate.getDate() + 1);
                 // Skip weekends going forwards
                 if (newDate.getDay() === 6) {{ // Saturday
                     newDate.setDate(newDate.getDate() + 2); // Go to Monday
                 }}
             }}
             
             // Update the display
             updateMenuDisplay(newDate);
         }}
         
         function updateMenuDisplay(date) {{
             const dateStr = date.toISOString().split('T')[0];
             const dayNames = ['Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres'];
             const dayName = dayNames[date.getDay() - 1]; // Adjust for Monday=0
             
             // Find menu for this date
             let menu = null;
             for (const weekMenu of menuData) {{
                 for (const weekRange of weekMenu.weeks) {{
                     if (weekRange.start <= dateStr && dateStr <= weekRange.end) {{
                         menu = weekMenu;
                         break;
                     }}
                 }}
                 if (menu) break;
             }}
             
             // Update the display
             const currentDateElement = document.getElementById('current-date');
             const menuContentElement = document.getElementById('menu-content');
             
             currentDateElement.dataset.currentDate = dateStr;
             // Update the h2 in menu-header (which now contains the date)
             document.querySelector('.menu-header h2').textContent = 
                 `📅 ${{dayName}} - ${{date.getDate().toString().padStart(2, '0')}}/${{(date.getMonth() + 1).toString().padStart(2, '0')}}/${{date.getFullYear()}}`;
             
             if (menu && menu.days && menu.days[dayName]) {{
                 const dayMenu = menu.days[dayName];
                 let html = '';
                 
                 if (dayMenu.entrant) {{
                     html += `<div class="menu-item"><strong>Entrant:</strong> ${{dayMenu.entrant}}</div>`;
                 }}
                 if (dayMenu.main) {{
                     html += `<div class="menu-item"><strong>Principal:</strong> ${{dayMenu.main}}</div>`;
                 }}
                 if (dayMenu.dessert) {{
                     html += `<div class="menu-item"><strong>Postre:</strong> ${{dayMenu.dessert}}</div>`;
                 }}
                 
                 menuContentElement.innerHTML = html || '<div class="no-menu">No hi ha menú disponible per aquest dia</div>';
             }} else {{
                 // Check if this is a bank holiday (date within quarterly range) or missing menu
                 if (isDateWithinQuarterlyRange(date)) {{
                     menuContentElement.innerHTML = '<div class="no-menu">Dia de lliure disposició</div>';
                 }} else {{
                     menuContentElement.innerHTML = '<div class="no-menu">El menú no està actualitzat. Si us plau, contacteu <a href="mailto:joaoqalves@hey.com">joaoqalves@hey.com</a></div>';
                 }}
             }}
             
             // Ensure nav-buttons stay after menu content
             const navButtons = currentDateElement.querySelector('.nav-buttons');
             if (navButtons) {{
                 currentDateElement.appendChild(navButtons);
             }}
         }}
         
         function goToToday() {{
             updateMenuDisplay(originalToday);
         }}
         
         function shareMenu() {{
             const currentUrl = window.location.href;
             
             // Check if Web Share API is supported (mobile)
             if (navigator.share) {{
                 navigator.share({{
                     title: 'Menú Sant Nicolau',
                     text: 'Consulta el menú escolar del Centre Escolar Sant Nicolau',
                     url: currentUrl
                 }}).catch(err => {{
                     console.log('Error sharing:', err);
                     fallbackShare(currentUrl);
                 }});
             }} else {{
                 fallbackShare(currentUrl);
             }}
         }}
         
         function fallbackShare(url) {{
             // Copy URL to clipboard
             if (navigator.clipboard) {{
                 navigator.clipboard.writeText(url).then(() => {{
                     alert('URL copiat al porta-retalls!');
                 }}).catch(() => {{
                     promptShare(url);
                 }});
             }} else {{
                 promptShare(url);
             }}
         }}
         
         function promptShare(url) {{
             // Fallback: show URL in prompt for manual copying
             const shareWindow = window.open('', '_blank', 'width=500,height=200');
             shareWindow.document.write(`
                 <html>
                     <head><title>Compartir Menú</title></head>
                     <body style="font-family: Arial, sans-serif; padding: 20px;">
                         <h3>Menú Sant Nicolau</h3>
                         <p>Copieu aquesta URL per compartir:</p>
                         <input type="text" readonly style="width: 100%; padding: 10px; margin: 10px 0; font-size: 14px;" value="${{url}}" onclick="this.select()">
                         <p><button onclick="window.close()">Tancar</button></p>
                     </body>
                 </html>
             `);
         }}
     </script>
 </body>
 </html>"""

    # Generate sobre.html (About page)
    sobre_html = """<!DOCTYPE html>
<html lang="ca">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sobre - Menú Sant Nicolau</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .content {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .content h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8rem;
        }
        
        .content h3 {
            color: #495057;
            margin: 20px 0 10px 0;
            font-size: 1.3rem;
        }
        
        .content p {
            margin-bottom: 15px;
            text-align: justify;
        }
        
        .content ul {
            margin-left: 20px;
            margin-bottom: 15px;
        }
        
        .content li {
            margin-bottom: 8px;
        }
        
        .nav {
            text-align: center;
            margin-top: 30px;
        }
        
        .nav a {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            margin: 0 10px;
            transition: background 0.3s ease;
        }
        
        .nav a:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .contact {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            margin-top: 20px;
        }
        
        @media (max-width: 600px) {
            .container {
                padding: 15px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .content {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ℹ️ Sobre aquest projecte</h1>
        </div>
        
        <div class="content">
            <h2>Menú Sant Nicolau</h2>
            
            <p>Aquesta aplicació web permet consultar fàcilment el menú escolar del <strong>Centre Escolar Sant Nicolau de Sabadell</strong>. L'aplicació processa els PDFs del menú trimestral i els converteix en un format web fàcil d'usar.</p>
            
            <h3>Característiques</h3>
            <ul>
                <li><strong>Consulta ràpida:</strong> Veieu què han dinat avui, ahir i demà</li>
                <li><strong>Disseny mòbil:</strong> Optimitzat per a dispositius mòbils</li>
                <li><strong>Calendari:</strong> Descarregueu el menú com a esdeveniments del calendari</li>
                <li><strong>Actualització automàtica:</strong> Detecta quan el menú no està actualitzat</li>
            </ul>
            
            <h3>Com funciona</h3>
            <p>L'aplicació utilitza una eina de processament de PDFs per extreure les dades estructurades del menú escolar. Aquestes dades es converteixen en format JSON i després es generen les pàgines web que podeu veure.</p>
            
            <h3>Font de dades</h3>
            <p>Els menús es descarreguen directament de l'aplicació oficial <strong>Qualla</strong> del Centre Escolar Sant Nicolau. Totes les dades es processen localment per garantir la privacitat.</p>
            
            <h3>Ús</h3>
            <p>Aquesta aplicació està dissenyada per a ús personal dels pares i mares dels alumnes del centre. No és un servei oficial de l'escola.</p>
            
            <div class="contact">
                <h3>Contacte</h3>
                <p>Si teniu problemes amb l'aplicació o necessiteu ajuda, podeu contactar-nos a: <strong>aaa@bbb.com</strong></p>
            </div>
            
            <h3>Enllaços útils</h3>
            <ul>
                <li><a href="https://santnicolau.com/" target="_blank">Centre Escolar Sant Nicolau</a></li>
                <li><a href="https://app.quallakids.com/" target="_blank">Aplicació Qualla Kids</a></li>
            </ul>
        </div>
        
        <div class="nav">
            <a href="index.html">← Tornar al menú</a>
        </div>
    </div>
</body>
</html>"""

    # Save HTML files
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    with open('sobre.html', 'w', encoding='utf-8') as f:
        f.write(sobre_html)

def get_quarterly_date_range(menu_data):
    """Get the overall date range covered by the quarterly menu."""
    if not menu_data:
        return None, None
    
    all_dates = []
    for week_menu in menu_data:
        for week_range in week_menu['weeks']:
            all_dates.append(week_range['start'])
            all_dates.append(week_range['end'])
    
    if not all_dates:
        return None, None
    
    return min(all_dates), max(all_dates)

def is_date_within_quarterly_range(target_date, menu_data):
    """Check if a date falls within the quarterly menu range."""
    start_date, end_date = get_quarterly_date_range(menu_data)
    if not start_date or not end_date:
        return False
    
    target_date_str = target_date.isoformat()
    return start_date <= target_date_str <= end_date

def generate_menu_html(week_menu, day_name, target_date=None, full_menu_data=None):
    """Generate HTML for a specific day's menu."""
    if not week_menu or not day_name or day_name not in week_menu['days']:
        # Check if this is a bank holiday (date within quarterly range) or missing menu
        if target_date and full_menu_data and is_date_within_quarterly_range(target_date, full_menu_data):
            return '<div class="no-menu">Dia de lliure disposició</div>'
        else:
            return '<div class="no-menu">El menú no està actualitzat. Si us plau, contacteu aaa@bbb.com</div>'
    
    day_menu = week_menu['days'][day_name]
    html = ''
    
    if day_menu.get('entrant'):
        html += f'<div class="menu-item"><strong>Entrant:</strong> {day_menu["entrant"]}</div>'
    
    if day_menu.get('main'):
        html += f'<div class="menu-item"><strong>Principal:</strong> {day_menu["main"]}</div>'
    
    if day_menu.get('dessert'):
        html += f'<div class="menu-item"><strong>Postre:</strong> {day_menu["dessert"]}</div>'
    
    return html if html else '<div class="no-menu">No hi ha menú disponible per aquest dia</div>'

@click.command()
@click.argument('pdf_file', type=click.Path(exists=True))
@click.option('--output', '-o', 'output_file', type=click.Path(), help='Output JSON file path (default: based on PDF filename)')
@click.option('--print', 'print_output', is_flag=True, help='Print parsed menu to stdout')
@click.option('--ics', 'ics_output', type=click.Path(), help='Output ICS calendar file path (default: based on PDF filename)')
@click.option('--html', 'html_output', is_flag=True, help='Generate HTML pages (index.html and sobre.html)')
def main(pdf_file, output_file, print_output, ics_output, html_output):
    """Parse a school menu PDF file and convert it to JSON format."""
    # Get base filename without extension
    base_file = os.path.splitext(os.path.basename(pdf_file))[0]
    
    # Set default output file if not provided
    if output_file is None:
        output_file = f"{base_file}_menu.json"
    
    # Set default ICS output file if not provided
    if ics_output is None:
        ics_output = f"{base_file}_menu.ics"
    
    # Check if JSON already exists in output folder
    json_path = f"output/{base_file}.json"
    
    if os.path.exists(json_path):
        print(f"Using existing parsed data from {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"Parsing PDF file: {pdf_file}")
        opendataloader_pdf.run(
            input_path=pdf_file,
            output_folder="output",
            generate_markdown=True,
            generate_html=True,
            generate_annotated_pdf=True,
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    # Parse the menu
    parsed_menu = parse_menu(data)
    
    # Save to output file
    save_menu_json(parsed_menu, output_file)
    print(f"Menu saved to: {output_file}")
    
    # Generate ICS calendar if requested
    if ics_output:
        generate_ics_calendar(parsed_menu, ics_output)
        print(f"Calendar saved to: {ics_output}")
    
    # Generate HTML pages if requested
    if html_output:
        generate_html_pages(parsed_menu, output_file, ics_output or f"{base_file}_menu.ics")
        print("HTML pages generated: index.html and sobre.html")
    
    # Print to stdout if requested
    if print_output:
        print("\nParsed menu:")
        print(json.dumps(parsed_menu, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
