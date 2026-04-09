from pathlib import Path

from text2pdf import cli, imagegen


def test_build_parser_supports_no_toc_flag():
    parser = cli.build_parser()
    args = parser.parse_args(['convert', 'input.txt', '--no-toc'])

    assert args.toc is False



def test_process_image_directives_rewrites_to_local_markdown(tmp_path, monkeypatch):
    generated_path = tmp_path / 'assets' / 'image_001.png'

    def fake_generate(request):
        generated_path.parent.mkdir(parents=True, exist_ok=True)
        generated_path.write_bytes(b'png')
        return imagegen.GeneratedImageResult(
            path=generated_path,
            provider='gemini',
            model='gemini-2.5-flash-image',
            mime_type='image/png',
            response={'ok': True},
        )

    monkeypatch.setattr(imagegen, 'generate_image', fake_generate)
    defaults = imagegen.ImageGenerationRequest(
        prompt='',
        output_path=tmp_path / 'assets' / 'generated',
        provider='gemini',
    )

    rewritten, results = imagegen.process_image_directives(
        'Intro\n[[image: A fjord at sunrise | alt=Cover art | aspect=16:9]]\nDone',
        defaults=defaults,
        output_dir=tmp_path / 'assets',
        relative_to=tmp_path,
    )

    assert rewritten == 'Intro\n![Cover art](assets/image_001.png)\nDone'
    assert len(results) == 1
    assert results[0].path == generated_path



def test_cmd_image_uses_prompt_file(tmp_path, monkeypatch):
    prompt_file = tmp_path / 'prompt.txt'
    prompt_file.write_text('A clean product mockup', encoding='utf-8')
    output_file = tmp_path / 'output.png'
    captured = {}

    def fake_generate(request):
        captured['request'] = request
        output_file.write_bytes(b'png')
        return imagegen.GeneratedImageResult(
            path=output_file,
            provider='gemini',
            model='gemini-2.5-flash-image',
            mime_type='image/png',
            response={'ok': True},
        )

    monkeypatch.setattr(imagegen, 'generate_image', fake_generate)
    args = cli.build_parser().parse_args(
        ['image', '--prompt-file', str(prompt_file), '-o', str(output_file)]
    )

    assert cli.cmd_image(args) == 0
    assert captured['request'].prompt == 'A clean product mockup'
    assert captured['request'].output_path == output_file
