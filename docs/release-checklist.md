# Release Checklist

Use this checklist for source-only alpha milestones and future Store releases.

## Source-Only Alpha

- Confirm the tag matches `v0.x.y-alpha.n`.
- Confirm GitHub Release is marked draft or prerelease before publication.
- Confirm no installable Windows binary is attached.
- Run the artifact guard on any local artifact directory:
  `pwsh -File scripts/release/validate-release-artifacts.ps1 -ArtifactPath <path> -Channel alpha`
- Include compact validation summaries only.
- Confirm release notes state that public Windows installer distribution remains
  deferred to the future Microsoft Store MSIX/AppX path.
- Confirm no `.env`, API key, raw session evidence, screenshots, OCR text, model
  files, local private paths, or validation logs with private content are
  included.

## Future Store Beta Or Stable

Do not start this section without explicit owner approval.

- Confirm Microsoft Store product identity and Partner Center setup are approved.
- Confirm Store-compatible MSIX/AppX packaging path is implemented.
- Confirm Windows App Certification Kit checks where applicable.
- Confirm package identity, publisher, version, and capabilities match Store
  requirements.
- Confirm Store submission/certification status is recorded.
- Confirm install/update evidence comes from the intended Store channel.
- Confirm NSIS/internal QA artifacts are not mixed with Store release assets.
- Confirm Tauri updater remains disabled unless a separately approved trusted
  update channel exists.

## Required Product Evidence Before External Beta

- Minimal deterministic CI is green.
- Local compact gates pass for touched areas.
- Installed-app smoke evidence is current for packaging changes.
- Local AI report path is verified or missing-runtime behavior is documented.
- Privacy/security review is current.
- Deletion/privacy cleanup proof remains passing.
- Release notes include known limitations and distribution status.
