#!/usr/bin/env python3
"""Prepare and inspect an unsigned, arm64-only parallel Readest test build.

No signing, installation, or publishing occurs here. Production Readest,
Google Drive and OneDrive OAuth callbacks are deliberately unavailable in this
reading test build; file import and ordinary network/API access remain enabled.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

spec = importlib.util.spec_from_file_location("academic_shared", Path(__file__).with_name("academic-linux-ci.py"))
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
command = shared.command
digest = shared.digest
PART_SIZE = 16 * 1024 * 1024
APP = Path("apps/readest-app")
ANDROID = APP / "src-tauri/gen/android"
OUTPUT = Path("academic-android-artifact")
APP_ID = "com.bilingify.readest.academic.v2"
NAMESPACE = "com.bilingify.readest"
LABEL = "Readest 学术测试版 2"
A = "{http://schemas.android.com/apk/res/android}"
ET.register_namespace("android", A[1:-1])


def academic_manifest(source):
    root = ET.fromstring(source)
    for permission in list(root.findall("uses-permission")):
        if permission.get(A + "name") == "android.permission.REQUEST_INSTALL_PACKAGES":
            root.remove(permission)
    app = root.find("application")
    app.set(A + "label", LABEL)
    app.set(A + "extractNativeLibs", "true")
    for activity in app.findall("activity"):
        activity.set(A + "label", LABEL)
        name = activity.get(A + "name", "")
        if name.startswith("."):
            activity.set(A + "name", NAMESPACE + name)
        for intent in list(activity.findall("intent-filter")):
            # The original app continues to own its web and OAuth callbacks.
            # content/file intents and MIME-based sharing remain available.
            if any(node.get(A + "scheme", "") not in {"", "file", "content"} for node in intent.findall("data")):
                activity.remove(intent)
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"


def prepare_project():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Scaffolding preparation is restricted to a fresh GitHub Actions checkout")
    if command("git", "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Refusing to regenerate scaffolding over changed tracked files")
    if (ANDROID / "keystore.properties").exists():
        raise RuntimeError("Unsigned CI must not have keystore.properties")
    cli = json.loads((APP / "node_modules/@tauri-apps/cli/package.json").read_text())
    if cli["version"] != "2.11.4":
        raise RuntimeError("Review the Android scaffolding before changing the pinned CLI")
    # Save exactly the customized Android files. Never reset the rest of the
    # checkout or silently undo application/build-generated source changes.
    tracked = command("git", "ls-files", str(ANDROID)).splitlines()
    originals = {Path(name): Path(name).read_bytes() for name in tracked}
    shutil.rmtree(ANDROID)
    try:
        subprocess.run(["pnpm", "tauri", "android", "init", "--ci", "--skip-targets-install"], cwd=APP, check=True)
        with tempfile.TemporaryDirectory(prefix="academic-icons-") as tmp:
            icon_dir = Path(tmp) / "icons"
            subprocess.run(["pnpm", "tauri", "icon", "../../data/icons/readest-book.png", "--output", str(icon_dir)], cwd=APP, check=True)
            shutil.copytree(icon_dir / "android", ANDROID / "app/src/main/res", dirs_exist_ok=True)
    finally:
        for path, data in originals.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    root_build = ANDROID / "build.gradle.kts"
    generated = root_build.read_text()
    if 'com.android.tools.build:gradle:8.11.0' not in generated or 'org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.25' not in generated:
        raise RuntimeError("Unexpected npm CLI Android template; review AGP/Kotlin before building")
    # Lifecycle 2.10.0 uses Kotlin metadata newer than the npm CLI's 1.9.25.
    # Keep the actual CLI's AGP/Gradle pair, update only Kotlin in generated code.
    root_build.write_text(generated.replace("kotlin-gradle-plugin:1.9.25", "kotlin-gradle-plugin:2.2.10"))
    wrapper = (ANDROID / "gradle/wrapper/gradle-wrapper.properties").read_text()
    if "gradle-8.14.3-" not in wrapper:
        raise RuntimeError("Unexpected generated Gradle version")
    properties = ANDROID / "gradle.properties"
    text = re.sub(r"(?m)^org.gradle.jvmargs=.*$", "org.gradle.jvmargs=-Xmx3072m -Dfile.encoding=UTF-8", properties.read_text())
    properties.write_text(text + "\norg.gradle.workers.max=2\nkotlin.daemon.jvmargs=-Xmx1024m\n")
    academic = ANDROID / "app/src/academic/AndroidManifest.xml"
    academic.parent.mkdir(parents=True, exist_ok=True)
    academic.write_text(academic_manifest((ANDROID / "app/src/main/AndroidManifest.xml").read_text()))
    print("Prepared unsigned academic identity; original tracked Android customizations restored")


def preflight():
    # tauri.build.gradle.kts is emitted by Rust build scripts, so the real app
    # cannot be configured before its first Rust compile. Copy the real app
    # Gradle script, omitting only its Rust plugin/registration. This checks
    # the academic identity DSL, app Maven dependencies, AAR requirements, and
    # Kotlin metadata. Native plugin integration is checked by the real build.
    with tempfile.TemporaryDirectory(prefix="academic-android-preflight-") as tmp:
        # Preserve the real rootProject -> ../../../.env relationship. A probe
        # directly beneath /tmp would otherwise inspect environment paths at /.
        app_root = Path(tmp) / "readest-app"
        probe = app_root / "src-tauri/gen/android"
        (probe / "app/src/main/java").mkdir(parents=True)
        shutil.copyfile(APP / ".env", app_root / ".env")
        (probe / "settings.gradle").write_text("include ':app'\n")
        shutil.copyfile(ANDROID / "build.gradle.kts", probe / "build.gradle.kts")
        shutil.copyfile(ANDROID / "gradle.properties", probe / "gradle.properties")
        app_build = (ANDROID / "app/build.gradle.kts").read_text()
        for registration in ['    id("rust")\n', 'rust {\n    rootDirRel = "../../../"\n}\n',
                             'apply(from = "tauri.build.gradle.kts")']:
            if app_build.count(registration) != 1:
                raise RuntimeError("Review preflight after changing the app's Rust Gradle registration")
            app_build = app_build.replace(registration, "")
        (probe / "app/build.gradle.kts").write_text(app_build)
        shutil.copytree(ANDROID / "app/src/main/res", probe / "app/src/main/res")
        (probe / "app/src/academic").mkdir()
        shutil.copyfile(ANDROID / "app/src/academic/AndroidManifest.xml", probe / "app/src/academic/AndroidManifest.xml")
        (probe / "app/src/main/java/MetadataProbe.kt").write_text('''package com.bilingify.readest.academic.preflight
class MetadataProbe : androidx.lifecycle.LifecycleOwner {
    override val lifecycle get() = androidx.lifecycle.LifecycleRegistry(this)
}
''')
        subprocess.run([str((ANDROID / "gradlew").resolve()), "-p", str(probe), "--no-daemon",
                        ":app:checkReleaseAarMetadata", ":app:compileReleaseKotlin"], check=True)
        manifests = list((probe / "app/build/intermediates/merged_manifests/release").rglob("AndroidManifest.xml"))
        if len(manifests) != 1:
            raise RuntimeError("Expected one merged release manifest from preflight")
        errors = manifest_errors(ET.parse(manifests[0]).getroot())
        if errors:
            raise RuntimeError("Preflight manifest failed: " + "; ".join(errors))
    print("Academic manifest, app Gradle/Maven dependencies, AAR requirements and Kotlin metadata preflight passed")


def manifest_errors(root):
    errors = []
    if root.get("package") != APP_ID:
        errors.append("APK package is not the separate academic applicationId")
    app = root.find("application")
    if app is None:
        return errors + ["APK has no application"]
    if app.get(A + "label") != LABEL:
        errors.append("APK label is not the academic test label")
    if app.get(A + "debuggable", "false") != "false":
        errors.append("APK is debuggable")
    if app.get(A + "extractNativeLibs") != "true":
        errors.append("Legacy native packaging requires extractNativeLibs=true")
    if not any(node.get(A + "name") == NAMESPACE + ".MainActivity" for node in app.findall("activity")):
        errors.append("Original Java/JNI MainActivity namespace was not preserved")
    for node in root.iter("provider"):
        authorities = node.get(A + "authorities", "").split(";")
        if any(not authority.startswith(APP_ID + ".") for authority in authorities):
            errors.append("APK provider authority can collide with the original app: " + ";".join(authorities))
    if not any(node.get(A + "authorities") == APP_ID + ".fileprovider" for node in root.iter("provider")):
        errors.append("Academic FileProvider is missing")
    for node in root.iter("data"):
        if node.get(A + "scheme", "") not in {"", "content", "file"}:
            errors.append("APK claims a production link or OAuth scheme")
    if any(node.get(A + "name") == "android.permission.REQUEST_INSTALL_PACKAGES" for node in root.findall("uses-permission")):
        errors.append("APK still requests package-install permission")
    return errors


def inspect_native(apk):
    errors, libraries = [], []
    with zipfile.ZipFile(apk) as bundle:
        entries = [entry for entry in bundle.infolist() if entry.filename.startswith("lib/") and entry.filename.endswith(".so")]
        abis = sorted({entry.filename.split("/")[1] for entry in entries})
        if abis != ["arm64-v8a"]:
            errors.append("Expected only arm64-v8a native libraries; found " + repr(abis))
        for entry in entries:
            data = bundle.read(entry)
            if data[:6] != b"\x7fELF\x02\x01" or len(data) < 64 or struct.unpack_from("<H", data, 18)[0] != 183:
                errors.append("Invalid AArch64 ELF: " + entry.filename)
                continue
            offset = struct.unpack_from("<Q", data, 32)[0]
            size, count = struct.unpack_from("<HH", data, 54)
            if size < 56 or offset + size * count > len(data):
                errors.append("Invalid ELF program headers: " + entry.filename)
                continue
            loads = [struct.unpack_from("<IIQQQQQQ", data, offset + index * size) for index in range(count)
                     if struct.unpack_from("<I", data, offset + index * size)[0] == 1]
            alignments = [load[7] for load in loads]
            if not loads or any(load[7] < 16384 or (load[3] - load[2]) % 16384 for load in loads):
                errors.append("ELF LOAD segments are not 16 KiB aligned: " + entry.filename)
            if entry.compress_type != zipfile.ZIP_DEFLATED:
                errors.append("Expected compressed native library for legacy packaging: " + entry.filename)
            libraries.append({"path": entry.filename, "bytes": len(data), "loadAlignments": alignments,
                              "compression": entry.compress_type})
        if any(re.match(r"META-INF/.*\.(RSA|DSA|EC|SF)$", name, re.IGNORECASE) for name in bundle.namelist()):
            errors.append("APK contains a JAR signature")
    return {"abis": abis, "libraries": libraries, "errors": errors}


def inspect_apk(apk):
    sdk = Path(os.environ["ANDROID_HOME"])
    build_tools = sdk / "build-tools/36.0.0"
    manifest = command(str(sdk / "cmdline-tools/latest/bin/apkanalyzer"), "manifest", "print", str(apk))
    native = inspect_native(apk)
    errors = manifest_errors(ET.fromstring(manifest)) + native["errors"]
    alignment = subprocess.run([str(build_tools / "zipalign"), "-c", "-P", "16", "-v", "4", str(apk)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if alignment.returncode:
        errors.append("APK zipalign 16 KiB check failed")
    signature = subprocess.run([str(build_tools / "apksigner"), "verify", "--verbose", str(apk)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    expected_unsigned = signature.returncode != 0 and any(text in signature.stdout for text in ["Missing META-INF/MANIFEST.MF", "No signatures", "No JAR signatures"])
    if not expected_unsigned:
        errors.append("apksigner did not confirm the expected unsigned APK")
    return {"passed": not errors, "errors": errors, "manifest": manifest, "native": native,
            "zipalign": alignment.stdout, "apksigner": signature.stdout,
            "badging": command(str(build_tools / "aapt2"), "dump", "badging", str(apk))}


def export_artifact():
    repo = Path.cwd()
    apks = list((repo / ANDROID / "app/build/outputs/apk").rglob("*-release-unsigned.apk"))
    if len(apks) != 1:
        raise RuntimeError("Expected exactly one unsigned release APK, found " + repr(apks))
    apk = apks[0]
    out = repo / OUTPUT
    out.mkdir(exist_ok=False)
    # Preserve a built candidate and the complete diff before gating it, even
    # when generated tracked changes or APK checks require review.
    try:
        validation = inspect_apk(apk)
    except Exception as error:
        validation = {"passed": False, "errors": [str(error)]}
    source = command("git", "rev-parse", "HEAD")
    provenance = {
        "sourceCommit": source, "sourceTree": command("git", "rev-parse", "HEAD^{tree}"),
        "parserVersion": re.search(r"PARSER_VERSION = ['\"]([^'\"]+)",
                                   (repo / APP / "src/services/academic/layout.ts").read_text()).group(1),
        "sourceIntegrity": shared.inspect_source(), "apkValidation": validation,
        "profile": "unsigned Android release / production frontend / aarch64 only",
        "installable": False, "signing": "unsigned; local signing and device acceptance still required",
        "applicationId": APP_ID, "javaJniNamespace": NAMESPACE, "label": LABEL,
        "productionOAuthCallbacks": "disabled", "inAppUpdater": "disabled by NEXT_PUBLIC_DISABLE_UPDATER=1",
        "apkSha256": digest(apk), "apkBytes": apk.stat().st_size,
        "lockfiles": {name: digest(repo / name) for name in ["Cargo.lock", "pnpm-lock.yaml"]},
        "tools": {name: command(name, "--version") for name in ["rustc", "cargo", "node", "pnpm"]},
        "androidToolchain": {"sdk": 36, "buildTools": "36.0.0", "ndk": "28.2.13676358",
                             "agp": "8.11.0", "kotlin": "2.2.10", "gradle": "8.14.3"},
        "runUrl": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
    }
    (out / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n")
    parts = []
    with apk.open("rb") as stream:
        while data := stream.read(PART_SIZE):
            if len(parts) >= 8:
                raise RuntimeError("APK exceeds the bounded 128 MiB transfer budget")
            part = out / f"apk.part{len(parts):02}"
            part.write_bytes(data)
            parts.append({"name": part.name, "bytes": len(data), "sha256": digest(part)})
    transfer = {"sourceCommit": source, "fileName": "Readest-Academic-arm64-unsigned.apk",
                "fileSha256": digest(apk), "fileBytes": apk.stat().st_size, "parts": parts}
    (out / "transfer.json").write_text(json.dumps(transfer, indent=2) + "\n")
    print(json.dumps(transfer, indent=2))


def verify_candidate():
    provenance = json.loads((Path.cwd() / OUTPUT / "provenance.json").read_text())
    if not provenance["sourceIntegrity"]["passed"] or not provenance["apkValidation"]["passed"]:
        print(json.dumps(provenance["sourceIntegrity"], indent=2))
        print(json.dumps(provenance["apkValidation"], indent=2))
        raise RuntimeError("Candidate quarantined: source and APK checks must pass before signing")
    print("Source, separate app identity, arm64 ABI, unsigned status and 16 KiB alignment verified")
    print("Unsigned APK is not installable; local signing and device acceptance remain pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    steps = {"prepare-project": prepare_project, "preflight": preflight,
             "export-artifact": export_artifact, "verify-candidate": verify_candidate}
    parser.add_argument("step", choices=steps)
    steps[parser.parse_args().step]()
