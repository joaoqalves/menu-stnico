import pytest
import json
import os
import tempfile
from datetime import date
from unittest.mock import patch, mock_open, MagicMock
from click.testing import CliRunner

from menu_parser import (
    normalize_text,
    parse_weeks,
    parse_menu,
    save_menu_json,
    generate_ics_calendar,
    main
)


class TestNormalizeText:
    """Test cases for normalize_text function."""
    
    def test_normalize_basic_text(self):
        """Test basic text normalization."""
        assert normalize_text("hello world") == "Hello world"
        assert normalize_text("HELLO WORLD") == "Hello world"
        assert normalize_text("hELLo WoRLd") == "Hello world"
    
    def test_normalize_with_accents(self):
        """Test text normalization preserves Catalan accents."""
        assert normalize_text("cafè") == "Cafè"
        assert normalize_text("niño") == "Niño"
        assert normalize_text("MONGETA TENDRA") == "Mongeta tendra"
    
    def test_normalize_with_dashes_and_spaces(self):
        """Test normalization strips dashes and spaces."""
        assert normalize_text("- hello world -") == "Hello world"
        assert normalize_text("  -  test  -  ") == "Test"
        assert normalize_text("---special---") == "Special"
    
    def test_normalize_empty_strings(self):
        """Test normalization handles empty strings."""
        assert normalize_text("") == ""
        assert normalize_text("   ") == ""
        assert normalize_text("-") == ""
        assert normalize_text("---") == ""
    
    def test_normalize_single_character(self):
        """Test normalization of single characters."""
        assert normalize_text("a") == "A"
        assert normalize_text("A") == "A"
        assert normalize_text("ñ") == "Ñ"


class TestParseWeeks:
    """Test cases for parse_weeks function."""
    
    def test_parse_single_week(self):
        """Test parsing a single week range."""
        weeks_str = "Del 9 al 12/09"
        year = 2025
        result = parse_weeks(weeks_str, year)
        
        expected = [{"start": "2025-09-09", "end": "2025-09-12"}]
        assert result == expected
    
    def test_parse_multiple_weeks(self):
        """Test parsing multiple week ranges."""
        weeks_str = "Del 9 al 12/09 Del 6 al 10/10"
        year = 2025
        result = parse_weeks(weeks_str, year)
        
        expected = [
            {"start": "2025-09-09", "end": "2025-09-12"},
            {"start": "2025-10-06", "end": "2025-10-10"}
        ]
        assert result == expected
    
    def test_parse_academic_year_boundary(self):
        """Test parsing across academic year boundary (month < 7 gets year + 1)."""
        weeks_str = "Del 1 al 5/01"
        year = 2025
        result = parse_weeks(weeks_str, year)
        
        expected = [{"start": "2026-01-01", "end": "2026-01-05"}]
        assert result == expected
    
    def test_parse_single_digit_days(self):
        """Test parsing single digit days."""
        weeks_str = "Del 1 al 3/03"
        year = 2025
        result = parse_weeks(weeks_str, year)
        
        # March is < 7, so it gets year + 1 (academic year boundary)
        expected = [{"start": "2026-03-01", "end": "2026-03-03"}]
        assert result == expected
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_weeks("", 2025)
        assert result == []
    
    def test_parse_no_matches(self):
        """Test parsing string with no valid patterns."""
        result = parse_weeks("No valid patterns here", 2025)
        assert result == []


class TestParseMenu:
    """Test cases for parse_menu function."""
    
    def test_parse_menu_basic(self):
        """Test basic menu parsing with mock data."""
        mock_data = {
            "kids": [
                {
                    "type": "table",
                    "rows": [
                        {
                            "cells": [
                                {"kids": [{"content": "SETMANA"}]},
                                {"kids": [{"content": "Dilluns"}]},
                                {"kids": [{"content": "Dimarts"}]},
                                {"kids": [{"content": "Dimecres"}]}
                            ]
                        },
                        {
                            "cells": [
                                {
                                    "kids": [{"content": "Del 9 al 12/09"}]
                                },
                                {
                                    "kids": [
                                        {
                                            "type": "list",
                                            "list items": [
                                                {"content": "Mongeta tendra amb patates"},
                                                {"content": "Gall dindi a la planxa amb amanida"},
                                                {"content": "Fruita"}
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "kids": [
                                        {
                                            "type": "list",
                                            "list items": [
                                                {"content": "Macarrons a la bolonyesa"},
                                                {"content": "Filet de lluç amb amanida"},
                                                {"content": "Iogurt natural"}
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "kids": [
                                        {
                                            "type": "list",
                                            "list items": [
                                                {"content": "Empedrat de cigrons"},
                                                {"content": "Croquetes de pollastre amb amanida"},
                                                {"content": "Fruita"}
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        with patch('menu_parser.date') as mock_date:
            mock_date.today.return_value.year = 2025
            # Mock the date constructor to return proper date objects
            def mock_date_constructor(year, month, day):
                return date(year, month, day)
            mock_date.side_effect = mock_date_constructor
            result = parse_menu(mock_data)
        
        assert len(result) == 1
        week_menu = result[0]
        
        # Check weeks
        assert len(week_menu["weeks"]) == 1
        assert week_menu["weeks"][0]["start"] == "2025-09-09"
        assert week_menu["weeks"][0]["end"] == "2025-09-12"
        
        # Check days
        assert "Dilluns" in week_menu["days"]
        assert "Dimarts" in week_menu["days"]
        assert "Dimecres" in week_menu["days"]
        
        # Check meal structure
        dilluns = week_menu["days"]["Dilluns"]
        assert dilluns["entrant"] == "Mongeta tendra amb patates"
        assert dilluns["main"] == "Gall dindi a la planxa amb amanida"
        assert dilluns["dessert"] == "Fruita"
        assert len(dilluns["raw"]) == 3
    
    def test_parse_menu_empty_cells(self):
        """Test parsing menu with empty cells."""
        mock_data = {
            "kids": [
                {
                    "type": "table",
                    "rows": [
                        {
                            "cells": [
                                {"kids": [{"content": "SETMANA"}]},
                                {"kids": [{"content": "Dilluns"}]},
                                {"kids": []}  # Empty cell
                            ]
                        },
                        {
                            "cells": [
                                {"kids": [{"content": "Del 9 al 12/09"}]},
                                {"kids": [{"type": "list", "list items": [{"content": "Test meal"}]}]},
                                {"kids": []}  # Empty cell
                            ]
                        }
                    ]
                }
            ]
        }
        
        with patch('menu_parser.date') as mock_date:
            mock_date.today.return_value.year = 2025
            # Mock the date constructor to return proper date objects
            def mock_date_constructor(year, month, day):
                return date(year, month, day)
            mock_date.side_effect = mock_date_constructor
            result = parse_menu(mock_data)
        
        assert len(result) == 1
        week_menu = result[0]
        assert "Dilluns" in week_menu["days"]
        assert "Dimarts" not in week_menu["days"]  # Empty cell should be skipped
    
    def test_parse_menu_no_meals(self):
        """Test parsing menu row with no meals."""
        mock_data = {
            "kids": [
                {
                    "type": "table",
                    "rows": [
                        {
                            "cells": [
                                {"kids": [{"content": "SETMANA"}]},
                                {"kids": [{"content": "Dilluns"}]}
                            ]
                        },
                        {
                            "cells": [
                                {"kids": [{"content": "Del 9 al 12/09"}]},
                                {"kids": []}  # No meals
                            ]
                        }
                    ]
                }
            ]
        }
        
        with patch('menu_parser.date') as mock_date:
            mock_date.today.return_value.year = 2025
            # Mock the date constructor to return proper date objects
            def mock_date_constructor(year, month, day):
                return date(year, month, day)
            mock_date.side_effect = mock_date_constructor
            result = parse_menu(mock_data)
        
        assert len(result) == 1
        week_menu = result[0]
        assert len(week_menu["days"]) == 0  # No days should be added


class TestSaveMenuJson:
    """Test cases for save_menu_json function."""
    
    def test_save_menu_json(self):
        """Test saving menu data to JSON file."""
        menu_data = [
            {
                "weeks": [{"start": "2025-09-09", "end": "2025-09-12"}],
                "days": {
                    "Dilluns": {
                        "entrant": "Test meal",
                        "main": "Main course",
                        "dessert": "Dessert",
                        "raw": ["Test meal", "Main course", "Dessert"]
                    }
                }
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            save_menu_json(menu_data, tmp_path)
            
            # Verify file was created and contains correct data
            assert os.path.exists(tmp_path)
            
            with open(tmp_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            assert loaded_data == menu_data
        finally:
            os.unlink(tmp_path)


class TestGenerateIcsCalendar:
    """Test cases for generate_ics_calendar function."""
    
    def test_generate_ics_calendar_basic(self):
        """Test basic ICS calendar generation."""
        menu_data = [
            {
                "weeks": [{"start": "2025-09-08", "end": "2025-09-12"}],  # Monday to Friday
                "days": {
                    "Dilluns": {
                        "entrant": "Mongeta tendra amb patates",
                        "main": "Gall dindi a la planxa amb amanida",
                        "dessert": "Fruita",
                        "raw": ["Mongeta tendra amb patates", "Gall dindi a la planxa amb amanida", "Fruita"]
                    },
                    "Dimarts": {
                        "entrant": "Macarrons a la bolonyesa",
                        "main": "Filet de lluç amb amanida",
                        "dessert": "Iogurt natural",
                        "raw": ["Macarrons a la bolonyesa", "Filet de lluç amb amanida", "Iogurt natural"]
                    }
                }
            }
        ]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ics') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            generate_ics_calendar(menu_data, tmp_path)
            
            # Verify file was created
            assert os.path.exists(tmp_path)
            
            # Read and verify ICS content
            with open(tmp_path, 'rb') as f:
                ics_content = f.read()
            
            # Basic checks for ICS format
            assert b'BEGIN:VCALENDAR' in ics_content
            assert b'END:VCALENDAR' in ics_content
            assert b'BEGIN:VEVENT' in ics_content
            assert b'END:VEVENT' in ics_content
            
            # Check for specific content (decode to string for non-ASCII characters)
            ics_text = ics_content.decode('utf-8')
            assert 'Menú Sant Nicolau - Dilluns' in ics_text
            assert 'Menú Sant Nicolau - Dimarts' in ics_text
            assert 'Primer: Mongeta tendra amb patates' in ics_text
            # Check for wrapped content in ICS format (ICS wraps long lines)
            assert 'Segon: Gall dindi a la pla' in ics_text
            assert 'nxa amb amanida' in ics_text
            assert 'Postre: Fruita' in ics_text
            assert 'Centre Escolar Sant Nicolau' in ics_text
            
        finally:
            os.unlink(tmp_path)
    
    def test_generate_ics_calendar_weekend_skip(self):
        """Test that weekend days are skipped in ICS generation."""
        menu_data = [
            {
                "weeks": [{"start": "2025-09-07", "end": "2025-09-13"}],  # Sunday to Saturday
                "days": {
                    "Dilluns": {
                        "entrant": "Test meal",
                        "main": "Main course",
                        "dessert": "Dessert",
                        "raw": ["Test meal", "Main course", "Dessert"]
                    }
                }
            }
        ]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ics') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            generate_ics_calendar(menu_data, tmp_path)
            
            # Read and verify ICS content
            with open(tmp_path, 'rb') as f:
                ics_content = f.read()
            
            # Should only have Monday event, not weekend events
            ics_text = ics_content.decode('utf-8')
            assert 'Menú Sant Nicolau - Dilluns' in ics_text
            # Count events - should be 1 (only Monday)
            event_count = ics_content.count(b'BEGIN:VEVENT')
            assert event_count == 1
            
        finally:
            os.unlink(tmp_path)
    
    def test_generate_ics_calendar_empty_menu(self):
        """Test ICS generation with empty menu data."""
        menu_data = []
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ics') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            generate_ics_calendar(menu_data, tmp_path)
            
            # Verify file was created
            assert os.path.exists(tmp_path)
            
            # Read and verify ICS content
            with open(tmp_path, 'rb') as f:
                ics_content = f.read()
            
            # Should have calendar structure but no events
            assert b'BEGIN:VCALENDAR' in ics_content
            assert b'END:VCALENDAR' in ics_content
            assert b'BEGIN:VEVENT' not in ics_content
            
        finally:
            os.unlink(tmp_path)


class TestMainFunction:
    """Test cases for main CLI function."""
    
    def test_main_help(self):
        """Test main function help output."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert "Parse a school menu PDF file" in result.output
        assert "PDF_FILE" in result.output
        assert "--output" in result.output
        assert "--print" in result.output


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_full_workflow_with_mock_data(self):
        """Test complete workflow from JSON data to output."""
        # This would be a more comprehensive integration test
        # using real-like data structures
        pass


if __name__ == "__main__":
    pytest.main([__file__])
