import streamlit as st
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials

# --- Configuration ---
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# --- Initialization ---
if 'playlists' not in st.session_state:
    st.session_state.playlists = []

def get_authenticated_service():
    # 1. Try to load saved credentials (token.json)
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    # 2. Local Flow (Generates the token.json for you)
    if os.path.exists(CLIENT_SECRETS_FILE):
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Save token for future use
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            
        return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    return None

def main():
    st.title("YouTube Playlist Manager")

    # 1. Login
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        st.error(f"Authentication error: {e}")
        st.stop()

    if not youtube:
        st.warning("Authentication files missing.")
        st.info("Please ensure client_secret.json is present locally, or token.json is uploaded for cloud deployment.")
        st.stop()
    
    st.success("Connected to YouTube")

    # 2. Fetch Playlists
    if not st.session_state.playlists:
        with st.spinner("Loading playlists..."):
            try:
                playlists = []
                next_page_token = None
                while True:
                    request = youtube.playlists().list(
                        part="snippet,contentDetails",
                        mine=True,
                        maxResults=50,
                        pageToken=next_page_token
                    )
                    response = request.execute()
                    
                    for item in response.get("items", []):
                        playlists.append({
                            'id': item['id'], 
                            'title': item['snippet']['title']
                        })
                    
                    next_page_token = response.get("nextPageToken")
                    if not next_page_token: 
                        break
                
                st.session_state.playlists = playlists
                
            except Exception as e:
                st.error(f"Error fetching data: {e}")
                st.stop()

    # 3. Interface
    if st.session_state.playlists:
        st.write(f"Total Playlists: {len(st.session_state.playlists)}")
        
        select_all = st.checkbox("Select All")
        
        with st.form("delete_form"):
            selected_ids = []
            
            # Scrollable list container
            with st.container(height=400):
                for p in st.session_state.playlists:
                    if st.checkbox(p['title'], key=p['id'], value=select_all):
                        selected_ids.append(p)
            
            st.divider()
            
            # Action Button
            submitted = st.form_submit_button("Delete Selected", type="primary")
            
            if submitted and selected_ids:
                progress_text = st.empty()
                progress_bar = st.progress(0)
                deleted_count = 0
                
                for i, p in enumerate(selected_ids):
                    progress_text.text(f"Deleting: {p['title']}")
                    try:
                        youtube.playlists().delete(id=p['id']).execute()
                        deleted_count += 1
                    except Exception as e:
                        st.error(f"Could not delete {p['title']}: {e}")
                    
                    progress_bar.progress((i + 1) / len(selected_ids))
                
                progress_text.text(f"Complete. Deleted {deleted_count} playlists.")
                
                # Refresh state
                st.session_state.playlists = []
                st.rerun()

if __name__ == "__main__":
    main()