#!/usr/bin/env python3
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"


def run(cmd, **kwargs):
    """Run a command, echoing it first."""
    print("+", " ".join(str(c) for c in cmd))
    subprocess.check_call(cmd, **kwargs)


def main() -> None:
    print("=== AI Orchestrator Setup ===\n")

    # 1) Create virtual environment
    if not VENV_DIR.exists():
        print(f"Creating virtualenv at {VENV_DIR} ...")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print(f"Virtualenv already exists at {VENV_DIR}")

    # 2) Work out paths to pip & python inside the venv
    if os.name == "nt":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
        venv_pip = VENV_DIR / "Scripts" / "pip.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"
        venv_pip = VENV_DIR / "bin" / "pip"

    if not venv_python.exists():
        raise SystemExit(f"Could not find venv python at {venv_python}")

    # 3) Install requirements
    req = ROOT / "requirements.txt"
    if req.exists():
        print("\nInstalling dependencies from requirements.txt ...")
        run([str(venv_pip), "install", "-r", str(req)])
    else:
        print("WARNING: requirements.txt not found. Skipping dependency install.")

    # 4) Configure API key
    print("\n" + "="*50)
    print("API KEY CONFIGURATION")
    print("="*50)
    print("The AI Orchestrator requires an OpenAI API key.")
    print("You can set it in several ways (in order of security):")
    print("1. Environment variable (most secure for production)")
    print("2. System keyring (secure, persistent)")
    print("3. Config file (secure for personal use)")
    print("4. Local file (development only, least secure)")
    print()

    # Check if key is already configured
    from cloud_agent.cloud_client import _load_api_key
    try:
        existing_key = _load_api_key()
        if existing_key:
            print("✓ API key is already configured.")
            update_key = input("Update/reconfigure API key? [y/N]: ").strip().lower()
            if update_key not in ('y', 'yes'):
                print("Keeping existing API key configuration.")
            else:
                existing_key = None
    except:
        existing_key = None

    if not existing_key:
        configure_api_key()

    # 5) Final instructions
    print("\n=== Setup complete ===\n")
    print("To run the orchestrator, use:")
    if os.name == "nt":
        print(f'  "{venv_python}" orchestrator.py "Your prompt here"')
    else:
        print(f'  {venv_python} orchestrator.py "Your prompt here"')
    print("\nOr activate the venv first, then run:")
    if os.name == "nt":
        print(rf"  {VENV_DIR}\Scripts\activate")
        print('  python orchestrator.py "Your prompt here"')
    else:
        print(f"  source {VENV_DIR}/bin/activate")
        print('  python orchestrator.py "Your prompt here"')


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled.")


def configure_api_key() -> None:
    """Configure the OpenAI API key using the user's preferred method."""
    print("Choose how to store your OpenAI API key:")
    print("1. Environment variable (recommended for production)")
    print("2. System keyring (recommended for personal use)")
    print("3. Config file")
    print("4. Local file (development only)")
    
    while True:
        choice = input("Choose [1-4] or 'skip' to configure later: ").strip().lower()
        
        if choice in ('1', 'env', 'environment'):
            print("\nTo set as environment variable:")
            print("Linux/macOS: export OPENAI_API_KEY='your-key-here'")
            print("Windows:     set OPENAI_API_KEY=your-key-here")
            print("Or add it to your shell profile (.bashrc, .zshrc, etc.)")
            input("Press Enter when you've set the environment variable...")
            break
            
        elif choice in ('2', 'keyring'):
            try:
                import keyring
                key = input("Enter your OpenAI API key (starts with 'sk-'): ").strip()
                if key:
                    keyring.set_password("ai_orchestrator", "openai_api_key", key)
                    print("✓ API key saved to system keyring.")
                else:
                    print("No key entered.")
                break
            except ImportError:
                print("❌ keyring package not available. Install with: pip install keyring")
                continue
            except Exception as e:
                print(f"❌ Failed to save to keyring: {e}")
                continue
                
        elif choice in ('3', 'config', 'file'):
            cfg_dir = Path.home() / ".config" / "ai_orchestrator"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            cfg_file = cfg_dir / "openai_api_key"
            key = input("Enter your OpenAI API key (starts with 'sk-'): ").strip()
            if key:
                cfg_file.write_text(key, encoding="utf-8")
                try:
                    os.chmod(cfg_dir, 0o700)
                    os.chmod(cfg_file, 0o600)
                except Exception:
                    pass
                print(f"✓ API key saved to: {cfg_file}")
            else:
                print("No key entered.")
            break
            
        elif choice in ('4', 'local'):
            key_file = ROOT / "cloud_agent" / "apikey.txt"
            key = input("Enter your OpenAI API key (starts with 'sk-'): ").strip()
            if key:
                key_file.write_text(key, encoding="utf-8")
                print(f"⚠️  API key saved to: {key_file} (development only - not secure!)")
            else:
                print("No key entered.")
            break
            
        elif choice == 'skip':
            print("You can configure the API key later.")
            break
            
        else:
            print("Invalid choice. Please choose 1-4 or 'skip'.")
