"""Tests for template variable parameters in convert and analyze commands."""

import pathlib
from click.testing import CliRunner
from sigma.cli.convert import convert
from sigma.cli.analyze import analyze_group
import tempfile


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
