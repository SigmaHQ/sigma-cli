import imp
import click
from .list import list_group
from .convert import convert
from .check import check

@click.group()
def cli():
    pass

def main():
    cli.add_command(list_group)
    cli.add_command(convert)
    cli.add_command(check)
    cli()