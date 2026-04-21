import json
from pathlib import Path

NOTEBOOK_PATH = Path("d:/VJ/Voxtral/voxtral_baseline.ipynb")


def code_cell(source: list[str]) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


def markdown_cell(source: list[str]) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source,
    }


def patch_notebook() -> None:
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    filtered_cells = []
    for cell in nb["cells"]:
        source_text = "".join(cell.get("source", []))
        if "## 1.2. Prepare Repository Source on Colab" in source_text:
            continue
        if "REPO_URL = os.getenv(\"VOXTRAL_REPO_URL\"" in source_text:
            continue
        filtered_cells.append(cell)
    nb["cells"] = filtered_cells

    nb["cells"][0]["source"] = [
        "# Voxtral ASR Baseline Setup\n",
        "This notebook sets up the `mistralai/Voxtral-Mini-4B-Realtime-2602` model using `Transformers` and exposes it via `ngrok` for remote access.",
    ]

    nb["cells"][2]["source"] = [
        "import sys\n",
        "import os\n",
        "import subprocess\n",
        "import importlib.metadata as metadata\n",
        "\n",
        "\n",
        "def installed_version(name: str) -> str | None:\n",
        "    try:\n",
        "        return metadata.version(name)\n",
        "    except metadata.PackageNotFoundError:\n",
        "        return None\n",
        "\n",
        "\n",
        "TARGET_PACKAGES = [\"fastapi\", \"uvicorn\", \"transformers\", \"mistral-common\", \"bitsandbytes\", \"torch\"]\n",
        "before_versions = {name: installed_version(name) for name in TARGET_PACKAGES}\n",
        "\n",
        "IN_COLAB = 'google.colab' in sys.modules\n",
        "\n",
        "if IN_COLAB:\n",
        "    print(\"Detected Google Colab environment. Installing Voxtral serving stack...\")\n",
        "    !python -m pip install -U pip\n",
        "\n",
        "    !python -m pip uninstall -y vllm compressed-tensors\n",
        "\n",
        "    # websockets must stay <16.0 so that google-adk and gradio-client on Colab don't break\n",
        "    !python -m pip install -U \"transformers>=5.2.0\" \"mistral-common[audio]>=1.9.1\" fastapi uvicorn bitsandbytes librosa \"websockets>=15.0.1,<16.0\" soundfile soxr pyngrok python-dotenv \"requests==2.32.4\" packaging\n",
        "\n",
        "    after_versions = {name: installed_version(name) for name in TARGET_PACKAGES}\n",
        "    print(\"\\nInstalled versions:\")\n",
        "    for pkg in TARGET_PACKAGES:\n",
        "        print(f\"  {pkg}: {after_versions[pkg] or 'not found'}\")\n",
        "\n",
        "    changed = before_versions != after_versions\n",
        "    missing_after = [name for name, value in after_versions.items() if value is None and name != 'torch']\n",
        "    if missing_after:\n",
        "        raise RuntimeError(f\"Missing packages after installation: {', '.join(missing_after)}\")\n",
        "\n",
        "    if changed:\n",
        "        raise SystemExit(\n",
        "            'The serving stack changed in this runtime. Restart the runtime now, then run all cells again '\n",
        "            'to avoid stale imports and false dependency mismatches.'\n",
        "        )\n",
        "\n",
        "    print(\"\\nServing stack already matched the required versions. No restart needed.\")\n",
        "else:\n",
        "    print(\"Running in local environment. Ensure dependencies are installed via requirements.txt\")\n",
    ]

    nb["cells"][5]["source"] = [
        "import importlib.metadata as metadata\n",
        "import sys\n",
        "from packaging.version import Version\n",
        "\n",
        "\n",
        "def installed_version(name: str) -> str | None:\n",
        "    try:\n",
        "        return metadata.version(name)\n",
        "    except metadata.PackageNotFoundError:\n",
        "        return None\n",
        "\n",
        "\n",
        "versions = {name: installed_version(name) for name in [\"transformers\", \"mistral-common\", \"torch\"]}\n",
        "print(\"Resolved serving stack:\")\n",
        "for name, value in versions.items():\n",
        "    print(f\"  {name}: {value or 'missing'}\")\n",
        "\n",
        "missing = [name for name, value in versions.items() if value is None and name != 'torch']\n",
        "if missing:\n",
        "    raise RuntimeError(f\"Missing required packages for serving: {', '.join(missing)}\")\n",
        "\n",
        "transformers_version = Version(versions['transformers'])\n",
        "mistral_common_version = Version(versions['mistral-common'])\n",
        "\n",
        "if transformers_version < Version('5.2.0'):\n",
        "    raise RuntimeError(f\"transformers>=5.2.0 is required, found {transformers_version}\")\n",
        "\n",
        "if mistral_common_version < Version('1.9.1'):\n",
        "    raise RuntimeError(f\"mistral-common>=1.9.1 is required, found {mistral_common_version}\")\n",
        "\n",
        "try:\n",
        "    from transformers import VoxtralRealtimeForConditionalGeneration  # noqa: F401\n",
        "    from mistral_common.tokens.tokenizers.audio import Audio  # noqa: F401\n",
        "except Exception as exc:\n",
        "    raise RuntimeError(\n",
        "        'Required classes not found. Ensure transformers>=5.2.0 and mistral-common[audio]>=1.9.1 are installed. '\n",
        "        'Reinstall the Voxtral stack before launching the server.'\n",
        "    ) from exc\n",
        "\n",
        "print(\"Serving stack preflight passed for Transformer backend.\")\n",
    ]

    prepare_repo_markdown = markdown_cell(
        [
            "## 1.2. Prepare Repository Source on Colab\n",
            "The server script lives in this repo, so Colab must clone the source before launching the FastAPI process.",
        ]
    )

    prepare_repo_code = code_cell(
        [
            "import os\n",
            "import subprocess\n",
            "import sys\n",
            "from pathlib import Path\n",
            "\n",
            "REPO_URL = os.getenv(\"VOXTRAL_REPO_URL\", \"https://github.com/TCTri205/VJ.git\")\n",
            "REPO_BRANCH = os.getenv(\"VOXTRAL_REPO_BRANCH\", \"fix/colab-t4-vllm-alternative\")\n",
            "REPO_SUBDIR = os.getenv(\"VOXTRAL_REPO_SUBDIR\", \"Voxtral\")\n",
            "CLONE_ROOT = Path(\"/content/voxtral-src\")\n",
            "REPO_ROOT = CLONE_ROOT / \"repo\"\n",
            "\n",
            "if 'google.colab' in sys.modules:\n",
            "    CLONE_ROOT.mkdir(parents=True, exist_ok=True)\n",
            "    if REPO_ROOT.exists():\n",
            "        print(f\"Repository already present at: {REPO_ROOT}\")\n",
            "    else:\n",
            "        gh_token = None\n",
            "        try:\n",
            "            from google.colab import userdata\n",
            "            gh_token = userdata.get('GITHUB_TOKEN')\n",
            "        except (ImportError, Exception):\n",
            "            gh_token = os.getenv(\"GITHUB_TOKEN\")\n",
            "\n",
            "        if gh_token:\n",
            "            # Inject token into the URL for authenticated clone\n",
            "            authenticated_url = REPO_URL.replace(\"https://\", f\"https://{gh_token}@\")\n",
            "        else:\n",
            "            authenticated_url = REPO_URL\n",
            "            print(\"GITHUB_TOKEN not found. Attempting public clone...\")\n",
            "\n",
            "        clone_cmd = [\"git\", \"clone\", \"--depth\", \"1\", \"--branch\", REPO_BRANCH]\n",
            "        clone_cmd.extend([authenticated_url, str(REPO_ROOT)])\n",
            "        print(f\"Cloning repository: {REPO_URL} (Branch: {REPO_BRANCH})\")\n",
            "        subprocess.run(clone_cmd, check=True)\n",
            "    PROJECT_DIR = REPO_ROOT / REPO_SUBDIR\n",
            "else:\n",
            "    PROJECT_DIR = Path.cwd()\n",
            "    print(f\"Running outside Colab. Using local project directory: {PROJECT_DIR}\")\n",
            "\n",
            "if not PROJECT_DIR.exists():\n",
            "    raise RuntimeError(f\"Project subdirectory not found: {PROJECT_DIR}\")\n",
            "\n",
            "os.chdir(PROJECT_DIR)\n",
            "SERVER_SCRIPT_PATH = (PROJECT_DIR / \"voxtral_server_transformers.py\").resolve()\n",
            "if not SERVER_SCRIPT_PATH.exists():\n",
            "    raise RuntimeError(\n",
            "        f\"Server script not found at {SERVER_SCRIPT_PATH}. Check REPO_URL/REPO_SUBDIR before launching the server.\"\n",
            "    )\n",
            "\n",
            "print(f\"Using project directory: {PROJECT_DIR}\")\n",
            "print(f\"Resolved server script: {SERVER_SCRIPT_PATH}\")\n",
        ]
    )

    launch_markdown = markdown_cell(
        [
            "## 3. Launch Transformers Server (Background)\n",
            "We clone the repo source first, then launch the FastAPI server from the resolved script path and wait for it to be ready.",
        ]
    )

    launch_code = code_cell(
        [
            "import os\n",
            "import subprocess\n",
            "import time\n",
            "from pathlib import Path\n",
            "\n",
            "import requests\n",
            "import torch\n",
            "\n",
            "\n",
            "def read_server_log() -> str:\n",
            "    try:\n",
            "        with open('/tmp/voxtral_server.log', encoding='utf-8') as f:\n",
            "            return f.read()\n",
            "    except FileNotFoundError:\n",
            "        return ''\n",
            "\n",
            "\n",
            "HAS_GPU = torch.cuda.is_available()\n",
            "print(f\"GPU Available: {HAS_GPU}\")\n",
            "\n",
            "model_id = \"mistralai/Voxtral-Mini-4B-Realtime-2602\"\n",
            "server_script = Path(globals().get(\"SERVER_SCRIPT_PATH\", Path.cwd() / \"voxtral_server_transformers.py\")).resolve()\n",
            "if not server_script.exists():\n",
            "    raise RuntimeError(\n",
            "        f\"Cannot launch server because the script is missing: {server_script}. Run the repository setup cell first.\"\n",
            "    )\n",
            "\n",
            "launch_env = os.environ.copy()\n",
            "launch_cwd = str(server_script.parent)\n",
            "args = [\"--model\", model_id, \"--port\", \"8000\"]\n",
            "\n",
            "if HAS_GPU:\n",
            "    gpu_name = torch.cuda.get_device_name(0)\n",
            "    major, minor = torch.cuda.get_device_capability(0)\n",
            "    print(f\"GPU detected: {gpu_name} ({major}.{minor})\")\n",
            "    if major < 8:\n",
            "        print(\"Turing GPU (T4) detected. Using 4-bit quantization for VRAM safety.\")\n",
            "        args.append(\"--load-in-4bit\")\n",
            "\n",
            "command = [\"python\", str(server_script)] + args\n",
            "\n",
            "print(f\"Launch command: {' '.join(command)}\")\n",
            "print(f\"Launch cwd: {launch_cwd}\")\n",
            "log_file = open(\"/tmp/voxtral_server.log\", \"w\", encoding=\"utf-8\")\n",
            "process = subprocess.Popen(command, stdout=log_file, stderr=log_file, env=launch_env, cwd=launch_cwd)\n",
            "print(\"Starting Voxtral Transformers server... (Log: /tmp/voxtral_server.log)\")\n",
            "\n",
            "max_wait = 60 * 15\n",
            "waited = 0\n",
            "while waited < max_wait:\n",
            "    if process.poll() is not None:\n",
            "        print(f'\\nServer exited unexpectedly with code: {process.returncode}')\n",
            "        print(\"--- Log History ---\")\n",
            "        print(read_server_log())\n",
            "        break\n",
            "    try:\n",
            "        response = requests.get(\"http://localhost:8000/v1/models\", timeout=2)\n",
            "        if response.status_code == 200:\n",
            "            print(\"Server is ready!\")\n",
            "            break\n",
            "    except Exception:\n",
            "        pass\n",
            "    time.sleep(10)\n",
            "    waited += 10\n",
            "    if waited % 60 == 0:\n",
            "        log_text = read_server_log()\n",
            "        print(f\"Wait {waited}s... Last log line: {log_text.splitlines()[-1] if log_text.splitlines() else 'None'}\")\n",
            "else:\n",
            "    print(\"Timeout: Server not ready after 15 minutes.\")\n",
        ]
    )

    while len(nb["cells"]) < 12:
        nb["cells"].append(markdown_cell([""]))

    nb["cells"].insert(6, prepare_repo_markdown)
    nb["cells"].insert(7, prepare_repo_code)

    nb["cells"][10] = launch_markdown
    nb["cells"][11] = launch_code

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=4, ensure_ascii=False)

    print(f"Successfully patched {NOTEBOOK_PATH} for Transformers backend.")


if __name__ == "__main__":
    patch_notebook()
