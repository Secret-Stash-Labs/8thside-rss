#!/usr/bin/env python3
import os
import sys
import subprocess
import platform

def main():
    """Set up development environment for the RSS feed generator."""
    print("Setting up development environment...")
    
    # Create virtual environment
    if not os.path.exists("venv"):
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    
    # Determine activation script based on platform
    if platform.system() == "Windows":
        activate_script = os.path.join("venv", "Scripts", "activate")
        activate_cmd = f"{activate_script}"
        pip_cmd = os.path.join("venv", "Scripts", "pip")
        python_cmd = os.path.join("venv", "Scripts", "python")
    else:
        activate_script = os.path.join("venv", "bin", "activate")
        activate_cmd = f"source {activate_script}"
        pip_cmd = os.path.join("venv", "bin", "pip")
        python_cmd = os.path.join("venv", "bin", "python")
    
    # Install dependencies
    print("Installing dependencies...")
    subprocess.check_call([pip_cmd, "install", "-r", "requirements.txt"])
    
    # Install Playwright browsers
    print("Installing Playwright browsers...")
    subprocess.check_call([python_cmd, "-m", "playwright", "install", "chromium"])
    
    # Success message and instructions
    print("\nEnvironment setup complete!")
    print(f"\nTo activate the virtual environment, run:")
    print(f"  {activate_cmd}")
    print("\nTo run the feed generator:")
    print("  python feedgen-new.py")
    print("  or")
    print("  python feedgen-playwright.py (for JavaScript-rendered sites)")

if __name__ == "__main__":
    main()
