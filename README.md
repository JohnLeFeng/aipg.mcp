# AI Playground ComfyUI MCP

This workspace exposes AI Playground's running ComfyUI backend to VS Code and GitHub Copilot through a local Streamable HTTP MCP server.

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

## Tools

- `comfyui_status`: verifies that AI Playground's ComfyUI backend is reachable.
- `generate_image`: generates a PNG with the captured Draft Image - Fast workflow.

`generate_image` accepts `prompt`, `negative_prompt`, `width`, `height`, `steps`, and `seed`. Width and height must be multiples of 8 between 64 and 2048. Use seed `-1` for a random image. Four steps is the tuned default for the bundled LCM workflow.

Generated files remain in `C:\Users\John\Documents\AI-Playground\media` and are also returned as MCP image content.

## Troubleshooting

- Start AI Playground before calling either tool.
- If authentication fails after restarting AI Playground, call the tool again; the bridge discovers the newest rotating token on every invocation.
- If port `8765` is already in use, stop the other process before running the launcher.
- The ComfyUI `nodes_glsl.py` OpenGL warning in the supplied log is unrelated to this MCP bridge and does not prevent image generation.