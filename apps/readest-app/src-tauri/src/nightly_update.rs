//! Nightly update channel: base-aware version comparator + verify/install
//! commands. The comparator mirrors `src/utils/version.ts::isUpdateNewer` and is
//! validated against the same matrix.

use semver::Version;

/// Returns the 10-digit nightly stamp if the prerelease is exactly `YYYYMMDDHH`.
fn parse_stamp(v: &Version) -> Option<u64> {
    let pre = v.pre.as_str();
    if pre.len() == 10 && pre.bytes().all(|b| b.is_ascii_digit()) {
        pre.parse::<u64>().ok()
    } else {
        None
    }
}

/// Base-aware "is `candidate` newer than `current`?" — see version.ts for the rule.
pub fn is_update_newer(candidate: &str, current: &str) -> bool {
    let (c, cur) = match (Version::parse(candidate), Version::parse(current)) {
        (Ok(c), Ok(cur)) => (c, cur),
        _ => return false,
    };
    let c_base = (c.major, c.minor, c.patch);
    let cur_base = (cur.major, cur.minor, cur.patch);
    if c_base != cur_base {
        return c_base > cur_base;
    }
    match (parse_stamp(&c), parse_stamp(&cur)) {
        (Some(_), None) => true,
        (None, Some(_)) => false,
        (Some(cs), Some(curs)) => cs > curs,
        (None, None) => false,
    }
}

/// Authenticate the currently read artifact bytes with the compiled official
/// updater key. The renderer supplies only a path and signature, never a key.
/// This is not an atomic verify-and-launch operation: existing custom installers
/// still reopen a pathname and must not use this boolean as a race-free capability.
#[tauri::command]
pub async fn verify_update_signature<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    path: String,
    signature: String,
) -> bool {
    let Ok(path) = crate::transfer_file::ensure_path_allowed(&app, &path) else {
        return false;
    };
    let Ok(data) = tokio::fs::read(&path).await else {
        return false;
    };
    crate::update_signature::verify_official_signature(&data, &signature)
}

/// Progress event streamed to the JS install dialog over an IPC `Channel`.
#[cfg(desktop)]
#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct NightlyProgress {
    pub event: String, // "progress" | "finished"
    pub downloaded: u64,
    pub content_length: u64,
}

/// Drives the Tauri updater against a single nightly/stable manifest endpoint
/// with the base-aware [`is_update_newer`] comparator, then downloads, installs
/// and relaunches. Reuses Tauri's minisign verification and native installers
/// (`.app.tar.gz` on macOS, NSIS on Windows). Progress is streamed to the JS
/// dialog over `channel`.
#[cfg(desktop)]
#[tauri::command]
pub async fn install_nightly_update<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    endpoint: String,
    channel: tauri::ipc::Channel<NightlyProgress>,
) -> std::result::Result<(), String> {
    use tauri::Url;
    use tauri_plugin_updater::UpdaterExt;

    let url = Url::parse(&endpoint).map_err(|e| e.to_string())?;
    let updater = app
        .updater_builder()
        .endpoints(vec![url])
        .map_err(|e| e.to_string())?
        .version_comparator(|current, release| {
            is_update_newer(&release.version.to_string(), &current.to_string())
        })
        .build()
        .map_err(|e| e.to_string())?;

    let Some(update) = updater.check().await.map_err(|e| e.to_string())? else {
        return Err("no update available".into());
    };

    let mut downloaded: u64 = 0;
    let progress_channel = channel.clone();
    update
        .download_and_install(
            move |chunk, total| {
                downloaded += chunk as u64;
                let _ = progress_channel.send(NightlyProgress {
                    event: "progress".into(),
                    downloaded,
                    content_length: total.unwrap_or(0),
                });
            },
            move || {
                let _ = channel.send(NightlyProgress {
                    event: "finished".into(),
                    downloaded: 0,
                    content_length: 0,
                });
            },
        )
        .await
        .map_err(|e| e.to_string())?;

    app.restart()
}

#[cfg(test)]
mod tests {
    use super::is_update_newer;

    #[test]
    fn matrix() {
        let cases: &[(&str, &str, bool)] = &[
            ("0.11.5", "0.11.4-2026061406", true),
            ("0.11.4-2026061506", "0.11.4-2026061406", true),
            ("0.11.4-2026061406", "0.11.4-2026061506", false),
            ("0.11.4", "0.11.4-2026061406", false),
            ("0.11.4-2026061406", "0.11.4", true),
            ("0.11.5-2026070106", "0.11.4", true),
            ("0.11.4", "0.11.4", false),
            ("0.11.4-2026061406", "0.11.4-2026061406", false),
            ("0.11.4-rc.1", "0.11.4", false),
            ("", "0.11.4", false),
            ("0.11.4", "", false),
        ];
        for (cand, cur, want) in cases {
            assert_eq!(
                is_update_newer(cand, cur),
                *want,
                "is_update_newer({cand}, {cur})"
            );
        }
    }
}
