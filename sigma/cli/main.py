import imp
import click
import pkg_resources
from .list import list_group
from .convert import convert
from .check import check
from .plugin import plugin_group
from .analyze import analyze_group

@click.group()
def cli():
    pass

@click.command()
def version():
    """Print version of Sigma CLI."""
    click.echo(pkg_resources.get_distribution("sigma-cli").version)

def main():
    cli.add_command(analyze_group)
    cli.add_command(plugin_group)
    cli.add_command(list_group)
    cli.add_command(convert)
    cli.add_command(check)
    cli.add_command(version)
    cli()


if __name__ == "__main__":
    main()
