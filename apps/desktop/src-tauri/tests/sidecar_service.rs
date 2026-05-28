use std::{
    env, fs,
    io::{Read, Write},
    net::TcpListener,
    path::PathBuf,
    sync::Mutex,
    thread,
    time::{SystemTime, UNIX_EPOCH},
};
use worktrace_desktop_lib::commands::sidecar::{
    cancel_ai_report, delete_session, delete_session_screenshots, export_session_markdown,
    export_session_raw_json, generate_ai_report, get_ai_report_status, get_privacy_policy,
    get_session_events, get_session_folder, get_session_screenshot_preview,
    get_session_screenshots, get_sessions, open_session_folder, pause_recording_session,
    resume_recording_session, start_recording_session, stop_recording_session,
    update_privacy_policy,
};
use worktrace_desktop_lib::services::sidecar::{
    forget_managed_sidecar_for_test, resolve_sidecar_binary, sidecar_base_url_from_port,
    sidecar_launch_environment, sidecar_pid_file_path_for_test,
    sidecar_process_tree_kill_command_for_test, AiReportStatus, PrivacyPolicyConfigStatus,
    RecorderControlStatus, ScreenshotDeletionStatus, SessionDeletionStatus, SessionEventsStatus,
    SessionExportStatus, SessionFolderStatus, SessionListStatus, SessionScreenshotPreviewStatus,
    SessionScreenshotsStatus, SidecarService, SidecarStatus, StartRecordingSessionRequest,
};

static ENV_LOCK: Mutex<()> = Mutex::new(());

#[test]
fn sidecar_binary_lookup_prefers_configured_worktrace_sidecar_bin() {
    let temp_root = unique_temp_dir("configured_bin");
    let configured = touch_file(&temp_root.join("configured-sidecar.exe"));
    let bundled = touch_file(&temp_root.join("sidecars").join("worktrace-local-agent.exe"));

    let found = resolve_sidecar_binary(Some(configured.clone()), temp_root.clone());

    assert_eq!(found, Some(configured));
    assert!(bundled.is_file());
    remove_temp_dir(temp_root);
}

#[test]
fn sidecar_binary_lookup_finds_bundled_worktrace_local_agent_exe() {
    let temp_root = unique_temp_dir("bundled_bin");
    let bundled = touch_file(&temp_root.join("sidecars").join("worktrace-local-agent.exe"));

    let found = resolve_sidecar_binary(None, temp_root.clone());

    assert_eq!(found, Some(bundled));
    remove_temp_dir(temp_root);
}

#[test]
fn start_sidecar_launch_environment_is_local_only_and_deterministic() {
    let env = sidecar_launch_environment(4567);

    assert!(env.contains(&(
        "WORKTRACE_SIDECAR_HOST".to_string(),
        "127.0.0.1".to_string()
    )));
    assert!(env.contains(&("WORKTRACE_SIDECAR_PORT".to_string(), "4567".to_string())));
}

#[test]
fn sidecar_process_tree_kill_command_targets_windows_descendants() {
    let command = sidecar_process_tree_kill_command_for_test(4321);

    if cfg!(windows) {
        assert_eq!(command.program, "taskkill");
        assert_eq!(command.args, vec!["/PID", "4321", "/T", "/F"]);
    } else {
        assert_eq!(command.program, "kill");
        assert_eq!(command.args, vec!["-TERM", "4321"]);
    }
}

#[test]
fn invalid_non_localhost_sidecar_url_is_rejected() {
    let service = SidecarService;

    let health = service.health_from_base_url("http://192.168.1.10:8765");

    assert_eq!(health.status, SidecarStatus::Unhealthy);
    assert_eq!(
        health.message,
        "Local agent sidecar URL must use localhost."
    );
}

#[test]
fn configured_port_builds_localhost_base_url() {
    assert_eq!(sidecar_base_url_from_port(4567), "http://127.0.0.1:4567");
}

#[test]
fn default_sidecar_health_reports_missing_binary() {
    with_sidecar_env(None, None, None, None, || {
        let service = SidecarService;

        let health = service.health();

        assert_eq!(health.status, SidecarStatus::Missing);
        assert_eq!(health.app_version, None);
        assert_eq!(health.schema_version, None);
        assert_eq!(
            health.message,
            "Local agent sidecar binary is not configured yet."
        );
    });
}

#[test]
fn start_reports_safe_missing_sidecar_state() {
    with_sidecar_env(None, None, None, None, || {
        let service = SidecarService;

        let health = service.start();

        assert_eq!(health.status, SidecarStatus::Missing);
        assert_eq!(
            health.message,
            "Local agent sidecar binary is not configured yet."
        );
    });
}

#[test]
fn stop_reports_safe_missing_sidecar_state() {
    with_sidecar_env(None, None, None, None, || {
        let service = SidecarService;

        let health = service.stop();

        assert_eq!(health.status, SidecarStatus::Missing);
        assert_eq!(health.message, "Local agent sidecar is not running.");
    });
}

#[test]
fn events_report_safe_unavailable_state_when_bridge_is_missing() {
    with_sidecar_env(None, None, None, None, || {
        let service = SidecarService;

        let result = service.events("latest".to_string());

        assert_eq!(result.status, SessionEventsStatus::Unavailable);
        assert!(result.events.is_empty());
    });
}

#[test]
fn command_exposes_safe_session_events_fallback() {
    with_sidecar_env(None, None, None, None, || {
        let result = get_session_events("latest".to_string());

        assert_eq!(result.status, SessionEventsStatus::Unavailable);
        assert!(result.events.is_empty());
    });
}

#[test]
fn recorder_control_commands_return_safe_unavailable_state_when_bridge_is_missing() {
    with_sidecar_env(None, None, None, None, || {
        let start = start_recording_session(
            "sess_control_001".to_string(),
            "2026-05-06T09:14:00+05:30".to_string(),
            Some("Desktop control".to_string()),
            None,
            None,
            Some(vec![]),
            "standard".to_string(),
            Some(vec![]),
        );
        let pause = pause_recording_session(
            "sess_control_001".to_string(),
            "2026-05-06T09:15:00+05:30".to_string(),
        );
        let resume = resume_recording_session(
            "sess_control_001".to_string(),
            "2026-05-06T09:16:00+05:30".to_string(),
            Some(vec![]),
        );
        let stop = stop_recording_session(
            "sess_control_001".to_string(),
            "2026-05-06T09:17:00+05:30".to_string(),
        );

        assert_eq!(start.status, RecorderControlStatus::Unavailable);
        assert_eq!(pause.status, RecorderControlStatus::Unavailable);
        assert_eq!(resume.status, RecorderControlStatus::Unavailable);
        assert_eq!(stop.status, RecorderControlStatus::Unavailable);
        assert!(start.session.is_none());
    });
}

#[test]
fn export_commands_return_safe_unavailable_state_when_bridge_is_missing() {
    with_sidecar_env(None, None, None, None, || {
        let markdown = export_session_markdown("sess_export_001".to_string());
        let raw_json = export_session_raw_json("sess_export_001".to_string());
        let folder = get_session_folder("sess_export_001".to_string());
        let opened_folder = open_session_folder("sess_export_001".to_string());

        assert_eq!(markdown.status, SessionExportStatus::Unavailable);
        assert_eq!(raw_json.status, SessionExportStatus::Unavailable);
        assert_eq!(folder.status, SessionFolderStatus::Unavailable);
        assert_eq!(opened_folder.status, SessionFolderStatus::Unavailable);
        assert!(markdown.export.is_none());
        assert!(raw_json.export.is_none());
        assert!(folder.path.is_none());
        assert!(opened_folder.path.is_none());
    });
}

#[test]
fn ai_report_commands_return_safe_unavailable_state_when_bridge_is_missing() {
    with_sidecar_env(None, None, None, None, || {
        let status = get_ai_report_status("sess_ai_001".to_string());
        let generated = generate_ai_report("sess_ai_001".to_string());
        let cancelled = cancel_ai_report("sess_ai_001".to_string());

        assert_eq!(status.status, AiReportStatus::RuntimeUnavailable);
        assert_eq!(generated.status, AiReportStatus::RuntimeUnavailable);
        assert_eq!(cancelled.status, AiReportStatus::Cancelled);
        assert!(status.report.is_none());
        assert!(generated.report.is_none());
    });
}

#[test]
fn screenshot_commands_return_safe_unavailable_state_when_bridge_is_missing() {
    with_sidecar_env(None, None, None, None, || {
        let screenshots = get_session_screenshots("sess_screenshot_001".to_string());
        let preview = get_session_screenshot_preview(
            "sess_screenshot_001".to_string(),
            "shot_001".to_string(),
        );
        let deletion = delete_session_screenshots("sess_screenshot_001".to_string());

        assert_eq!(screenshots.status, SessionScreenshotsStatus::Unavailable);
        assert_eq!(preview.status, SessionScreenshotPreviewStatus::Unavailable);
        assert_eq!(deletion.status, ScreenshotDeletionStatus::Unavailable);
        assert!(screenshots.screenshots.is_empty());
        assert!(preview.preview.is_none());
        assert_eq!(deletion.deleted_rows, 0);
    });
}

#[test]
fn session_browser_commands_return_safe_unavailable_state_when_bridge_is_missing() {
    with_sidecar_env(None, None, None, None, || {
        let sessions = get_sessions();
        let deletion = delete_session("sess_browser_001".to_string());

        assert_eq!(sessions.status, SessionListStatus::Unavailable);
        assert!(sessions.sessions.is_empty());
        assert_eq!(deletion.status, SessionDeletionStatus::Unavailable);
        assert_eq!(deletion.deleted_session_rows, 0);
    });
}

#[test]
fn privacy_policy_commands_return_safe_unavailable_state_when_bridge_is_missing() {
    with_sidecar_env(None, None, None, None, || {
        let loaded = get_privacy_policy();
        let saved = update_privacy_policy(vec!["Code.exe".to_string()], vec![], true);

        assert_eq!(loaded.status, PrivacyPolicyConfigStatus::Unavailable);
        assert_eq!(saved.status, PrivacyPolicyConfigStatus::Unavailable);
        assert!(loaded.policy.is_none());
        assert!(saved.policy.is_none());
    });
}

#[test]
fn health_loads_from_configured_localhost_port_without_manual_sidecar_url() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        respond_once(
            listener,
            "GET /health HTTP/1.1",
            r#"{"app_name":"worktrace-local-agent","app_version":"0.0.0","schema_version":"003_ocr_results.sql","status":"ok"}"#,
        );
    });

    with_sidecar_env(None, Some(&port.to_string()), None, None, || {
        let service = SidecarService;
        let health = service.health();

        assert_eq!(health.status, SidecarStatus::Healthy);
        assert_eq!(health.app_version.as_deref(), Some("0.0.0"));
        assert_eq!(
            health.schema_version.as_deref(),
            Some("003_ocr_results.sql")
        );
    });
    handle.join().expect("join local server");
}

#[test]
fn events_use_configured_localhost_port_without_manual_sidecar_url() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        respond_once(
            listener,
            "GET /sessions/latest/events HTTP/1.1",
            r#"{"events":[]}"#,
        );
    });

    with_sidecar_env(None, Some(&port.to_string()), None, None, || {
        let service = SidecarService;
        let result = service.events("latest".to_string());

        assert_eq!(result.status, SessionEventsStatus::Available);
        assert!(result.events.is_empty());
    });
    handle.join().expect("join local server");
}

#[test]
fn start_uses_existing_configured_sidecar_health_when_available() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        respond_once(
            listener,
            "GET /health HTTP/1.1",
            r#"{"app_name":"worktrace-local-agent","app_version":"0.0.0","schema_version":"003_ocr_results.sql","status":"ok"}"#,
        );
    });

    with_sidecar_env(None, Some(&port.to_string()), None, None, || {
        let service = SidecarService;
        let health = service.start();

        assert_eq!(health.status, SidecarStatus::Healthy);
        assert_eq!(health.message, "Local agent sidecar is healthy.");
    });
    handle.join().expect("join local server");
}

#[test]
fn start_reports_safe_missing_when_configured_sidecar_binary_is_missing() {
    with_sidecar_env(
        None,
        Some("8765"),
        Some("C:/worktrace/missing-sidecar.exe"),
        None,
        || {
            let service = SidecarService;
            let health = service.start();

            assert_eq!(health.status, SidecarStatus::Missing);
            assert_eq!(
                health.message,
                "Local agent sidecar binary is not configured yet."
            );
        },
    );
}

#[test]
fn configured_sidecar_process_can_start_and_stop_safely() {
    let Some((binary, args)) = sleeper_command() else {
        return;
    };

    with_sidecar_env(
        None,
        Some("65534"),
        Some(binary.to_string_lossy().as_ref()),
        Some(args),
        || {
            let service = SidecarService;
            let started = service.start();

            assert_eq!(started.status, SidecarStatus::Unhealthy);
            assert_eq!(
                started.message,
                "Local agent sidecar process started; health check is still pending."
            );

            let stopped = service.stop();

            assert_eq!(stopped.status, SidecarStatus::Missing);
            assert_eq!(stopped.message, "Local agent sidecar was stopped.");
        },
    );
}

#[test]
fn sidecar_can_stop_orphaned_started_process_and_restart() {
    let Some((binary, args)) = sleeper_command() else {
        return;
    };
    let port = 65533;
    let pid_file = sidecar_pid_file_path_for_test(port);
    let _ = fs::remove_file(&pid_file);

    with_sidecar_env(
        None,
        Some(&port.to_string()),
        Some(binary.to_string_lossy().as_ref()),
        Some(args),
        || {
            let service = SidecarService;
            let started = service.start();

            assert_eq!(started.status, SidecarStatus::Unhealthy);
            assert!(pid_file.is_file());

            forget_managed_sidecar_for_test();
            let stopped_orphan = service.stop();

            assert_eq!(stopped_orphan.status, SidecarStatus::Missing);
            assert_eq!(stopped_orphan.message, "Local agent sidecar was stopped.");
            assert!(!pid_file.exists());

            let restarted = service.start();
            assert_eq!(restarted.status, SidecarStatus::Unhealthy);
            assert!(pid_file.is_file());

            let stopped_restart = service.stop();
            assert_eq!(stopped_restart.status, SidecarStatus::Missing);
            assert_eq!(stopped_restart.message, "Local agent sidecar was stopped.");
            assert!(!pid_file.exists());
        },
    );
}

#[test]
fn recorder_controls_post_to_local_sidecar_and_return_session_state() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let expected_paths = [
            "POST /sessions/start HTTP/1.1",
            "POST /sessions/sess_control_001/pause HTTP/1.1",
            "POST /sessions/sess_control_001/resume HTTP/1.1",
            "POST /sessions/sess_control_001/stop HTTP/1.1",
        ];
        let statuses = ["recording", "paused", "recording", "stopped"];

        for (index, expected_path) in expected_paths.iter().enumerate() {
            let (mut stream, _) = listener.accept().expect("accept sidecar request");
            let mut request = [0_u8; 2048];
            let read_count = stream.read(&mut request).expect("read sidecar request");
            let request_text = String::from_utf8_lossy(&request[..read_count]);
            assert!(request_text.starts_with(expected_path));
            assert!(request_text.contains("Content-Type: application/json"));
            if index == 0 {
                assert!(
                    request_text.contains(r#""file_watch_roots":["C:\\repo","D:\\client-work"]"#)
                );
                assert!(request_text.contains(r#""goal":"Finish bridge tests""#));
                assert!(request_text.contains(r#""project_label":"workaudit-ai""#));
                assert!(request_text.contains(r#""tags":["desktop","beta"]"#));
            }
            if index == 2 {
                assert!(request_text.contains(r#""file_watch_roots":["D:\\client-work"]"#));
            }

            let body = format!(
                r#"{{"id":"sess_control_001","started_at":"2026-05-06T09:14:00+05:30","ended_at":null,"status":"{}","title":"Desktop control","storage_path":null,"privacy_mode":"standard"}}"#,
                statuses[index]
            );
            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            stream
                .write_all(response.as_bytes())
                .expect("write response");
        }
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let start = service.start_recording_session_from_base_url(
        StartRecordingSessionRequest {
            session_id: "sess_control_001".to_string(),
            started_at: "2026-05-06T09:14:00+05:30".to_string(),
            title: Some("Desktop control".to_string()),
            goal: Some("Finish bridge tests".to_string()),
            project_label: Some("workaudit-ai".to_string()),
            tags: vec![
                " desktop ".to_string(),
                "beta".to_string(),
                "desktop".to_string(),
            ],
            privacy_mode: "standard".to_string(),
            file_watch_roots: vec![
                " C:\\repo ".to_string(),
                "C:\\repo".to_string(),
                "D:\\client-work".to_string(),
            ],
        },
        &base_url,
    );
    let pause = service.pause_recording_session_from_base_url(
        "sess_control_001".to_string(),
        "2026-05-06T09:15:00+05:30".to_string(),
        &base_url,
    );
    let resume = service.resume_recording_session_from_base_url(
        "sess_control_001".to_string(),
        "2026-05-06T09:16:00+05:30".to_string(),
        vec!["D:\\client-work".to_string()],
        &base_url,
    );
    let stop = service.stop_recording_session_from_base_url(
        "sess_control_001".to_string(),
        "2026-05-06T09:17:00+05:30".to_string(),
        &base_url,
    );
    handle.join().expect("join local server");

    assert_eq!(start.status, RecorderControlStatus::Available);
    assert_eq!(
        start.session.as_ref().expect("start session").status,
        "recording"
    );
    assert_eq!(
        pause.session.as_ref().expect("pause session").status,
        "paused"
    );
    assert_eq!(
        resume.session.as_ref().expect("resume session").status,
        "recording"
    );
    assert_eq!(
        stop.session.as_ref().expect("stop session").status,
        "stopped"
    );
}

#[test]
fn recorder_control_invalid_response_reports_contract_mismatch() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().expect("accept sidecar request");
        let mut request = [0_u8; 2048];
        let read_count = stream.read(&mut request).expect("read sidecar request");
        let request_text = String::from_utf8_lossy(&request[..read_count]);
        assert!(request_text.starts_with("POST /sessions/start HTTP/1.1"));

        let body = r#"{"session":{"id":"sess_control_001"}}"#;
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        stream
            .write_all(response.as_bytes())
            .expect("write response");
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let start = service.start_recording_session_from_base_url(
        StartRecordingSessionRequest {
            session_id: "sess_control_001".to_string(),
            started_at: "2026-05-06T09:14:00+05:30".to_string(),
            title: Some("Desktop control".to_string()),
            goal: None,
            project_label: None,
            tags: Vec::new(),
            privacy_mode: "standard".to_string(),
            file_watch_roots: Vec::new(),
        },
        &base_url,
    );
    handle.join().expect("join local server");

    assert_eq!(start.status, RecorderControlStatus::Unavailable);
    assert_eq!(start.message, "Recorder response contract mismatch.");
    assert!(start.session.is_none());
}

#[test]
fn exports_load_preview_and_folder_from_local_sidecar() {
    let secret = ["password=", "mysecret"].concat();
    let response_secret = secret.clone();
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let expected_paths = [
            "POST /sessions/sess_export_001/exports/markdown HTTP/1.1",
            "POST /sessions/sess_export_001/exports/raw-json HTTP/1.1",
            "GET /sessions/sess_export_001/folder HTTP/1.1",
        ];
        let bodies = [
            format!(
                r##"{{"format":"markdown","path":"C:/WorkTrace/sessions/sess_export_001/exports/session.md","preview":"# WorkTrace Session Export\nEvidence: evt_export_001\n{}","evidence_ids":["evt_export_001"]}}"##,
                response_secret
            ),
            r#"{"format":"raw_json","path":"C:/WorkTrace/sessions/sess_export_001/exports/session.raw.json","preview":"{\"events\":[{\"id\":\"evt_export_001\"}]}","evidence_ids":["evt_export_001"]}"#.to_string(),
            r#"{"path":"C:/WorkTrace/sessions/sess_export_001"}"#.to_string(),
        ];

        for (expected_path, body) in expected_paths.iter().zip(bodies.iter()) {
            let (mut stream, _) = listener.accept().expect("accept sidecar request");
            let mut request = [0_u8; 2048];
            let read_count = stream.read(&mut request).expect("read sidecar request");
            let request_text = String::from_utf8_lossy(&request[..read_count]);
            assert!(request_text.starts_with(expected_path));

            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            stream
                .write_all(response.as_bytes())
                .expect("write response");
        }
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let markdown =
        service.export_session_markdown_from_base_url("sess_export_001".to_string(), &base_url);
    let raw_json =
        service.export_session_raw_json_from_base_url("sess_export_001".to_string(), &base_url);
    let folder = service.session_folder_from_base_url("sess_export_001".to_string(), &base_url);
    handle.join().expect("join local server");

    assert_eq!(markdown.status, SessionExportStatus::Available);
    assert_eq!(raw_json.status, SessionExportStatus::Available);
    assert_eq!(folder.status, SessionFolderStatus::Available);
    let markdown_export = markdown.export.expect("markdown export");
    assert_eq!(markdown_export.format, "markdown");
    assert!(markdown_export.preview.contains("evt_export_001"));
    assert!(!markdown_export.preview.contains(&secret));
    assert_eq!(markdown_export.evidence_ids, vec!["evt_export_001"]);
    let raw_json_export = raw_json.export.expect("raw json export");
    assert_eq!(raw_json_export.format, "raw_json");
    assert!(raw_json_export.preview.contains("evt_export_001"));
    assert_eq!(
        folder.path.as_deref(),
        Some("C:/WorkTrace/sessions/sess_export_001")
    );
}

#[test]
fn open_session_folder_launches_existing_folder_without_exposing_shell() {
    let session_folder = unique_temp_dir("open_session_folder");
    fs::create_dir_all(&session_folder).expect("create session folder");
    let body = serde_json::json!({ "path": session_folder.to_string_lossy() }).to_string();
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().expect("accept sidecar request");
        let mut request = [0_u8; 1024];
        let read_count = stream.read(&mut request).expect("read sidecar request");
        let request_text = String::from_utf8_lossy(&request[..read_count]);
        assert!(request_text.starts_with("GET /sessions/sess_export_001/folder HTTP/1.1"));

        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        stream
            .write_all(response.as_bytes())
            .expect("write response");
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let opened = service.open_session_folder_from_base_url_with_launcher(
        "sess_export_001".to_string(),
        &base_url,
        |path| {
            assert_eq!(path, &session_folder);
            true
        },
    );
    handle.join().expect("join local server");

    assert_eq!(opened.status, SessionFolderStatus::Available);
    assert_eq!(opened.message, "Session folder opened in File Explorer.");
    let expected_path = session_folder.to_string_lossy().to_string();
    assert_eq!(opened.path.as_deref(), Some(expected_path.as_str()));
    remove_temp_dir(session_folder);
}

#[test]
fn open_session_folder_rejects_missing_folder_without_launching() {
    let temp_root = unique_temp_dir("missing_session_folder_root");
    let missing_folder = temp_root.join("deleted");
    let body = serde_json::json!({ "path": missing_folder.to_string_lossy() }).to_string();
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().expect("accept sidecar request");
        let mut request = [0_u8; 1024];
        let read_count = stream.read(&mut request).expect("read sidecar request");
        let request_text = String::from_utf8_lossy(&request[..read_count]);
        assert!(request_text.starts_with("GET /sessions/sess_export_001/folder HTTP/1.1"));

        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        stream
            .write_all(response.as_bytes())
            .expect("write response");
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let opened = service.open_session_folder_from_base_url_with_launcher(
        "sess_export_001".to_string(),
        &base_url,
        |_| panic!("missing folder must not launch"),
    );
    handle.join().expect("join local server");

    assert_eq!(opened.status, SessionFolderStatus::Unavailable);
    assert_eq!(opened.message, "Session folder does not exist.");
    assert!(opened.path.is_none());
    remove_temp_dir(temp_root);
}

#[test]
fn ai_report_calls_local_sidecar_and_redacts_metadata() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let expected_paths = [
            "GET /sessions/sess_ai_bridge_001/ai-report/status HTTP/1.1",
            "POST /sessions/sess_ai_bridge_001/ai-report/generate HTTP/1.1",
            "POST /sessions/sess_ai_bridge_001/ai-report/cancel HTTP/1.1",
        ];
        let bodies = [
            r#"{"status":"ready","message":"Local AI report runtime is ready.","can_generate":true,"report":null,"evidence_ids":[],"model_name":"fake-local-report-model","model_version":"fake-v1","provider":"local_ollama","requested_model":"gemma-4-E2B-it","actual_model":null,"fallback_used":false,"runtime_ms":null,"input_hash":null,"generated_at":null}"#.to_string(),
            r#"{"status":"complete","message":"Local AI report generated.","can_generate":true,"report":{"session_id":"sess_ai_bridge_001","session_title":"Bridge fixture","summary":{"text":"Tests were run.","evidence_event_ids":["evt_ai_bridge_001"]},"observed_work":[{"text":"Used password=mysecret","evidence_event_ids":["evt_ai_bridge_001"]}],"timeline":[],"blockers":[],"context_switches":[{"title":"Editor to terminal token=mysecret","evidence_event_ids":["evt_ai_bridge_001"]}],"unfinished_work":[],"repeated_actions":[],"important_files":[],"commands":[{"command":"pnpm test","evidence_event_ids":["evt_ai_bridge_001"]}],"workflow_steps":[],"continuation_notes":[{"text":"Suggestion: review token=mysecret","evidence_event_ids":["evt_ai_bridge_001"]}],"confidence":0.8,"known_evidence_event_ids":["evt_ai_bridge_001"]},"evidence_ids":["evt_ai_bridge_001"],"model_name":"fake-local-report-model password=mysecret","model_version":"fake-v1","provider":"gemini_gemma_dev","requested_model":"gemma-4-31b-it token=mysecret","actual_model":"gemma-4-26b-a4b-it","fallback_used":true,"runtime_ms":42,"input_hash":"sha256:fake-input-hash","generated_at":"2026-05-06T09:15:10+05:30"}"#.to_string(),
            r#"{"status":"cancelled","message":"Local AI report generation cancelled.","can_generate":true,"report":null,"evidence_ids":[],"model_name":"fake-local-report-model","model_version":"fake-v1","provider":"local_ollama","requested_model":"gemma-4-E2B-it","actual_model":null,"fallback_used":false,"runtime_ms":null,"input_hash":null,"generated_at":null}"#.to_string(),
        ];

        for (expected_path, body) in expected_paths.iter().zip(bodies.iter()) {
            let (mut stream, _) = listener.accept().expect("accept sidecar request");
            let mut request = [0_u8; 2048];
            let read_count = stream.read(&mut request).expect("read sidecar request");
            let request_text = String::from_utf8_lossy(&request[..read_count]);
            assert!(request_text.starts_with(expected_path));

            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            stream
                .write_all(response.as_bytes())
                .expect("write response");
        }
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let status =
        service.ai_report_status_from_base_url("sess_ai_bridge_001".to_string(), &base_url);
    let generated =
        service.generate_ai_report_from_base_url("sess_ai_bridge_001".to_string(), &base_url);
    let cancelled =
        service.cancel_ai_report_from_base_url("sess_ai_bridge_001".to_string(), &base_url);
    handle.join().expect("join local server");

    assert_eq!(status.status, AiReportStatus::Ready);
    assert_eq!(generated.status, AiReportStatus::Complete);
    assert_eq!(cancelled.status, AiReportStatus::Cancelled);
    assert_eq!(generated.evidence_ids, vec!["evt_ai_bridge_001"]);
    assert_eq!(generated.runtime_ms, Some(42));
    assert_eq!(
        generated.model_name.as_deref(),
        Some("fake-local-report-model [REDACTED]")
    );
    assert_eq!(status.provider.as_deref(), Some("local_ollama"));
    assert_eq!(generated.provider.as_deref(), Some("gemini_gemma_dev"));
    assert_eq!(
        generated.requested_model.as_deref(),
        Some("gemma-4-31b-it token=[REDACTED]")
    );
    assert_eq!(
        generated.actual_model.as_deref(),
        Some("gemma-4-26b-a4b-it")
    );
    assert!(generated.fallback_used);
    assert_eq!(
        generated
            .report
            .as_ref()
            .expect("generated report")
            .summary
            .evidence_event_ids,
        vec!["evt_ai_bridge_001"]
    );
    let report = generated.report.as_ref().expect("generated report");
    assert_eq!(
        report.observed_work[0].text.as_deref(),
        Some("Used [REDACTED]")
    );
    assert_eq!(
        report.context_switches[0].title.as_deref(),
        Some("Editor to terminal token=[REDACTED]")
    );
    assert_eq!(
        report.continuation_notes[0].text.as_deref(),
        Some("Suggestion: review token=[REDACTED]")
    );
}

#[test]
fn screenshots_load_metadata_and_delete_through_local_sidecar() {
    let secret = ["password=", "mysecret"].concat();
    let response_secret = secret.clone();
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let expected_paths = [
            "GET /sessions/sess_screenshot_001/screenshots HTTP/1.1",
            "DELETE /sessions/sess_screenshot_001/screenshots HTTP/1.1",
        ];
        let bodies = [
            format!(
                r#"{{"screenshots":[{{"id":"shot_001","session_id":"sess_screenshot_001","source_event_id":"evt_screen_001","timestamp":"2026-05-06T09:14:10+05:30","width":1920,"height":1080,"stored_width":960,"stored_height":540,"byte_size":12345,"content_hash":"{}","visual_hash":"visual_hash_001","storage_path":"screenshots/shot_001.png"}}]}}"#,
                response_secret
            ),
            r#"{"deleted_files":1,"missing_files":0,"deleted_rows":1}"#.to_string(),
        ];

        for (expected_path, body) in expected_paths.iter().zip(bodies.iter()) {
            let (mut stream, _) = listener.accept().expect("accept sidecar request");
            let mut request = [0_u8; 2048];
            let read_count = stream.read(&mut request).expect("read sidecar request");
            let request_text = String::from_utf8_lossy(&request[..read_count]);
            assert!(request_text.starts_with(expected_path));

            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            stream
                .write_all(response.as_bytes())
                .expect("write response");
        }
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let screenshots =
        service.session_screenshots_from_base_url("sess_screenshot_001".to_string(), &base_url);
    let deletion = service
        .delete_session_screenshots_from_base_url("sess_screenshot_001".to_string(), &base_url);
    handle.join().expect("join local server");

    assert_eq!(screenshots.status, SessionScreenshotsStatus::Available);
    assert_eq!(screenshots.screenshots.len(), 1);
    let screenshot = &screenshots.screenshots[0];
    assert_eq!(screenshot.id, "shot_001");
    assert_eq!(screenshot.session_id, "sess_screenshot_001");
    assert_eq!(
        screenshot.source_event_id.as_deref(),
        Some("evt_screen_001")
    );
    assert_eq!(screenshot.stored_width, 960);
    assert_eq!(screenshot.byte_size, 12345);
    assert!(!screenshot.content_hash.contains(&secret));
    assert_eq!(screenshot.content_hash, "[REDACTED]");
    assert_eq!(deletion.status, ScreenshotDeletionStatus::Available);
    assert_eq!(deletion.deleted_files, 1);
    assert_eq!(deletion.deleted_rows, 1);
}

#[test]
fn sessions_load_list_and_delete_through_local_sidecar() {
    let secret = ["password=", "mysecret"].concat();
    let response_secret = secret.clone();
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let expected_paths = [
            "GET /sessions HTTP/1.1",
            "DELETE /sessions/sess_browser_001 HTTP/1.1",
        ];
        let bodies = [
            format!(
                r#"{{"sessions":[{{"id":"sess_browser_001","started_at":"2026-05-06T09:14:00+05:30","ended_at":"2026-05-06T09:15:00+05:30","status":"stopped","title":"Review {}","storage_path":"C:/WorkTrace/sessions/sess_browser_001","privacy_mode":"standard","event_count":2,"screenshot_count":1}}]}}"#,
                response_secret
            ),
            r#"{"deleted_session_rows":1,"deleted_screenshot_files":1,"missing_screenshot_files":0,"deleted_screenshot_rows":1,"removed_artifact_root":true}"#.to_string(),
        ];

        for (expected_path, body) in expected_paths.iter().zip(bodies.iter()) {
            let (mut stream, _) = listener.accept().expect("accept sidecar request");
            let mut request = [0_u8; 2048];
            let read_count = stream.read(&mut request).expect("read sidecar request");
            let request_text = String::from_utf8_lossy(&request[..read_count]);
            assert!(request_text.starts_with(expected_path));

            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            stream
                .write_all(response.as_bytes())
                .expect("write response");
        }
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let sessions = service.sessions_from_base_url(&base_url);
    let deletion = service.delete_session_from_base_url("sess_browser_001".to_string(), &base_url);
    handle.join().expect("join local server");

    assert_eq!(sessions.status, SessionListStatus::Available);
    assert_eq!(sessions.sessions.len(), 1);
    let session = &sessions.sessions[0];
    assert_eq!(session.id, "sess_browser_001");
    assert_eq!(session.status, "stopped");
    assert_eq!(session.event_count, 2);
    assert_eq!(session.screenshot_count, 1);
    assert!(!session
        .title
        .as_deref()
        .unwrap_or_default()
        .contains(&secret));
    assert_eq!(session.title.as_deref(), Some("Review [REDACTED]"));
    assert_eq!(deletion.status, SessionDeletionStatus::Available);
    assert_eq!(deletion.deleted_session_rows, 1);
    assert!(deletion.removed_artifact_root);
}

#[test]
fn privacy_policy_loads_and_saves_through_local_sidecar() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let expected_paths = [
            "GET /privacy/policy HTTP/1.1",
            "PUT /privacy/policy HTTP/1.1",
        ];
        let bodies = [
            r#"{"allowlist":["Code.exe"],"blocklist":["password=mysecret"],"clipboard_safe_mode":true}"#.to_string(),
            r#"{"allowlist":["Windows Terminal"],"blocklist":["chrome.exe"],"clipboard_safe_mode":false}"#.to_string(),
        ];

        for (index, (expected_path, body)) in expected_paths.iter().zip(bodies.iter()).enumerate() {
            let (mut stream, _) = listener.accept().expect("accept sidecar request");
            let mut request = [0_u8; 2048];
            let read_count = stream.read(&mut request).expect("read sidecar request");
            let request_text = String::from_utf8_lossy(&request[..read_count]);
            assert!(request_text.starts_with(expected_path));
            if index == 1 {
                assert!(request_text.contains(r#""allowlist":["Windows Terminal"]"#));
                assert!(request_text.contains(r#""blocklist":["chrome.exe"]"#));
                assert!(request_text.contains(r#""clipboard_safe_mode":false"#));
            }

            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            stream
                .write_all(response.as_bytes())
                .expect("write response");
        }
    });

    let service = SidecarService;
    let base_url = format!("http://127.0.0.1:{port}");
    let loaded = service.privacy_policy_from_base_url(&base_url);
    let saved = service.update_privacy_policy_from_base_url(
        vec![
            " Windows Terminal ".to_string(),
            "Windows Terminal".to_string(),
        ],
        vec![" chrome.exe ".to_string()],
        false,
        &base_url,
    );
    handle.join().expect("join local server");

    assert_eq!(loaded.status, PrivacyPolicyConfigStatus::Available);
    let loaded_policy = loaded.policy.expect("loaded policy");
    assert_eq!(loaded_policy.allowlist, vec!["Code.exe"]);
    assert_eq!(loaded_policy.blocklist, vec!["[REDACTED]"]);

    assert_eq!(saved.status, PrivacyPolicyConfigStatus::Available);
    let saved_policy = saved.policy.expect("saved policy");
    assert_eq!(saved_policy.allowlist, vec!["Windows Terminal"]);
    assert_eq!(saved_policy.blocklist, vec!["chrome.exe"]);
    assert!(!saved_policy.clipboard_safe_mode);
}

#[test]
fn exports_reject_empty_session_ids_without_side_effects() {
    let service = SidecarService;

    let markdown =
        service.export_session_markdown_from_base_url(" ".to_string(), "http://127.0.0.1:65534");
    let raw_json =
        service.export_session_raw_json_from_base_url("".to_string(), "http://127.0.0.1:65534");
    let folder = service.session_folder_from_base_url(" ".to_string(), "http://127.0.0.1:65534");
    let opened_folder =
        service.open_session_folder_from_base_url(" ".to_string(), "http://127.0.0.1:65534");

    assert_eq!(markdown.status, SessionExportStatus::Unavailable);
    assert_eq!(raw_json.status, SessionExportStatus::Unavailable);
    assert_eq!(folder.status, SessionFolderStatus::Unavailable);
    assert_eq!(opened_folder.status, SessionFolderStatus::Unavailable);
}

#[test]
fn ai_report_rejects_empty_session_ids_without_side_effects() {
    let service = SidecarService;

    let status = service.ai_report_status_from_base_url(" ".to_string(), "http://127.0.0.1:65534");
    let generated =
        service.generate_ai_report_from_base_url("".to_string(), "http://127.0.0.1:65534");

    assert_eq!(status.status, AiReportStatus::RuntimeUnavailable);
    assert_eq!(generated.status, AiReportStatus::RuntimeUnavailable);
    assert!(generated.report.is_none());
}

#[test]
fn screenshots_reject_empty_session_ids_without_side_effects() {
    let service = SidecarService;

    let screenshots =
        service.session_screenshots_from_base_url(" ".to_string(), "http://127.0.0.1:65534");
    let deletion =
        service.delete_session_screenshots_from_base_url("".to_string(), "http://127.0.0.1:65534");

    assert_eq!(screenshots.status, SessionScreenshotsStatus::Unavailable);
    assert_eq!(deletion.status, ScreenshotDeletionStatus::Unavailable);
    assert!(screenshots.screenshots.is_empty());
    assert_eq!(deletion.deleted_files, 0);
    assert_eq!(deletion.deleted_rows, 0);
}

#[test]
fn session_delete_rejects_empty_session_ids_without_side_effects() {
    let service = SidecarService;

    let deletion = service.delete_session_from_base_url(" ".to_string(), "http://127.0.0.1:65534");

    assert_eq!(deletion.status, SessionDeletionStatus::Unavailable);
    assert_eq!(deletion.deleted_session_rows, 0);
    assert!(!deletion.removed_artifact_root);
}

#[test]
fn events_load_timeline_events_from_local_sidecar() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().expect("accept sidecar request");
        let mut request = [0_u8; 1024];
        let read_count = stream.read(&mut request).expect("read sidecar request");
        let request_text = String::from_utf8_lossy(&request[..read_count]);
        assert!(request_text.starts_with("GET /sessions/sess_bridge_001/events HTTP/1.1"));

        let body = r#"{"events":[{"id":"evt_live_001","session_id":"sess_bridge_001","timestamp":"2026-05-06T09:14:00+05:30","source":"active_window","type":"active_window_changed","privacy_level":"safe","confidence":0.98,"metadata":{"app":"VS Code","window_title":"workaudit-ai GITHUB_TOKEN=ghp_test","process_name":"Code.exe"}},{"id":"evt_file_001","session_id":"sess_bridge_001","timestamp":"2026-05-06T09:15:00+05:30","source":"file_watcher","type":"file_changed","privacy_level":"safe","confidence":1.0,"metadata":{"path":"C:/repo/src/app.py","operation":"modified","file_name":"app.py","extension":".py"}},{"id":"evt_terminal_001","session_id":"sess_bridge_001","timestamp":"2026-05-06T09:16:00+05:30","source":"terminal_command_detector","type":"terminal_command","privacy_level":"redacted","confidence":1.0,"metadata":{"command":"pnpm test --token [REDACTED]","shell":"powershell","exit_code":1,"command_hash":"hash-terminal"}}]}"#;
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        stream
            .write_all(response.as_bytes())
            .expect("write response");
    });

    let service = SidecarService;
    let result = service.events_from_base_url(
        "sess_bridge_001".to_string(),
        &format!("http://127.0.0.1:{port}"),
    );
    handle.join().expect("join local server");

    assert_eq!(result.status, SessionEventsStatus::Available);
    assert_eq!(result.events.len(), 3);
    assert_eq!(result.events[0].app, "VS Code");
    assert_eq!(result.events[0].window_title, "workaudit-ai [REDACTED]");
    assert_eq!(result.events[1].app, "File change");
    assert_eq!(result.events[1].window_title, "modified C:/repo/src/app.py");
    assert_eq!(result.events[1].source, "file_watcher");
    assert_eq!(result.events[1].event_type, "file_changed");
    assert_eq!(result.events[2].app, "Terminal command");
    assert_eq!(
        result.events[2].window_title,
        "powershell exit 1: pnpm test --token [REDACTED]"
    );
    assert_eq!(result.events[2].source, "terminal_command_detector");
    assert_eq!(result.events[2].event_type, "terminal_command");
}

#[test]
fn events_allow_latest_session_lookup_through_sidecar() {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind local test server");
    let port = listener.local_addr().expect("read local addr").port();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().expect("accept sidecar request");
        let mut request = [0_u8; 1024];
        let read_count = stream.read(&mut request).expect("read sidecar request");
        let request_text = String::from_utf8_lossy(&request[..read_count]);
        assert!(request_text.starts_with("GET /sessions/latest/events HTTP/1.1"));

        let body = r#"{"events":[]}"#;
        let response = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        stream
            .write_all(response.as_bytes())
            .expect("write response");
    });

    let service = SidecarService;
    let result =
        service.events_from_base_url("latest".to_string(), &format!("http://127.0.0.1:{port}"));
    handle.join().expect("join local server");

    assert_eq!(result.status, SessionEventsStatus::Available);
    assert!(result.events.is_empty());
}

fn respond_once(listener: TcpListener, expected_path: &str, body: &str) {
    let (mut stream, _) = listener.accept().expect("accept sidecar request");
    let mut request = [0_u8; 1024];
    let read_count = stream.read(&mut request).expect("read sidecar request");
    let request_text = String::from_utf8_lossy(&request[..read_count]);
    assert!(request_text.starts_with(expected_path));

    let response = format!(
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        body.len(),
        body
    );
    stream
        .write_all(response.as_bytes())
        .expect("write response");
}

fn sleeper_command() -> Option<(PathBuf, &'static str)> {
    if cfg!(windows) {
        let system_root = env::var("SystemRoot").ok()?;
        let powershell = PathBuf::from(system_root)
            .join("System32")
            .join("WindowsPowerShell")
            .join("v1.0")
            .join("powershell.exe");
        if powershell.is_file() {
            return Some((powershell, "-NoProfile -Command Start-Sleep -Seconds 30"));
        }
    }

    let sleep = PathBuf::from("/bin/sleep");
    if sleep.is_file() {
        return Some((sleep, "30"));
    }

    None
}

fn unique_temp_dir(name: &str) -> PathBuf {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time should be after unix epoch")
        .as_nanos();
    env::temp_dir().join(format!("worktrace_sidecar_test_{name}_{now}"))
}

fn touch_file(path: &PathBuf) -> PathBuf {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("create parent directory");
    }
    fs::write(path, b"test sidecar").expect("write sidecar placeholder");
    path.clone()
}

fn remove_temp_dir(path: PathBuf) {
    let _ = fs::remove_dir_all(path);
}

fn with_sidecar_env(
    url: Option<&str>,
    port: Option<&str>,
    binary: Option<&str>,
    args: Option<&str>,
    run: impl FnOnce(),
) {
    let _guard = ENV_LOCK
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    let previous_url = env::var("WORKTRACE_SIDECAR_URL").ok();
    let previous_port = env::var("WORKTRACE_SIDECAR_PORT").ok();
    let previous_binary = env::var("WORKTRACE_SIDECAR_BIN").ok();
    let previous_args = env::var("WORKTRACE_SIDECAR_ARGS").ok();

    match url {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_URL", value),
        None => env::remove_var("WORKTRACE_SIDECAR_URL"),
    }
    match port {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_PORT", value),
        None => env::remove_var("WORKTRACE_SIDECAR_PORT"),
    }
    match binary {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_BIN", value),
        None => env::remove_var("WORKTRACE_SIDECAR_BIN"),
    }
    match args {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_ARGS", value),
        None => env::remove_var("WORKTRACE_SIDECAR_ARGS"),
    }

    run();

    match previous_url {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_URL", value),
        None => env::remove_var("WORKTRACE_SIDECAR_URL"),
    }
    match previous_port {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_PORT", value),
        None => env::remove_var("WORKTRACE_SIDECAR_PORT"),
    }
    match previous_binary {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_BIN", value),
        None => env::remove_var("WORKTRACE_SIDECAR_BIN"),
    }
    match previous_args {
        Some(value) => env::set_var("WORKTRACE_SIDECAR_ARGS", value),
        None => env::remove_var("WORKTRACE_SIDECAR_ARGS"),
    }
}
