from intentional_py import cli, __app_name__


def main() -> None:
    cli.app(prog_name=__app_name__)


if __name__ == "__main__":
    from intentional_py.cli import app

    app()
