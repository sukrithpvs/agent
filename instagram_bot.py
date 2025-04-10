import asyncio
import os
from typing import Optional, Tuple, Dict
from instagrapi import Client
from dotenv import load_dotenv
import questionary
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint
from rich.table import Table
import logging
from pathlib import Path
import requests
from groq import AsyncGroq
import urllib.parse
import tempfile
from PIL import Image
from io import BytesIO
import json
import re

# Load environment variables
load_dotenv()

# Initialize Rich console and logging
console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('instagram_bot')

# Initialize Groq client
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

class AIAssistant:
    @staticmethod
    async def process_command(prompt: str) -> Dict:
        try:
            # First, analyze the command type
            command_lower = prompt.lower()
            
            # Handle message commands
            if "send" in command_lower and "to" in command_lower:
                try:
                    # Extract username and message
                    parts = prompt.split("to", 1)
                    message = parts[0].replace("send", "").strip()
                    username = parts[1].strip()
                    return {
                        "action": "message",
                        "details": {
                            "username": username,
                            "message": message
                        }
                    }
                except Exception:
                    logger.error("Failed to parse message command")
                    return None

            # Handle post commands
            elif "post" in command_lower or "create" in command_lower:
                return {
                    "action": "post",
                    "details": {
                        "caption": prompt,
                        "image_prompt": prompt
                    }
                }

            # Handle like commands
            elif "like" in command_lower:
                try:
                    url = prompt.split("like", 1)[1].strip()
                    return {
                        "action": "like",
                        "details": {
                            "post_url": url
                        }
                    }
                except Exception:
                    logger.error("Failed to parse like command")
                    return None

            # Handle comment commands
            elif "comment" in command_lower:
                try:
                    parts = prompt.split("comment", 1)[1].strip().split("on", 1)
                    comment_text = parts[0].strip()
                    post_url = parts[1].strip()
                    return {
                        "action": "comment",
                        "details": {
                            "post_url": post_url,
                            "comment_text": comment_text
                        }
                    }
                except Exception:
                    logger.error("Failed to parse comment command")
                    return None

            # Handle follow commands
            elif "follow" in command_lower:
                try:
                    username = prompt.split("follow", 1)[1].strip()
                    return {
                        "action": "follow",
                        "details": {
                            "username": username
                        }
                    }
                except Exception:
                    logger.error("Failed to parse follow command")
                    return None

            # Handle unfollow commands
            elif "unfollow" in command_lower:
                try:
                    username = prompt.split("unfollow", 1)[1].strip()
                    return {
                        "action": "unfollow",
                        "details": {
                            "username": username
                        }
                    }
                except Exception:
                    logger.error("Failed to parse unfollow command")
                    return None

            else:
                logger.error(f"Unknown command type: {prompt}")
                return None

        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return None

class ContentGenerator:
    @staticmethod
    async def generate_content(prompt: str) -> Tuple[str, str]:
        try:
            system_prompt = """Create Instagram content. Respond with JSON only:
            {
                "caption": "Instagram caption with hashtags",
                "image_prompt": "detailed image generation prompt"
            }"""

            response = await groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="meta-llama/llama-4-scout-17b-16e-instruct"
            )

            response_text = response.choices[0].message.content.strip()
            response_text = response_text.replace('```json\n', '').replace('```', '')
            
            content = json.loads(response_text)
            return content["caption"], content["image_prompt"]

        except Exception as e:
            logger.error(f"Content generation error: {e}")
            return None, None

    @staticmethod
    async def generate_image(prompt: str) -> Optional[str]:
        try:
            encoded_prompt = urllib.parse.quote(prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            response = requests.get(image_url)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(response.content)
                return temp_file.name

        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None

class InstagramBot:
    def __init__(self):
        self.client = Client()
        self.logged_in = False
        self.username = None
        self.session_file = 'session.json'
        self.settings_file = 'instagram_settings.json'
        self.content_generator = ContentGenerator()
        self.ai_assistant = AIAssistant()

    async def save_session(self):
        try:
            self.client.dump_settings(self.settings_file)
            session_data = {
                'username': self.username,
                'logged_in': self.logged_in
            }
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
            logger.info("Session saved successfully")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    async def load_session(self) -> bool:
        try:
            if os.path.exists(self.settings_file) and os.path.exists(self.session_file):
                self.client.load_settings(self.settings_file)
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                self.username = session_data.get('username')
                self.logged_in = session_data.get('logged_in', False)
                try:
                    self.client.get_timeline_feed()
                    logger.info("Session loaded successfully")
                    return True
                except Exception:
                    logger.info("Saved session expired")
                    return False
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
        return False

    async def login(self, username: str, password: str) -> bool:
        try:
            if await self.load_session():
                console.print("[green]Logged in using saved session[/green]")
                return True

            self.client.login(username, password)
            self.logged_in = True
            self.username = username
            await self.save_session()
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def logout(self):
        try:
            self.client.logout()
            self.logged_in = False
            self.username = None
            for file in [self.session_file, self.settings_file]:
                if os.path.exists(file):
                    os.remove(file)
            console.print("[green]Logged out successfully[/green]")
        except Exception as e:
            logger.error(f"Logout error: {e}")

    async def process_natural_command(self, command: str) -> bool:
        try:
            console.print(f"[blue]Processing command: {command}[/blue]")
            action_data = await self.ai_assistant.process_command(command)
            
            if not action_data:
                console.print("[red]Failed to process command[/red]")
                return False

            action = action_data["action"]
            details = action_data["details"]

            console.print(f"[blue]Executing action: {action}[/blue]")

            if action == "post":
                return await self.create_ai_post(details.get("caption", command))
            elif action == "message":
                return await self.send_dm(details["username"], details["message"])
            elif action == "like":
                return await self.like_post(details["post_url"])
            elif action == "comment":
                return await self.comment_on_post(details["post_url"], details["comment_text"])
            elif action == "follow":
                return await self.follow_user(details["username"])
            elif action == "unfollow":
                return await self.unfollow_user(details["username"])
            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                return False

        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return False

    # In instagram_bot.py, modify the create_ai_post method:

    async def create_ai_post(self, prompt: str) -> tuple:
        try:
            caption, image_prompt = await self.content_generator.generate_content(prompt)
            if not caption or not image_prompt:
                return False, None, None

            image_path = await self.content_generator.generate_image(image_prompt)
            if not image_path:
                return False, None, None

            # Return a tuple of success status, image path, and caption
            return True, image_path, caption

        except Exception as e:
            logger.error(f"Error creating AI post: {e}")
            return False, None, None

    async def send_dm(self, username: str, message: str) -> bool:
        try:
            user_id = self.client.user_id_from_username(username)
            self.client.direct_send(message, [user_id])
            console.print(f"[green]Message sent to {username}![/green]")
            return True
        except Exception as e:
            logger.error(f"Error sending DM: {e}")
            return False

    async def like_post(self, post_url: str) -> bool:
        try:
            media_id = self.client.media_id(self.client.media_pk_from_url(post_url))
            self.client.media_like(media_id)
            console.print("[green]Post liked successfully![/green]")
            return True
        except Exception as e:
            logger.error(f"Error liking post: {e}")
            return False

    async def comment_on_post(self, post_url: str, comment: str) -> bool:
        try:
            media_id = self.client.media_id(self.client.media_pk_from_url(post_url))
            self.client.media_comment(media_id, comment)
            console.print("[green]Comment posted successfully![/green]")
            return True
        except Exception as e:
            logger.error(f"Error commenting: {e}")
            return False

    async def follow_user(self, username: str) -> bool:
        try:
            user_id = self.client.user_id_from_username(username)
            self.client.user_follow(user_id)
            console.print(f"[green]Now following {username}![/green]")
            return True
        except Exception as e:
            logger.error(f"Error following user: {e}")
            return False

    async def unfollow_user(self, username: str) -> bool:
        try:
            user_id = self.client.user_id_from_username(username)
            self.client.user_unfollow(user_id)
            console.print(f"[green]Unfollowed {username}![/green]")
            return True
        except Exception as e:
            logger.error(f"Error unfollowing user: {e}")
            return False