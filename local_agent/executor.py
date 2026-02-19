import os
import subprocess
from local_agent import context_log
from utils.helper import attach_launchers

def execute(files, project_dir=None, autorun=False):
    """
    Save and (optionally) run one or more generated files.
    
    files: list of dicts like [{"filename": "app.py", "code": "..."}]
    project_dir: directory where to save the files (required for launchers)
    autorun: if True, runs the detected MAIN file after saving
    """
    if not files:
        error_msg = "❌ No files provided to execute()"
        print(error_msg)
        context_log.append_error(error_msg)
        return False, error_msg

    if not project_dir:
        error_msg = "❌ project_dir not specified"
        print(error_msg)
        context_log.append_error(error_msg)
        return False, error_msg

    os.makedirs(project_dir, exist_ok=True)

    files_written = []
    for f in files:
        filename, code = f.get("filename"), f.get("code")
        if not filename or not code:
            error_msg = "❌ Plan missing 'code' or 'filename'"
            print(error_msg)
            context_log.append_error(error_msg)
            continue

        path = os.path.join(project_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        files_written.append(path)

        print(f"✅ Saved {filename}")

    # Always attach launchers after saving
    attach_launchers(project_dir, files_written)

    # Autorun only if requested and we have a clear MAIN file
    if autorun and files_written:
        main_sh = os.path.join(project_dir, "run.sh")
        print(f"▶ Running project via {main_sh} …")
        try:
            subprocess.run([main_sh], check=True)
            print("✅ Project executed successfully.")
            return True, ""
        except subprocess.CalledProcessError as e:
            error_msg = f"❌ Error running project: {e}"
            print(error_msg)
            context_log.append_error(error_msg)
            return False, error_msg

    return True, ""

