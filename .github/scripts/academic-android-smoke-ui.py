#!/usr/bin/env python3
"""Public HPCC import through Android's normal file picker, using observed nodes.

The existing repository CDP lane targets debuggable com.bilingify.readest, so it
cannot inspect this production release. Selectors below mirror LibraryPage.ts,
AcademicReadingButton, AcademicAppearancePanel and ZoomControls accessibility
labels, but every tap is resolved from the live Android hierarchy first.
"""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('smoke', Path(__file__).with_name('academic-android-smoke.py'))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
PICKERS = {'com.android.documentsui', 'com.google.android.documentsui'}


def bounds(node):
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.get('bounds', ''))
    if not match:
        return None
    x1, y1, x2, y2 = map(int, match.groups())
    return (x1, y1, x2, y2) if 0 <= x1 < x2 <= 720 and 0 <= y1 < y2 <= 1280 else None


def matches(node, labels, packages, pattern=None):
    if node.get('package') not in packages or node.get('enabled') == 'false' or not bounds(node):
        return False
    values = [node.get('text', ''), node.get('content-desc', '')]
    return any(v in labels or (pattern and re.fullmatch(pattern, v)) for v in values)


class UI:
    def __init__(self):
        self.deadline = time.monotonic() + 175
        self.steps = []
        self.tree = None

    def remaining(self):
        smoke.require(time.monotonic() < self.deadline, 'UI smoke exceeded its bounded observation window')
        return max(1, min(12, self.deadline - time.monotonic()))

    def dump(self):
        smoke.adb('shell', 'uiautomator', 'dump', '/sdcard/smoke-window.xml', timeout=self.remaining())
        xml = smoke.adb('shell', 'cat', '/sdcard/smoke-window.xml', timeout=self.remaining())
        self.tree = ET.fromstring(xml[xml.index('<hierarchy'):])
        (smoke.EVIDENCE / 'last-hierarchy.xml').write_text(xml)
        return self.tree

    def capture(self, name):
        self.dump()
        (smoke.EVIDENCE / (name + '.xml')).write_bytes(ET.tostring(self.tree))
        paths = json.loads((smoke.INPUT / 'sdk.json').read_text())
        screenshot = subprocess.run([paths['adb'], '-s', 'emulator-5554', 'exec-out', 'screencap', '-p'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=self.remaining(), check=True).stdout
        smoke.require(screenshot.startswith(b'\x89PNG') and len(screenshot) < 4 * 1024**2,
                      'Unexpected screenshot format or size')
        (smoke.EVIDENCE / (name + '.png')).write_bytes(screenshot)

    def find(self, labels=(), packages=None, pattern=None, seconds=15, clickable=False):
        stop = min(self.deadline, time.monotonic() + seconds)
        while True:
            tree = self.dump()
            nodes = [n for n in tree.iter('node') if matches(n, labels, packages or {smoke.APP_ID}, pattern)
                     and (not clickable or n.get('clickable') == 'true')]
            if nodes:
                return nodes[0]
            if time.monotonic() >= stop:
                return None
            time.sleep(0.5)

    def tap(self, labels=(), packages=None, pattern=None, seconds=15):
        node = self.find(labels, packages, pattern, seconds)
        smoke.require(node is not None, f'Expected UI selector unavailable: {labels or pattern}')
        x1, y1, x2, y2 = bounds(node)
        smoke.adb('shell', 'input', 'tap', str((x1 + x2) // 2), str((y1 + y2) // 2), timeout=self.remaining())
        self.steps.append({'tap': node.get('content-desc') or node.get('text'),
                           'package': node.get('package'), 'bounds': node.get('bounds')})

    def night(self, mode, name):
        smoke.adb('shell', 'cmd', 'uimode', 'night', mode, timeout=self.remaining())
        time.sleep(1)
        smoke.save(name + '-uimode.txt', smoke.adb('shell', 'cmd', 'uimode', 'night') + '\n' +
                   smoke.adb('shell', 'dumpsys', 'uimode'))
        self.capture(name)

    def run(self):
        self.capture('01-launch')
        self.night('yes', '02-launch-system-dark')
        self.night('no', '03-launch-system-light')
        # Only decline the application's known telemetry dialog; never accept
        # permissions, account setup, update, security or unrelated dialogs.
        if self.find(['Help improve Readest'], seconds=0) is not None:
            self.tap(['Not now'])
        smoke.adb('push', smoke.INPUT / 'hpcc.pdf', '/sdcard/Download/hpcc.pdf')
        smoke.adb('shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                  '-d', 'file:///sdcard/Download/hpcc.pdf', check=False)
        self.tap(['Import Books'])
        self.tap(['From Local File'])
        self.capture('04-file-picker')
        if self.find(['hpcc.pdf'], packages=PICKERS, seconds=0) is None:
            self.tap(['Show roots', 'Open navigation drawer'], packages=PICKERS)
            self.tap(['Downloads'], packages=PICKERS)
        self.tap(['hpcc.pdf'], packages=PICKERS)
        # The single-document SAF picker usually returns immediately. Some
        # versions expose an Open confirmation, only inside DocumentsUI.
        if self.find(['Open', 'OPEN'], packages=PICKERS, seconds=0) is not None:
            self.tap(['Open', 'OPEN'], packages=PICKERS)
        self.capture('05-import-return')
        if self.find(['PDF / Reading'], seconds=1) is None:
            card = self.find(pattern=r'(?:HPCC:.*|hpcc(?:\.pdf)?)', seconds=20)
            if card is not None:
                self.tap(pattern=r'(?:HPCC:.*|hpcc(?:\.pdf)?)', seconds=0)
        if self.find(['PDF / Reading'], seconds=1) is None:
            # The repository ReaderPage.revealHeader clicks the viewer's top
            # strip. Resolve its actual accessible bounds instead of guessing.
            content = self.find(['Book Content'], seconds=10)
            smoke.require(content is not None, 'Imported document or reader header could not be verified')
            x1, y1, x2, _ = bounds(content)
            smoke.adb('shell', 'input', 'tap', str((x1 + x2) // 2), str(y1 + 4))
        self.tap(['PDF / Reading'])
        smoke.require(self.find(['Reading appearance'], seconds=40) is not None,
                      'Reading parser did not expose the appearance control')
        self.capture('06-reading')
        self.night('yes', '07-reading-system-dark')
        self.night('no', '08-reading-system-light')
        self.tap(['Reading appearance'])
        smoke.require(self.find(['Font Size'], seconds=5) is not None, 'Aa panel did not open')
        self.capture('09-appearance')
        self.tap(['Close'])
        figure = None
        for _ in range(6):
            figure = self.find(['Figure: Tap to zoom'], seconds=0)
            if figure is not None:
                break
            container = self.find(['Academic Reading Mode'], seconds=0)
            smoke.require(container is not None, 'Reading dialog disappeared while finding a figure')
            x1, y1, x2, y2 = bounds(container)
            x = (x1 + x2) // 2
            smoke.adb('shell', 'input', 'swipe', str(x), str(y1 + (y2-y1)*4//5),
                      str(x), str(y1 + (y2-y1)*2//5), '400')
        smoke.require(figure is not None, 'No figure found within six observed reader swipes; acceptance incomplete')
        self.tap(['Figure: Tap to zoom'], seconds=0)
        smoke.require(self.find(['Image viewer'], seconds=15) is not None, 'Figure viewer did not open')
        self.capture('10-figure-viewer')
        self.tap(['Zoom In'])
        self.capture('11-figure-zoomed')
        self.tap(['Close'])
        smoke.require(self.find(['Reading appearance'], seconds=5) is not None, 'Figure close did not restore reading')
        self.capture('12-reader-restored')
        smoke.save('result.json', {'status': 'public PDF / Reading / Aa / figure smoke exercised',
                                  'readerAcceptance': False, 'uiFlowCompleted': True,
                                  'visualReviewRequired': True, 'systemThemeEvidenceCaptured': True,
                                  'limitation': smoke.LIMITATION,
                                  'note': 'Review screenshots for layout and theme correctness; selectors alone cannot establish visual acceptance.'})


if __name__ == '__main__':
    ui = UI()
    try:
        ui.run()
    except Exception as error:
        try:
            # Preserve a final screenshot even when the UI deadline expired.
            ui.deadline = time.monotonic() + 10
            ui.capture('incomplete-ui')
        except Exception:
            pass
        smoke.save('result.json', {'status': 'launch succeeded; reader smoke incomplete',
                                  'readerAcceptance': False, 'uiFlowCompleted': False,
                                  'blocker': str(error), 'limitation': smoke.LIMITATION})
        raise
    finally:
        smoke.save('ui-actions.json', ui.steps)
