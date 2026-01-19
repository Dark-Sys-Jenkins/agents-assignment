"""
Verification Script - Check if everything is set up correctly
Location: examples/voice_agents/verify_setup.py

Run this to diagnose any setup issues.
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("🔍 SETUP VERIFICATION SCRIPT")
print("=" * 70)

# 1. Check Python version
print("\n1️⃣ Python Version:")
print(f"   Version: {sys.version}")
if sys.version_info >= (3, 9):
    print("   ✅ Python version OK (3.9+)")
else:
    print("   ❌ Python version too old (need 3.9+)")

# 2. Check directory structure
print("\n2️⃣ Directory Structure:")
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent

print(f"   Current directory: {current_dir}")
print(f"   Project root: {project_root}")

# Check for key files/directories
checks = [
    (project_root / ".env", "✅ .env file exists" if (project_root / ".env").exists() else "❌ .env file MISSING"),
    (project_root / "livekit-agents", "✅ livekit-agents directory exists" if (project_root / "livekit-agents").exists() else "❌ livekit-agents directory MISSING"),
    (project_root / "livekit-agents" / "livekit", "✅ livekit directory exists" if (project_root / "livekit-agents" / "livekit").exists() else "❌ livekit directory MISSING"),
    (project_root / "livekit-agents" / "livekit" / "agents", "✅ agents directory exists" if (project_root / "livekit-agents" / "livekit" / "agents").exists() else "❌ agents directory MISSING"),
    (project_root / "livekit-agents" / "livekit" / "agents" / "voice", "✅ voice directory exists" if (project_root / "livekit-agents" / "livekit" / "agents" / "voice").exists() else "❌ voice directory MISSING"),
    (project_root / "livekit-agents" / "livekit" / "agents" / "voice" / "interruption_handler.py", "✅ interruption_handler.py exists" if (project_root / "livekit-agents" / "livekit" / "agents" / "voice" / "interruption_handler.py").exists() else "❌ interruption_handler.py MISSING"),
]

for path, message in checks:
    print(f"   {message}")

# 3. Check environment variables
print("\n3️⃣ Environment Variables:")
from dotenv import load_dotenv
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

required_vars = {
    "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY"),
    "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
}

for var_name, var_value in required_vars.items():
    if var_value:
        if var_name == "GOOGLE_APPLICATION_CREDENTIALS":
            if os.path.exists(var_value):
                print(f"   ✅ {var_name}: {var_value[:50]}... (file exists)")
            else:
                print(f"   ⚠️  {var_name}: {var_value[:50]}... (FILE NOT FOUND)")
        else:
            print(f"   ✅ {var_name}: {var_value[:20]}...")
    else:
        if var_name == "GOOGLE_APPLICATION_CREDENTIALS":
            print(f"   ⚠️  {var_name}: Not set (will use gcloud auth)")
        else:
            print(f"   ❌ {var_name}: NOT SET")

# 4. Check installed packages
print("\n4️⃣ Installed Packages:")
required_packages = [
    "livekit",
    "livekit-agents",
    "livekit-plugins-deepgram",
    "livekit-plugins-google",
    "livekit-plugins-silero",
    "google-cloud-texttospeech",
]

for package in required_packages:
    try:
        __import__(package.replace("-", "_"))
        print(f"   ✅ {package}")
    except ImportError:
        print(f"   ❌ {package} - NOT INSTALLED")

# 5. Test import path
print("\n5️⃣ Import Path Test:")
livekit_agents_path = project_root / "livekit-agents"
sys.path.insert(0, str(livekit_agents_path))

try:
    from livekit.agents.voice.interruption_handler import (
        SemanticInterruptionHandler,
        InterruptionManager,
        AgentState,
    )
    print(f"   ✅ Successfully imported interruption handler")
    print(f"   ✅ Import path: {livekit_agents_path}")
except ImportError as e:
    print(f"   ❌ Failed to import: {e}")
    print(f"   ❌ Searched in: {livekit_agents_path}")

# 6. Check Google Cloud authentication
print("\n6️⃣ Google Cloud Authentication:")
try:
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    print("   ✅ Google Cloud authentication successful")
except Exception as e:
    print(f"   ❌ Google Cloud authentication failed")
    print(f"   Error: {e}")
    print("\n   Fix:")
    print("   Run: gcloud auth application-default login")
    print("   Or set GOOGLE_APPLICATION_CREDENTIALS in .env")

# Summary
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)

issues = []
if not (project_root / ".env").exists():
    issues.append("Missing .env file")
if not (project_root / "livekit-agents" / "livekit" / "agents" / "voice" / "interruption_handler.py").exists():
    issues.append("Missing interruption_handler.py")
if not os.getenv("GOOGLE_API_KEY"):
    issues.append("Missing GOOGLE_API_KEY")
if not os.getenv("DEEPGRAM_API_KEY"):
    issues.append("Missing DEEPGRAM_API_KEY")

if issues:
    print("❌ Issues found:")
    for issue in issues:
        print(f"   • {issue}")
    print("\nPlease fix these issues before running the agent.")
else:
    print("✅ All checks passed!")
    print("✅ You should be able to run the agent now!")
    print("\nNext steps:")
    print("   1. Authenticate: gcloud auth application-default login")
    print("   2. Run agent: python smart_interruption_agent.py console")

print("=" * 70)