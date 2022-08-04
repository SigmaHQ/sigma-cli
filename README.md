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

Available conversion backends and processing pipelines can be listed with `sigma list`.

Backends can support different output formats, e.g. plain queries and a file that can be imported into the target
system. These formats can be listed with `sigma list formats <backend>` and specified for conversion with the `-f`
option.

In addition, an output file can be specified with `-o`.

Example for output formats and files:

```
sigma convert -t splunk -f savedsearches -p sysmon -o savedsearches.conf sigma/rules/windows/process_creation
```

Outputs a Splunk savedsearches.conf containing the converted searches.

### Integration of Backends and Pipelines

Backends and pipelines can be integrated by adding the corresponding packages as dependency with:

```
poetry add <package name>
```

A backend has to be added to the `backends` dict in `sigma/cli/backends.py` by creation of a `Backend` named tuple with
the following parameters:

* The backend class.
* A display name shown to the user in the targets list (`sigma list targets`).
* A dict that maps output format names (used in `-f` parameter) to descriptions of the formats that are shown in the
  format list (`sigma list formats <backend>`). The formats must be supported by the backend!

The dict key is the name used in the `-t` parameter.

A processing pipeline is defined in the `pipelines` variable dict in `sigma/cli/pipelines.py`. The variable contains a
`ProcessingPipelineResolver` that is instantiated with a dict that maps identifiers that can
be used in the `-p` parameter to functions that return `ProcessingPipeline` objects. The descriptive text shown in the pipeline list (`sigma list pipelines`) is provided from
the `name` attribute of the `ProcessingPipeline` object.

## Maintainers

The project is currently maintained by:

- Thomas Patzke <thomas@patzke.org>
