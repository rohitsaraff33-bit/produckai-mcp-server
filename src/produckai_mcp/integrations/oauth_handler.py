"""OAuth handler for integration authentication with local web server."""

import asyncio
import secrets
import webbrowser
from typing import Dict, Optional
from urllib.parse import urlencode

import keyring
from aiohttp import web

from produckai_mcp.utils.logger import get_logger

logger = get_logger(__name__)


# OAuth configuration for Slack
SLACK_OAUTH_CONFIG = {
    "authorize_url": "https://slack.com/oauth/v2/authorize",
    "token_url": "https://slack.com/api/oauth.v2.access",
    "scopes": [
        "channels:history",
        "channels:read",
        "groups:history",  # For private channels
        "groups:read",
        "users:read",
        "users:read.email",
    ],
}

# OAuth configuration for Google Drive
GOOGLE_DRIVE_OAUTH_CONFIG = {
    "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "scopes": [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ],
}


class OAuthHandler:
    """Handles OAuth2 flows for integrations with local callback server."""

    def __init__(self, integration: str):
        """
        Initialize OAuth handler.

        Args:
            integration: Integration name (slack, gdrive, jira, zoom)
        """
        self.integration = integration
        self.auth_code: Optional[str] = None
        self.state: str = secrets.token_urlsafe(32)
        self.error: Optional[str] = None

    async def start_slack_oauth_flow(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8765/callback",
    ) -> Dict[str, any]:
        """
        Start OAuth flow for Slack.

        Args:
            client_id: Slack app client ID
            client_secret: Slack app client secret
            redirect_uri: OAuth redirect URI (default: http://localhost:8765/callback)

        Returns:
            Dict with status and tokens

        Raises:
            Exception if OAuth flow fails
        """
        logger.info("Starting Slack OAuth flow")

        # Start local callback server
        app = web.Application()
        app.router.add_get("/callback", self._handle_callback)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", 8765)

        try:
            await site.start()
            logger.info("OAuth callback server started on port 8765")

            # Build authorization URL
            auth_params = {
                "client_id": client_id,
                "scope": ",".join(SLACK_OAUTH_CONFIG["scopes"]),
                "redirect_uri": redirect_uri,
                "state": self.state,
            }
            auth_url = f"{SLACK_OAUTH_CONFIG['authorize_url']}?{urlencode(auth_params)}"

            logger.info(f"Opening authorization URL: {auth_url}")

            # Open browser
            webbrowser.open(auth_url)

            # Wait for callback (with timeout)
            try:
                await asyncio.wait_for(self._wait_for_code(), timeout=300)
            except asyncio.TimeoutError:
                raise Exception("OAuth flow timed out after 5 minutes")

            if self.error:
                raise Exception(f"OAuth error: {self.error}")

            if not self.auth_code:
                raise Exception("No authorization code received")

            # Exchange code for tokens
            import httpx

            token_response = await httpx.AsyncClient().post(
                SLACK_OAUTH_CONFIG["token_url"],
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": self.auth_code,
                    "redirect_uri": redirect_uri,
                },
            )

            if token_response.status_code != 200:
                raise Exception(f"Token exchange failed: {token_response.text}")

            token_data = token_response.json()

            if not token_data.get("ok"):
                raise Exception(f"Slack error: {token_data.get('error')}")

            # Store tokens in keyring
            self._store_slack_tokens(token_data)

            result = {
                "status": "success",
                "integration": "slack",
                "workspace": token_data.get("team", {}).get("name"),
                "scopes": token_data.get("scope", "").split(","),
                "bot_user_id": token_data.get("bot_user_id"),
            }

            logger.info("Slack OAuth flow completed successfully")
            return result

        finally:
            # Clean up server
            await runner.cleanup()
            logger.info("OAuth callback server stopped")

    async def _handle_callback(self, request: web.Request) -> web.Response:
        """Handle OAuth callback from authorization server."""
        # Verify state
        state = request.query.get("state")
        if state != self.state:
            self.error = "Invalid state parameter"
            return web.Response(
                text="""
                <html>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h1>❌ Authorization Failed</h1>
                        <p>Invalid state parameter. Please try again.</p>
                        <script>setTimeout(() => window.close(), 3000);</script>
                    </body>
                </html>
                """,
                content_type="text/html",
            )

        # Check for errors
        error = request.query.get("error")
        if error:
            self.error = error
            return web.Response(
                text=f"""
                <html>
                    <body style="font-family: Arial; text-align: center; padding: 50px;">
                        <h1>❌ Authorization Failed</h1>
                        <p>Error: {error}</p>
                        <script>setTimeout(() => window.close(), 3000);</script>
                    </body>
                </html>
                """,
                content_type="text/html",
            )

        # Get authorization code
        self.auth_code = request.query.get("code")

        return web.Response(
            text="""
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>✅ Authorization Successful!</h1>
                    <p>You can close this window and return to Claude.</p>
                    <p>Setting up Slack integration...</p>
                    <script>setTimeout(() => window.close(), 3000);</script>
                </body>
            </html>
            """,
            content_type="text/html",
        )

    async def _wait_for_code(self) -> None:
        """Wait for authorization code to be received."""
        while self.auth_code is None and self.error is None:
            await asyncio.sleep(0.1)

    def _store_slack_tokens(self, token_data: Dict) -> None:
        """
        Store Slack tokens in system keyring.

        Args:
            token_data: Token response from Slack
        """
        # Store access token
        access_token = token_data.get("access_token")
        if access_token:
            keyring.set_password("produckai-mcp", "slack_access_token", access_token)
            logger.info("Stored Slack access token in keyring")

        # Store additional metadata in JSON format
        import json

        metadata = {
            "workspace_id": token_data.get("team", {}).get("id"),
            "workspace_name": token_data.get("team", {}).get("name"),
            "bot_user_id": token_data.get("bot_user_id"),
            "scopes": token_data.get("scope", "").split(","),
        }
        keyring.set_password(
            "produckai-mcp", "slack_metadata", json.dumps(metadata)
        )
        logger.info("Stored Slack metadata in keyring")

    @staticmethod
    def get_slack_token() -> Optional[str]:
        """
        Get Slack access token from keyring.

        Returns:
            Access token or None
        """
        try:
            return keyring.get_password("produckai-mcp", "slack_access_token")
        except Exception as e:
            logger.error(f"Failed to get Slack token: {e}")
            return None

    @staticmethod
    def get_slack_metadata() -> Optional[Dict]:
        """
        Get Slack metadata from keyring.

        Returns:
            Metadata dict or None
        """
        try:
            import json

            metadata_str = keyring.get_password("produckai-mcp", "slack_metadata")
            if metadata_str:
                return json.loads(metadata_str)
            return None
        except Exception as e:
            logger.error(f"Failed to get Slack metadata: {e}")
            return None

    # Google Drive OAuth methods

    async def start_google_drive_oauth_flow(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8765/callback",
    ) -> Dict[str, any]:
        """
        Start Google Drive OAuth2 flow.

        Opens browser for user authorization and starts local callback server.
        Stores access token securely in keyring on success.

        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            redirect_uri: OAuth callback URL (default: localhost:8765)

        Returns:
            Dict with status, account info, and granted scopes

        Raises:
            ValueError: If OAuth flow fails
        """
        import httpx

        config = GOOGLE_DRIVE_OAUTH_CONFIG

        # Build authorization URL
        auth_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config["scopes"]),
            "state": self.state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }

        auth_url = f"{config['authorize_url']}?{urlencode(auth_params)}"

        logger.info(f"Starting Google Drive OAuth flow for integration: {self.integration}")
        logger.info(f"Opening browser to: {auth_url}")

        # Start local callback server
        app = web.Application()
        app.router.add_get("/callback", self._handle_callback)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, "localhost", 8765)
        await site.start()

        logger.info("Local callback server started on http://localhost:8765")

        try:
            # Open browser
            webbrowser.open(auth_url)

            # Wait for callback (max 5 minutes)
            for _ in range(300):  # 300 seconds = 5 minutes
                if self.auth_code or self.error:
                    break
                await asyncio.sleep(1)

            if self.error:
                raise ValueError(f"OAuth authorization failed: {self.error}")

            if not self.auth_code:
                raise ValueError("OAuth authorization timed out after 5 minutes")

            logger.info("Authorization code received, exchanging for access token")

            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config["token_url"],
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": self.auth_code,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )

                if response.status_code != 200:
                    raise ValueError(f"Token exchange failed: {response.text}")

                token_data = response.json()

                # Store tokens in keyring
                self._store_google_drive_tokens(token_data)

                # Get user info
                user_info = await self._get_google_user_info(token_data["access_token"])

                logger.info(f"Google Drive OAuth completed for user: {user_info.get('email')}")

                return {
                    "status": "success",
                    "user_email": user_info.get("email"),
                    "user_name": user_info.get("name"),
                    "scopes": token_data.get("scope", "").split(),
                    "expires_in": token_data.get("expires_in", 3600),
                }

        finally:
            # Cleanup server
            await runner.cleanup()
            logger.info("Local callback server stopped")

    async def _get_google_user_info(self, access_token: str) -> Dict[str, any]:
        """Get Google user information."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                logger.warning(f"Failed to get user info: {response.text}")
                return {}

            return response.json()

    def _store_google_drive_tokens(self, token_data: Dict[str, any]) -> None:
        """Store Google Drive tokens in keyring."""
        import json

        # Store access token
        keyring.set_password(
            "produckai-mcp",
            "gdrive_access_token",
            token_data["access_token"],
        )
        logger.info("Stored Google Drive access token in keyring")

        # Store refresh token (if available)
        if "refresh_token" in token_data:
            keyring.set_password(
                "produckai-mcp",
                "gdrive_refresh_token",
                token_data["refresh_token"],
            )
            logger.info("Stored Google Drive refresh token in keyring")

        # Store metadata
        metadata = {
            "expires_in": token_data.get("expires_in", 3600),
            "scope": token_data.get("scope", ""),
            "token_type": token_data.get("token_type", "Bearer"),
        }

        keyring.set_password(
            "produckai-mcp",
            "gdrive_metadata",
            json.dumps(metadata),
        )
        logger.info("Stored Google Drive metadata in keyring")

    @staticmethod
    def get_google_drive_token() -> Optional[str]:
        """
        Get Google Drive access token from keyring.

        Returns:
            Access token or None
        """
        try:
            return keyring.get_password("produckai-mcp", "gdrive_access_token")
        except Exception as e:
            logger.error(f"Failed to get Google Drive token: {e}")
            return None

    @staticmethod
    def get_google_drive_refresh_token() -> Optional[str]:
        """
        Get Google Drive refresh token from keyring.

        Returns:
            Refresh token or None
        """
        try:
            return keyring.get_password("produckai-mcp", "gdrive_refresh_token")
        except Exception as e:
            logger.error(f"Failed to get Google Drive refresh token: {e}")
            return None

    @staticmethod
    def get_google_drive_metadata() -> Optional[Dict]:
        """
        Get Google Drive metadata from keyring.

        Returns:
            Metadata dict or None
        """
        try:
            import json

            metadata_str = keyring.get_password("produckai-mcp", "gdrive_metadata")
            if metadata_str:
                return json.loads(metadata_str)
            return None
        except Exception as e:
            logger.error(f"Failed to get Google Drive metadata: {e}")
            return None
