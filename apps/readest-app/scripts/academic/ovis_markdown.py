"""Content-independent Ovis block grouping; never correct recognized words/math."""
import re
from collections import Counter

IMAGE = re.compile(r'<img\s+src="images/bbox_(\d+)_(\d+)_(\d+)_(\d+)\.jpg"\s*/?>')
CAPTION = re.compile(r'^(?:Figure\s+|Fig\.\s*|图\s*)(\d+)[.:：\s]', re.I)
MARKER = re.compile(r'\$\s*\^\{(\d+|\\dagger|\\ddagger|\*)\}\s*\$')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')


def without_code(text):
    """Mask code without shifting offsets, for reference/image detection only."""
    masked = list(text)

    def mask(start, end):
        for offset in range(start, end):
            if text[offset] not in '\r\n':
                masked[offset] = ' '

    index = 0
    while index < len(text):
        end = None
        if index == 0 or text[index - 1] == '\n':
            line_end = text.find('\n', index)
            line_end = len(text) if line_end < 0 else line_end + 1
            line = text[index:line_end]
            fence = FENCE.match(line)
            if fence:
                closing = re.compile(r'^ {0,3}' + re.escape(fence[1][0]) +
                                     '{' + str(len(fence[1])) + r',}[ \t]*\r?$', re.M)
                match = closing.search(text, line_end)
                end = match.end() if match else len(text)
            elif line.startswith(('    ', '\t')):
                end = line_end
        if end is None and text[index] == '`':
            run = re.match(r'`+', text[index:])[0]
            closing = re.compile(r'(?<!`)' + re.escape(run) + r'(?!`)')
            match = closing.search(text, index + len(run))
            if match:
                end = match.end()
            else:
                index += len(run)
                continue
        if end is None and text[index] == '<':
            opening = re.match(r'<(pre|code)\b[^>]*>', text[index:], re.I)
            if opening:
                closing = re.compile(r'</' + opening[1] + r'\s*>', re.I)
                match = closing.search(text, index + opening.end())
                end = match.end() if match else len(text)
        if end is not None:
            mask(index, end)
            index = end
        else:
            index += 1
    return ''.join(masked)


def parse_blocks(markdown):
    # Paragraph separators inside code, display math and tables are content.
    chunks, current = [], []
    display, table, fence, html_code_depth = False, False, None, 0
    for line, visible_line in zip(markdown.splitlines(), without_code(markdown).splitlines()):
        if not line.strip() and not display and not table and not fence and not html_code_depth:
            if current:
                chunks.append('\n'.join(current))
                current = []
            continue
        current.append(line)
        match = FENCE.match(line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not line[match.end():].strip():
                fence = None
            continue
        # HTML code contents cannot open Markdown fences, tables or math.
        if html_code_depth:
            for tag in re.findall(r'</?(?:pre|code)\b[^>]*>', line, re.I):
                html_code_depth = max(0, html_code_depth + (-1 if tag.startswith('</') else 1))
            continue
        if match:
            fence = match[1]
            continue
        if line.startswith(('    ', '\t')) and not display and not table and not html_code_depth:
            continue
        html_tags = re.findall(r'</?(?:pre|code)\b[^>]*>',
                               re.sub(r'(`+)([\s\S]*?)\1', '', line), re.I)
        for tag in html_tags:
            html_code_depth = max(0, html_code_depth + (-1 if tag.startswith('</') else 1))
        if html_code_depth:
            continue
        if visible_line.count('$$') % 2:
            display = not display
        if visible_line.strip() == r'\[':
            display = True
        if visible_line.strip() == r'\]':
            display = False
        if '<table' in visible_line.lower():
            table = True
        if '</table>' in visible_line.lower():
            table = False
    if current:
        chunks.append('\n'.join(current))
    blocks = []
    for index, text in enumerate(chunks):
        code = FENCE.match(text) or text.startswith(('    ', '\t'))
        image = None if code else IMAGE.fullmatch(text.strip())
        visible = without_code(text)
        if not image and re.search(r'<img\b|!\[', visible, re.I):
            raise ValueError('Image geometry is missing or unsupported; expected a standalone Ovis bbox image')
        kind = ('image' if image else 'code' if code else
                'table' if text.lstrip().startswith('<table') else
                'math' if text.lstrip().startswith(('$$', r'\[')) else
                'heading' if re.match(r'^#{1,6}\s', text) else 'text')
        block = {'id': f'b{index}', 'kind': kind, 'markdown': text}
        if image:
            bounds = [int(value) for value in image.groups()]
            left, top, right, bottom = bounds
            if not (0 <= left < right <= 1000 and 0 <= top < bottom <= 1000):
                raise ValueError('Image bounds must be positive and inside the 0–1000 Ovis page')
            block['bbox'] = bounds
        blocks.append(block)
    return blocks


def note_marker(block):
    match = MARKER.match(block['markdown']) if block['kind'] == 'text' else None
    return match[1] if match else None


def is_label(block):
    text = block['markdown']
    return (block['kind'] == 'text' and not CAPTION.match(text) and len(text.split()) <= 12
            and len(text) <= 100 and not re.search(r'[.!?。！？;:]\s*$', text) and '\n' not in text)


def adapt_blocks(blocks):
    definitions = Counter(note_marker(block) for block in blocks if note_marker(block))
    references = set()
    for block in blocks:
        if not note_marker(block):
            references.update(MARKER.findall(without_code(block['markdown'])))
    notes, body = [], []
    for block in blocks:
        marker = note_marker(block)
        content = MARKER.sub('', block['markdown'], count=1).lstrip() if marker else ''
        if marker and definitions[marker] == 1 and marker in references and content:
            notes.append({**block, 'kind': 'footnote', 'marker': marker, 'content': content})
        else:
            body.append(block)
    grouped, index = [], 0
    while index < len(body):
        # A short paragraph before an image is not evidence of a figure label.
        # Keep it visible in reading order rather than hiding prose in details.
        if body[index]['kind'] != 'image':
            grouped.append(body[index])
            index += 1
            continue
        pending = []
        while index < len(body) and (body[index]['kind'] == 'image' or is_label(body[index])):
            pending.append(body[index])
            index += 1
        if (any(block['kind'] == 'image' for block in pending) and index < len(body)
                and CAPTION.match(body[index]['markdown'])):
            caption = body[index]
            grouped.append({
                'id': pending[0]['id'], 'kind': 'figure',
                'images': [block for block in pending if block['kind'] == 'image'],
                'labels': [block['markdown'] for block in pending if block['kind'] != 'image'],
                'caption': caption['markdown'], 'number': CAPTION.match(caption['markdown'])[1],
                'source_ids': [block['id'] for block in pending] + [caption['id']],
            })
            index += 1
        else:
            grouped.extend(pending)
            if index < len(body):
                grouped.append(body[index])
                index += 1
    return {'blocks': grouped, 'notes': notes}


def figure_region(page, figure):
    """Union model panels in PDF points, with relative padding capped by captions."""
    import fitz
    boxes = [image['bbox'] for image in figure['images']]
    bounds = [min(box[0] for box in boxes), min(box[1] for box in boxes),
              max(box[2] for box in boxes), max(box[3] for box in boxes)]
    region = fitz.Rect(bounds[0] * page.rect.width / 1000, bounds[1] * page.rect.height / 1000,
                       bounds[2] * page.rect.width / 1000, bounds[3] * page.rect.height / 1000)
    padding = min(page.rect.width, page.rect.height) * .025
    crop = fitz.Rect(region.x0 - padding, region.y0 - padding,
                     region.x1 + padding, region.y1 + padding) & page.rect
    pattern = re.compile(r'^(?:Figure\s+|Fig\.\s*|图\s*)' + re.escape(figure['number']) + r'[.:：\s]', re.I)
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            text = ''.join(span['text'] for span in line['spans']).strip()
            bounds = line['bbox']
            if (pattern.match(text) and bounds[1] >= region.y1 + 2
                    and bounds[0] < crop.x1 and bounds[2] > crop.x0):
                crop.y1 = min(crop.y1, bounds[1] - 2)
    return crop
