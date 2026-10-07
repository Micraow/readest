#!/usr/bin/env python3
"""One bounded release-artifact smoke, with no build or license acceptance.

Only run/image/preflight need a GitHub-hosted SDK. The verification functions and
unit tests use Python's standard library. All output intended for upload lives in
smoke-evidence; the APK, disposable keystore and AVD never do.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

SOURCE = 'dca7a24b17c69d47ef9fb8640c80ff9e6e396392'
TREE = 'ae7e185d31983cbae64b3c5ff4cdee4fd2fbc070'
APK_SHA = '0c097206a47e18dd33659dcc9204b2ee7913a97ca02fce9089b23af2c53a1722'
APK_BYTES = 36475143
APP_ID = 'com.bilingify.readest.academic'
PARTS = [
    ('apk.part00', 16777216, '426a1e071d7070b32cea1f1db7e56a05c3fae527353688d8c791c942f62a6993'),
    ('apk.part01', 16777216, 'f034d36619e98c0903953779676edc0da33767d085695f206441a92a46e0d214'),
    ('apk.part02', 2920711, 'f7aee0a0cd0b26981c24129c8c384229455b450e778191609034b82e3b788b90'),
]
IMAGE = 'system-images;android-30;google_apis;x86_64'
META_URL = 'https://dl.google.com/android/repository/sys-img/google_apis/sys-img2-3.xml'
IMAGE_BYTES = 1438186618
IMAGE_SHA1 = '6ae21030eaadc041078444d3798e4b399f3e787d'
PDF_URL = 'https://liyuliang001.github.io/publications/hpcc.pdf'
PDF_SHA = '8199b81f7325b8797623b6c44fad90eb2664b4bc6a8e0f9bdbad7e043b02fe8a'
EVIDENCE = Path('smoke-evidence')
INPUT = Path('smoke-input')
LIMITATION = ('Same APK payload as the pinned unsigned artifact, with a different disposable test '
              'signature. ARM64 runs through x86 native translation. This is not real ARM-device '
              'performance or acceptance of the separately delivered signed APK, or of newer source changes.')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(value, indent=2) + '\n' if not isinstance(value, str) else value)


def command(*args, timeout=30, check=True, env=None, input=None):
    result = subprocess.run([str(a) for a in args], input=input, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout, env=env, text=True)
    if check and result.returncode:
        raise RuntimeError(f'{Path(args[0]).name} failed ({result.returncode}): {result.stdout[-3000:]}')
    return result.stdout


def bounded_download(url, maximum, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        require(response.geturl().startswith('https://'), 'Insecure download redirect')
        data = response.read(maximum + 1)
    require(len(data) <= maximum, 'Download exceeds its byte budget')
    return data


def zip_entries(path, expected):
    with zipfile.ZipFile(path) as bundle:
        entries = bundle.infolist()
        require(len(entries) == len(expected) and {e.filename for e in entries} == set(expected),
                'Unexpected, duplicate, or unsafe artifact ZIP entries')
        for entry in entries:
            mode = entry.external_attr >> 16
            require(not stat.S_ISLNK(mode) and not entry.is_dir() and not entry.flag_bits & 1,
                    'Symlink, directory or encrypted artifact entry')
            require(entry.file_size <= expected[entry.filename], 'Artifact entry exceeds its byte budget')
        return {e.filename: bundle.read(e) for e in entries}


def validate_manifests(transfer, provenance):
    require(transfer.get('sourceCommit') == SOURCE and provenance.get('sourceCommit') == SOURCE,
            'Source commit mismatch')
    require(provenance.get('sourceTree') == TREE, 'Source tree mismatch')
    require(transfer.get('fileName') == 'Readest-Academic-arm64-unsigned.apk', 'Unexpected APK filename')
    require(transfer.get('fileBytes') == APK_BYTES and provenance.get('apkBytes') == APK_BYTES,
            'APK size mismatch')
    require(transfer.get('fileSha256') == APK_SHA and provenance.get('apkSha256') == APK_SHA,
            'APK digest mismatch')
    require(transfer.get('parts') == [dict(name=n, bytes=b, sha256=h) for n, b, h in PARTS],
            'Transfer part order, size or digest mismatch')
    require(provenance.get('sourceIntegrity', {}).get('passed') is True and
            provenance.get('apkValidation', {}).get('passed') is True, 'Source/APK validation did not pass')
    require(provenance.get('applicationId') == APP_ID and provenance.get('installable') is False and
            provenance.get('javaJniNamespace') == 'com.bilingify.readest' and
            provenance.get('apkValidation', {}).get('native', {}).get('abis') == ['arm64-v8a'],
            'APK identity, unsigned state or ABI mismatch')


def verify():
    manifests = zip_entries(INPUT / 'academic-android-manifest.zip',
                            {'transfer.json': 65536, 'provenance.json': 262144})
    transfer, provenance = (json.loads(manifests[n]) for n in ['transfer.json', 'provenance.json'])
    validate_manifests(transfer, provenance)
    output = INPUT / 'unsigned.apk'
    with output.open('xb') as stream:
        for name, size, digest in PARTS:
            data = zip_entries(INPUT / f'academic-android-{name[4:]}.zip', {name: size})[name]
            require(len(data) == size and sha(data) == digest, 'APK part verification failed: ' + name)
            stream.write(data)
    require(output.stat().st_size == APK_BYTES and sha(output.read_bytes()) == APK_SHA, 'Whole APK mismatch')
    output.chmod(0o444)
    save('provenance.json', provenance)
    save('transfer.json', transfer)
    save('limitations.txt', LIMITATION + '\n')
    print('Pinned source gates, ZIP allowlist, each part and complete unsigned APK verified')


def image_metadata(xml):
    root = ET.fromstring(xml)
    packages = [n for n in root if n.tag.endswith('remotePackage') and n.get('path') == IMAGE]
    require(len(packages) == 1, 'Expected exactly one official system image entry')
    package = packages[0]
    complete = package.find('archives/archive/complete')
    require(package.findtext('revision/major') == '16' and complete is not None, 'Image revision changed')
    size = int(complete.findtext('size'))
    require(size == IMAGE_BYTES and size <= 1536 * 1024**2, 'Image compressed size changed/exceeds 1.5 GiB')
    require(complete.findtext('checksum') == IMAGE_SHA1 and complete.findtext('url') == 'x86_64-30_r16.zip',
            'Official image checksum or URL changed')
    license_id = package.find('uses-license').get('ref')
    require(re.fullmatch(r'[a-z0-9-]+', license_id) is not None, 'Unsafe license ID')
    licenses = [n for n in root if n.tag.endswith('license') and n.get('id') == license_id]
    require(len(licenses) == 1 and licenses[0].text, 'Required license text is missing')
    # Android repository License.getLicenseHash hashes the exact UTF-8 value,
    # without strip(): platform/tools/base repository/api/License.java.
    text = licenses[0].text
    return {'package': IMAGE, 'revision': 16, 'compressedBytes': size, 'sha1': IMAGE_SHA1,
            'metadataUrl': META_URL, 'archiveUrl': META_URL.rsplit('/', 1)[0] + '/x86_64-30_r16.zip',
            'licenseId': license_id, 'licenseSha1': hashlib.sha1(text.encode()).hexdigest(),
            'licenseText': text}


def sdk_paths():
    root = Path(os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT', '/missing-sdk'))
    cli = root / 'cmdline-tools/latest/bin'
    versions = sorted((root / 'build-tools').glob('*'),
                      key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)), reverse=True)
    build = next((p for p in versions if (p / 'apksigner').is_file() and (p / 'zipalign').is_file()), None)
    paths = {'sdk': str(root), 'sdkmanager': str(cli / 'sdkmanager'), 'avdmanager': str(cli / 'avdmanager'),
             'emulator': str(root / 'emulator/emulator'), 'adb': str(root / 'platform-tools/adb'),
             'apksigner': str(build / 'apksigner') if build else '',
             'zipalign': str(build / 'zipalign') if build else ''}
    for key, value in paths.items():
        if key != 'sdk':
            require(bool(value) and os.access(value, os.X_OK),
                    f'Hosted SDK prerequisite missing: {key}; no unreviewed tool download attempted')
    require(shutil.which('keytool') is not None, 'Hosted Java keytool is missing')
    return paths


def preflight():
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Emulator operations are GitHub-only')
    require(os.path.exists('/dev/kvm') and os.access('/dev/kvm', os.R_OK | os.W_OK),
            'KVM unavailable; permission changes are forbidden')
    require(shutil.disk_usage('.').free >= 10 * 1024**3, 'Less than 10 GiB free disk')
    paths = sdk_paths()
    info = image_metadata(bounded_download(META_URL, 5 * 1024**2))
    license_text = info.pop('licenseText')
    accepted = Path(paths['sdk']) / 'licenses' / info['licenseId']
    hashes = accepted.read_text().split() if accepted.is_file() else []
    info['alreadyAccepted'] = info['licenseSha1'] in hashes
    save('image-metadata.json', info)
    if not info['alreadyAccepted']:
        save('unaccepted-license.txt', license_text)
        raise RuntimeError(f"New terms need approval: {info['licenseId']} ({info['licenseSha1']}); "
                           f"see {META_URL}. Image not downloaded, license not accepted.")
    INPUT.joinpath('sdk.json').write_text(json.dumps(paths))
    save('host-tools.txt', command(paths['emulator'], '-version', check=False)[:4000] + '\n' +
         command(paths['adb'], 'version') + '\n' + command(paths['apksigner'], 'version'))


def install_image():
    paths = json.loads((INPUT / 'sdk.json').read_text())
    result = subprocess.run([paths['sdkmanager'], '--sdk_root=' + paths['sdk'], '--install', IMAGE],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=330, text=True)
    save('image-install.txt', result.stdout[-12000:])
    require(result.returncode == 0, 'sdkmanager failed; no new terms were accepted (stdin was closed)')
    properties = Path(paths['sdk']) / 'system-images/android-30/google_apis/x86_64/source.properties'
    require(properties.is_file() and re.search(r'(?m)^Pkg.Revision\s*=\s*16\s*$', properties.read_text()),
            'Pinned image revision 16 was not installed')


def adb(*args, timeout=20, check=True):
    paths = json.loads((INPUT / 'sdk.json').read_text())
    return command(paths['adb'], '-s', 'emulator-5554', *args, timeout=timeout, check=check)


def payload(apk):
    with zipfile.ZipFile(apk) as bundle:
        return {n: sha(bundle.read(n)) for n in bundle.namelist()
                if not re.fullmatch(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:RSA|DSA|EC|SF))', n, re.I)}


def sign_copy(paths):
    original = INPUT / 'unsigned.apk'
    signed = INPUT / 'temporary-test-signature.apk'
    with tempfile.TemporaryDirectory(prefix='academic-smoke-key-') as keydir:
        key = Path(keydir) / 'test.p12'
        env = {**os.environ, 'ACADEMIC_SMOKE_PASS': secrets.token_hex(24)}
        command('keytool', '-genkeypair', '-keystore', key, '-storetype', 'PKCS12',
                '-storepass:env', 'ACADEMIC_SMOKE_PASS', '-alias', 'smoke', '-keyalg', 'RSA',
                '-keysize', '2048', '-validity', '1', '-dname', 'CN=Disposable Readest CI smoke', env=env)
        command(paths['zipalign'], '-c', '-P', '16', '4', original)
        command(paths['apksigner'], 'sign', '--ks', key, '--ks-pass', 'env:ACADEMIC_SMOKE_PASS',
                '--out', signed, original, env=env)
        verification = command(paths['apksigner'], 'verify', '--verbose', '--print-certs', signed)
    require(sha(original.read_bytes()) == APK_SHA, 'Original unsigned bytes changed')
    require(payload(original) == payload(signed), 'Signing changed an APK payload entry')
    save('test-signature.txt', verification + '\n' + LIMITATION + '\n')
    save('apk-identity.json', {'unsignedSha256': APK_SHA, 'testSignedSha256': sha(signed.read_bytes()),
                             'payloadUnchanged': True, 'realDeliveredSigningKeyUsed': False})
    return signed


def run():
    paths = json.loads((INPUT / 'sdk.json').read_text())
    signed = sign_copy(paths)
    pdf = bounded_download(PDF_URL, 20 * 1024**2)
    require(sha(pdf) == PDF_SHA, 'Public-author HPCC fixture digest changed')
    (INPUT / 'hpcc.pdf').write_bytes(pdf)
    save('fixture.json', {'url': PDF_URL, 'sha256': PDF_SHA, 'privateUserDocument': False})
    command(paths['avdmanager'], 'create', 'avd', '--force', '--name', 'academic-smoke',
            '--package', IMAGE, '--device', 'pixel_2', timeout=30, input='no\n')
    avd = Path.home() / '.android/avd/academic-smoke.avd/config.ini'
    settings = dict(line.split('=', 1) for line in avd.read_text().splitlines() if '=' in line)
    settings.update({'hw.cpu.ncore': '2', 'hw.ramSize': '2048', 'hw.lcd.width': '720',
                     'hw.lcd.height': '1280', 'hw.lcd.density': '320', 'hw.keyboard': 'yes',
                     'hw.camera.back': 'none', 'hw.camera.front': 'none', 'disk.dataPartition.size': '1024M',
                     'showDeviceFrame': 'no', 'snapshot.present': 'no'})
    avd.write_text(''.join(f'{k}={v}\n' for k, v in settings.items()))
    cpu_set = ','.join(str(n) for n in sorted(os.sched_getaffinity(0))[:2])
    emulator_args = ['taskset', '-c', cpu_set, paths['emulator'], '-avd', 'academic-smoke',
                     '-port', '5554', '-accel', 'on', '-cores', '2', '-memory', '2048',
                     '-skin', '720x1280', '-no-window', '-no-audio', '-no-boot-anim', '-no-snapshot',
                     '-camera-back', 'none', '-camera-front', 'none', '-gpu', 'swiftshader_indirect',
                     '-prop', 'persist.sys.locale=en-US']
    with (INPUT / 'emulator.log').open('w') as log:
        emulator = subprocess.Popen(emulator_args, stdout=log, stderr=subprocess.STDOUT)
    (INPUT / 'emulator.pid').write_text(str(emulator.pid))
    boot_deadline = time.monotonic() + 240
    while time.monotonic() < boot_deadline:
        require(emulator.poll() is None, 'Emulator exited before boot')
        try:
            if adb('shell', 'getprop', 'sys.boot_completed', timeout=5, check=False).strip() == '1':
                break
        except subprocess.TimeoutExpired:
            pass
        time.sleep(2)
    else:
        raise RuntimeError('Emulator failed the 4 minute boot deadline')
    abi = adb('shell', 'getprop', 'ro.product.cpu.abilist').strip()
    save('device.txt', 'ABI: ' + abi + '\nAndroid: ' + adb('shell', 'getprop', 'ro.build.version.release') +
         '\nWebView:\n' + adb('shell', 'dumpsys', 'webviewupdate') + '\n' + LIMITATION)
    require('arm64-v8a' in abi.split(','), 'Image lacks required ARM64 native bridge; no alternate image attempted')
    adb('shell', 'input', 'keyevent', '82')
    adb('logcat', '-c')
    save('install.txt', adb('install', '--no-streaming', signed, timeout=60))
    save('launch.txt', adb('shell', 'am', 'start', '-W', '-n', APP_ID + '/com.bilingify.readest.MainActivity', timeout=30))
    pid = adb('shell', 'pidof', APP_ID, check=False).strip()
    require(re.fullmatch(r'\d+', pid) is not None, 'App has no live process after launch')
    (INPUT / 'app.pid').write_text(pid)
    save('result.json', {'status': 'launched; reader acceptance pending', 'readerAcceptance': False,
                         'limitation': LIMITATION})
    command(sys.executable, Path(__file__).with_name('academic-android-smoke-ui.py'), timeout=190)


def finish():
    EVIDENCE.mkdir(exist_ok=True)
    found_crash = False
    if (INPUT / 'sdk.json').exists():
        try:
            pidfile = INPUT / 'app.pid'
            pids = set(pidfile.read_text().split() if pidfile.exists() else [])
            pids.update(adb('shell', 'pidof', APP_ID, timeout=5, check=False).split())
            logs = []
            for pid in sorted(p for p in pids if p.isdigit())[:3]:
                logs.append(adb('logcat', '-d', '--pid=' + pid, '-t', '1500', timeout=5, check=False)[-150000:])
            save('own-app-logcat.txt', '\n'.join(logs) or 'No app PID was observed.\n')
            crash = adb('logcat', '-b', 'crash', '-d', '-t', '500', timeout=5, check=False)
            lines = crash.splitlines()
            indices = {j for i, line in enumerate(lines) if APP_ID in line
                       for j in range(max(0, i - 3), min(len(lines), i + 70))}
            filtered = '\n'.join(lines[i] for i in sorted(indices))
            save('own-app-crash.txt', filtered or 'No own-app crash record found in the bounded crash buffer.\n')
            save('own-app-exit-info.txt', adb('shell', 'dumpsys', 'activity', 'exit-info', APP_ID, timeout=5, check=False)[-12000:])
            if filtered and (EVIDENCE / 'result.json').exists():
                found_crash = True
                result = json.loads((EVIDENCE / 'result.json').read_text())
                result.update(status='app crash observed', readerAcceptance=False)
                save('result.json', result)
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            save('cleanup.txt', str(error))
        finally:
            try:
                adb('emu', 'kill', timeout=8, check=False)
            except subprocess.TimeoutExpired:
                save('cleanup.txt', 'Emulator stop timed out; the hosted job remains bounded to 20 minutes.\n')
    log = INPUT / 'emulator.log'
    if log.exists():
        with log.open('rb') as stream:
            stream.seek(max(0, log.stat().st_size - 24000))
            save('emulator-tail.txt', stream.read().decode(errors='replace'))
    if not (EVIDENCE / 'result.json').exists():
        save('result.json', {'status': 'blocked before app launch; see step logs/blocker.txt',
                             'readerAcceptance': False, 'limitation': LIMITATION})
    require(not found_crash, 'Own-app crash found in the clean emulator crash buffer')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=['verify', 'preflight', 'image', 'run', 'finish'])
    step = parser.parse_args().step
    try:
        {'verify': verify, 'preflight': preflight, 'image': install_image, 'run': run, 'finish': finish}[step]()
    except Exception as error:
        save('blocker.txt', f'{step}: {error}\n')
        print(f'::error::{step}: {error}', file=sys.stderr)
        sys.exit(1)
