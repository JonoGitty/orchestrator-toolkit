#!/usr/bin/env python3
from __future__ import annotations
import os, json, time, threading, sys, re, logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import openai

from config import get_config

# ---- Logging setup -----------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---- OpenAI client -----------------------------------------------------------
def _load_api_key() -> str:
    """
    Load OpenAI API key with priority:
    1. Local apikey.txt (for your workflow preference)
    2. Environment variable OPENAI_API_KEY
    3. System keyring (if available)
    4. Config file (~/.config/ai_orchestrator/openai_api_key)

    Raises RuntimeError if no key found.
    """
    import os
    from pathlib import Path

    # 1. Local apikey.txt
    key_file = Path(__file__).parent / "apikey.txt"
    if key_file.exists():
        try:
            key = key_file.read_text().strip()
            if key:
                logger.info(f"Using API key from {key_file}")
                return key
        except Exception as e:
            logger.warning(f"Failed to read apikey.txt: {e}")

    # 2. Environment variable
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        logger.info("Using API key from environment variable")
        return key

    # 3. System keyring
    try:
        import keyring
        key = keyring.get_password("ai_orchestrator", "openai_api_key") or ""
        if key:
            logger.info("Using API key from system keyring")
            return key
    except ImportError:
        logger.debug("keyring not available, skipping keyring lookup")
    except Exception as e:
        logger.warning(f"Failed to access keyring: {e}")

    # 4. Config file
    cfg_path = os.path.expanduser("~/.config/ai_orchestrator/openai_api_key")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, 'r') as f:
                key = f.read().strip()
            if key:
                logger.info(f"Using API key from config file: {cfg_path}")
                return key
        except Exception as e:
            logger.warning(f"Failed to read config file {cfg_path}: {e}")

    raise RuntimeError(
        "OPENAI_API_KEY not found. Please set it using one of these methods:\n"
        "1. Create cloud_agent/apikey.txt with your key (preferred by you)\n"
        "2. Environment variable: export OPENAI_API_KEY='your-key-here'\n"
        "3. System keyring: pip install keyring; keyring.set_password('ai_orchestrator','openai_api_key','your-key')\n"
        "4. Config file: echo 'your-key-here' > ~/.config/ai_orchestrator/openai_api_key\n"
    )

_client = None


def _get_client():
    """Lazy-init the OpenAI client (avoids crash on import without API key)."""
    global _client
    if _client is None:
        _client = openai.OpenAI(api_key=_load_api_key())
    return _client

# ---- System prompt (nudges to single object; parser still handles anything) --
DEFAULT_SYSTEM = r"""
You are a project plan generator for an orchestration toolkit.
Output ONLY a valid JSON object with this structure:
{
  "name": "<kebab-case-project-name>",
  "description": "<one-line description>",
  "files": [{"filename": "<relative-path>", "code": "<file-content>"}],
  "post_install": ["<optional shell commands to run after dependency install>"],
  "run": "<command to run the project>"
}
Rules:
1) Always populate "files" with the complete project source.
2) Include requirements.txt (Python), package.json (Node), or equivalent as needed.
3) No explanations, no markdown — output ONLY the JSON object.
4) Write robust, working code using modern techniques and latest stable versions.
5) Choose the best language/stack for the task.
"""

# ---- Simple on-disk plan cache ----------------------------------------------
def _cache_paths() -> Path:
    cfg = get_config()
    base = Path(os.path.expanduser(cfg.paths.config_dir)) / "cache"
    base.mkdir(parents=True, exist_ok=True)
    return base

def _cache_key(prompt: str, model: str, temperature: float) -> str:
    import hashlib, json as _json
    payload = _json.dumps({"p": prompt, "m": model, "t": temperature}, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _cache_get(prompt: str, model: str, temperature: float) -> Optional[Dict[str, Any]]:
    cfg = get_config()
    if not cfg.llm.cache_enabled:
        return None
    key = _cache_key(prompt, model, temperature)
    path = _cache_paths() / f"{key}.json"
    if not path.exists():
        return None
    try:
        ttl = max(0, int(cfg.llm.cache_ttl_seconds))
        if ttl:
            age = time.time() - path.stat().st_mtime
            if age > ttl:
                return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _cache_set(prompt: str, model: str, temperature: float, plan: Dict[str, Any]) -> None:
    cfg = get_config()
    if not cfg.llm.cache_enabled:
        return
    try:
        key = _cache_key(prompt, model, temperature)
        path = _cache_paths() / f"{key}.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
    except Exception:
        pass

# ---- Spinner -----------------------------------------------------------------
class Spinner:
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    def __init__(self, label: str = "Working"):
        self.label = label
        self._stop = threading.Event()
        self._t = None
        self._start = 0.0

    def start(self):
        self._start = time.time()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self):
        i = 0
        while not self._stop.is_set():
            elapsed = time.time() - self._start
            frame = self.FRAMES[i % len(self.FRAMES)]
            msg = f"\r{self.label} {frame}  ⏱ {elapsed:0.1f}s "
            try:
                sys.stdout.write(msg)
                sys.stdout.flush()
            except Exception:
                pass
            time.sleep(0.08)
            i += 1

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join(timeout=0.2)
        try:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
        except Exception:
            pass

# ---- Robust parsing + normalization -----------------------------------------
_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL | re.IGNORECASE)
_FIRST_OBJ   = re.compile(r"(\{.*\})", re.DOTALL)
_FIRST_ARRAY = re.compile(r"(\[.*\])", re.DOTALL)

def _extract_json_candidates(raw: str) -> List[str]:
    cands: List[str] = []
    for m in _JSON_FENCE.finditer(raw):
        cands.append(m.group(1))
    if not cands:
        m = _FIRST_OBJ.search(raw)
        if m:
            cands.append(m.group(1))
        m2 = _FIRST_ARRAY.search(raw)
        if m2:
            cands.append(m2.group(1))
    return cands

def _json_load_lenient(txt: str) -> Any:
    # tolerate trailing commas
    txt2 = re.sub(r",(\s*[}\]])", r"\1", txt)
    return json.loads(txt2)

def _guess_run(files: List[Dict[str, str]]) -> str:
    names = {f.get("filename","") for f in files}
    if "run.sh" in names: return "./run.sh"
    if "run.command" in names: return "./run.command"
    if "run.bat" in names: return "run.bat"
    pkgs = [n.split("/")[0] for n in names if n.endswith("/__main__.py")]
    if pkgs:
        return f"python -m {sorted(pkgs, key=len)[0]}"
    for cand in ("main.py","app.py"):
        if cand in names:
            return f"python {cand}"
    if "package.json" in names:
        return "npm start"
    return ""

def _wrap_array_as_plan(arr: List[Any]) -> Dict[str, Any]:
    files: List[Dict[str,str]] = []
    for it in arr:
        if isinstance(it, dict) and "filename" in it and "code" in it:
            files.append({"filename": str(it["filename"]), "code": str(it["code"])})
    if not files:
        return {
            "name": "Generated Project",
            "description": "Auto-wrapped array response",
            "files": [{"filename": "main.txt", "code": json.dumps(arr, indent=2)}],
            "post_install": [],
            "run": ""
        }
    return {
        "name": "Generated Project",
        "description": "Auto-wrapped file list",
        "files": files,
        "post_install": [],
        "run": _guess_run(files)
    }

def _normalize_plan(root: Any) -> Dict[str, Any]:
    # object → plan
    if isinstance(root, dict):
        files = root.get("files")
        if not isinstance(files, list):
            files = []
            for k, v in list(root.items()):
                if isinstance(v, str) and any(k.endswith(ext) for ext in (
                    ".py",".js",".ts",".tsx",".txt",".md",".sh",".bat",".command",
                    ".json",".yaml",".yml",".go",".rs",".java",".cpp",".hpp",".cc",".cxx",
                    "CMakeLists.txt","build.gradle","settings.gradle","pom.xml",
                )):
                    files.append({"filename": k, "code": v})
        cleaned: List[Dict[str,str]] = []
        for it in files or []:
            if isinstance(it, dict) and "filename" in it and "code" in it:
                cleaned.append({"filename": str(it["filename"]).lstrip("/\\"),
                                "code": str(it["code"])})
        plan = dict(root)
        plan["files"] = cleaned
        plan.setdefault("name", "Generated Project")
        plan.setdefault("description", "")
        post = plan.get("post_install", [])
        if not isinstance(post, list):
            post = [str(post)]
        plan["post_install"] = post
        plan.setdefault("run", _guess_run(plan["files"]))
        return plan

    # array of file objects
    if isinstance(root, list):
        return _wrap_array_as_plan(root)

    # raw code string → script
    if isinstance(root, str):
        return {
            "name": "Generated Script",
            "description": "Wrapped single code block",
            "files": [{"filename": "main.py", "code": root}],
            "post_install": [],
            "run": "python main.py"
        }

    # fallback
    return {
        "name": "Generated Project",
        "description": "Unrecognized model shape",
        "files": [{"filename": "main.txt", "code": repr(root)}],
        "post_install": [],
        "run": ""
    }

def _parse_any_plan(raw: str, bad_reply_path: Optional[str] = None) -> Dict[str, Any]:
    logger.debug(f"Parsing raw response: {raw[:200]}...")
    for cand in _extract_json_candidates(raw):
        try:
            parsed = _normalize_plan(_json_load_lenient(cand))
            logger.info("Successfully parsed JSON candidate")
            return parsed
        except Exception as e:
            logger.warning(f"Failed to parse JSON candidate: {e}")
            pass
    try:
        parsed = _normalize_plan(_json_load_lenient(raw))
        logger.info("Successfully parsed raw as JSON")
        return parsed
    except Exception as e:
        logger.warning(f"Failed to parse raw as JSON: {e}")
        pass
    logger.error("All JSON parsing failed, falling back to text wrapping")
    if bad_reply_path:
        try:
            Path(bad_reply_path).write_text(raw, encoding="utf-8")
            logger.info(f"Saved bad reply to {bad_reply_path}")
        except Exception as e:
            logger.error(f"Failed to save bad reply: {e}")
    return _normalize_plan(raw)

# ---- Chat call ---------------------------------------------------------------
def _chat_raw(messages: List[Dict[str, str]], model: str, temperature: float) -> str:
    logger.info(f"Sending prompt to cloud LLM with model {model}")
    print("☁ Sending prompt to cloud LLM…")
    spin = Spinner(label="Contacting LLM")
    spin.start()
    t0 = time.time()
    try:
        resp = _get_client().chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        raw = (resp.choices[0].message.content or "").strip()
        logger.info(f"LLM reply received in {time.time() - t0:.2f}s")
        return raw
    finally:
        spin.stop()
        dt = time.time() - t0
        print(f"✅ LLM reply received. ⏱ {dt:0.2f}s")

# ---- Public API --------------------------------------------------------------
def get_plan(
    user_prompt: str,
    *,
    system_prompt: str = DEFAULT_SYSTEM,
    model: str = None,
    temperature: float = None,
    bad_reply_path: Optional[str] = None,
    max_retries: int = None,
    use_cache: Optional[bool] = None,
) -> Dict[str, Any]:
    # Use config defaults if not specified
    config = get_config()
    if model is None:
        model = config.llm.model
    if temperature is None:
        temperature = config.llm.temperature
    if max_retries is None:
        max_retries = config.llm.max_retries
    
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt is empty")
    
    logger.info(f"Generating plan for prompt: {user_prompt[:100]}...")
    
    # Cache lookup
    caching_enabled = get_config().llm.cache_enabled if use_cache is None else bool(use_cache)
    if caching_enabled:
        cached = _cache_get(user_prompt, model, temperature)
        if cached is not None:
            print("💾 Using cached plan")
            return cached
    
    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt.strip()},
            ]
            raw = _chat_raw(messages, model=model, temperature=temperature)
            logger.info(f"Raw LLM response length: {len(raw)}")
            try:
                if get_config().behavior.verbose_logging:
                    print("📩 Raw reply:")
                    print(raw)
            except Exception:
                pass
            plan = _parse_any_plan(raw, bad_reply_path)
            logger.info(f"Parsed plan with {len(plan.get('files', []))} files")
            if caching_enabled:
                _cache_set(user_prompt, model, temperature, plan)
            return plan
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"⚠️  Generation attempt {attempt + 1} failed. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"❌ All {max_retries} attempts failed. Last error: {e}")
                raise RuntimeError(f"Failed to generate plan after {max_retries} attempts: {e}")
    
    # This should never be reached, but just in case
    raise RuntimeError("Unexpected error in plan generation")

def parse_model_reply_to_plan(raw: str, bad_reply_path: Optional[str] = None) -> Dict[str, Any]:
    return _parse_any_plan(raw, bad_reply_path)
