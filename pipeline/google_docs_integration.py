"""
Google Docs API integration for pushing plan documents.

Handles authentication and document creation/updating via Google Docs API.

Setup:
    1. Create a Google Cloud project
    2. Enable Google Docs API and Google Drive API
    3. Create OAuth 2.0 credentials (Desktop app)
    4. Download credentials.json to config/
    5. Copy config/google_docs.ini.example to config/google_docs.ini
    6. Update config with credentials path
"""

import configparser
import logging
import os
from pathlib import Path
from typing import Optional

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


logger = logging.getLogger(__name__)


# OAuth 2.0 scopes required for Google Docs
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


class GoogleDocsUploader:
    """Client for uploading plan documents to Google Docs."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Google Docs uploader.

        Args:
            config_path: Path to configuration INI file (default: config/google_docs.ini)
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google API packages not installed. Run:\n"
                "pip install google-auth google-auth-oauthlib "
                "google-auth-httplib2 google-api-python-client"
            )

        if config_path is None:
            config_path = "config/google_docs.ini"

        self.config = self._load_config(config_path)
        self.credentials = None
        self.docs_service = None
        self.drive_service = None
        self._authenticate()

    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load configuration from INI file."""
        config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        config.read(config_path)

        # Validate required sections and keys
        if "google_docs" not in config:
            raise ValueError("Missing [google_docs] section in config")

        required_keys = ["credentials_file"]
        for key in required_keys:
            if key not in config["google_docs"]:
                raise ValueError(f"Missing required config key: {key}")

        return config

    def _authenticate(self):
        """Authenticate with Google APIs using OAuth 2.0."""
        creds = None
        token_file = self.config["google_docs"].get("token_file", "config/token.json")
        credentials_file = self.config["google_docs"]["credentials_file"]

        # Load existing token if available
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {credentials_file}\n"
                        "Download from Google Cloud Console and save to this location."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future use
            Path(token_file).parent.mkdir(parents=True, exist_ok=True)
            with open(token_file, "w") as token:
                token.write(creds.to_json())

        self.credentials = creds
        self.docs_service = build("docs", "v1", credentials=creds)
        self.drive_service = build("drive", "v3", credentials=creds)

    def create_document_from_markdown(self, markdown_content: str, title: str) -> str:
        """
        Create a new Google Doc with markdown content.

        Args:
            markdown_content: Markdown-formatted content to insert
            title: Document title

        Returns:
            URL of created document
        """
        try:
            logger.info(f"Creating Google Doc: {title}")

            # Create blank document
            doc = self.docs_service.documents().create(body={"title": title}).execute()
            doc_id = doc["documentId"]
            logger.info(f"Document created with ID: {doc_id}")

            # Convert markdown to plain text (basic conversion)
            # For production, consider using a markdown parser
            plain_content = self._markdown_to_plain(markdown_content)

            # Insert content
            requests = [
                {"insertText": {"location": {"index": 1}, "text": plain_content}}
            ]

            self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={"requests": requests}
            ).execute()
            logger.info("Content inserted successfully")

            # Set sharing permissions if configured
            sharing = self.config["google_docs"].get("sharing", "private")
            if sharing == "anyone":
                logger.info("Sharing document with anyone")
                self._share_document(doc_id, "anyone", "reader")
            elif sharing == "domain":
                domain = self.config["google_docs"].get("domain", "")
                if domain:
                    logger.info(f"Sharing document with domain: {domain}")
                    self._share_document(doc_id, f"domain:{domain}", "reader")

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            logger.info(f"Document created: {doc_url}")
            return doc_url

        except HttpError as error:
            logger.error(f"Failed to create Google Doc: {error}")
            raise RuntimeError(f"Failed to create Google Doc: {error}")

    def update_document(self, doc_id: str, markdown_content: str) -> str:
        """
        Update an existing Google Doc with new content.

        Args:
            doc_id: Google Docs document ID
            markdown_content: Markdown-formatted content to insert

        Returns:
            URL of updated document
        """
        try:
            # Get document to find end index
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            content = doc.get("body").get("content")
            end_index = content[-1].get("endIndex", 1)

            # Convert markdown to plain text
            plain_content = self._markdown_to_plain(markdown_content)

            # Replace all content
            requests = [
                {
                    "deleteContentRange": {
                        "range": {"startIndex": 1, "endIndex": end_index - 1}
                    }
                },
                {"insertText": {"location": {"index": 1}, "text": plain_content}},
            ]

            self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={"requests": requests}
            ).execute()

            return f"https://docs.google.com/document/d/{doc_id}/edit"

        except HttpError as error:
            raise RuntimeError(f"Failed to update Google Doc: {error}")

    def _share_document(self, doc_id: str, email_or_domain: str, role: str = "reader"):
        """
        Share document with specific user or domain.

        Args:
            doc_id: Document ID
            email_or_domain: Email address, 'anyone', or 'domain:example.com'
            role: Permission role ('reader', 'writer', 'commenter')
        """
        try:
            permission = {
                "type": "user" if "@" in email_or_domain else "anyone",
                "role": role,
            }

            if email_or_domain.startswith("domain:"):
                permission["type"] = "domain"
                permission["domain"] = email_or_domain.split(":", 1)[1]
            elif email_or_domain == "anyone":
                permission["type"] = "anyone"
            else:
                permission["emailAddress"] = email_or_domain

            self.drive_service.permissions().create(
                fileId=doc_id, body=permission
            ).execute()

        except HttpError as error:
            # Non-fatal: document is still created, just not shared
            print(f"Warning: Failed to share document: {error}")

    def _markdown_to_plain(self, markdown: str) -> str:
        """
        Convert markdown to plain text (basic implementation).

        For production use, consider integrating a proper markdown parser
        that preserves formatting using Google Docs API formatting requests.

        Args:
            markdown: Markdown content

        Returns:
            Plain text version
        """
        # Basic markdown stripping (preserves structure but loses formatting)
        text = markdown

        # Remove markdown bold/italic
        text = text.replace("**", "").replace("__", "")
        text = text.replace("*", "").replace("_", "")

        # Keep checkbox format
        text = text.replace("- [ ]", "☐")
        text = text.replace("- [x]", "☑")

        return text

    def list_documents(self, max_results: int = 10) -> list:
        """
        List recent Google Docs documents.

        Args:
            max_results: Maximum number of documents to return

        Returns:
            List of document metadata dictionaries
        """
        try:
            results = (
                self.drive_service.files()
                .list(
                    q="mimeType='application/vnd.google-apps.document'",
                    pageSize=max_results,
                    fields="files(id, name, createdTime, modifiedTime, webViewLink)",
                )
                .execute()
            )

            return results.get("files", [])

        except HttpError as error:
            raise RuntimeError(f"Failed to list documents: {error}")
