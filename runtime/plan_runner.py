from __future__ import annotations
import os, sys, json, shutil, subprocess, re, logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

from utils.helper import slugify, safe_join, ensure_executable, attach_launchers

logger = logging.getLogger(__name__)

def _run(cmd: str, cwd: Path, env: Optional[Dict[str, str]] = None) -> int:
    return subprocess.call(cmd, cwd=str(cwd), shell=True, env=env)

def _check_exists(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _init_git_repo(project_dir: Path) -> None:
    """Initialize a git repository for the project."""
    try:
        # Initialize git repo
        _run("git init", project_dir)
        
        # Create .gitignore
        gitignore_content = """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
logs/
*.log

# Temporary files
tmp/
temp/
"""
        gitignore_path = project_dir / ".gitignore"
        gitignore_path.write_text(gitignore_content, encoding="utf-8")
        
        # Initial commit (only if user.email configured)
        rc = _run("git config user.email", project_dir)
        _run("git add .", project_dir)
        if rc == 0:
            _run('git commit -m "Initial commit - AI generated project"', project_dir)
        else:
            logger.info("Git user not configured; skipping initial commit")
        
        logger.info(f"Initialized git repository in {project_dir}")
    except Exception as e:
        logger.warning(f"Failed to initialize git repository: {e}")
        # Don't fail the whole process if git init fails

def _python_bin(venv_dir: Path) -> Tuple[str, str]:
    if os.name == "nt":
        py = str(venv_dir / "Scripts" / "python.exe")
        pip = str(venv_dir / "Scripts" / "pip.exe")
    else:
        py = str(venv_dir / "bin" / "python")
        pip = str(venv_dir / "bin" / "pip")
    return py, pip

def _create_or_reuse_venv(project_dir: Path) -> Path:
    venv_dir = project_dir / ".venv"
    if not venv_dir.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
    return venv_dir

def _write_files(project_dir: Path, files: List[Dict[str, str]]) -> List[Path]:
    written: List[Path] = []
    for f in files:
        rel = f["filename"].lstrip("/\\")
        dest = safe_join(project_dir, rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f["code"], encoding="utf-8")
        if dest.suffix in {".sh", ".command"} or dest.name.lower() in {"run.sh", "run.command"}:
            ensure_executable(dest)
        written.append(dest)
    return written

def _detect_stack(files: List[Dict[str, str]]) -> str:
    names = {f["filename"].lower() for f in files}
    if "pyproject.toml" in names or "requirements.txt" in names or any(n.endswith(".py") for n in names):
        return "python"
    if "package.json" in names or any(n.endswith((".js",".ts",".tsx")) for n in names):
        return "node"
    if "go.mod" in names or any(n.endswith(".go") for n in names):
        return "go"
    if "cargo.toml" in names:
        return "rust"
    if {"build.gradle","settings.gradle","gradlew","gradlew.bat"} & names:
        return "java-gradle"
    if "pom.xml" in names:
        return "java-maven"
    if any(n.endswith(".java") for n in names):
        return "java-plain"
    if "cmakelists.txt" in names or any(n.endswith((".cpp",".hpp",".cc",".cxx")) for n in names):
        return "cpp"
    return "generic"

def _install_python(project_dir: Path, plan: Dict[str, Any]) -> Tuple[Optional[Path], Optional[str]]:
    venv_dir = _create_or_reuse_venv(project_dir)
    py, pip = _python_bin(venv_dir)
    pyproject = project_dir / "pyproject.toml"
    has_poetry = False
    has_pdm = False
    if pyproject.exists():
        txt = _read_text(pyproject)
        has_poetry = "[tool.poetry]" in txt
        has_pdm = "[tool.pdm]" in txt

    if has_poetry and _check_exists("poetry"):
        _run("poetry install", project_dir)
        return (None, f"poetry run {plan.get('run') or 'python main.py'}")
    if has_pdm and _check_exists("pdm"):
        _run("pdm install", project_dir)
        return (None, f"pdm run {plan.get('run') or 'python main.py'}")

    # Upgrade pip first for reliability
    try:
        subprocess.check_call([pip, "install", "--upgrade", "pip"])
    except Exception:
        logger.warning("Failed to upgrade pip; continuing with existing version")

    req = project_dir / "requirements.txt"
    if req.exists():
        subprocess.check_call([pip, "install", "-r", str(req)])

    env = os.environ.copy()
    env["PATH"] = str(Path(py).parent) + os.pathsep + env.get("PATH", "")
    for cmd in (plan.get("post_install") or []):
        if isinstance(cmd, str):
            _run(cmd, project_dir, env=env)

    return (venv_dir, None)

def _install_node(project_dir: Path, plan: Dict[str, Any]) -> None:
    lock_yarn = project_dir / "yarn.lock"
    lock_pnpm = project_dir / "pnpm-lock.yaml"
    lock_npm = project_dir / "package-lock.json"
    if lock_yarn.exists() and _check_exists("yarn"):
        _run("yarn install", project_dir)
    elif lock_pnpm.exists() and _check_exists("pnpm"):
        _run("pnpm install", project_dir)
    else:
        _run("npm ci" if lock_npm.exists() else "npm install", project_dir)
    # Heuristic: ensure Vite plugins required by config are installed
    try:
        pkg_json = project_dir / "package.json"
        pkg = json.loads(pkg_json.read_text(encoding="utf-8")) if pkg_json.exists() else {}
        deps = set((pkg.get("dependencies") or {}).keys()) | set((pkg.get("devDependencies") or {}).keys())
    except Exception:
        deps = set()
    # Detect vite and plugin-react usage
    vite_cfg = None
    for name in ["vite.config.ts","vite.config.js","vite.config.mjs","vite.config.cjs"]:
        p = project_dir / name
        if p.exists():
            vite_cfg = p
            break
    if vite_cfg:
        txt = _read_text(vite_cfg)
        # Install vite if referenced but missing
        if "vite" in txt and "vite" not in deps:
            _run("npm install -D vite", project_dir)
        # React plugin
        if "@vitejs/plugin-react" in txt and "@vitejs/plugin-react" not in deps:
            _run("npm install -D @vitejs/plugin-react", project_dir)
        # Vue plugin
        if "@vitejs/plugin-vue" in txt and "@vitejs/plugin-vue" not in deps:
            _run("npm install -D @vitejs/plugin-vue", project_dir)
        # Svelte plugin
        if "@sveltejs/vite-plugin-svelte" in txt and "@sveltejs/vite-plugin-svelte" not in deps:
            _run("npm install -D @sveltejs/vite-plugin-svelte", project_dir)
    for cmd in (plan.get("post_install") or []):
        if isinstance(cmd, str):
            _run(cmd, project_dir)

def _build_go(project_dir: Path) -> Optional[str]:
    if (project_dir / "go.mod").exists():
        bin_dir = project_dir / "bin"
        bin_dir.mkdir(exist_ok=True)
        out = bin_dir / ("app.exe" if os.name == "nt" else "app")
        _run("go mod tidy", project_dir)
        rc = _run(f"go build -o \"{out}\" .", project_dir)
        if rc == 0 and out.exists():
            ensure_executable(out); return str(out)
        return "go run ."
    return "go run ."

def _build_rust(project_dir: Path) -> Optional[str]:
    name = "app"
    cargo = project_dir / "Cargo.toml"
    if cargo.exists():
        txt = _read_text(cargo)
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', txt, re.MULTILINE)
        if m: name = m.group(1)
    _run("cargo build --release", project_dir)
    exe = project_dir / "target" / "release" / (name + (".exe" if os.name == "nt" else ""))
    if exe.exists():
        ensure_executable(exe); return str(exe)
    exe = project_dir / "target" / "debug" / (name + (".exe" if os.name == "nt" else ""))
    if exe.exists():
        ensure_executable(exe); return str(exe)
    return "cargo run --release"

def _build_java_gradle(project_dir: Path) -> Optional[str]:
    if (project_dir / "gradlew").exists():
        ensure_executable(project_dir / "gradlew")
        _run("./gradlew build -x test", project_dir)
    else:
        _run("gradle build -x test", project_dir)
    libs = sorted((project_dir / "build" / "libs").glob("*.jar"),
                  key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
    if libs:
        return f"java -jar \"{libs[0]}\""
    return None

def _build_java_maven(project_dir: Path) -> Optional[str]:
    _run("mvn -q -DskipTests package", project_dir)
    jars = sorted((project_dir / "target").glob("*.jar"),
                  key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
    if jars:
        return f"java -jar \"{jars[0]}\""
    return None

def _build_java_plain(project_dir: Path) -> Optional[str]:
    java_files = list(project_dir.rglob("*.java"))
    if not java_files:
        return None
    build_dir = project_dir / "bin"
    build_dir.mkdir(exist_ok=True)
    srcs = " ".join(f"\"{p}\"" for p in java_files)
    _run(f"javac -d \"{build_dir}\" {srcs}", project_dir)
    mains = []
    for p in java_files:
        t = _read_text(p)
        if "public static void main" in t:
            rel = p.relative_to(project_dir)
            parts = list(rel.parts)
            while parts and parts[0].lower() in {"src","main","java"}:
                parts.pop(0)
            if parts:
                mains.append(".".join(Path(*parts).with_suffix("").parts))
    if mains:
        return f"java -cp \"{build_dir}\" {mains[0]}"
    return None

def _build_cpp(project_dir: Path) -> Optional[str]:
    if (project_dir / "CMakeLists.txt").exists() and _check_exists("cmake"):
        build = project_dir / "build"
        build.mkdir(exist_ok=True)
        if _run("cmake .. -DCMAKE_BUILD_TYPE=Release", build) == 0:
            _run("cmake --build . --config Release", build)
            exes = []
            for p in build.rglob("*"):
                if p.is_file() and os.access(p, os.X_OK) and p.suffix not in {".so",".dylib",".dll"}:
                    exes.append(p)
            if exes:
                exes.sort(key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
                ensure_executable(exes[0]); return str(exes[0])
    cpp_files = [p for p in project_dir.rglob("*.cpp")]
    if cpp_files and _check_exists("g++"):
        bin_dir = project_dir / "bin"
        bin_dir.mkdir(exist_ok=True)
        out = bin_dir / ("app.exe" if os.name == "nt" else "app")
        srcs = " ".join(f"\"{p}\"" for p in cpp_files)
        _run(f"g++ -O2 -std=c++17 {srcs} -o \"{out}\"", project_dir)
        if out.exists():
            ensure_executable(out); return str(out)
    return None

def _final_run_cmd(stack: str, project_dir: Path, plan_run: str, venv_dir: Optional[Path], python_hint: Optional[str]) -> str:
    if plan_run:
        if stack == "python" and venv_dir:
            py, _ = _python_bin(venv_dir)
            parts = plan_run.strip().split()
            if parts and parts[0].startswith("python"):
                parts[0] = py
                return " ".join(parts)
        return plan_run.strip()

    if stack == "python":
        if python_hint:
            return python_hint
        py, _ = _python_bin(venv_dir or _create_or_reuse_venv(project_dir))
        for cand in ("main.py","app.py"):
            if (project_dir / cand).exists():
                return f"{py} {cand}"
        mains = list(project_dir.rglob("__main__.py"))
        if mains:
            pkg = mains[0].parent.name
            return f"{py} -m {pkg}"
        return f"{py} -c \"print('No entry point; edit run.sh')\""

    if stack == "node":
        pkg = project_dir / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                if "scripts" in data and "start" in data["scripts"]:
                    return "npm start"
            except Exception:
                pass
        for cand in ("app.js","main.js","index.js"):
            if (project_dir / cand).exists():
                return f"node {cand}"
        return "node -e \"console.log('No entry point');\""

    if stack == "go":
        return _build_go(project_dir) or "go run ."

    if stack == "rust":
        return _build_rust(project_dir) or "cargo run --release"

    if stack == "java-gradle":
        return _build_java_gradle(project_dir) or "gradle run"

    if stack == "java-maven":
        return _build_java_maven(project_dir) or "mvn -q exec:java"

    if stack == "java-plain":
        return _build_java_plain(project_dir) or "echo 'No main class found'"

    if stack == "cpp":
        return _build_cpp(project_dir) or "echo 'No executable built'"

    return ""

def apply_plan(plan: Dict[str, Any], base_dir: Path, *, is_app: bool = True) -> Dict[str, Any]:
    name = plan.get("name") or "Generated Project"
    logger.info(f"Applying plan for project: {name}")
    slug = slugify(name) or "project"
    project_dir = base_dir / slug
    i = 2
    while project_dir.exists():
        project_dir = base_dir / f"{slug}-{i}"
        i += 1
    project_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created project directory: {project_dir}")

    files = plan.get("files") or []
    written = _write_files(project_dir, files)
    logger.info(f"Wrote {len(written)} files")

    # Initialize git repository
    _init_git_repo(project_dir)

    stack = _detect_stack(files)
    logger.info(f"Detected stack: {stack}")
    venv_dir: Optional[Path] = None
    python_hint: Optional[str] = None

    if stack == "python":
        venv_dir, python_hint = _install_python(project_dir, plan)
        logger.info(f"Python venv: {venv_dir}, hint: {python_hint}")
    elif stack == "node":
        _install_node(project_dir, plan)
        logger.info("Installed Node.js dependencies")
    else:
        for cmd in (plan.get("post_install") or []):
            if isinstance(cmd, str):
                logger.info(f"Running post-install command: {cmd}")
                _run(cmd, project_dir)

    run_cmd = _final_run_cmd(stack, project_dir, plan.get("run",""), venv_dir, python_hint)
    logger.info(f"Final run command: {run_cmd}")

    # Create launchers and HOW_TO_RUN.txt
    attach_launchers(
        str(project_dir),
        [str(p) for p in written],
        direct_cmd=run_cmd,   # ensures HOW_TO_RUN uses the real launch command
        is_app=is_app         # only write HOW_TO_RUN for apps
    )
    logger.info("Attached launchers")

    # Initialize git repository if available
    try:
        if _check_exists("git"):
            _init_git_repo(project_dir)
            logger.info("Initialized git repository")
        else:
            logger.info("Git not available; skipping repo initialization")
    except Exception as e:
        logger.warning(f"Git initialization failed: {e}")

    result = {
        "project_dir": str(project_dir),
        "stack": stack,
        "venv": str(venv_dir) if venv_dir else "",
        "run_cmd": run_cmd,
    }
    logger.info(f"Plan application complete: {result}")
    return result

