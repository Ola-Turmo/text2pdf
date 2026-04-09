from pathlib import Path

import pytest

from text2pdf import structure


def test_convert_to_html_preserves_block_order():
    text = '# Title\n\nFirst paragraph.\n\n## Section\n\n- Item 1\n- Item 2\n\nSecond paragraph.\n'
    html = structure.convert_to_html(text, {'toc': False})
    body = html.split('<body>\n', 1)[1].split('\n</body>', 1)[0]

    heading_index = body.index('<h1 id="title">Title</h1>')
    first_paragraph_index = body.index('<p>First paragraph.</p>')
    section_index = body.index('<h2 id="section">Section</h2>')
    list_index = body.index('<ul><li>Item 1</li><li>Item 2</li></ul>')
    second_paragraph_index = body.index('<p>Second paragraph.</p>')

    assert heading_index < first_paragraph_index < section_index < list_index < second_paragraph_index



def test_fenced_code_block_is_detected():
    text = '```python\nprint(1)\n```\n'
    structure_data = structure.detect_structure(text)

    assert structure_data['code_blocks'] == [{'lang': 'python', 'code': 'print(1)'}]
    assert structure_data['paragraphs'] == []



def test_embed_images_rewrites_remote_image_sources(monkeypatch):
    monkeypatch.setattr(structure, '_download_image', lambda url, image_dir: 'assets/local-image.png')

    html = structure.convert_to_html(
        '![Alt text](https://example.com/image.png)',
        {'toc': False, 'embed_images': True, 'image_dir': 'assets'},
    )

    assert '<img src="assets/local-image.png" alt="Alt text">' in html



def test_running_footer_uses_css_counters():
    footer = structure._build_running_footer('Page {page} of {pages}')

    assert 'counter(page)' in footer
    assert 'counter(pages)' in footer
    assert '"Page "' in footer
