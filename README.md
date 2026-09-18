# Sigma Command Line Interface

![Tests](https://github.com/SigmaHQ/sigma-cli/actions/workflows/test.yml/badge.svg)
![Coverage Badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/thomaspatzke/0c868df261d4a5d5a1dafe71b1557d69/raw/SigmaHQ-sigma-cli.json)
![Status](https://img.shields.io/badge/Status-pre--release-orange)

This is the Sigma command line interface using the [pySigma](https://github.com/SigmaHQ/pySigma) library to manage, list
and convert Sigma rules into query languages.

## Getting Started

### Installation

The easiest way to install the Sigma CLI is via *pipx* or *pip*. For this purpose run one of the following:

```
python -m pipx install sigma-cli
python -m pip install sigma-cli
```
on macOS use
```
python3 -m pip install sigma-cli
```
```
brew install sigma-cli
```

Another way is to run this from source in a virtual environment managed by [Poetry](https://python-poetry.org/docs/basic-usage/):

```
git clone https://github.com/SigmaHQ/sigma-cli.git
cd sigma-cli
poetry install
poetry shell
```

### Usage

The CLI is available as *sigma* command. A typical invocation is:

```
sigma convert -t <backend> -p <processing pipeline 1> -p <processing pipeline 2> [...] <directory or file>
```

E.g. to convert process creation Sigma rules from a directory into Splunk queries for Sysmon logs run:

```
sigma convert -t splunk -p sysmon sigma/rules/windows/process_creation
```

Required backends must be installed using the following command prior to conducting conversions.

To list all available plugins run the following command:
```
sigma plugin list
```
Install a plugin of your choice with:
```
sigma plugin install <backend>
```
E.g. to install the splunk backend run:
```
sigma plugin install splunk
```

Available conversion backends and processing pipelines can be listed with `sigma list`. 
Use `-O` or `--backend-option` for passing options to the backend as key=value pairs (`-O testparam=123`) .
This backend option parameter can be used multiple times (`-O first=123 -O second=456`).

Backends can support different output formats, e.g. plain queries and a file that can be imported into the target
system. These formats can be listed with `sigma list formats <backend>` and specified for conversion with the `-f`
option.

In addition, an output file can be specified with `-o`.

Example for output formats and files:

```
sigma convert -t splunk -f savedsearches -p sysmon -o savedsearches.conf sigma/rules/windows/process_creation
```

Outputs a Splunk savedsearches.conf containing the converted searches.

#### Separate File Output

For scenarios where you need to convert multiple rules into separate files (e.g., for version control or selective deployment),
use the `--output-dir` parameter along with `--output-filename-template`:

```
sigma convert -t esql -p ecs_windows --output-dir translated_rules/ rules/
```

This will create a separate file for each converted rule in the `translated_rules/` directory.

**Template Variables:**

The `--output-filename-template` parameter accepts the following variables:

- `{path}`: Relative source directory path (e.g., `windows` for `rules/windows/rule.yml`)
- `{stem}`: Filename without extension (e.g., `rule` for `rule.yml`)
- `{index}`: Query index for rules that generate multiple queries (empty if only one query)

**Examples:**

Flat output structure (all files in one directory):
```
sigma convert -t esql -p ecs_windows --output-dir translated/ --output-filename-template "{stem}.esql" rules/
```

Preserve directory structure:
```
sigma convert -t esql -p ecs_windows --output-dir translated/ --output-filename-template "{path}/{stem}.esql" rules/
```

Handle rules with multiple queries:
```
sigma convert -t esql -p ecs_windows --output-dir translated/ --output-filename-template "{stem}-{index}.esql" rules/
```

Given input structure:
```
rules/
├── windows/
│   └── rule_1.yml
├── linux/
│   └── rule_2.yml
```

With `--output-filename-template "{path}/{stem}.esql"`, the output will be:
```
translated/
├── windows/
│   └── rule_1.esql
├── linux/
│   └── rule_2.esql
```


### Integration of Backends and Pipelines

Sigma CLI automatically discovers installed pySigma backend and processing pipeline plugins.
Install the plugin package in the same Python environment as Sigma CLI. For plugins listed by
`sigma plugin list`, use `sigma plugin install <identifier>`.

For a custom plugin package, use the command matching your Sigma CLI installation:

```sh
# Sigma CLI installed with pip
python -m pip install <package-name>

# Sigma CLI installed with pipx
pipx inject sigma-cli <package-name>

# Sigma CLI source checkout managed by Poetry
poetry add <package-name>
```

Custom plugins provide backend classes under the `sigma.backends` namespace and processing
pipeline factories under the `sigma.pipelines` namespace. See the
[pySigma plugin guide](https://sigmahq-pysigma.readthedocs.io/en/latest/guides/plugin_system.html)
for the package layout and exports. No changes to Sigma CLI's source files are needed.

After installation, use `sigma list targets` and `sigma list pipelines` to find the identifiers
accepted by `sigma convert -t` and `-p`. Use `sigma list formats <backend>` to list the backend's
output formats for `-f`.

## Maintainers

The project is currently maintained by:

- Thomas Patzke <thomas@patzke.org>
