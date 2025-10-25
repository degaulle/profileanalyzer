"""
Flask backend for Instagram Profile Analyzer
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import threading
from datetime import datetime
from dotenv import load_dotenv

from scraper import InstagramScraper
from utils.ai_analyzer import ProfileAnalyzer
from database import InstagramDatabase

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Store active analysis sessions
analysis_sessions = {}


class AnalysisSession:
    """Track analysis progress"""
    def __init__(self, username):
        self.username = username
        self.status = 'initializing'
        self.progress = 0
        self.message = 'Starting analysis...'
        self.profile_data = None
        self.posts_data = []
        self.website_data = None
        self.analysis_result = None
        self.error = None
        self.started_at = datetime.now()
        self.completed_at = None


def run_analysis(session_id: str, profile_url: str, results_limit: int = 10):
    """
    Run profile analysis in background thread with parallel processing

    Args:
        session_id: Session ID
        profile_url: Instagram profile URL
        results_limit: Number of posts to fetch (default: 10)
    """
    session = analysis_sessions[session_id]

    try:
        # Initialize scraper
        session.status = 'scraping'
        session.progress = 10
        session.message = 'Fetching Instagram profile...'

        scraper = InstagramScraper(APIFY_API_TOKEN, use_database=True)

        # Scrape profile
        session.progress = 20
        session.message = 'Downloading posts...'

        result = scraper.scrape_profile(profile_url, results_limit)

        if not result:
            session.status = 'error'
            session.error = 'Failed to fetch profile data'
            return

        session.profile_data = result['profile']
        session.posts_data = result['posts']
        session.website_data = result.get('website_data')

        session.progress = 60
        session.message = 'Generating collages complete. Starting AI analysis...'

        # Run AI analysis
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_anthropic_api_key_here':
            session.status = 'analyzing'
            session.progress = 70
            session.message = 'Analyzing profile with AI...'

            analyzer = ProfileAnalyzer(ANTHROPIC_API_KEY)

            # Get collage paths
            collage_paths = [
                post.get('collage_path')
                for post in session.posts_data
                if post.get('collage_path')
            ]

            analysis = analyzer.analyze_profile(
                session.posts_data,
                session.profile_data,
                session.website_data,
                collage_paths
            )

            session.analysis_result = analysis

            # Save analysis to database
            db = InstagramDatabase()
            db.save_analysis(session.username, analysis)
            db.close()

        else:
            session.message = 'AI analysis skipped (API key not configured)'
            # Use fallback
            analyzer = ProfileAnalyzer('dummy')
            session.analysis_result = analyzer._generate_fallback_analysis(
                session.posts_data,
                session.profile_data
            )

        # Complete
        session.status = 'completed'
        session.progress = 100
        session.message = 'Analysis complete!'
        session.completed_at = datetime.now()

        scraper.close()

    except Exception as e:
        session.status = 'error'
        session.error = str(e)
        session.message = f'Error: {str(e)}'
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """Start profile analysis with parallel processing"""
    data = request.json
    profile_url = data.get('profile_url', '')
    results_limit = data.get('results_limit', 10)

    if not profile_url:
        return jsonify({'error': 'Profile URL is required'}), 400

    # Create session
    scraper = InstagramScraper(APIFY_API_TOKEN)
    username = scraper.extract_username_from_url(profile_url)

    session_id = f"{username}_{datetime.now().timestamp()}"
    session = AnalysisSession(username)
    analysis_sessions[session_id] = session

    # Start analysis in background thread
    thread = threading.Thread(
        target=run_analysis,
        args=(session_id, profile_url, results_limit)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'session_id': session_id,
        'username': username,
        'message': 'Analysis started'
    })


@app.route('/api/status/<session_id>')
def get_status(session_id):
    """Get analysis status"""
    session = analysis_sessions.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    response = {
        'status': session.status,
        'progress': session.progress,
        'message': session.message,
        'username': session.username
    }

    # Include posts for carousel during processing
    if session.posts_data:
        response['posts_preview'] = [
            {
                'url': post.get('url'),
                'caption': post.get('caption', '')[:100],
                'images': [img['url'] for img in post.get('images', [])[:1]],
                'type': post.get('type')
            }
            for post in session.posts_data[:10]
        ]

    if session.status == 'error':
        response['error'] = session.error

    return jsonify(response)


@app.route('/api/report/<session_id>')
def get_report(session_id):
    """Get analysis report"""
    session = analysis_sessions.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if session.status != 'completed':
        return jsonify({'error': 'Analysis not completed'}), 400

    # Build complete report
    report = {
        'username': session.username,
        'profile': session.profile_data,
        'website_data': session.website_data,
        'analysis': session.analysis_result,
        'posts': session.posts_data,
        'started_at': session.started_at.isoformat(),
        'completed_at': session.completed_at.isoformat()
    }

    return jsonify(report)


@app.route('/collages/<path:filename>')
def serve_collage(filename):
    """Serve collage images"""
    return send_from_directory('output/collages', filename)


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'apify_configured': bool(APIFY_API_TOKEN),
        'anthropic_configured': bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_anthropic_api_key_here')
    })


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('output/collages', exist_ok=True)
    os.makedirs('output/images', exist_ok=True)

    # Run Flask app
    print("\n" + "="*60)
    print("Instagram Profile Analyzer - Starting Server")
    print("="*60)
    print(f"Apify API: {'✓ Configured' if APIFY_API_TOKEN else '✗ Not configured'}")
    print(f"Claude API: {'✓ Configured' if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_anthropic_api_key_here' else '✗ Not configured'}")
    print("="*60)
    print("\nServer running at: http://localhost:5000")
    print("="*60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
