
import streamlit as st
import websocket
import json
import threading
import time
from datetime import datetime
import uuid
import queue

class WebSocketClient:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        self.ws = None
        self.connected = False
        self.message_queue = queue.Queue()
        
    def connect(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.url,
            header={'x-api-key': self.api_key},
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Start WebSocket connection in a separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Wait for connection
        timeout = 5
        start_time = time.time()
        while not self.connected and time.time() - start_time < timeout:
            time.sleep(0.1)
            
        return self.connected
    
    def on_message(self, ws, message):
        """Handle incoming messages"""
        try:
            self.message_queue.put(json.loads(message))
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def on_error(self, ws, error):
        print(f"Error: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")
        self.connected = False
        
    def on_open(self, ws):
        print("WebSocket connection established")
        self.connected = True
    
    def send_message(self, message):
        """Send message to WebSocket server"""
        if self.connected:
            try:
                payload = {
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.ws.send(json.dumps(payload))
                return True
            except Exception as e:
                print(f"Error sending message: {e}")
                return False
        return False
    
    def get_response(self, timeout=30):
        """Get response from the message queue"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()

def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'ws_client' not in st.session_state:
        st.session_state.ws_client = None
    if 'connected' not in st.session_state:
        st.session_state.connected = False

def connect_websocket():
    """Connect to WebSocket server"""
    websocket_url = st.session_state.websocket_url
    api_key = st.session_state.api_key
    
    if st.session_state.ws_client:
        st.session_state.ws_client.close()
        
    ws_client = WebSocketClient(websocket_url, api_key)
    
    if ws_client.connect():
        st.session_state.ws_client = ws_client
        st.session_state.connected = True
        return True
    return False

def main():
    st.set_page_config(
        page_title="Chat Interface",
        page_icon="💬",
        layout="centered"
    )
    
    st.title("💬 Chat Interface")
    
    # Initialize session state
    init_session_state()
    
    # Connection settings
    with st.sidebar:
        st.header("Connection Settings")
        
        # WebSocket URL input
        websocket_url = st.text_input(
            "WebSocket URL",
            value=st.session_state.get('websocket_url', ''),
            placeholder="wss://your-api-gateway-url/dev",
            key="websocket_url"
        )
        
        # API Key input
        api_key = st.text_input(
            "API Key",
            value=st.session_state.get('api_key', ''),
            type="password",
            key="api_key"
        )
        
        # Connect button
        if st.button("Connect", key="connect"):
            with st.spinner("Connecting..."):
                if connect_websocket():
                    st.success("Connected!")
                else:
                    st.error("Connection failed!")
        
        # Connection status
        st.write("Status: " + ("Connected ✅" if st.session_state.connected else "Disconnected ❌"))
    
    # Chat interface
    st.divider()
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
    # Input for new message
    if prompt := st.chat_input("Type your message here"):
        if not st.session_state.connected:
            st.error("Please connect to the WebSocket server first!")
            return
            
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # Send message and wait for response
        if st.session_state.ws_client.send_message(prompt):
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.session_state.ws_client.get_response()
                    if response:
                        st.write(response.get('response', 'No response received'))
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response.get('response', 'No response received')
                        })
                    else:
                        st.error("No response received")
        else:
            st.error("Failed to send message")

if __name__ == "__main__":
    main()