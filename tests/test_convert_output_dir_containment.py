"""--output-dir must never write outside the output directory."""

import pathlib

import pytest
from click.testing import CliRunner

from sigma.cli.convert import (
    contained_output_path,
    convert,
    render_output_filename,
    safe_filename,
)
import sigma.backends.test.backend  # noqa: F401  (registers text_query_test)

RULE = """title: {title}
{idline}logsource:
  category: test
detection:
  sel:
    fieldA: {value}
  condition: sel
"""


def files_under(p: pathlib.Path):
    return sorted(x.relative_to(p).as_posix() for x in p.rglob("*") if x.is_file())


@pytest.mark.parametrize(
    "title",
    [
        "../../escaped/pwned",
        "../escaped",
        "/tmp/absolute/pwned",
        "a/../../b",
        "..",
    ],
)
def test_stdin_rule_title_cannot_escape_output_dir(tmp_path, monkeypatch, title):
    work = tmp_path / "victim" / "project"
    work.mkdir(parents=True)
    monkeypatch.chdir(work)
    result = CliRunner().invoke(
        convert,
        ["-t", "text_query_test", "-od", "out", "-ot", "{path}/{stem}.txt", "-"],
        input=RULE.format(title=f'"{title}"', idline="", value="content"),
    )
    assert result.exit_code == 0, result.output
    # the only file written anywhere below tmp_path is inside ./out, in its top level
    written = files_under(tmp_path)
    assert len(written) == 1
    assert written[0].startswith("victim/project/out/")
    assert "/" not in written[0][len("victim/project/out/") :]


def test_stdin_rule_with_id_uses_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rule_id = "5013332f-8a70-4e04-bcc1-06a98a2cca2e"
    result = CliRunner().invoke(
        convert,
        ["-t", "text_query_test", "-od", "out", "-"],
        input=RULE.format(title="t", idline=f"id: {rule_id}\n", value="v"),
    )
    assert result.exit_code == 0, result.output
    assert files_under(tmp_path / "out") == [f"{rule_id}.txt"]


def test_second_input_outside_first_input_dir_stays_inside(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    (proj / "rules").mkdir(parents=True)
    (tmp_path / "extra").mkdir()
    (proj / "rules" / "a.yml").write_text(RULE.format(title="A", idline="", value="a"))
    (tmp_path / "extra" / "b.yml").write_text(
        RULE.format(title="B", idline="", value="b")
    )
    monkeypatch.chdir(proj)
    result = CliRunner().invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-od",
            "out",
            "-ot",
            "{path}/{stem}.txt",
            "rules",
            "../extra",
        ],
    )
    assert result.exit_code == 0, result.output
    assert not (proj / "extra").exists()
    assert files_under(tmp_path) == [
        "extra/b.yml",
        "proj/out/a.txt",
        "proj/out/extra/b.txt",
        "proj/rules/a.yml",
    ]


def test_template_escaping_output_dir_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "a.yml").write_text(
        RULE.format(title="A", idline="", value="a")
    )
    result = CliRunner().invoke(
        convert,
        ["-t", "text_query_test", "-od", "out", "-ot", "../{stem}.txt", "rules"],
    )
    assert result.exit_code != 0
    assert "Refusing to write output file" in result.output
    assert not (tmp_path / "a.txt").exists()


def test_render_output_filename_fallback_drops_anchor_and_dotdot(tmp_path):
    base = tmp_path / "rules"
    assert render_output_filename(
        "{path}/{stem}.txt", pathlib.Path("../extra/b.yml"), base
    ) == pathlib.Path("extra/b.txt")
    abs_rule = tmp_path / "elsewhere" / "c.yml"
    rendered = render_output_filename("{path}/{stem}.txt", abs_rule, base)
    assert not rendered.is_absolute()
    assert ".." not in rendered.parts
    assert rendered.parts[-2:] == ("elsewhere", "c.txt")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Suspicious Logon", "Suspicious Logon"),
        ("../../x", ".._.._x"),
        ("a\\b", "a_b"),
        ("C:evil", "C_evil"),
    ],
)
def test_safe_filename(name, expected):
    assert safe_filename(name) == expected


@pytest.mark.parametrize("name", ["", ".", "..", "  "])
def test_safe_filename_never_special(name):
    result = safe_filename(name)
    assert result not in ("", ".", "..")
    assert len(pathlib.Path(result).parts) == 1


@pytest.mark.parametrize("rel", ["../x.txt", "a/../../x.txt", "/abs/x.txt", "", "."])
def test_contained_output_path_rejects(tmp_path, rel):
    import click

    with pytest.raises(click.ClickException):
        contained_output_path(tmp_path, pathlib.Path(rel))


def test_contained_output_path_accepts(tmp_path):
    assert (
        contained_output_path(tmp_path, pathlib.Path("a/b.txt"))
        == tmp_path / "a" / "b.txt"
    )
