"""Точка входа приложения."""
import logging
import sys
from pathlib import Path
import click
from cli import (
    cmd_init, cmd_update, cmd_list, cmd_import,
    cmd_export_list, cmd_export_detail, cmd_backup,
    cmd_update_supplies, cmd_export_supplies,
)

# Настройка логирования
LOG_FILE = Path("wb_importer.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


@click.group(help="Импорт финансовых отчётов и поставок Wildberries в PostgreSQL")
def cli():
    pass


cli.add_command(cmd_init, "init")
cli.add_command(cmd_update, "update")
cli.add_command(cmd_list, "list")
cli.add_command(cmd_import, "import")
cli.add_command(cmd_update_supplies, "update-supplies")
cli.add_command(cmd_export_list, "export-list")
cli.add_command(cmd_export_detail, "export-detail")
cli.add_command(cmd_backup, "backup")
cli.add_command(cmd_export_supplies, "export-supplies")


if __name__ == "__main__":
    cli()