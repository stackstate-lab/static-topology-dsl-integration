# StackState Static Topology DSL

## Overview

StackState Static Topology DSL allows you to easily define components, relations and health
in `.topo` files using a ___Topology Language___.


![Example Topo file](./grammar/syntax_highlighting.png)

The topology can be sent to the StackState server via a CLI or configured as an Agent Check.

See [documentation](https://stackstate-lab.github.io/static-topology-dsl-integration/) for more information.


## Development

### Prerequisites:

- python 3.7+
- [Poetry](https://python-poetry.org/docs/#installation)
- [Docker](https://www.docker.com/get-started)
- [stsdev](https://github.com/stackstate-lab/stslab-dev)

### Topology grammar

The Topology language is defined in [topology.tx](./grammar/topology.tx) using [Textx](https://textx.github.io/textX/3.0/) meta-language

Visualization of the model [topoloy.topo](./grammar/topology.topo)

![Visualization of the model](./grammar/topology.dot.png)

### Syntax Highlighting

For VSCode, copy `./grammar/topo-vscode` to `~/.vscode/extensions`

For Intellij import the `./grammar/topo-tmbundle`. See [Textmate Bundles](https://www.jetbrains.com/help/idea/textmate.html)

## Quick-Start for `stsdev`

`stsdev` is a tool to aid with the development StackState Agent integrations.

### Managing dependencies

[Poetry](https://python-poetry.org/) is used as the packaging and dependency management system.

Dependencies for your project can be managed through `poetry add` or `poetry add -D` for development dependency.

```console
$ poetry add PyYAML
```

###Build the project
To build the project,
```console
$ stsdev build --no-run-tests
```
This will automatically run code formatting, linting, tests and finally the build.

###Unit Testing
To run tests in the project,
```console
$ stsdev test
```
This will automatically run code formatting, linting, and tests.

###Dry-run a check

A check can be dry-run inside the StackState Agent by running
```console
$ sudo -u stackstate-agent check xxx
```
`stsdev` makes this take simple by packaging your checks and running the agent check using docker.

```console
$ stsdev agent check static_topology_dsl
```
Before running the command, remember to copy the example conf `tests/resources/conf.d/static_topology_dsl.d/conf.yaml.example` to
`tests/resources/conf.d/static_topology_dsl.d/conf.yaml`.


###Running checks in the Agent

Starts the StackState Agent in the foreground using the test configuration `tests/resources/conf.d`

```console
$ stsdev agent run
```

### Packaging checks

```console
$  stsdev package --no-run-tests
```
This will automatically run code formatting, linting, tests and finally the packaging.
A zip file is created in the `dist` directory.  Copy this to the host running the agent and unzip it.
Run the `install.sh`.

