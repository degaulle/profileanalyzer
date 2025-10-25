"""
Database module for storing Instagram data
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any


class InstagramDatabase:
    def __init__(self, db_path="instagram_data.db"):
        """Initialize database connection and create tables"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT,
                profile_pic_url TEXT,
                bio TEXT,
                website TEXT,
                follower_count INTEGER,
                following_count INTEGER,
                is_verified BOOLEAN,
                is_private BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                short_code TEXT,
                type TEXT,
                caption TEXT,
                timestamp TIMESTAMP,
                likes_count INTEGER,
                comments_count INTEGER,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Images table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                url TEXT,
                is_thumbnail BOOLEAN,
                type TEXT,
                local_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

        # Videos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                url TEXT,
                view_count INTEGER,
                local_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        ''')

        # Scraping sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                posts_fetched INTEGER,
                status TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                summary TEXT,
                openers TEXT,
                keywords TEXT,
                detailed_report TEXT,
                confidence_scores TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def save_user(self, user_data: Dict[str, Any]):
        """Save or update user data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users
            (id, username, full_name, profile_pic_url, bio, website, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_data.get('ownerId'),
            user_data.get('ownerUsername'),
            user_data.get('ownerFullName'),
            user_data.get('ownerProfilePicUrl'),
            user_data.get('bio', ''),
            user_data.get('website', '')
        ))
        self.conn.commit()

    def save_post(self, post_data: Dict[str, Any]):
        """Save a single post"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO posts
            (id, user_id, short_code, type, caption, timestamp, likes_count, comments_count, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_data['id'],
            post_data.get('ownerId'),
            post_data['shortCode'],
            post_data['type'],
            post_data['caption'],
            post_data['timestamp'],
            post_data['likesCount'],
            post_data['commentsCount'],
            post_data['url']
        ))

        # Save images
        for img in post_data.get('images', []):
            cursor.execute('''
                INSERT INTO images (post_id, url, is_thumbnail, type)
                VALUES (?, ?, ?, ?)
            ''', (
                post_data['id'],
                img['url'],
                img['is_thumbnail'],
                img['type']
            ))

        # Save videos
        for video in post_data.get('videos', []):
            cursor.execute('''
                INSERT INTO videos (post_id, url, view_count)
                VALUES (?, ?, ?)
            ''', (
                post_data['id'],
                video['url'],
                video.get('viewCount', 0)
            ))

        self.conn.commit()

    def save_posts_batch(self, username: str, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Save multiple posts and return statistics"""
        stats = {
            'posts_saved': 0,
            'images_saved': 0,
            'videos_saved': 0
        }

        # Save user data from first post
        if posts:
            self.save_user(posts[0])

        for post in posts:
            self.save_post(post)
            stats['posts_saved'] += 1
            stats['images_saved'] += len(post.get('images', []))
            stats['videos_saved'] += len(post.get('videos', []))

        return stats

    def log_scraping_session(self, username: str, posts_fetched: int, status: str, started_at: datetime):
        """Log a scraping session"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO scraping_sessions (username, posts_fetched, status, started_at)
            VALUES (?, ?, ?, ?)
        ''', (username, posts_fetched, status, started_at.isoformat()))
        self.conn.commit()

    def save_analysis(self, username: str, analysis_data: Dict[str, Any]):
        """Save analysis results"""
        cursor = self.conn.cursor()

        # Extract summary data
        summary = analysis_data.get('summary', {})
        if isinstance(summary, dict):
            summary_text = summary.get('one_sentence', '')
            openers = summary.get('openers', [])
            keywords = summary.get('keywords', [])
        else:
            summary_text = str(summary)
            openers = []
            keywords = []

        cursor.execute('''
            INSERT INTO analysis_results
            (username, summary, openers, keywords, detailed_report, confidence_scores)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            username,
            summary_text,
            json.dumps(openers),
            json.dumps(keywords),
            json.dumps(analysis_data.get('detailed_report', {})),
            json.dumps(analysis_data.get('confidence_scores', {}))
        ))
        self.conn.commit()

    def get_user_posts(self, username: str) -> List[Dict[str, Any]]:
        """Get all posts for a user"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE u.username = ?
            ORDER BY p.timestamp DESC
        ''', (username,))

        posts = []
        for row in cursor.fetchall():
            post = dict(row)
            # Get images
            cursor.execute('SELECT * FROM images WHERE post_id = ?', (post['id'],))
            post['images'] = [dict(r) for r in cursor.fetchall()]
            # Get videos
            cursor.execute('SELECT * FROM videos WHERE post_id = ?', (post['id'],))
            post['videos'] = [dict(r) for r in cursor.fetchall()]
            posts.append(post)

        return posts

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        cursor = self.conn.cursor()
        stats = {}

        cursor.execute('SELECT COUNT(*) as count FROM users')
        stats['total_users'] = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM posts')
        stats['total_posts'] = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM images')
        stats['total_images'] = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM videos')
        stats['total_videos'] = cursor.fetchone()['count']

        return stats

    def close(self):
        """Close database connection"""
        self.conn.close()
