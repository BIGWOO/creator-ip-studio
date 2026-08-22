from pathlib import Path

import typer

from creator_ip_studio.config import init_workspace


def main(workspace: Path, mode: str = "cpu") -> None:
    typer.echo(str(init_workspace(workspace, mode=mode)))


if __name__ == "__main__":
    typer.run(main)

