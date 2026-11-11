"""Tests for template variable parameters in convert and analyze commands."""

import pathlib
from click.testing import CliRunner
from sigma.cli.convert import convert
from sigma.cli.analyze import analyze_group
import tempfile
from sigma.exceptions import SigmaError


def test_convert_enable_template_vars_flag():
    """Test that --enable-template-vars flag is accepted by convert command."""
    cli = CliRunner()
    result = cli.invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "--enable-template-vars",
            "tests/files/valid",
        ],
    )
    # Command should succeed (exit code 0) or fail with a validation error, 
    # not with an unrecognized option error
    assert "--enable-template-vars" not in result.output
    assert "Error: no such option" not in result.output.lower()


def test_convert_template_vars_path_option():
    """Test that --template-vars-path option is accepted by convert command."""
    cli = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        result = cli.invoke(
            convert,
            [
                "-t",
                "text_query_test",
                "-p",
                "another_test",
                "--disable-pipeline-check",
                "--template-vars-path",
                tmpdir,
                "tests/files/valid",
            ],
        )
        # Command should succeed or fail with validation error, not option error
        assert "--template-vars-path" not in result.output
        assert "Error: no such option" not in result.output.lower()


def test_convert_multiple_template_vars_paths():
    """Test that multiple --template-vars-path options can be specified."""
    cli = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir1:
        with tempfile.TemporaryDirectory() as tmpdir2:
            result = cli.invoke(
                convert,
                [
                    "-t",
                    "text_query_test",
                    "-p",
                    "another_test",
                    "--disable-pipeline-check",
                    "--template-vars-path",
                    tmpdir1,
                    "--template-vars-path",
                    tmpdir2,
                    "tests/files/valid",
                ],
            )
            # Command should accept multiple paths without error
            assert "--template-vars-path" not in result.output
            assert "Error: no such option" not in result.output.lower()


def test_analyze_fields_enable_template_vars_flag():
    """Test that --enable-template-vars flag is accepted by analyze fields command."""
    cli = CliRunner()
    result = cli.invoke(
        analyze_group,
        [
            "fields",
            "-t",
            "text_query_test",
            "-p",
            "another_test",
            "--disable-pipeline-check",
            "--enable-template-vars",
            "tests/files/valid",
        ],
    )
    # Command should work without unrecognized option error
    assert "--enable-template-vars" not in result.output
    assert "Error: no such option" not in result.output.lower()


def test_analyze_fields_template_vars_path_option():
    """Test that --template-vars-path option is accepted by analyze fields command."""
    cli = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        result = cli.invoke(
            analyze_group,
            [
                "fields",
                "-t",
                "text_query_test",
                "-p",
                "another_test",
                "--disable-pipeline-check",
                "--template-vars-path",
                tmpdir,
                "tests/files/valid",
            ],
        )
        # Command should accept the path without error
        assert "--template-vars-path" not in result.output
        assert "Error: no such option" not in result.output.lower()


def _write_vars_pipeline(tmp_path):
    """Pipeline file with a template postprocessing item that uses a vars file next to it."""
    pipeline_dir = tmp_path / "pipelines"
    pipeline_dir.mkdir()
    vars_file = pipeline_dir / "helpers.py"
    vars_file.write_text("vars = {'marker': lambda q: 'VARS_OK(' + q + ')'}\n")
    pipeline_file = pipeline_dir / "vars_pipeline.yml"
    pipeline_file.write_text(
        "name: vars pipeline\n"
        "priority: 100\n"
        "postprocessing:\n"
        "  - type: template\n"
        "    template: '{{ marker(query) }}'\n"
        f"    vars: '{vars_file.as_posix()}'\n"
    )
    return pipeline_file


def _convert_with_vars_pipeline(pipeline_file, *args):
    return CliRunner().invoke(
        convert,
        [
            "-t",
            "text_query_test",
            "-p",
            str(pipeline_file),
            *args,
            "tests/files/valid/sigma_rule.yml",
        ],
    )


def test_convert_template_vars_disabled_by_default(tmp_path, monkeypatch):
    """Without --enable-template-vars the vars file is rejected with a clean error."""
    monkeypatch.delenv("PYSIGMA_ALLOW_VARS_EXECUTION", raising=False)
    result = _convert_with_vars_pipeline(_write_vars_pipeline(tmp_path))
    assert result.exit_code == 2
    assert "disabled by default" in result.output
    assert not isinstance(result.exception, SigmaError)


def test_convert_enable_template_vars_is_applied(tmp_path, monkeypatch):
    """--enable-template-vars enables the vars file of a pipeline loaded from a file."""
    monkeypatch.delenv("PYSIGMA_ALLOW_VARS_EXECUTION", raising=False)
    result = _convert_with_vars_pipeline(
        _write_vars_pipeline(tmp_path), "--enable-template-vars"
    )
    assert result.exit_code == 0, result.output
    assert "VARS_OK(" in result.stdout


def test_convert_template_vars_path_is_applied(tmp_path, monkeypatch):
    """--template-vars-path restricts the directories vars files may be loaded from."""
    monkeypatch.delenv("PYSIGMA_ALLOW_VARS_EXECUTION", raising=False)
    pipeline_file = _write_vars_pipeline(tmp_path)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    result = _convert_with_vars_pipeline(
        pipeline_file, "--enable-template-vars", "--template-vars-path", str(other_dir)
    )
    assert result.exit_code == 2
    assert "outside the allowed base directories" in result.output

    result = _convert_with_vars_pipeline(
        pipeline_file,
        "--enable-template-vars",
        "--template-vars-path",
        str(pipeline_file.parent),
    )
    assert result.exit_code == 0, result.output
    assert "VARS_OK(" in result.stdout


def test_convert_template_vars_path_is_applied_with_env_var(tmp_path, monkeypatch):
    """--template-vars-path also restricts vars files when enabled by environment variable."""
    monkeypatch.setenv("PYSIGMA_ALLOW_VARS_EXECUTION", "1")
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    result = _convert_with_vars_pipeline(
        _write_vars_pipeline(tmp_path), "--template-vars-path", str(other_dir)
    )
    assert result.exit_code == 2
    assert "outside the allowed base directories" in result.output


def test_analyze_fields_enable_template_vars_is_applied(tmp_path, monkeypatch):
    """--enable-template-vars is applied by analyze fields, and without it the error is clean."""
    monkeypatch.delenv("PYSIGMA_ALLOW_VARS_EXECUTION", raising=False)
    pipeline_file = _write_vars_pipeline(tmp_path)
    args = ["fields", "-t", "text_query_test", "-p", str(pipeline_file)]
    result = CliRunner().invoke(analyze_group, [*args, "tests/files/valid/sigma_rule.yml"])
    assert result.exit_code == 2
    assert "disabled by default" in result.output

    result = CliRunner().invoke(
        analyze_group, [*args, "--enable-template-vars", "tests/files/valid/sigma_rule.yml"]
    )
    assert result.exit_code == 0, result.output
