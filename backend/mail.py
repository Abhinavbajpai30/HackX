"""
FastAPI Backend with Google OAuth, Gmail Watch API and MongoDB
Requirements:
    pip install fastapi uvicorn google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-jose[cryptography] python-multipart motor pymongo python-dotenv
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db import get_async_session
from models import GmailUser, GmailEmail, OAuthState, GmailSenderStat, EmailEvent
import os
import json
from typing import Optional
from datetime import datetime, timedelta
import base64
from dotenv import load_dotenv, find_dotenv

from datetime import datetime, timedelta, timezone
import base64
from dotenv import load_dotenv, find_dotenv
from contextlib import asynccontextmanager

load_dotenv(find_dotenv())

# UTC constant for timezone-aware datetimes
UTC = timezone.utc

app = FastAPI()

# Configuration - Store these in environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your-client-id.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "your-client-secret")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# CORS Configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:3000"
).split(",")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Google OAuth scopes - requesting Gmail access
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
]

# Client configuration for OAuth flow
CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI],
    }
}

@app.on_event("startup")
async def startup_event():
    # Tables are created in backend/main.py
    print("Postgres ready via SQLAlchemy AsyncSession")


def credentials_to_dict(credentials):
    """Convert credentials object to dictionary for storage"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


def dict_to_credentials(creds_dict):
    """Convert dictionary back to credentials object"""
    return Credentials(
        token=creds_dict['token'],
        refresh_token=creds_dict.get('refresh_token'),
        token_uri=creds_dict['token_uri'],
        client_id=creds_dict['client_id'],
        client_secret=creds_dict['client_secret'],
        scopes=creds_dict['scopes']
    )


@app.get("/")
async def root():
    return {"message": "Google OAuth & Gmail API Server with Postgres"}


@app.get("/auth/login")
async def login(session: AsyncSession = Depends(get_async_session)):
    """Initiate OAuth flow"""
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store state in Postgres for verification
    state_row = OAuthState(
        state=state,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    session.add(state_row)
    await session.commit()
    
    return {"authorization_url": authorization_url, "state": state}


@app.get("/auth/callback")
async def auth_callback(code: str, state: str, session: AsyncSession = Depends(get_async_session)):
    """Handle OAuth callback"""
    try:
        # Verify state
        res = await session.execute(select(OAuthState).where(OAuthState.state == state))
        state_row = res.scalar_one_or_none()
        if not state_row or state_row.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid or expired state")
        
        # Delete used state
        await session.execute(delete(OAuthState).where(OAuthState.state == state))
        await session.commit()
        
        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Exchange authorization code for credentials
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        user_email = user_info.get('email')
        
        # Store/update user in Postgres
        res_user = await session.execute(select(GmailUser).where(GmailUser.email == user_email))
        user_row = res_user.scalar_one_or_none()
        if not user_row:
            user_row = GmailUser(
                email=user_email,
                user_info=user_info,
                credentials=credentials_to_dict(credentials),
                last_login=datetime.utcnow(),
            )
            session.add(user_row)
        else:
            user_row.user_info = user_info
            user_row.credentials = credentials_to_dict(credentials)
            user_row.last_login = datetime.utcnow()
        await session.commit()
        
        # Set up Gmail watch for this user
        await setup_gmail_watch(user_email, session)
        
        return RedirectResponse(url=f"{FRONTEND_URL}/dashboard?email={user_email}")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


async def setup_gmail_watch(user_email: str, session: AsyncSession = Depends(get_async_session)):
    """
    Set up Gmail Push Notifications using Pub/Sub
    
    Prerequisites:
    1. Create a Google Cloud Project
    2. Enable Gmail API
    3. Create a Pub/Sub topic (e.g., 'gmail-notifications')
    4. Grant Gmail service account publish rights to the topic:
       gmail-api-push@system.gserviceaccount.com
    5. Create a subscription to the topic pointing to your webhook URL
    """
    
    try:
        res_user = await session.execute(select(GmailUser).where(GmailUser.email == user_email))
        user = res_user.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        credentials = dict_to_credentials(user.credentials)
        service = build('gmail', 'v1', credentials=credentials)
        
        # Watch request - monitors inbox for new messages
        request = {
            'labelIds': ['INBOX'],
            'topicName': 'projects/hackx3/topics/gmail-notifications'
        }
        
        response = service.users().watch(userId='me', body=request).execute()
        
        # Update user with watch info
        expiration = datetime.utcnow() + timedelta(milliseconds=int(response['expiration']))
        user.watch_expiration = expiration
        user.history_id = response['historyId']
        await session.commit()
        
        print(f"Gmail watch set up for {user_email}, expires at {expiration}")
        return response
        
    except HttpError as error:
        print(f"An error occurred setting up watch: {error}")
        raise


@app.post("/webhook/gmail")
async def gmail_webhook(request: Request, session: AsyncSession = Depends(get_async_session)):
    """
    Webhook endpoint for Gmail push notifications
    
    Google Pub/Sub will POST to this endpoint when new emails arrive.
    Set up a Pub/Sub push subscription pointing to this URL.
    """
    
    try:
        body = await request.body()
        if not body:
            print("⚠️ Empty body received from Pub/Sub")
            return {"status": "no_body"}
        
        data = json.loads(body.decode("utf-8"))
        print("✅ Raw Pub/Sub push:", data)
        
        message = data.get("message", {})
        if "data" in message:
            decoded_data = base64.b64decode(message["data"]).decode("utf-8")
            print("📩 Decoded message data:", decoded_data)
            
            # Parse the notification data
            notification_data = json.loads(decoded_data)
            email_address = notification_data.get("emailAddress")
            history_id = notification_data.get("historyId")
            
            print(f"📧 Email: {email_address}, History ID: {history_id}")
            
            # Process the new emails in the background
            if email_address and history_id:
                await process_new_emails(email_address, str(history_id), session)
        else:
            print("⚠️ No 'data' field in message")

        # Always return 200 so Pub/Sub knows we received it
        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}


async def process_new_emails(email_address: str, new_history_id: str, session: AsyncSession):
    """
    Process new emails by fetching history since last check
    """
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email_address))
    user = res_user.scalar_one_or_none()
    if not user:
        print(f"No user found for {email_address}")
        return
    
    try:
        credentials = dict_to_credentials(user.credentials)
        service = build('gmail', 'v1', credentials=credentials)
        
        last_history_id = user.history_id
        
        if not last_history_id:
            print("No history_id found, fetching latest emails instead")
            # If no history_id, fetch the most recent email
            messages_response = service.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()
            
            if messages_response.get('messages'):
                message_id = messages_response['messages'][0]['id']
                await fetch_and_store_email(service, email_address, message_id, session)
            
            # Update history_id for next time
            user.history_id = new_history_id
            user.last_sync = datetime.now(UTC)
            await session.commit()
            return
        
        print(f"Fetching history from {last_history_id} to {new_history_id}")
        
        # Fetch history since last check
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=last_history_id,
            historyTypes=['messageAdded']
        ).execute()
        
        # Update stored history_id
        user.history_id = new_history_id
        user.last_sync = datetime.now(UTC)
        await session.commit()
        
        if 'history' not in history_response:
            print("No new messages in history")
            return
        
        print(f"Found {len(history_response['history'])} history items")
        
        # Process each new message
        for history_item in history_response['history']:
            if 'messagesAdded' in history_item:
                for message_added in history_item['messagesAdded']:
                    message_data = message_added['message']
                    message_id = message_data['id']
                    
                    print(f"Processing message ID: {message_id}")
                    await fetch_and_store_email(service, email_address, message_id, session)
        
    except HttpError as error:
        print(f"An error occurred fetching emails: {error}")
        import traceback
        traceback.print_exc()


async def fetch_and_store_email(service, email_address: str, message_id: str, session: AsyncSession):
    """Fetch full email details and store in Postgres"""
    try:
        # Fetch full message details with metadata and body
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        print(f"🔍 Fetching message: {message_id}")
        
        # Extract email information
        email_info = extract_email_info(message)
        email_info['user_email'] = email_address
        
        # Extract email body (plain text and HTML)
        body_data = extract_email_body(message)
        email_info.update(body_data)
        
        # Extract attachments metadata
        attachments_info = extract_attachments_info(message)
        print(f"🔍 Extracted {len(attachments_info)} attachments")
        
        if attachments_info:
            email_info['attachments'] = attachments_info
            email_info['has_attachments'] = True
            print(f"📎 Attachments to store: {attachments_info}")
        
        # Debug: Print what we're about to store
        print(f"📦 Email info to store:")
        print(f"   - message_id: {email_info.get('message_id')}")
        print(f"   - has_attachments: {email_info.get('has_attachments', False)}")
        print(f"   - attachments count: {len(email_info.get('attachments', []))}")
        if email_info.get('attachments'):
            print(f"   - attachments data: {json.dumps(email_info['attachments'], indent=6)}")
        
        # Store email in Postgres
        await store_email(email_info, session)
        
        # Call custom handler
        await handle_new_email(email_address, email_info, message, session)
        
        print(f"✅ Stored email: {email_info['subject']}")
        print(f"📧 From: {email_info['from']}")
        print(f"📝 Body preview: {email_info['body_plain'][:100] if email_info.get('body_plain') else 'No plain text body'}...")
        
        if attachments_info:
            print(f"📎 Attachments:")
            for att in attachments_info:
                print(f"   - {att['filename']} ({att['mime_type']}, {att['size']} bytes)")
                print(f"     Attachment ID: {att['attachment_id']}")
                # Generate download URL using filename (URL-encoded)
                from urllib.parse import quote
                encoded_filename = quote(att['filename'])
                download_url = f"http://localhost:8000/user/emails/{message_id}/attachments/{encoded_filename}"
                print(f"     🔗 Download: {download_url}")
        
    except HttpError as error:
        print(f"Error fetching message {message_id}: {error}")
        import traceback
        traceback.print_exc()


def extract_email_body(message):
    """Extract plain text and HTML body from email"""
    body_data = {
        'body_plain': '',
        'body_html': '',
        'body_snippet': message.get('snippet', '')
    }
    
    def parse_parts(parts):
        """Recursively parse message parts"""
        plain_text = ''
        html_text = ''
        
        for part in parts:
            mime_type = part.get('mimeType', '')
            
            # Check if this part has nested parts
            if 'parts' in part:
                nested_plain, nested_html = parse_parts(part['parts'])
                plain_text += nested_plain
                html_text += nested_html
            
            # Extract body data
            if 'body' in part and 'data' in part['body']:
                body_data = part['body']['data']
                decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                
                if mime_type == 'text/plain':
                    plain_text += decoded_body
                elif mime_type == 'text/html':
                    html_text += decoded_body
        
        return plain_text, html_text
    
    # Check if message has parts (multipart)
    if 'parts' in message['payload']:
        plain, html = parse_parts(message['payload']['parts'])
        body_data['body_plain'] = plain
        body_data['body_html'] = html
    
    # Check if body is directly in payload (simple message)
    elif 'body' in message['payload'] and 'data' in message['payload']['body']:
        body = base64.urlsafe_b64decode(
            message['payload']['body']['data']
        ).decode('utf-8', errors='ignore')
        
        mime_type = message['payload'].get('mimeType', '')
        if mime_type == 'text/plain':
            body_data['body_plain'] = body
        elif mime_type == 'text/html':
            body_data['body_html'] = body
        else:
            body_data['body_plain'] = body
    
    return body_data


def extract_attachments_info(message):
    """Extract attachment metadata from email"""
    attachments = []
    
    def parse_parts(parts, level=0):
        """Recursively parse message parts for attachments"""
        indent = "  " * level
        for i, part in enumerate(parts):
            part_id = part.get('partId', f'part-{i}')
            mime_type = part.get('mimeType', '')
            filename = part.get('filename', '')
            
            print(f"{indent}📄 Part {part_id}: {mime_type}, filename='{filename}'")
            
            # Check for nested parts
            if 'parts' in part:
                print(f"{indent}  ↳ Has {len(part['parts'])} sub-parts")
                parse_parts(part['parts'], level + 1)
            
            # Check if this part has a body with attachmentId
            body = part.get('body', {})
            attachment_id = body.get('attachmentId')
            size = body.get('size', 0)
            
            # An attachment either has a filename or an attachmentId with reasonable size
            if filename and attachment_id:
                attachment_info = {
                    'filename': filename,
                    'mime_type': mime_type,
                    'size': size,
                    'attachment_id': attachment_id,
                    'part_id': part_id
                }
                attachments.append(attachment_info)
                print(f"{indent}  ✅ Added attachment: {filename}")
            elif filename and not attachment_id:
                # Inline content without separate attachment
                print(f"{indent}  ⚠️  File '{filename}' has no attachmentId (inline content)")
            elif attachment_id:
                # Attachment without filename (rare but possible)
                print(f"{indent}  ⚠️  Attachment ID found but no filename")
    
    # Parse message parts
    print("🔍 Parsing message structure:")
    if 'parts' in message['payload']:
        parse_parts(message['payload']['parts'])
    else:
        # Single part message
        print("  📄 Single-part message (no attachments)")
    
    return attachments


@app.post("/user/emails/{message_id}/resync")
async def resync_email(email: str, message_id: str, session: AsyncSession = Depends(get_async_session)):
    """Re-fetch and update an email from Gmail (useful for fixing missing data)"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        credentials = dict_to_credentials(user.credentials)
        service = build('gmail', 'v1', credentials=credentials)
        
        # Fetch the email again
        await fetch_and_store_email(service, email, message_id, session)
        
        return {"status": "success", "message": f"Email {message_id} re-synced"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New endpoint to get a single email with full content
@app.get("/user/emails/{message_id}")
async def get_email_details(email: str, message_id: str, session: AsyncSession = Depends(get_async_session)):
    """Get full details of a specific email including body and attachments"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    res_email = await session.execute(
        select(GmailEmail).where(GmailEmail.user_email == email, GmailEmail.message_id == message_id)
    )
    email_doc = res_email.scalar_one_or_none()
    
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {
        "user_email": email_doc.user_email,
        "message_id": email_doc.message_id,
        "thread_id": email_doc.thread_id,
        "from": email_doc.from_addr,
        "to": email_doc.to_addr,
        "subject": email_doc.subject,
        "date": email_doc.date,
        "snippet": email_doc.snippet,
        "labels": email_doc.labels,
        "internal_date": email_doc.internal_date,
        "received_at": email_doc.received_at.isoformat() if email_doc.received_at else None,
        "body_plain": email_doc.body_plain,
        "body_html": email_doc.body_html,
        "body_snippet": email_doc.body_snippet,
        "has_attachments": email_doc.has_attachments,
        "attachments": email_doc.attachments,
        "priority": email_doc.priority,
        "is_important": email_doc.is_important,
        "category": email_doc.category,
        "sender_domain": email_doc.sender_domain,
    }


# New endpoint to download attachment
@app.get("/user/emails/{message_id}/attachments/{attachment_filename}")
async def download_attachment(
    message_id: str,
    attachment_filename: str,
    email: str = None,
    session: AsyncSession = Depends(get_async_session),
):
    """Download a specific attachment from an email by filename"""
    
    print(f"🔍 Download request - message_id: {message_id}, filename: {attachment_filename}")
    
    # If email not provided as query param, find it from the message
    if not email:
        res_email = await session.execute(select(GmailEmail).where(GmailEmail.message_id == message_id))
        email_doc = res_email.scalar_one_or_none()
        if not email_doc:
            print(f"❌ Email document not found for message_id: {message_id}")
            raise HTTPException(status_code=404, detail="Email not found")
        email = email_doc.user_email
        print(f"✅ Found user email: {email}")
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        print(f"❌ User not found: {email}")
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        credentials = dict_to_credentials(user.credentials)
        service = build('gmail', 'v1', credentials=credentials)
        
        # Fetch the full message again to get attachment IDs
        print(f"📥 Fetching message from Gmail API...")
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        # Find the attachment with matching filename
        def find_attachment_id(parts, target_filename):
            """Recursively search for attachment by filename"""
            for part in parts:
                if 'parts' in part:
                    result = find_attachment_id(part['parts'], target_filename)
                    if result:
                        return result
                
                filename = part.get('filename', '')
                if filename == target_filename:
                    attachment_id = part.get('body', {}).get('attachmentId')
                    if attachment_id:
                        return {
                            'attachment_id': attachment_id,
                            'mime_type': part.get('mimeType', 'application/octet-stream'),
                            'size': part.get('body', {}).get('size', 0)
                        }
            return None
        
        attachment_info = None
        if 'parts' in message['payload']:
            attachment_info = find_attachment_id(message['payload']['parts'], attachment_filename)
        
        if not attachment_info:
            print(f"❌ Attachment '{attachment_filename}' not found in message")
            raise HTTPException(status_code=404, detail=f"Attachment '{attachment_filename}' not found")
        
        print(f"✅ Found attachment: {attachment_filename}")
        print(f"   - attachment_id: {attachment_info['attachment_id'][:50]}...")
        print(f"   - mime_type: {attachment_info['mime_type']}")
        print(f"   - size: {attachment_info['size']} bytes")
        
        # Download the attachment
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_info['attachment_id']
        ).execute()
        
        # Decode the attachment data
        file_data = base64.urlsafe_b64decode(attachment['data'])
        print(f"✅ Downloaded {len(file_data)} bytes")
        
        # Return the file
        return Response(
            content=file_data,
            media_type=attachment_info['mime_type'],
            headers={
                'Content-Disposition': f'attachment; filename="{attachment_filename}"'
            }
        )
        
    except HttpError as error:
        print(f"❌ Gmail API error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


def extract_email_info(message):
    """Extract relevant information from Gmail message"""
    headers = message['payload']['headers']
    
    def get_header(name):
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return None
    
    return {
        'message_id': message['id'],
        'thread_id': message['threadId'],
        'from': get_header('From'),
        'to': get_header('To'),
        'subject': get_header('Subject'),
        'date': get_header('Date'),
        'snippet': message.get('snippet', ''),
        'labels': message.get('labelIds', []),
        'internal_date': int(message.get('internalDate', 0)),
        'received_at': datetime.utcnow()
    }


async def store_email(email_info: dict, session: AsyncSession):
    """Store email in Postgres"""
    try:
        res = await session.execute(select(GmailEmail).where(GmailEmail.message_id == email_info['message_id']))
        row = res.scalar_one_or_none()
        if not row:
            row = GmailEmail(
                user_email=email_info.get('user_email'),
                message_id=email_info.get('message_id'),
                thread_id=email_info.get('thread_id'),
                from_addr=email_info.get('from'),
                to_addr=email_info.get('to'),
                subject=email_info.get('subject'),
                date=email_info.get('date'),
                snippet=email_info.get('snippet'),
                labels=email_info.get('labels') or [],
                internal_date=str(email_info.get('internal_date') or ''),
                body_plain=email_info.get('body_plain'),
                body_html=email_info.get('body_html'),
                body_snippet=email_info.get('body_snippet'),
                has_attachments=email_info.get('has_attachments', False),
                attachments=email_info.get('attachments') or [],
            )
            session.add(row)
        else:
            row.user_email = email_info.get('user_email')
            row.thread_id = email_info.get('thread_id')
            row.from_addr = email_info.get('from')
            row.to_addr = email_info.get('to')
            row.subject = email_info.get('subject')
            row.date = email_info.get('date')
            row.snippet = email_info.get('snippet')
            row.labels = email_info.get('labels') or []
            row.internal_date = str(email_info.get('internal_date') or '')
            row.body_plain = email_info.get('body_plain')
            row.body_html = email_info.get('body_html')
            row.body_snippet = email_info.get('body_snippet')
            row.has_attachments = email_info.get('has_attachments', False)
            row.attachments = email_info.get('attachments') or []
        await session.commit()
        print(f"Stored email: {email_info['subject']}")
    except Exception as e:
        print(f"Error storing email: {e}")


async def handle_new_email(user_email: str, email_info: dict, full_message: dict, session: AsyncSession):
    """
    CUSTOM EMAIL HANDLER - Implement your business logic here
    
    This function is called whenever a new email is received.
    The email has already been stored in MongoDB at this point.
    
    Args:
        user_email: Email address of the user who received the email
        email_info: Extracted email information (from, subject, date, etc.)
        full_message: Full Gmail message object with all data
    
    Implementation Examples:
    
    1. NOTIFICATION SYSTEM:
       Send real-time notifications to the user about important emails
       
    2. EMAIL CATEGORIZATION:
       Use AI to categorize emails and update labels in MongoDB
       
    3. AUTO-RESPONSES:
       Automatically respond to certain types of emails
       
    4. DATA EXTRACTION:
       Parse emails for specific data (invoices, tracking numbers, etc.)
       
    5. WORKFLOW TRIGGERS:
       Trigger business processes based on email content
       
    6. ANALYTICS:
       Track email patterns, response times, sender statistics
    
    Example implementation below:
    """
    
    # Example 1: Check for high-priority emails
    subject = email_info.get('subject', '').lower()
    sender = email_info.get('from', '').lower()
    
    # Mark as important based on keywords
    is_important = any(keyword in subject for keyword in ['urgent', 'important', 'asap', 'critical'])
    
    if is_important:
        res_email = await session.execute(select(GmailEmail).where(GmailEmail.message_id == email_info['message_id']))
        row = res_email.scalar_one_or_none()
        if row:
            row.priority = "high"
            row.is_important = True
            await session.commit()
        print(f"⚠️  High priority email detected: {email_info['subject']}")
        
        # TODO: Send push notification to user
        # await send_push_notification(user_email, {
        #     "title": "Important Email",
        #     "body": f"From: {email_info['from']}\nSubject: {email_info['subject']}"
        # })
    
    # Example 2: Categorize by sender domain
    if '@' in sender:
        domain = sender.split('@')[1].split('>')[0]
        res_email = await session.execute(select(GmailEmail).where(GmailEmail.message_id == email_info['message_id']))
        row = res_email.scalar_one_or_none()
        if row:
            row.sender_domain = domain
        # Track sender statistics
        res_stat = await session.execute(
            select(GmailSenderStat).where(GmailSenderStat.user_email == user_email, GmailSenderStat.domain == domain)
        )
        stat = res_stat.scalar_one_or_none()
        if not stat:
            stat = GmailSenderStat(user_email=user_email, domain=domain, email_count=1, last_email_date=datetime.utcnow())
            session.add(stat)
        else:
            stat.email_count = (stat.email_count or 0) + 1
            stat.last_email_date = datetime.utcnow()
        await session.commit()
    
    # Example 3: Extract and store attachments info
    if 'parts' in full_message['payload']:
        attachments = []
        for part in full_message['payload']['parts']:
            if part.get('filename'):
                attachments.append({
                    "filename": part['filename'],
                    "mime_type": part['mimeType'],
                    "size": part['body'].get('size', 0)
                })
        
        if attachments:
            res_email = await session.execute(select(GmailEmail).where(GmailEmail.message_id == email_info['message_id']))
            row = res_email.scalar_one_or_none()
            if row:
                row.attachments = attachments
                row.has_attachments = True
                await session.commit()
            print(f"📎 Email has {len(attachments)} attachment(s)")
    
    # Example 4: Auto-tag promotional emails
    if any(keyword in subject for keyword in ['sale', 'discount', 'offer', 'deal']):
        res_email = await session.execute(select(GmailEmail).where(GmailEmail.message_id == email_info['message_id']))
        row = res_email.scalar_one_or_none()
        if row:
            row.category = "promotional"
            await session.commit()
    
    # Example 5: Log email event for analytics
    session.add(EmailEvent(
        user_email=user_email,
        event_type="email_received",
        message_id=email_info['message_id'],
        sender=email_info.get('from'),
        subject=email_info.get('subject'),
        timestamp=datetime.utcnow(),
    ))
    await session.commit()
    
    # TODO: Add your custom business logic here
    # - Send to AI for summarization
    # - Trigger workflows
    # - Update CRM
    # - Create calendar events
    # - Auto-reply logic
    # etc.


@app.get("/user/emails")
async def get_user_emails(email: str, skip: int = 0, limit: int = 20, session: AsyncSession = Depends(get_async_session)):
    """Fetch user's emails from Postgres with pagination"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    res_emails = await session.execute(
        select(GmailEmail)
        .where(GmailEmail.user_email == email)
        .order_by(GmailEmail.internal_date.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    emails_rows = res_emails.scalars().all()
    emails = [
        {
            "user_email": r.user_email,
            "message_id": r.message_id,
            "subject": r.subject,
            "from": r.from_addr,
            "to": r.to_addr,
            "snippet": r.snippet,
            "internal_date": r.internal_date,
            "has_attachments": r.has_attachments,
            "received_at": r.received_at.isoformat() if r.received_at else None,
        }
        for r in emails_rows
    ]
    total = len(
        (
            await session.execute(
                select(GmailEmail).where(GmailEmail.user_email == email)
            )
        ).scalars().all()
    )
    return {"emails": emails, "total": total, "skip": skip, "limit": limit}


@app.get("/user/emails/search")
async def search_emails(email: str, query: str, limit: int = 20, session: AsyncSession = Depends(get_async_session)):
    """Search user's emails by subject or sender"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    q = f"%{query}%"
    res_emails = await session.execute(
        select(GmailEmail)
        .where(
            GmailEmail.user_email == email,
            (GmailEmail.subject.ilike(q)) | (GmailEmail.from_addr.ilike(q)),
        )
        .order_by(GmailEmail.internal_date.desc().nullslast())
        .limit(limit)
    )
    emails_rows = res_emails.scalars().all()
    emails = [
        {
            "user_email": r.user_email,
            "message_id": r.message_id,
            "subject": r.subject,
            "from": r.from_addr,
            "to": r.to_addr,
            "snippet": r.snippet,
            "internal_date": r.internal_date,
            "has_attachments": r.has_attachments,
            "received_at": r.received_at.isoformat() if r.received_at else None,
        }
        for r in emails_rows
    ]
    return {"emails": emails, "query": query}


@app.get("/user/status")
async def get_user_status(email: str, session: AsyncSession = Depends(get_async_session)):
    """Check user's authentication and watch status"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "email": email,
        "authenticated": True,
        "watch_active": user.watch_expiration is not None,
        "watch_expires": user.watch_expiration.isoformat() if user.watch_expiration else None,
        "last_sync": user.last_sync.isoformat() if user.last_sync else None,
        "email_count": len((await session.execute(select(GmailEmail).where(GmailEmail.user_email == email))).scalars().all()),
    }


@app.post("/user/refresh-watch")
async def refresh_watch(email: str, session: AsyncSession = Depends(get_async_session)):
    """Manually refresh Gmail watch (call this before expiration)"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        await setup_gmail_watch(email, session)
        return {"status": "success", "message": "Watch refreshed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/analytics")
async def get_email_analytics(email: str, session: AsyncSession = Depends(get_async_session)):
    """Get email analytics for user"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Total emails
    total_emails = len((await session.execute(select(GmailEmail).where(GmailEmail.user_email == email))).scalars().all())

    # Important emails
    important_emails = await session.execute(
        select(GmailEmail).where(GmailEmail.user_email == email, GmailEmail.is_important == True)
    )
    important_count = len(important_emails.scalars().all())

    # Emails with attachments
    emails_with_att = await session.execute(
        select(GmailEmail).where(GmailEmail.user_email == email, GmailEmail.has_attachments == True)
    )
    attachment_count = len(emails_with_att.scalars().all())

    # Top senders
    res_senders = await session.execute(
        select(GmailSenderStat)
        .where(GmailSenderStat.user_email == email)
        .order_by(GmailSenderStat.email_count.desc())
        .limit(10)
    )
    top_senders_rows = res_senders.scalars().all()
    top_senders = [
        {
            "user_email": s.user_email,
            "domain": s.domain,
            "email_count": s.email_count,
            "last_email_date": s.last_email_date.isoformat() if s.last_email_date else None,
        }
        for s in top_senders_rows
    ]
    
    return {
        "total_emails": total_emails,
        "important_emails": important_count,
        "emails_with_attachments": attachment_count,
        "top_senders": top_senders
    }


@app.delete("/user/logout")
async def logout(email: str, session: AsyncSession = Depends(get_async_session)):
    """Logout user and optionally remove their data"""
    
    res_user = await session.execute(select(GmailUser).where(GmailUser.email == email))
    user = res_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.credentials = None
    user.watch_expiration = None
    user.history_id = None
    user.logged_out_at = datetime.utcnow()
    await session.commit()
    return {"status": "success", "message": "User logged out"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)