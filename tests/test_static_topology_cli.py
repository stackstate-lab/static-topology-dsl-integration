from static_topo_impl.cli.main import run as cli


def test_cli():
    cli("cli-conf.yaml", "info", True, False, "tests/resources", 60)
