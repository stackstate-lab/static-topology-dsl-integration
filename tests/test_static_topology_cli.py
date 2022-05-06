from static_topo_impl.cli.main import cli


def test_cli():
    cli("cli-conf.yaml", "info", True, "tests/resources")
