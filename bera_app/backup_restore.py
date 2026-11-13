"""
Utilidad de copia de seguridad y restauración de la base de datos SQLite de BERA.
Uso:
  python3 backup_restore.py backup
  python3 backup_restore.py restore backups/bera_backup_YYYYMMDD_HHMMSS.db
"""
import os
import shutil
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BERA_DB_PATH", os.path.join(BASE_DIR, "bera.db"))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"bera_backup_{ts}.db")
    shutil.copy2(DB_PATH, dest)
    print(f"Backup creado en: {dest}")


def restore(src: str):
    if not os.path.exists(src):
        print(f"Archivo no encontrado: {src}")
        sys.exit(1)
    shutil.copy2(src, DB_PATH)
    print(f"Base de datos restaurada desde: {src}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 backup_restore.py [backup | restore <ruta>]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "backup":
        backup()
    elif cmd == "restore" and len(sys.argv) == 3:
        restore(sys.argv[2])
    else:
        print("Comando inválido.")
        sys.exit(1)
