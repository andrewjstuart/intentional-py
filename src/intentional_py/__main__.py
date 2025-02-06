from intentional_py import __app_name__, intentional


def main() -> None:
    intentional.app(prog_name=__app_name__)


if __name__ == "__main__":
    from intentional_py.intentional import app

    app()
