import importlib.metadata
import subprocess
import sys
import os
from datetime import datetime
import click
from packaging.specifiers import SpecifierSet
from prettytable import PrettyTable

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

@click.group(
    name="pysigma",
    help="pySigma library management commands."
)
def pysigma_group():
    pass

@pysigma_group.command(
    name="check-version",
    help="Check if the installed version of pysigma is compatible with the version required by sigma-cli."
)
@click.option(
    "--quiet/--no-quiet",
    "-q/-Q",
    default=False,
    help="Suppress output if check passes.",
)
def check_version_command(quiet):
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
            click.echo("Incompatible pySigma version was keeped. You can rerun the check with: " + click.style("sigma pysigma check-version", fg="green"))


@pysigma_group.command(
    name="list-cache",
    help="List cached data versions and timestamps."
)
def list_cache_command():
    """List the cached versions of pySigma data and their timestamps."""
    try:
        from sigma.data import mitre_attack, mitre_d3fend
        
        # Configuration for datasets to check
        datasets = [
            {
                'name': 'MITRE ATT&CK',
                'module': mitre_attack,
                'cache_key': 'mitre_attack_data_default',
                'version_key': 'mitre_attack_version'
            },
            {
                'name': 'MITRE D3FEND',
                'module': mitre_d3fend,
                'cache_key': 'mitre_d3fend_data_default',
                'version_key': 'mitre_d3fend_version'
            }
        ]
        
        table = PrettyTable()
        table.field_names = ["Dataset", "Version", "Cached Date"]
        table.align = "l"
        
        for dataset in datasets:
            cache = dataset['module']._get_cache()
            
            # Check if cache directory exists and has the key
            if not os.path.exists(cache.directory) or dataset['cache_key'] not in cache:
                table.add_row([dataset['name'], "Not cached", "-"])
            else:
                # Get cached data without triggering download
                data = cache.get(dataset['cache_key'], read=True)
                version = data.get(dataset['version_key'], 'Unknown')
                
                # Get timestamp from cache files
                cache_files = [f for f in os.listdir(cache.directory) if not f.startswith('.')]
                if cache_files:
                    newest_mtime = max(os.path.getmtime(os.path.join(cache.directory, f)) for f in cache_files)
                    timestamp = datetime.fromtimestamp(newest_mtime).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = "Unknown"
                
                table.add_row([dataset['name'], version, timestamp])
        
        click.echo(table)
        
    except ImportError:
        click.echo(click.style("Error: Unable to import pySigma data modules.", fg="red"))
        click.echo("Make sure pySigma is installed correctly.")
    except Exception as e:
        click.echo(click.style(f"Error accessing cache: {str(e)}", fg="red"))


@pysigma_group.command(
    name="clear-cache",
    help="Delete all cached data."
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
def clear_cache_command(yes):
    """Delete the cached data for all datasets."""
    try:
        from sigma.data import mitre_attack, mitre_d3fend
        
        datasets = [
            {'name': 'MITRE ATT&CK', 'module': mitre_attack},
            {'name': 'MITRE D3FEND', 'module': mitre_d3fend}
        ]
        
        # Check what's cached
        cached_datasets = []
        total_size = 0
        total_entries = 0
        
        for dataset in datasets:
            cache = dataset['module']._get_cache()
            if os.path.exists(cache.directory):
                keys = list(cache.iterkeys())
                if keys:
                    size = cache.volume()
                    cached_datasets.append({
                        'name': dataset['name'],
                        'entries': len(keys),
                        'size': size
                    })
                    total_entries += len(keys)
                    total_size += size
        
        if not cached_datasets:
            click.echo(click.style("No cached data found. Nothing to clear.", fg="yellow"))
            return
        
        # Confirm deletion
        if not yes:
            for cached in cached_datasets:
                click.echo(f"{cached['name']}: {cached['entries']} entries, {cached['size']} bytes")
            click.echo(f"Total: {total_entries} entries, {total_size} bytes")
            if not click.confirm(click.style("Are you sure you want to clear all cached data?", fg="yellow")):
                click.echo("Cache clearing cancelled.")
                return
        
        # Clear all caches
        cleared_count = 0
        for dataset in datasets:
            cache = dataset['module']._get_cache()
            if os.path.exists(cache.directory):
                keys = list(cache.iterkeys())
                if keys:
                    dataset['module'].clear_cache()
                    cleared_count += 1
        
        click.echo(click.style(f"✓ Cache cleared successfully for {cleared_count} dataset(s).", fg="green"))
        click.echo(f"Removed {total_entries} cache entries ({total_size} bytes)")
        
    except ImportError:
        click.echo(click.style("Error: Unable to import pySigma data modules.", fg="red"))
        click.echo("Make sure pySigma is installed correctly.")
    except Exception as e:
        click.echo(click.style(f"Error clearing cache: {str(e)}", fg="red"))


@pysigma_group.command(
    name="update-cache",
    help="Update cache by clearing and re-caching data."
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt.",
)
def update_cache_command(yes):
    """Update the cache by deleting it and re-caching data for all datasets."""
    try:
        from sigma.data import mitre_attack, mitre_d3fend
        
        datasets = [
            {
                'name': 'MITRE ATT&CK',
                'module': mitre_attack,
                'trigger_attr': 'mitre_attack_techniques_tactics_mapping'
            },
            {
                'name': 'MITRE D3FEND',
                'module': mitre_d3fend,
                'trigger_attr': 'mitre_d3fend_techniques'
            }
        ]
        
        # Get current cache info
        cached_datasets = []
        total_size = 0
        total_entries = 0
        
        for dataset in datasets:
            cache = dataset['module']._get_cache()
            if os.path.exists(cache.directory):
                keys = list(cache.iterkeys())
                if keys:
                    size = cache.volume()
                    cached_datasets.append({
                        'name': dataset['name'],
                        'entries': len(keys),
                        'size': size
                    })
                    total_entries += len(keys)
                    total_size += size
        
        # Confirm update
        if not yes:
            if cached_datasets:
                click.echo("Current cache:")
                for cached in cached_datasets:
                    click.echo(f"  {cached['name']}: {cached['entries']} entries, {cached['size']} bytes")
                click.echo(f"Total: {total_entries} entries, {total_size} bytes")
            else:
                click.echo("No cached data found (will download fresh data)")
            
            if not click.confirm(click.style("Update cache by clearing and re-downloading data?", fg="yellow")):
                click.echo("Cache update cancelled.")
                return
        
        # Clear and update each dataset
        updated_count = 0
        new_total_size = 0
        new_total_entries = 0
        
        for dataset in datasets:
            click.echo(f"Updating {dataset['name']}...")
            
            # Clear cache
            dataset['module'].clear_cache()
            
            # Trigger re-caching by accessing data
            _ = getattr(dataset['module'], dataset['trigger_attr'])
            
            # Get new cache info
            cache = dataset['module']._get_cache()
            new_keys = list(cache.iterkeys())
            new_size = cache.volume()
            
            click.echo(click.style(f"  ✓ {dataset['name']} cached: {len(new_keys)} entries, {new_size} bytes", fg="green"))
            
            updated_count += 1
            new_total_entries += len(new_keys)
            new_total_size += new_size
        
        click.echo()
        click.echo(click.style(f"✓ Cache updated successfully for {updated_count} dataset(s).", fg="green"))
        click.echo(f"Total: {new_total_entries} entries, {new_total_size} bytes")
        
    except ImportError:
        click.echo(click.style("Error: Unable to import pySigma data modules.", fg="red"))
        click.echo("Make sure pySigma is installed correctly.")
    except Exception as e:
        click.echo(click.style(f"Error updating cache: {str(e)}", fg="red"))