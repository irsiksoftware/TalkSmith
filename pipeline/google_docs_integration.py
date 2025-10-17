#!/usr/bin/env python3
"""
Google Docs API integration for plan publishing.

Pushes structured plan documents to Google Docs for collaborative editing.
Requires Google Cloud project with Docs API enabled and service account credentials.
"""

import logging
import configparser
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logging.warning("Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


logger = logging.getLogger(__name__)


@dataclass
class GoogleDocsConfig:
    """Configuration for Google Docs integration."""
    credentials_file: Path
    folder_id: Optional[str] = None
    share_with_emails: Optional[List[str]] = None
    share_permission: str = "writer"  # reader, commenter, writer

    @classmethod
    def from_config_file(cls, config_file: Path = None) -> "GoogleDocsConfig":
        """Load configuration from INI file."""
        if config_file is None:
            config_file = Path("config/google_docs.ini")

        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}\n"
                f"Create it from config/google_docs.ini.example"
            )

        config = configparser.ConfigParser()
        config.read(config_file)

        credentials_file = Path(config.get("google_docs", "credentials_file"))
        folder_id = config.get("google_docs", "folder_id", fallback=None)

        share_emails = config.get("google_docs", "share_with_emails", fallback="")
        share_with_emails = [e.strip() for e in share_emails.split(",") if e.strip()]

        share_permission = config.get("google_docs", "share_permission", fallback="writer")

        return cls(
            credentials_file=credentials_file,
            folder_id=folder_id,
            share_with_emails=share_with_emails if share_with_emails else None,
            share_permission=share_permission
        )


class GoogleDocsPublisher:
    """Publishes plan documents to Google Docs."""

    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive.file'
    ]

    def __init__(self, config: Optional[GoogleDocsConfig] = None):
        """Initialize publisher with configuration."""
        if not GOOGLE_AVAILABLE:
            raise RuntimeError(
                "Google API libraries not installed. Run:\n"
                "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )

        if config is None:
            config = GoogleDocsConfig.from_config_file()

        self.config = config
        self.credentials = self._get_credentials()
        self.docs_service = build('docs', 'v1', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)

    def _get_credentials(self):
        """Get service account credentials."""
        if not self.config.credentials_file.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.config.credentials_file}\n"
                f"Download service account JSON from Google Cloud Console"
            )

        credentials = service_account.Credentials.from_service_account_file(
            str(self.config.credentials_file),
            scopes=self.SCOPES
        )
        return credentials

    def create_document(self, plan, share: bool = True) -> str:
        """
        Create Google Doc from plan.

        Args:
            plan: Plan object with title and sections
            share: Whether to share document with configured emails

        Returns:
            URL of created Google Doc
        """
        try:
            # Create document
            doc_metadata = {'title': plan.title}
            if self.config.folder_id:
                doc_metadata['parents'] = [self.config.folder_id]

            doc = self.docs_service.documents().create(body={'title': plan.title}).execute()
            doc_id = doc['documentId']
            logger.info(f"Created document: {plan.title} (ID: {doc_id})")

            # Build content requests
            requests = self._build_content_requests(plan)

            # Update document with content
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                logger.info(f"Added content to document")

            # Move to folder if specified
            if self.config.folder_id:
                self._move_to_folder(doc_id, self.config.folder_id)

            # Share document
            if share and self.config.share_with_emails:
                self._share_document(doc_id, self.config.share_with_emails)

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            return doc_url

        except HttpError as e:
            logger.error(f"Google Docs API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise

    def _build_content_requests(self, plan) -> List[Dict]:
        """Build batch update requests for document content."""
        requests = []
        index = 1

        # Add metadata
        requests.append({
            'insertText': {
                'location': {'index': index},
                'text': f"\n\nGenerated: {plan.generated_date}\nSource: {plan.source_file}\n\n"
            }
        })
        index += len(f"\n\nGenerated: {plan.generated_date}\nSource: {plan.source_file}\n\n")

        # Style metadata as small text
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': 1,
                    'endIndex': index
                },
                'textStyle': {
                    'fontSize': {
                        'magnitude': 9,
                        'unit': 'PT'
                    },
                    'foregroundColor': {
                        'color': {
                            'rgbColor': {
                                'red': 0.5,
                                'green': 0.5,
                                'blue': 0.5
                            }
                        }
                    }
                },
                'fields': 'fontSize,foregroundColor'
            }
        })

        # Add separator
        requests.append({
            'insertText': {
                'location': {'index': index},
                'text': "—" * 50 + "\n\n"
            }
        })
        index += 52

        # Add sections
        section_order = [
            "problem_statement",
            "target_users",
            "goals_objectives",
            "acceptance_criteria",
            "risks_considerations"
        ]

        for section_key in section_order:
            if section_key not in plan.sections:
                continue

            section = plan.sections[section_key]

            # Add section heading
            heading_text = f"{section.title}\n"
            requests.append({
                'insertText': {
                    'location': {'index': index},
                    'text': heading_text
                }
            })

            # Style heading
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': index,
                        'endIndex': index + len(heading_text)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2'
                    },
                    'fields': 'namedStyleType'
                }
            })
            index += len(heading_text)

            # Add content items
            for item in section.content:
                item_text = f"• {item}\n"
                requests.append({
                    'insertText': {
                        'location': {'index': index},
                        'text': item_text
                    }
                })
                index += len(item_text)

            # Add timestamps reference
            if section.timestamps:
                timestamp_text = f"\nReferenced timestamps: {', '.join(section.timestamps)}\n\n"
                requests.append({
                    'insertText': {
                        'location': {'index': index},
                        'text': timestamp_text
                    }
                })

                # Style timestamps as italic
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': index,
                            'endIndex': index + len(timestamp_text) - 2
                        },
                        'textStyle': {
                            'italic': True,
                            'fontSize': {
                                'magnitude': 9,
                                'unit': 'PT'
                            }
                        },
                        'fields': 'italic,fontSize'
                    }
                })
                index += len(timestamp_text)
            else:
                requests.append({
                    'insertText': {
                        'location': {'index': index},
                        'text': "\n"
                    }
                })
                index += 1

        return requests

    def _move_to_folder(self, doc_id: str, folder_id: str):
        """Move document to specified folder."""
        try:
            # Get current parents
            file_metadata = self.drive_service.files().get(
                fileId=doc_id,
                fields='parents'
            ).execute()

            previous_parents = ','.join(file_metadata.get('parents', []))

            # Move to new folder
            self.drive_service.files().update(
                fileId=doc_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()

            logger.info(f"Moved document to folder: {folder_id}")
        except HttpError as e:
            logger.warning(f"Failed to move document to folder: {e}")

    def _share_document(self, doc_id: str, emails: List[str]):
        """Share document with specified emails."""
        for email in emails:
            try:
                permission = {
                    'type': 'user',
                    'role': self.config.share_permission,
                    'emailAddress': email
                }

                self.drive_service.permissions().create(
                    fileId=doc_id,
                    body=permission,
                    sendNotificationEmail=True
                ).execute()

                logger.info(f"Shared document with {email} ({self.config.share_permission})")
            except HttpError as e:
                logger.warning(f"Failed to share with {email}: {e}")

    def update_document(self, doc_id: str, plan) -> str:
        """
        Update existing Google Doc with new plan content.

        Args:
            doc_id: Google Doc ID
            plan: Plan object with updated content

        Returns:
            URL of updated Google Doc
        """
        try:
            # Clear existing content (delete from index 1 to end)
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            content_length = doc['body']['content'][-1]['endIndex']

            delete_request = {
                'deleteContentRange': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': content_length - 1
                    }
                }
            }

            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': [delete_request]}
            ).execute()

            # Add new content
            requests = self._build_content_requests(plan)
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()

            logger.info(f"Updated document: {doc_id}")
            return f"https://docs.google.com/document/d/{doc_id}/edit"

        except HttpError as e:
            logger.error(f"Failed to update document: {e}")
            raise


def main():
    """Test Google Docs integration."""
    import argparse
    from plan_from_transcript import PlanExtractor

    parser = argparse.ArgumentParser(description="Test Google Docs integration")
    parser.add_argument("segments_file", type=Path, help="Segments JSON file")
    parser.add_argument("-c", "--config", type=Path, help="Config file path")

    args = parser.parse_args()

    # Extract plan
    extractor = PlanExtractor(args.segments_file)
    plan = extractor.extract_plan()

    # Publish to Google Docs
    config = GoogleDocsConfig.from_config_file(args.config) if args.config else None
    publisher = GoogleDocsPublisher(config)
    doc_url = publisher.create_document(plan)

    print(f"Document created: {doc_url}")


if __name__ == "__main__":
    main()
