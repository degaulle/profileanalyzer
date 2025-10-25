#!/usr/bin/env python3
"""
Enhanced Instagram Posts Scraper with Collage Generation
"""

import os
import sys
import json
from datetime import datetime
from apify_client import ApifyClient
from database import InstagramDatabase
from utils.image_processor import ImageProcessor
from utils.website_scraper import WebsiteScraper
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class InstagramScraper:
    def __init__(self, api_token, use_database=True, db_path="instagram_data.db"):
        """
        Initialize the scraper with Apify API token

        Args:
            api_token: Apify API token
            use_database: Whether to use database storage (default: True)
            db_path: Path to SQLite database file
        """
        self.client = ApifyClient(api_token)
        self.output_dir = "output"
        self.images_dir = os.path.join(self.output_dir, "images")
        self.data_file = os.path.join(self.output_dir, "posts_data.json")
        self.use_database = use_database
        self.db = None

        # Initialize image processor
        self.image_processor = ImageProcessor()

        # Initialize website scraper
        self.website_scraper = WebsiteScraper()

        # Create output directories
        os.makedirs(self.images_dir, exist_ok=True)

        # Initialize database if enabled
        if self.use_database:
            self.db = InstagramDatabase(db_path)
            print(f"Database storage enabled: {db_path}")

    def extract_username_from_url(self, url: str) -> str:
        """
        Extract username from Instagram URL

        Args:
            url: Instagram profile URL

        Returns:
            Username string
        """
        # Handle various Instagram URL formats
        url = url.strip().rstrip('/')

        if 'instagram.com/' in url:
            parts = url.split('instagram.com/')
            if len(parts) > 1:
                username = parts[1].split('/')[0].split('?')[0]
                return username

        # If no URL format detected, assume it's just the username
        return url

    def fetch_user_profile(self, username: str):
        """
        Fetch user profile information

        Args:
            username: Instagram username

        Returns:
            Profile data
        """
        print(f"Fetching profile for @{username}...")

        # Run the Actor to get profile data
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "posts",
            "resultsLimit": 1,
            "addParentData": True,
        }

        run = self.client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

        # Get first item to extract profile data
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        if items:
            item = items[0]

            # Extract profile picture - try multiple fields
            profile_pic_url = (
                item.get('profilePicUrlHD') or
                item.get('profilePicUrl') or
                item.get('ownerProfilePicUrl') or
                ''
            )

            # Extract full name and bio
            full_name = item.get('ownerFullName', '') or item.get('fullName', '')

            profile = {
                'username': username,
                'full_name': full_name,
                'profile_pic_url': profile_pic_url,
                'bio': item.get('bio', '') or item.get('biography', ''),
                'website': item.get('externalUrl', '') or item.get('website', ''),
                'ownerId': item.get('ownerId', '') or item.get('id', ''),
                'followers': item.get('followersCount', 0),
                'following': item.get('followsCount', 0),
                'is_verified': item.get('verified', False)
            }

            print(f"✓ Profile fetched: {full_name} (@{username})")
            print(f"  Profile pic: {profile_pic_url[:50]}..." if profile_pic_url else "  No profile pic")
            print(f"  Bio: {profile['bio'][:50]}..." if profile['bio'] else "  No bio")

            return profile

        print(f"✗ No profile data found for @{username}")
        return None

    def fetch_user_posts(self, username, results_limit=30):
        """
        Fetch posts from an Instagram user profile

        Args:
            username: Instagram username
            results_limit: Number of posts to fetch (default: 30)

        Returns:
            List of post data
        """
        print(f"Fetching posts from @{username}...")

        # Prepare the Actor input
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "posts",
            "resultsLimit": results_limit,
            "searchType": "hashtag",
            "searchLimit": 1,
            "addParentData": True,
        }

        # Run the Actor
        print("Running Apify actor...")
        run = self.client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

        # Fetch results
        print("Fetching results...")
        posts = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            posts.append(item)

        print(f"Successfully fetched {len(posts)} posts")
        return posts

    def process_posts(self, posts):
        """
        Process posts and extract relevant information

        Args:
            posts: List of raw post data from API

        Returns:
            List of processed post data
        """
        processed_posts = []

        for idx, post in enumerate(posts):
            # Extract profile avatar URL
            profile_pic_url = post.get("profilePicUrlHD") or post.get("profilePicUrl") or post.get("ownerProfilePicUrl", "")

            processed_post = {
                "id": post.get("id"),
                "shortCode": post.get("shortCode"),
                "type": post.get("type"),
                "caption": post.get("caption", ""),
                "timestamp": post.get("timestamp"),
                "likesCount": post.get("likesCount", 0),
                "commentsCount": post.get("commentsCount", 0),
                "videoViewCount": post.get("videoViewCount", 0),
                "url": post.get("url"),
                "ownerFullName": post.get("ownerFullName", ""),
                "ownerUsername": post.get("ownerUsername", ""),
                "ownerId": post.get("ownerId", ""),
                "ownerProfilePicUrl": profile_pic_url,
                "images": [],
                "videos": []
            }

            # Handle different post types
            if post.get("type") == "Video":
                if post.get("displayUrl"):
                    processed_post["images"].append({
                        "url": post.get("displayUrl"),
                        "is_thumbnail": True,
                        "type": "video_thumbnail"
                    })
                if post.get("videoUrl"):
                    processed_post["videos"].append({
                        "url": post.get("videoUrl"),
                        "viewCount": post.get("videoViewCount", 0)
                    })

            elif post.get("type") == "Image":
                if post.get("displayUrl"):
                    processed_post["images"].append({
                        "url": post.get("displayUrl"),
                        "is_thumbnail": False,
                        "type": "image"
                    })

            elif post.get("type") == "Sidecar":
                for child in post.get("childPosts", []):
                    if child.get("type") == "Video":
                        if child.get("displayUrl"):
                            processed_post["images"].append({
                                "url": child.get("displayUrl"),
                                "is_thumbnail": True,
                                "type": "video_thumbnail"
                            })
                        if child.get("videoUrl"):
                            processed_post["videos"].append({
                                "url": child.get("videoUrl")
                            })
                    elif child.get("type") == "Image":
                        if child.get("displayUrl"):
                            processed_post["images"].append({
                                "url": child.get("displayUrl"),
                                "is_thumbnail": False,
                                "type": "image"
                            })

            processed_posts.append(processed_post)

        return processed_posts

    def generate_collages(self, posts):
        """
        Generate image collages for all posts using parallel processing

        Args:
            posts: List of processed posts

        Returns:
            Updated posts with collage paths
        """
        # Use parallel processing for faster collage generation
        return self.image_processor.generate_collages_parallel(posts)

    def scrape_personal_website(self, profile_info):
        """
        Scrape personal website if available

        Args:
            profile_info: Profile information

        Returns:
            Website data
        """
        website_url = profile_info.get('website', '')

        if not website_url:
            print("No personal website found in profile")
            return None

        try:
            website_data = self.website_scraper.scrape_website(website_url)
            return website_data
        except Exception as e:
            print(f"Error scraping website: {e}")
            return None

    def save_data(self, posts, username, profile_info, website_data=None):
        """
        Save processed posts data

        Args:
            posts: List of processed post data
            username: Instagram username
            profile_info: Profile information
            website_data: Scraped website data
        """
        output_data = {
            "username": username,
            "profile": profile_info,
            "website_data": website_data,
            "fetch_timestamp": datetime.now().isoformat(),
            "total_posts": len(posts),
            "posts": posts
        }

        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"Data saved to JSON: {self.data_file}")

        # Save to database if enabled
        if self.use_database and self.db:
            print("Saving data to database...")
            stats = self.db.save_posts_batch(username, posts)
            print(f"Database stats: {stats}")

            self.db.log_scraping_session(
                username=username,
                posts_fetched=len(posts),
                status="success",
                started_at=datetime.now()
            )
            print("Database save complete!")

    def scrape_profile(self, profile_url: str, results_limit: int = 10):
        """
        Main method to scrape entire profile with parallel processing

        Args:
            profile_url: Instagram profile URL or username
            results_limit: Number of posts to fetch (default: 10)

        Returns:
            Complete profile data with analysis
        """
        # Extract username
        username = self.extract_username_from_url(profile_url)
        print(f"\n{'='*60}")
        print(f"Starting profile scrape for: @{username}")
        print(f"{'='*60}\n")

        # Fetch profile info
        profile_info = self.fetch_user_profile(username)
        if not profile_info:
            print(f"Error: Could not fetch profile for @{username}")
            return None

        # Fetch posts
        raw_posts = self.fetch_user_posts(username, results_limit)
        if not raw_posts:
            print(f"Error: No posts found for @{username}")
            return None

        # Process posts
        processed_posts = self.process_posts(raw_posts)

        # Generate collages
        processed_posts = self.generate_collages(processed_posts)

        # Scrape personal website if available
        website_data = self.scrape_personal_website(profile_info)

        # Save all data
        self.save_data(processed_posts, username, profile_info, website_data)

        return {
            'username': username,
            'profile': profile_info,
            'posts': processed_posts,
            'website_data': website_data,
            'total_posts': len(processed_posts)
        }

    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()


def main():
    """Main function for command-line usage"""
    API_TOKEN = os.getenv('APIFY_API_TOKEN')
    if not API_TOKEN:
        print("Error: APIFY_API_TOKEN not set")
        sys.exit(1)

    USERNAME = "_clwu_"
    RESULTS_LIMIT = 10

    scraper = InstagramScraper(API_TOKEN, use_database=True)

    try:
        result = scraper.scrape_profile(USERNAME, RESULTS_LIMIT)

        if result:
            print("\n" + "="*60)
            print("SCRAPE COMPLETE!")
            print(f"Username: @{result['username']}")
            print(f"Total posts: {result['total_posts']}")
            print(f"Profile data saved to: {scraper.output_dir}/")
            print("="*60)

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
