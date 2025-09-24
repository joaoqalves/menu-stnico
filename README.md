# Menu Sant Nico - CE Sant Nicolau (Sabadell) menu Parser

A Python tool for parsing quarterly school menu PDFs from the [Centre Escolar Sant Nicolau, Sabadell (Catalonia)][sant-nicolau] and converting them to structured JSON format.

## Disclaimer

This tool is designed to work with PDF files obtained from the official [Qualla app][qualla] for the Centre Escolar Sant Nicolau, Sabadell. The PDFs are downloaded directly from the official school application and processed locally for personal use.

## Installation

This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Or install manually
pip install opendataloader-pdf click
```

## Usage

### Basic Usage

```bash
# Parse a PDF file (uses default output filename)
uv run python menu_parser.py menu.pdf

# Parse with custom output filename
uv run python menu_parser.py menu.pdf -o my_menu.json

# Parse and print to stdout
uv run python menu_parser.py menu.pdf --print

# Parse with custom output and print
uv run python menu_parser.py menu.pdf -o my_menu.json --print

# Generate ICS calendar file
uv run python menu_parser.py menu.pdf --ics menu.ics

# Generate both JSON and ICS with custom names
uv run python menu_parser.py menu.pdf -o my_menu.json --ics my_calendar.ics

# Generate HTML pages (index.html and sobre.html)
uv run python menu_parser.py menu.pdf --html

# Generate all formats (JSON, ICS, and HTML)
uv run python menu_parser.py menu.pdf -o my_menu.json --ics my_calendar.ics --html
```

### Command Line Options

- `PDF_FILE`: Path to the PDF file to parse (required)
- `-o, --output PATH`: Output JSON file path (default: based on PDF filename)
- `--ics PATH`: Output ICS calendar file path (default: based on PDF filename)
- `--html`: Generate HTML pages (index.html and sobre.html)
- `--print`: Print parsed menu to stdout
- `--help`: Show help message

## Output Format

The parser generates JSON with the following structure:

```json
[
  {
    "weeks": [
      { "start": "2025-09-09", "end": "2025-09-12" },
      { "start": "2025-10-06", "end": "2025-10-10" }
    ],
    "days": {
      "Dilluns": {
        "entrant": "Mongeta tendra amb patates",
        "main": "Gall dindi a la planxa amb amanida",
        "dessert": "Fruita",
        "raw": [
          "Mongeta tendra amb patates",
          "Gall dindi a la planxa amb amanida",
          "Fruita"
        ]
      }
    }
  }
]
```

### HTML Output

The HTML generator creates two files:

- **`index.html`**: Main page showing today's, yesterday's, and tomorrow's menu
- **`sobre.html`**: About page explaining the project in Catalan

The HTML pages feature:

- **Mobile-friendly design** with responsive layout
- **Automatic date handling** with weekend edge cases (Friday ↔ Monday)
- **Menu validation** with fallback messages for outdated menus
- **Clean, modern UI** with gradient backgrounds and card-based layout
- **Catalan language** throughout the interface

## Features

- **JSON Export**: Structured menu data in JSON format
- **ICS Calendar Export**: Import menu events directly into your calendar app
- **HTML Web Pages**: Mobile-friendly web interface with today/yesterday/tomorrow menu display
- **Date Range Processing**: Handles quarterly menu periods with multiple week ranges
- **Catalan Language Support**: Preserves accents and proper text normalization
- **Command Line Interface**: Easy-to-use CLI with flexible output options

## How It Works

1. **PDF Processing**: Uses `opendataloader_pdf` to extract structured data from the PDF
2. **Data Parsing**: Processes the extracted JSON to identify menu tables and meal information
3. **Date Parsing**: Converts Catalan date ranges (e.g., "Del 9 al 12/09") to ISO format dates
4. **Text Normalization**: Standardizes capitalization while preserving Catalan accents
5. **Multi-format Output**: Generates JSON, ICS calendar files, and HTML web pages

## Requirements

- Python 3.8+
- opendataloader-pdf
- click
- icalendar
- pytz

## References

- [Centre Escolar Sant Nicolau, Sabadell][sant-nicolau]
- [Qualla Kids App][qualla]

[sant-nicolau]: https://santnicolau.com/
[qualla]: https://app.quallakids.com/
