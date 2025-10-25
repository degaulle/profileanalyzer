"""
AI-powered profile analyzer using Claude API
"""

import os
import json
from anthropic import Anthropic
from typing import Dict, List, Any
import base64
import requests
from io import BytesIO


class ProfileAnalyzer:
    def __init__(self, api_key: str):
        """Initialize analyzer with Anthropic API key"""
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20240620"  # Claude 3.5 Sonnet

    def analyze_profile(self, posts_data: List[Dict], profile_info: Dict,
                       website_data: Dict = None, collage_paths: List[str] = None) -> Dict[str, Any]:
        """
        Analyze Instagram profile and generate comprehensive report

        Args:
            posts_data: List of post data
            profile_info: Profile information
            website_data: Scraped website data (optional)
            collage_paths: List of image collage file paths (optional)

        Returns:
            Complete analysis report
        """
        print("Starting AI-powered profile analysis...")

        # Prepare analysis prompt
        prompt = self._build_analysis_prompt(posts_data, profile_info, website_data)

        # Prepare images for vision analysis (if available)
        image_content = []
        if collage_paths:
            # Limit to first 10 collages to avoid token limits
            for path in collage_paths[:10]:
                if os.path.exists(path):
                    try:
                        with open(path, 'rb') as f:
                            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
                            image_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data
                                }
                            })
                    except Exception as e:
                        print(f"Error loading image {path}: {e}")

        # Build message content
        message_content = []

        # Add text prompt
        message_content.append({
            "type": "text",
            "text": prompt
        })

        # Add images if available
        message_content.extend(image_content)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": message_content
                    }
                ]
            )

            # Parse response
            analysis_text = response.content[0].text
            analysis = self._parse_analysis_response(analysis_text, posts_data)

            print("Analysis complete!")
            return analysis

        except Exception as e:
            print(f"Error during AI analysis: {e}")
            return self._generate_fallback_analysis(posts_data, profile_info)

    def _build_analysis_prompt(self, posts_data: List[Dict], profile_info: Dict,
                              website_data: Dict = None) -> str:
        """Build comprehensive analysis prompt"""

        # Gather post information
        captions = []
        post_stats = []

        for idx, post in enumerate(posts_data[:30], 1):  # Limit to 30 posts
            caption = post.get('caption', '')
            likes = post.get('likesCount', 0)
            comments = post.get('commentsCount', 0)
            post_type = post.get('type', '')

            captions.append(f"Post {idx} ({post_type}): {caption}")
            post_stats.append(f"Post {idx}: {likes} likes, {comments} comments")

        # Build prompt
        prompt = f"""You are an expert social media analyst. Analyze this Instagram profile and provide a comprehensive report.

PROFILE INFORMATION:
Username: {profile_info.get('username', 'N/A')}
Full Name: {profile_info.get('full_name', 'N/A')}
Bio: {profile_info.get('bio', 'N/A')}
Website: {profile_info.get('website', 'N/A')}

POST CAPTIONS AND CONTENT:
{chr(10).join(captions[:20])}

POST ENGAGEMENT:
{chr(10).join(post_stats[:10])}
"""

        if website_data and not website_data.get('error'):
            prompt += f"""

PERSONAL WEBSITE DATA:
Website: {website_data.get('url', '')}
Title: {website_data.get('title', '')}
Description: {website_data.get('description', '')}
Content Preview: {website_data.get('text_content', '')[:1000]}
"""

        prompt += """

Please provide a detailed analysis in the following JSON format:

{
  "summary": {
    "one_sentence": "A one-sentence summary about this person",
    "openers": [
      "First suggested opener to start a conversation",
      "Second suggested opener",
      "Third suggested opener"
    ],
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
  },
  "detailed_report": {
    "name_and_handle": "Analysis of their name and username",
    "intro_and_websites": "Overview of their bio and personal website",
    "interests_and_hobbies": "Detailed analysis of their interests based on posts",
    "relationship_status": {
      "status": "single/in a relationship/married/unclear",
      "confidence": 75,
      "evidence": "Key evidence supporting this conclusion"
    },
    "personality": {
      "mbti": "ENFP",
      "confidence": 60,
      "analysis": "Detailed personality analysis with specific examples from posts"
    },
    "overall_presence": "Description of their overall social media presence and vibe",
    "life_attitude": "Their lifestyle, values, and approach to life",
    "notable_insights": "Other interesting observations about this person"
  }
}

IMPORTANT:
- Be specific and reference actual content from their posts
- Provide percentage confidence levels (0-100) for relationship status and MBTI
- Base your analysis on evidence, not assumptions
- Be respectful and professional
- Focus on positive insights while being honest
- Return ONLY valid JSON without any additional text or markdown formatting
"""

        return prompt

    def _parse_analysis_response(self, response_text: str, posts_data: List[Dict]) -> Dict[str, Any]:
        """Parse Claude's response into structured format"""
        try:
            # Try to extract JSON from response
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            analysis = json.loads(response_text.strip())

            # Add post collages to the analysis
            analysis['posts_with_collages'] = []
            for idx, post in enumerate(posts_data):
                post_entry = {
                    'post_number': idx + 1,
                    'type': post.get('type', ''),
                    'caption': post.get('caption', ''),
                    'likes': post.get('likesCount', 0),
                    'comments': post.get('commentsCount', 0),
                    'url': post.get('url', ''),
                    'collage_path': post.get('collage_path', ''),
                    'timestamp': post.get('timestamp', '')
                }
                analysis['posts_with_collages'].append(post_entry)

            return analysis

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response text: {response_text[:500]}")
            return self._generate_fallback_analysis(posts_data, {})

    def _generate_fallback_analysis(self, posts_data: List[Dict], profile_info: Dict) -> Dict[str, Any]:
        """Generate a basic fallback analysis if AI analysis fails"""
        username = profile_info.get('username', 'this user')

        return {
            "summary": {
                "one_sentence": f"{username} is an active Instagram user sharing diverse content.",
                "openers": [
                    f"Hey! I noticed your Instagram profile and found your content interesting.",
                    f"Hi! I saw your recent posts about [topic], would love to connect!",
                    f"Hello! Your profile caught my attention, especially your posts about [interest]."
                ],
                "keywords": ["Instagram", "Social Media", "Content Creator", "Active User", "Engaging"]
            },
            "detailed_report": {
                "name_and_handle": f"Username: {username}",
                "intro_and_websites": profile_info.get('bio', 'No bio available'),
                "interests_and_hobbies": "Based on their posts, they share diverse content on Instagram.",
                "relationship_status": {
                    "status": "unclear",
                    "confidence": 0,
                    "evidence": "Not enough information to determine"
                },
                "personality": {
                    "mbti": "N/A",
                    "confidence": 0,
                    "analysis": "Unable to determine personality type with current information"
                },
                "overall_presence": "Active on Instagram with regular posts",
                "life_attitude": "Shares content on social media regularly",
                "notable_insights": f"This user has {len(posts_data)} posts analyzed."
            },
            "posts_with_collages": [
                {
                    'post_number': idx + 1,
                    'type': post.get('type', ''),
                    'caption': post.get('caption', ''),
                    'likes': post.get('likesCount', 0),
                    'comments': post.get('commentsCount', 0),
                    'url': post.get('url', ''),
                    'collage_path': post.get('collage_path', ''),
                    'timestamp': post.get('timestamp', '')
                }
                for idx, post in enumerate(posts_data)
            ]
        }
