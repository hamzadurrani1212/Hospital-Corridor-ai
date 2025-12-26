import socket

# Try to create a route (Windows)
import subprocess

print("Testing network connectivity...")

# Your network
print(f"Your IP: 172.20.31.64")
print(f"Your subnet: 255.255.254.0")

# Check if we can add route to camera network
print("\nTrying to add route to 192.168.1.0 network...")

# This might require admin privileges
try:
    # Add route (requires admin)
    result = subprocess.run(
        ["route", "add", "192.168.1.0", "mask", "255.255.255.0", "172.20.30.1"],
        capture_output=True,
        text=True
    )
    print(f"Route add result: {result.returncode}")
    if result.returncode == 0:
        print("✅ Route added (temporarily)")
    else:
        print(f"❌ Could not add route: {result.stderr}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n💡 Solution: Connect your computer to the same network as cameras")
print("   OR change camera IPs to your network (172.20.31.x)")