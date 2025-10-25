# Instagram Profile Analyzer

A powerful web application that analyzes Instagram profiles using AI to provide comprehensive insights about personality, interests, relationship status, and more. Features include parallel processing for fast scraping, automatic image collage generation, video frame extraction, and AI-powered personality analysis.

## Features

### Core Functionality
- 🔍 **Deep Profile Analysis** - Scrape and analyze Instagram profiles with AI
- ⚡ **Parallel Processing** - Fast scraping with multi-threaded image/video downloads and collage generation
- 🎨 **Automatic Collage Generation** - Combine multi-image posts into beautiful collages
- 🎥 **Video Frame Extraction** - Extract 9 evenly-spaced frames from video posts
- 🌐 **Website Scraping** - Automatically scrape personal websites from profiles
- 🤖 **AI-Powered Insights** - Uses Claude AI for personality and lifestyle analysis

### Report Components

#### Summary Section
- One-sentence profile summary
- 3 suggested conversation openers
- 3-5 keyword tags

#### Detailed Analysis
- Name & handle analysis
- Intro and personal websites
- Interests and hobbies
- Relationship status (with confidence %)
- MBTI personality type (with confidence % and detailed analysis)
- Overall presence and vibe
- Attitude towards life and lifestyle values
- Notable insights

#### Visual Gallery
- All posts displayed as image collages with captions
- Engagement metrics (likes, comments, views)
- Direct links to original posts

### User Experience
- Beautiful, modern UI with dark theme
- Real-time progress tracking
- Animated carousel showing posts while processing
- Responsive design for all devices

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **AI**: Anthropic Claude API (Vision + Text)
- **Scraping**: Apify Instagram API
- **Image Processing**: Pillow (PIL)
- **Video Processing**: OpenCV
- **Database**: SQLite
- **Website Scraping**: BeautifulSoup4

## Prerequisites

- Python 3.8+
- Apify API Key (for Instagram scraping)
- Anthropic API Key (for AI analysis)

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd profileanalyzer
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the root directory:
```env
APIFY_API_TOKEN=your_apify_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

To get API keys:
- **Apify**: Sign up at [apify.com](https://apify.com) and get your API token
- **Anthropic**: Sign up at [anthropic.com](https://anthropic.com) and get your API key

## Usage

### Running the Web Application

1. **Start the Flask server**
```bash
python app.py
```

2. **Open your browser**
Navigate to: `http://localhost:8080`

3. **Enter Instagram profile**
- Enter a profile URL (e.g., `https://www.instagram.com/username`)
- Or just enter the username (e.g., `username`)

4. **Wait for analysis**
- Watch the progress bar and carousel animation
- Analysis typically takes 2-5 minutes depending on the number of posts

5. **View the report**
- Comprehensive analysis with all insights
- Visual collages of all posts
- Downloadable data

### Using as a Python Script

You can also use the scraper directly:

```python
from scraper import InstagramScraper
import os

# Initialize scraper
scraper = InstagramScraper(
    api_token=os.getenv('APIFY_API_TOKEN'),
    use_database=True
)

# Scrape a profile (default: 10 posts with parallel processing)
result = scraper.scrape_profile('username', results_limit=10)

# Data is saved to output/ directory
scraper.close()
```

## Project Structure

```
profileanalyzer/
├── app.py                      # Flask application
├── scraper.py                  # Instagram scraper
├── database.py                 # Database management
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
│
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── image_processor.py      # Image collage generation
│   ├── video_processor.py      # Video frame extraction
│   ├── website_scraper.py      # Website scraping
│   └── ai_analyzer.py          # AI analysis
│
├── templates/                  # HTML templates
│   └── index.html
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
└── output/                     # Generated content
    ├── collages/               # Image collages
    ├── images/                 # Downloaded images
    ├── videos/                 # Downloaded videos
    └── posts_data.json         # Scraped data
```

## API Endpoints

### `POST /api/analyze`
Start profile analysis
```json
{
  "profile_url": "username or URL",
  "results_limit": 30
}
```

### `GET /api/status/<session_id>`
Get analysis progress
```json
{
  "status": "scraping|analyzing|completed|error",
  "progress": 75,
  "message": "Status message",
  "posts_preview": [...]
}
```

### `GET /api/report/<session_id>`
Get complete analysis report
```json
{
  "username": "...",
  "profile": {...},
  "analysis": {...},
  "posts": [...],
  "website_data": {...}
}
```

### `GET /api/health`
Health check
```json
{
  "status": "healthy",
  "apify_configured": true,
  "anthropic_configured": true
}
```

## Configuration

### Adjust Number of Posts
In `app.py`, modify the `results_limit` parameter (default: 10):
```python
result = scraper.scrape_profile(profile_url, results_limit=20)
```

### Configure Parallel Processing
In `utils/image_processor.py`, adjust the number of parallel workers (default: 5):
```python
self.image_processor = ImageProcessor(max_workers=10)  # Increase for faster processing
```

### Change AI Model
In `utils/ai_analyzer.py`, change the model:
```python
self.model = "claude-3-5-sonnet-20241022"  # or another Claude model
```

## Troubleshooting

### "APIFY_API_TOKEN not set"
- Make sure your `.env` file exists and contains the correct API key
- Restart the Flask server after adding the key

### "Failed to fetch profile data"
- Check if the Instagram username is correct
- Verify your Apify API key is valid
- Check Apify usage limits

### Image collages not generating
- Ensure Pillow is installed correctly
- Check write permissions for `output/collages/` directory

### Video processing fails
- Ensure OpenCV is installed correctly
- Check that ffmpeg is available on your system

### AI analysis returns fallback data
- Verify Anthropic API key is set correctly
- Check API usage limits
- Ensure the key has access to Claude 3.5 Sonnet

## Performance

### Parallel Processing
The application uses multi-threaded parallel processing for optimal performance:

- **Image Downloads**: Up to 5 images downloaded simultaneously
- **Collage Generation**: Multiple posts processed in parallel
- **Video Frame Extraction**: Concurrent video processing

**Typical Processing Times** (10 posts):
- Image downloads: ~10-15 seconds (parallel)
- Collage generation: ~15-20 seconds (parallel)
- Video frame extraction: ~20-30 seconds per video
- AI analysis: ~30-45 seconds
- **Total**: ~1-2 minutes for complete analysis

**Performance Tips**:
- Increase `max_workers` in ImageProcessor for faster processing on powerful machines
- Reduce `results_limit` for quicker analysis
- SSD storage significantly improves video processing speed

## Limitations

- Instagram's rate limiting may affect scraping speed
- Video processing requires significant CPU resources
- AI analysis token limits may affect very large profiles
- Personal website scraping depends on site structure
- Parallel processing limited by network bandwidth and CPU cores

## Privacy & Ethics

This tool is designed for:
- Personal research and analysis
- Understanding public social media presence
- Generating conversation starters for networking

**Do not use this tool for:**
- Stalking or harassment
- Privacy invasion
- Unauthorized data collection
- Commercial purposes without consent

Always respect privacy and terms of service of platforms.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

## Acknowledgments

- Apify for Instagram scraping API
- Anthropic for Claude AI API
- OpenCV for video processing
- Flask for web framework
