//! Official update signature policy. The verification authority comes from the
//! application's compiled base configuration, never an IPC argument. This only
//! authenticates the bytes read here; it does not bind a subsequent path launch.

// Key rotation must update this base config and rebuild. Runtime environment
// or CLI configuration overlays cannot replace this verification authority.
const COMPILED_CONFIG: &str = include_str!("../tauri.conf.json");

fn configured_public_key(config: &str) -> Option<String> {
    let config: serde_json::Value = serde_json::from_str(config).ok()?;
    let key = config
        .get("plugins")?
        .get("updater")?
        .get("pubkey")?
        .as_str()?;
    (!key.trim().is_empty()).then(|| key.to_owned())
}

pub(crate) fn verify_official_signature(data: &[u8], signature: &str) -> bool {
    let Some(public_key) = configured_public_key(COMPILED_CONFIG) else {
        return false;
    };
    verify_signature_impl(data, signature, &public_key)
}

/// Base64-decode `s` and interpret the bytes as UTF-8, mirroring Tauri's
/// `base64_to_string` (`tauri-plugin-updater-2.10.1/src/updater.rs:1465`).
fn base64_to_string(s: &str) -> Option<String> {
    use base64::Engine;
    let decoded = base64::engine::general_purpose::STANDARD.decode(s).ok()?;
    String::from_utf8(decoded).ok()
}

/// Cryptographic primitive, deliberately private: production callers cannot
/// select the key. Returns `true` only when
/// `data` is covered by `signature` under `pub_key`; any decode error or
/// verification failure returns `false` (fail-closed).
fn verify_signature_impl(data: &[u8], signature: &str, pub_key: &str) -> bool {
    use minisign_verify::{PublicKey, Signature};

    let Some(pub_key_decoded) = base64_to_string(pub_key) else {
        return false;
    };
    let Ok(public_key) = PublicKey::decode(&pub_key_decoded) else {
        return false;
    };
    let Some(signature_decoded) = base64_to_string(signature) else {
        return false;
    };
    let Ok(sig) = Signature::decode(&signature_decoded) else {
        return false;
    };
    public_key.verify(data, &sig, true).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixtures generated with a THROWAWAY minisign keypair (`tauri signer
    // generate`/`sign`) over the exact bytes in TEST_DATA. The private key was
    // discarded; the public key + signature below are safe to embed. These
    // mirror the real inputs: `pub_key` is base64 of the `.pub` file (== the
    // tauri.conf `updater.pubkey` format) and `signature` is the base64 `.sig`
    // contents (== the manifest `signature` field).
    const TEST_DATA: &[u8] = b"readest-nightly-verify-test\n";
    const TEST_PUBKEY_B64: &str = "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IEZFQTAxMjIzNUEwRkE0OUIKUldTYnBBOWFJeEtnL2x4Q3dKR3dSWVJCY3dLNXdCR1l4d1YyVkhaZUppOVVNVm1kOGprbU85bTMK";
    const TEST_SIG_B64: &str = "dW50cnVzdGVkIGNvbW1lbnQ6IHNpZ25hdHVyZSBmcm9tIHRhdXJpIHNlY3JldCBrZXkKUlVTYnBBOWFJeEtnL3RvRC83dEJEUXZONVFZM1hranhKTUZxQzllR2lGWnNjckZMbCtOa3RXMi80aFdDYUNDUkdOa0NqUjJUQkZDL2dqaUVTeURlNzI0cW1BcUlZY2ZsOGcwPQp0cnVzdGVkIGNvbW1lbnQ6IHRpbWVzdGFtcDoxNzgxNDE0MzExCWZpbGU6bnYuYmluCkQzajlpbVZPOXVDYXdna2JBVWZ0TTE4K1d1cWdEYWVYQzVraGh4U1ZuOGNSTDZaOU5zV093OEVDajBvV0JydVV5VGY2K0tkb0hBbGJHYWprK0NsNUN3PT0K";

    #[test]
    fn verify_accepts_valid_signature() {
        assert!(verify_signature_impl(
            TEST_DATA,
            TEST_SIG_B64,
            TEST_PUBKEY_B64
        ));
    }

    #[test]
    fn verify_rejects_tampered_data() {
        // Correct key + correct signature, but the bytes changed → must fail.
        assert!(!verify_signature_impl(
            b"readest-nightly-verify-TAMPERED\n",
            TEST_SIG_B64,
            TEST_PUBKEY_B64
        ));
    }

    #[test]
    fn verify_rejects_bad_signature() {
        assert!(!verify_signature_impl(
            TEST_DATA,
            "not-base64-!!!",
            TEST_PUBKEY_B64
        ));
        assert!(!verify_signature_impl(TEST_DATA, "", TEST_PUBKEY_B64));
    }

    #[test]
    fn verify_rejects_malformed_pubkey() {
        assert!(!verify_signature_impl(TEST_DATA, TEST_SIG_B64, "aGVsbG8="));
        assert!(!verify_signature_impl(TEST_DATA, TEST_SIG_B64, ""));
    }

    #[test]
    fn official_policy_rejects_valid_signature_under_another_key() {
        assert!(verify_signature_impl(
            TEST_DATA,
            TEST_SIG_B64,
            TEST_PUBKEY_B64
        ));
        assert_ne!(
            configured_public_key(COMPILED_CONFIG).as_deref(),
            Some(TEST_PUBKEY_B64)
        );
        assert!(!verify_official_signature(TEST_DATA, TEST_SIG_B64));
    }

    #[test]
    fn compiled_key_is_present_and_decodes_as_a_verification_key() {
        let key = configured_public_key(COMPILED_CONFIG).expect("compiled updater key");
        let decoded = base64_to_string(&key).expect("base64 public key");
        assert!(minisign_verify::PublicKey::decode(&decoded).is_ok());
        assert!(!verify_official_signature(TEST_DATA, "not-base64"));
    }

    #[test]
    fn malformed_or_missing_configuration_cannot_supply_a_key() {
        for config in [
            "not json",
            "{}",
            r#"{"plugins":{"updater":{}}}"#,
            r#"{"plugins":{"updater":{"pubkey":"  "}}}"#,
            r#"{"plugins":{"updater":{"pubkey":23}}}"#,
        ] {
            assert_eq!(configured_public_key(config), None);
        }
    }
}
