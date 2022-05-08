import json
import logging
import os
import time

import click
import yaml
from schematics.exceptions import DataError
from static_topo_impl.cli_processor import CliProcessor
from static_topo_impl.model.instance import Configuration


def run(conf: str, log_level: str, dry_run: bool, repeat: bool, work_dir: str, repeat_interval: int):
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s (%(lineno)s) - %(levelname)s: %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    if work_dir != ".":
        os.chdir(work_dir)
        click.echo("Current working directory: {0}".format(os.getcwd()))

    if repeat:
        click.echo("Running in repeat mode.")
        while True:
            _internal_run(conf, dry_run)
            click.echo(f"Will repeat after {repeat_interval} seconds.")
            time.sleep(repeat_interval)
            click.echo(f"Repeating...")
    else:
        _internal_run(conf, dry_run)


def _internal_run(conf: str, dry_run: bool):
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
    click.echo(f"Total Events = {result.events}.")
    click.echo(f"Total Health Syncs = {result.checks}.")
    click.echo("-" * 80)
    click.echo("Done")


@click.command()
@click.option("-f", "--conf", default="./conf.yaml", help="Configuration yaml file")
@click.option("--log-level", default="info", help="Log Level")
@click.option("--dry-run", is_flag=True, help="Dry run static topology sync")
@click.option("--repeat", is_flag=True, help="Runs topology sync as specified by the --repeat-interval")
@click.option("--work-dir", default=".", help="Set the current working directory")
@click.option("--repeat-interval", default="30", type=int, help="Repeat interval in seconds. Default 30.")
def cli(conf: str, log_level: str, dry_run: bool, repeat: bool, work_dir: str, repeat_interval: int):
    return run(conf, log_level, dry_run, repeat, work_dir, repeat_interval)


def main():
    return cli()
