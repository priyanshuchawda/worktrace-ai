# WorkTrace AI Desktop

Tauri v2, React, TypeScript, and Tailwind desktop shell for WorkTrace AI.

The desktop app is no longer status-only. It includes sidecar health display,
configured sidecar start/stop controls, recorder start/pause/resume/stop
controls, raw timeline review, session browser/delete flows, screenshot metadata
review/delete controls, deterministic export preview, local model settings, and
an AI report panel wired through typed Tauri commands to the Python sidecar.

Current limits:

- AI report generation still depends on a configured backend report runtime; the
  default FastAPI app reports a safe unavailable state.
- Local model runtimes are not downloaded or started by the desktop.
- File-watch roots can be entered before starting or resuming a recording; the
  sidecar still records metadata-only events and redacts ignored/sensitive paths.
- Screenshot preview and OCR snippets are surfaced locally when artifacts and
  OCR rows exist; screenshots are still not uploaded to hosted development AI by
  default.
- Session folder open resolves the local session artifact path and launches it
  in Windows File Explorer when the folder still exists.
- Hosted Gemini/Gemma report generation is not wired yet and, when added, must
  remain explicitly enabled development-only behavior.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
