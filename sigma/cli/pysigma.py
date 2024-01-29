import importlib.metadata
import subprocess
import sys
import click
from packaging.specifiers import SpecifierSet

def get_pysigma_requirement():
    requires = importlib.metadata.requires("sigma-cli")
    return [
        r
        for r in requires
        if r.startswith("pysigma ")
        ][0]

def check_pysigma_version():
    """Check if the installed version of pysigma is compatible with the version required by sigma-cli."""
    requires_pysgima = get_pysigma_requirement()
    version_specifier = SpecifierSet(requires_pysgima.split(" ")[1][1:-1])
    return importlib.metadata.version("pysigma") in version_specifier

@click.command(
    name="check-pysigma",
    help="Check if the installed version of pysigma is compatible with the version required by sigma-cli."
)
@click.option(
    "--quiet/--no-quiet",
    "-q/-Q",
    default=False,
    help="Suppress output if check passes.",
)
def check_pysigma_command(quiet):
    check_pysigma(quiet)

def check_pysigma(quiet=False):
    """Check the version of pySigma against the required version of sigma-cli and reinstall on user prompt if
    necessary."""
    if check_pysigma_version():
        if not quiet:
            click.echo(click.style("pySigma version is compatible with sigma-cli", fg="green"))
    else:
        click.echo(click.style("The currently installed pySigma version is not compatible with sigma-cli!", fg="red"))
        click.echo(click.style("Installed pySigma version: ", fg="yellow") + click.style(importlib.metadata.version("pysigma"), bold=True, fg="yellow"))
        click.echo(click.style("Required pySigma version: ", fg="yellow") + click.style(get_pysigma_requirement(), bold=True, fg="yellow"))
        click.echo("Usually the reason for this is that a backend with a different required pySigma version was installed.")
        click.echo("Because pySigma development aims to keep the API stable, it is likely that the backend is still working with the pySigma version required by sigma-cli.")
        click.echo("You have now two options:")
        click.echo("✅ Reinstall pySigma to match the pySigma version required by the CLI. This can break the functionality of the backend!")
        click.echo("❌ Ignore this warning and continue using the CLI. This can lead to unexpected behaviour or break other plugins that rely on current features.")
        if click.confirm("Do you want to reinstall pySigma now?"):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--upgrade",
                    "--force-reinstall",
                    get_pysigma_requirement(),
                ]
            )
            click.echo("pySigma successfully reinstalled")
        else:
            click.echo("Incompatible pySigma version was keeped. You can rerun the check with: " + click.style("sigma check-pysigma", fg="green"))