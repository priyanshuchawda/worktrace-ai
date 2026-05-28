# Runtime Lifecycle Notes

WorkTrace desktop starts the local FastAPI sidecar as a Tauri-managed child process.
During development, a desktop reload or crash can drop the in-memory child handle while
the sidecar process is still alive. In that state, the next desktop instance can see the
sidecar health endpoint, but the stop command cannot clean up the process because it no
longer owns the original `Child` handle.

The desktop now writes a per-port pid file for sidecars it launches:

```text
%TEMP%/worktrace-local-agent-<port>.pid
```

Stop first uses the in-memory child handle. If that handle is unavailable, it falls back
to the pid file and removes the file after issuing the normal process-tree kill. This is
intended only for sidecars started by the desktop, not for arbitrary external model
runtimes.

Regression coverage:

```text
cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml sidecar_can_stop_orphaned_started_process_and_restart --test sidecar_service
```

The regression simulates losing the in-memory child handle, stops the orphaned started
process through the pid file, and verifies that a fresh start/stop cycle still works.
