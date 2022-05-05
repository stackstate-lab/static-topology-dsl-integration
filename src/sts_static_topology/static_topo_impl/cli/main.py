import logging

import click
import yaml
import json

from schematics.exceptions import DataError

from static_topo_impl.model.instance import Configuration
from static_topo_impl.cli_processor import CliProcessor


@click.command()
@click.option("-f", "--conf", default="./conf.yaml", help="Configuration yaml file")
@click.option("--log-level", default="info", help="Log Level")
@click.option("--dry-run", is_flag=True, help="Dry run static topology creation")
def run(conf: str, log_level: str, dry_run: bool):
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s (%(lineno)s) - %(levelname)s: %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S"
    )
    click.echo(f"Loading configuration from {conf}")
    with open(conf) as f:
        dict_config = yaml.safe_load(f)
    try:
        configuration = Configuration(dict_config)
        configuration.validate()
    except DataError as e:
        click.echo("Failed to load configuration:", err=True)
        click.echo(json.dumps(e.to_primitive(), indent=4), err=True)
        return 1

    if dry_run:
        click.echo("Running Static Topology sync in dry-run mode")
        result = CliProcessor(configuration).run(dry_run)
        click.echo("Discovered Component and Relation information:")
        click.echo("-" * 80)
        for payload in result.payloads:
            click.echo(payload)
            click.echo("-" * 80)
    else:
        click.echo("Running Static Topology sync")
        result = CliProcessor(configuration).run()

    click.echo("-" * 80)
    click.echo(f"Total Components = {result.components}.")
    click.echo(f"Total Relations = {result.relations}.")
    click.echo(f"Total Health Syncs = {result.checks}.")
    click.echo("-" * 80)
    click.echo("Done")


def main():
    return run()
