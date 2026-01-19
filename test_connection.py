"""
Simple script to test if the LiveKit agent is running and connectable.
This connects directly to the room without using a web browser.
"""

import asyncio
import os
from dotenv import load_dotenv
from livekit import rtc

load_dotenv()

async def test_connection():
    print("🧪 Testing LiveKit Agent Connection...")
    print("=" * 60)
    
    # Use the user token from the file
    with open("user_token.txt", "r") as f:
        token = f.read().strip()
    
    url = os.getenv("LIVEKIT_URL")
    
    print(f"📡 Connecting to: {url}")
    print(f"🎫 Using token from: user_token.txt")
    print(f"🚪 Room: test-room-2")
    print()
    
    room = rtc.Room()
    
    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        print(f"✅ Participant joined: {participant.identity}")
    
    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        print(f"📥 Track subscribed: {track.kind} from {participant.identity}")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("🔊 Audio track received from agent!")
    
    @room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        print(f"📨 Data received: {data}")
    
    try:
        print("⏳ Connecting...")
        await room.connect(url, token)
        print("✅ Connected to room!")
        print(f"👤 Local participant: {room.local_participant.identity}")
        print(f"🎭 Room participants: {len(room.remote_participants)}")
        
        for participant in room.remote_participants.values():
            print(f"   - {participant.identity}")
        
        # Enable microphone
        print("\n🎤 Enabling microphone...")
        source = rtc.AudioSource(48000, 1)
        track = rtc.LocalAudioTrack.create_audio_track("microphone", source)
        options = rtc.TrackPublishOptions()
        options.source = rtc.TrackSource.SOURCE_MICROPHONE
        
        await room.local_participant.publish_track(track, options)
        print("✅ Microphone track published!")
        
        print("\n💬 You can now speak! The agent should respond.")
        print("   Press Ctrl+C to exit.")
        print("=" * 60)
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Disconnecting...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await room.disconnect()
        print("✅ Disconnected")

if __name__ == "__main__":
    asyncio.run(test_connection())
