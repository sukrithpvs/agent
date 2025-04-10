import streamlit as st
import asyncio
from instagram_bot import InstagramBot, console, logger, GROQ_API_KEY
from rich.panel import Panel
from typing import Tuple
from pathlib import Path
import logging
import nest_asyncio
import time

# Enable nested async loops (needed for Streamlit)
nest_asyncio.apply()

class StreamlitInstagramBot:
    def __init__(self):
        self.bot = InstagramBot()
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False

    async def handle_login(self):
        """Handle the login process"""
        st.subheader("Login to Instagram")

        # Check if already logged in
        if st.session_state.logged_in:
            st.success(f"Already logged in as: {self.bot.username}")
            if st.button("Logout"):
                await self.handle_logout()
                st.rerun()
            return

        # Login form
        with st.form("login_form"):
            username = st.text_input("Instagram Username")
            password = st.text_input("Instagram Password", type="password")
            submit = st.form_submit_button("Login")

            if submit and username and password:
                with st.spinner("Logging in..."):
                    try:
                        if await self.bot.login(username, password):
                            st.session_state.logged_in = True
                            st.success("Successfully logged in!")
                            st.rerun()
                        else:
                            st.error("Login failed. Please check your credentials.")
                    except Exception as e:
                        st.error(f"Login error: {str(e)}")

    async def handle_logout(self):
        """Handle the logout process"""
        try:
            await self.bot.logout()
            st.session_state.logged_in = False
            st.success("Successfully logged out!")
        except Exception as e:
            st.error(f"Logout error: {str(e)}")

    async def handle_posting(self):
        """Handle post creation"""
        st.subheader("Create Post")
        
        # Initialize session state variables if they don't exist
        if 'generated_content' not in st.session_state:
            st.session_state.generated_content = None
        if 'post_type' not in st.session_state:
            st.session_state.post_type = "AI Generated Post"

        # Post type selection
        st.session_state.post_type = st.selectbox(
            "Select post type",
            ["AI Generated Post", "Regular Post", "Schedule Post"]
        )

        if st.session_state.post_type == "AI Generated Post":
            # Initialize prompt in session state if it doesn't exist
            if 'prompt' not in st.session_state:
                st.session_state.prompt = ""
            
            # Text input for prompt
            prompt = st.text_area("What would you like to post about?", value=st.session_state.prompt)
            st.session_state.prompt = prompt

            # Generate button
            if st.button("Generate Post") and prompt:
                with st.spinner("Creating AI post..."):
                    try:
                        success, image_path, caption = await self.bot.create_ai_post(prompt)
                        if success and image_path and caption:
                            st.session_state.generated_content = {
                                'image_path': image_path,
                                'caption': caption
                            }
                        else:
                            st.error("Failed to generate post content. Please try again.")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

            # Display preview if content was generated
            if st.session_state.generated_content:
                # Create two columns for preview
                col1, col2 = st.columns(2)
                
                with col1:
                    st.image(st.session_state.generated_content['image_path'], 
                            caption="Generated Image Preview")
                
                with col2:
                    st.text_area("Caption Preview", 
                                value=st.session_state.generated_content['caption'], 
                                height=200, 
                                disabled=True)
                
                # Add posting confirmation
                col3, col4 = st.columns(2)
                
                with col3:
                    if st.button("Post Content"):
                        try:
                            self.bot.client.photo_upload(
                                st.session_state.generated_content['image_path'],
                                st.session_state.generated_content['caption']
                            )
                            # Clean up
                            import os
                            if os.path.exists(st.session_state.generated_content['image_path']):
                                os.unlink(st.session_state.generated_content['image_path'])
                            
                            # Reset session state
                            st.session_state.generated_content = None
                            st.session_state.prompt = ""
                            
                            st.success("Posted successfully!")
                            time.sleep(2)  # Give time for the success message to be seen
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to post: {str(e)}")
                
                with col4:
                    if st.button("Cancel"):
                        try:
                            # Clean up
                            import os
                            if os.path.exists(st.session_state.generated_content['image_path']):
                                os.unlink(st.session_state.generated_content['image_path'])
                            
                            # Reset session state
                            st.session_state.generated_content = None
                            st.session_state.prompt = ""
                            
                            st.info("Post cancelled")
                            time.sleep(2)  # Give time for the info message to be seen
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error during cancellation: {str(e)}")

        elif st.session_state.post_type == "Regular Post":
            st.info("Regular posting feature coming soon!")
            upload_file = st.file_uploader("Choose an image", type=['jpg', 'jpeg', 'png'])
            caption = st.text_area("Write your caption")
            
            if upload_file is not None and st.button("Post"):
                st.info("This feature is not yet implemented")
        
        elif st.session_state.post_type == "Schedule Post":
            st.info("Post scheduling feature coming soon!")


    async def handle_messaging(self):
        """Handle messaging features"""
        st.subheader("Messaging")
        message_type = st.selectbox(
            "Select message type",
            ["Direct Message", "Bulk Messages", "Reply to Messages"]
        )

        if message_type == "Direct Message":
            with st.form("dm_form"):
                username = st.text_input("Recipient's username")
                message = st.text_area("Your message")
                submit = st.form_submit_button("Send Message")

                if submit and username and message:
                    with st.spinner("Sending message..."):
                        if await self.bot.send_dm(username, message):
                            st.success("Message sent successfully!")
                        else:
                            st.error("Failed to send message.")

    async def handle_interactions(self):
        """Handle user interactions"""
        st.subheader("Interactions")
        interaction_type = st.selectbox(
            "Select interaction type",
            ["Like Post", "Comment on Post", "Follow User", "Unfollow User"]
        )

        if interaction_type == "Like Post":
            with st.form("like_form"):
                post_url = st.text_input("Post URL")
                submit = st.form_submit_button("Like Post")

                if submit and post_url:
                    with st.spinner("Liking post..."):
                        if await self.bot.like_post(post_url):
                            st.success("Post liked successfully!")
                        else:
                            st.error("Failed to like post.")

async def main():
    # Set page config
    st.set_page_config(
        page_title="Instagram AI Assistant",
        page_icon="📸",
        layout="wide"
    )

    # Initialize bot
    if 'bot' not in st.session_state:
        st.session_state.bot = StreamlitInstagramBot()

    # Title
    st.title("Instagram AI Assistant")

    # Sidebar navigation
    nav_selection = st.sidebar.radio(
        "Navigation",
        ["Login", "Posting", "Messaging", "Interactions", "Settings"]
    )

    # Check login status and handle navigation
    if not st.session_state.logged_in and nav_selection != "Login":
        st.warning("Please login first!")
        nav_selection = "Login"

    # Handle navigation
    if nav_selection == "Login":
        await st.session_state.bot.handle_login()
    elif nav_selection == "Posting":
        await st.session_state.bot.handle_posting()
    elif nav_selection == "Messaging":
        await st.session_state.bot.handle_messaging()
    elif nav_selection == "Interactions":
        await st.session_state.bot.handle_interactions()
    elif nav_selection == "Settings":
        st.info("Settings feature coming soon!")

if __name__ == "__main__":
    # Create necessary directories
    for directory in ['logs', 'sessions']:
        Path(directory).mkdir(exist_ok=True)
        
    # Set debug logging
    logging.getLogger('instagram_bot').setLevel(logging.DEBUG)
    
    if not GROQ_API_KEY:
        st.error("Please set GROQ_API_KEY in your .env file")
    else:
        asyncio.run(main())