"""Aplica no banco os arquivos de migrations/ que ainda não foram aplicados.

Uso: uv run python -m alerta.migrate

Uma tabela `schema_migrations` registra quais arquivos já rodaram, então
executar este comando várias vezes é seguro: só o que é novo é aplicado.
"""

from pathlib import Path

import psycopg

from alerta.config import get_settings

# src/alerta/migrate.py -> sobe 3 níveis até a raiz do repositório
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def main() -> None:
    settings = get_settings()

    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        conn.commit()

        # sorted() garante a ordem 001, 002, 003...
        pending = [f for f in sorted(MIGRATIONS_DIR.glob("*.sql")) if f.stem not in applied]
        if not pending:
            print("Banco já está atualizado.")
            return

        for file in pending:
            print(f"Aplicando {file.name}...")
            # Uma transação por arquivo: se algo falhar no meio, nada daquele
            # arquivo fica pela metade no banco (rollback automático).
            with conn.transaction():
                conn.execute(file.read_text())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (file.stem,))
        print(f"{len(pending)} migration(s) aplicada(s).")


if __name__ == "__main__":
    main()
