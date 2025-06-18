# Tender Agent V3 🤖

An AI-powered tender monitoring system that automatically scrapes, categorizes, and notifies teams about relevant tenders.

## Features

- 🕷️ **Web Scraping**: Uses crawl4ai to scrape tender pages
- 🤖 **AI Agents**: LangGraph-powered multi-agent system for intelligent extraction
- 📊 **Categorization**: Automatically categorizes tenders for ESG and Credit Rating teams
- 📧 **Email Notifications**: Sends detailed notifications to respective teams
- ⏰ **Scheduled Monitoring**: Runs every 3 hours automatically
- 💾 **SQLite Database**: Tracks pages, tenders, and keywords
- 🎯 **Keyword Management**: Configurable keywords for each team

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│  Agent Pipeline  │───▶│   Database      │
│   (crawl4ai)    │    │   (langgraph)    │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Scheduler     │    │  Email Service   │    │  Web Dashboard  │
│   (every 3h)    │    │  (notifications) │    │                 |
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Update your `.env` file with the required credentials:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   ESG_TEAM_EMAIL=esg-team@company.com
   CREDIT_RATING_TEAM_EMAIL=credit-team@company.com
   ```

## Usage

### Quick Start

1. **Test All Components**:
   ```bash
   python main.py test
   ```

2. **Run Single Extraction**:
   ```bash
   python main.py run
   ```

3. **Start Continuous Monitoring**:
   ```bash
   python main.py schedule
   ```

4. **View Configuration**:
   ```bash
   python main.py config
   ```

### Component Testing

Test individual components:

```bash
# Test web scraper
python scraper.py

# Test AI agents
python agents.py

# Test database operations
python database.py

# Test email service
python email_service.py

# Test scheduler (single run)
python scheduler.py test
```

## Configuration

### Default Keywords

**ESG Keywords**:
- environmental, sustainability, green, carbon, climate
- renewable, esg, social responsibility, governance
- sustainable development, environmental impact

**Credit Rating Keywords**:
- credit rating, financial assessment, risk evaluation
- credit analysis, rating agency, financial review
- creditworthiness, financial audit, risk assessment

### Email Configuration

For Gmail, use an App Password instead of your regular password:
1. Enable 2-factor authentication
2. Generate an App Password
3. Use the App Password in the `EMAIL_PASSWORD` field

## Database Schema

- **monitored_pages**: URLs to monitor
- **keywords**: Configurable keywords by category
- **tenders**: Extracted tender information
- **crawl_logs**: Monitoring activity logs

## AI Agent Workflow

1. **Agent 1**: 
   - Extracts tender information from page content
   - Categorizes based on keywords (ESG/Credit Rating)
   - Returns structured data with title, URL, date, category

2. **Agent 2**:
   - Fetches full details for each relevant tender
   - Filters by date (only recent tenders)
   - Generates detailed descriptions
   - Prepares data for notifications

## Email Notifications

- Sends HTML-formatted emails to respective teams
- Includes tender title, category, date, description, and link
- Only sends notifications for new, unnotified tenders
- Marks tenders as notified to prevent duplicates

## Monitoring

- Runs every 3 hours by default (configurable)
- Tracks all monitored pages
- Logs crawl activities and errors
- Updates page last-crawled timestamps

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**: Check your API key and quota
2. **Email Failures**: Verify SMTP settings and app passwords
3. **Scraping Failures**: Check internet connection and target site availability
4. **Database Errors**: Ensure write permissions in project directory

### Logs

All activities are logged with timestamps. Check console output for:
- Scraping status
- Agent processing results
- Email sending status
- Database operations

## Development

### Adding New Monitored Pages

```python
from database import DatabaseManager
from models import get_db

db_manager = DatabaseManager()
with next(get_db()) as db:
    db_manager.add_monitored_page(db, "https://example.com/tenders", "Example Tenders")
```

### Adding New Keywords

```python
db_manager.add_keywords(db, ["new_keyword1", "new_keyword2"], "esg")
```

## Future Enhancements

- [ ] Web dashboard for URL and keyword management
- [ ] Tender detail page viewing
- [ ] Advanced filtering and search
- [ ] Multi-language support
- [ ] Integration with more tender platforms
- [ ] Slack/Teams notifications
- [ ] API endpoints for external integrations

## License

This project is for internal use. Please ensure compliance with target websites' robots.txt and terms of service.
