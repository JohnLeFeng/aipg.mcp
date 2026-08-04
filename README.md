# AI Playground ComfyUI MCP

This workspace exposes AI Playground's running ComfyUI backend to VS Code and GitHub Copilot through a local Streamable HTTP MCP server.

## Prerequisites

- Windows 10 or 11 with PowerShell
- Python 3.11, available through the Windows `py` launcher
- Intel AI Playground installed and able to generate images with
   **Draft Image - Fast**

The direct Python packages are `mcp==2.0.0`, `mcp-types==2.0.0`, and
`httpx==0.28.1`. Pip installs their transitive dependencies automatically.

## Setup

From the repository root, create the virtual environment expected by the
launcher and install the pinned dependencies:

```powershell
py -3.11 -m venv ____env
.\____env\Scripts\python.exe -m pip install --upgrade pip
.\____env\Scripts\python.exe -m pip install -r requirements.txt
```

To verify the installation, run the unit tests:

```powershell
.\____env\Scripts\python.exe -m unittest discover -s tests -v
```

## Start

1. Start AI Playground and generate at least one image with **Draft Image - Fast**.
2. From this workspace, run:

   ```powershell
   .\start-server.ps1
   ```

3. Keep that terminal open. Use the endpoint for your client:

   - VS Code or another Windows client: `http://127.0.0.1:8765/mcp`
   - SuperClaw with default WSL NAT: `http://host.docker.internal:8765/mcp`

   The server binds to `0.0.0.0` so SuperClaw's WSL/Docker backend can reach it. Keep Windows Firewall enabled; this MCP server does not provide user authentication.
4. In VS Code's MCP server view, start or refresh **aipg-comfyui**.

Press `Ctrl+C` in the server terminal to stop it.

## Configuration

The server automatically uses the standard Windows AI Playground locations:

- Resources: `%LOCALAPPDATA%\Programs\AI Playground\resources`
- Generated images: `%USERPROFILE%\Documents\AI-Playground\media`
- Workflow: `workflows\draft_image_fast.json` in this project
- MCP listener: `0.0.0.0:8765`

Set any of these environment variables before starting the server to override a
default: `AIPG_RESOURCES_DIR`, `AIPG_OUTPUT_DIR`, `AIPG_WORKFLOW_PATH`,
`AIPG_MCP_HOST`, or `AIPG_MCP_PORT`.

For example:

```powershell
$env:AIPG_OUTPUT_DIR = "D:\AI-Playground\media"
.\start-server.ps1
```

Overrides apply to the launched server process and must refer to the matching AI
Playground installation and output locations.

## Tools

- `comfyui_status`: verifies that AI Playground's ComfyUI backend is reachable.
- `generate_image`: generates a PNG with the captured Draft Image - Fast workflow.

`generate_image` accepts `prompt`, `negative_prompt`, `width`, `height`, `steps`, and `seed`. Width and height must be multiples of 8 between 64 and 2048. Use seed `-1` for a random image. Four steps is the tuned default for the bundled LCM workflow.

Generated files remain in `%USERPROFILE%\Documents\AI-Playground\media` by
default and are also returned as MCP image content.

## Troubleshooting

- Start AI Playground before calling either tool.
- If authentication fails after restarting AI Playground, call the tool again; the bridge discovers the newest rotating token on every invocation.
- If port `8765` is already in use, stop the other process before running the launcher.
- The ComfyUI `nodes_glsl.py` OpenGL warning in the supplied log is unrelated to this MCP bridge and does not prevent image generation.