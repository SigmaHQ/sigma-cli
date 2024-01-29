import click
import sys
import requests
from packaging.version import Version

try:
    import sigma.parser.base

    click.echo(
        click.style("ERROR:", bold=True, fg="red")
        + click.style(
            " the legacy 'sigmatools' package is installed in the same Python environment as Sigma CLI and pySigma. This can cause unexpected errors!",
            fg="red",
        )
    )
    click.echo(
        click.style(
            "Please uninstall 'sigmatools' from this Python environment!", fg="red"
        )
    )
    click.echo(
        click.style(
            "It is strogly recommended to install Sigma CLI with pipx (https://pypa.github.io/pipx/) to ensure a clean environment.",
            fg="green",
        )
    )
    sys.exit(100)
except ImportError:
    pass

import importlib.metadata as metadata
from .list import list_group
from .convert import convert
from .check import check
from .plugin import plugin_group
from .analyze import analyze_group
from .pysigma import check_pysigma_command


@click.group()
def cli():
    pass


@click.command()
def version():
    """Print version of Sigma CLI."""
    try:
        data = requests.get("https://pypi.org/pypi/sigma-cli/json").json()
        versions = list(data["releases"].keys())
        versions.sort(key=Version, reverse=True)
        last_version = versions[0]
    except:
        last_version = "0.0.0"

    current_version = metadata.version("sigma-cli")
    if last_version == "0.0.0":
        click.echo(current_version)
    else:
        color = "green" if last_version == current_version else "red"
        click.echo(
            f"{current_version} (online pypi.org: "
            + click.style(last_version, bold=True, fg=color)
            + ")"
        )


def main():
    cli.add_command(analyze_group)
    cli.add_command(plugin_group)
    cli.add_command(list_group)
    cli.add_command(convert)
    cli.add_command(check)
    cli.add_command(check_pysigma_command)
    cli.add_command(version)
    cli()


if __name__ == "__main__":
    main()
