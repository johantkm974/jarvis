"""Acciones sobre el sistema: XAMPP/MySQL, puertos, procesos, estado."""
from __future__ import annotations

import shutil
import subprocess
import time

import psutil

import config


# ---------------------------------------------------------------------------
# XAMPP / MySQL
# ---------------------------------------------------------------------------
def _port_open(port: int, timeout: float = 0.4) -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _xampp_exe(name: str):
    exe = config.XAMPP_DIR / name
    return exe if exe.is_file() else None


def mysql_start() -> str:
    if _port_open(config.MYSQL_PORT):
        return f"✅ MySQL ya está corriendo en el puerto {config.MYSQL_PORT}."

    exe = _xampp_exe("xampp_start.exe")
    if exe is None:
        return f"❌ No encuentro XAMPP en {config.XAMPP_DIR}. Ajusta XAMPP_DIR en .env"

    subprocess.Popen([str(exe)], cwd=str(config.XAMPP_DIR),
                     creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(20):                       # espera máx 10 s
        time.sleep(0.5)
        if _port_open(config.MYSQL_PORT):
            estado_apache = "con Apache" if _port_open(config.APACHE_PORT) else "sin Apache"
            return f"🚀 XAMPP levantado: MySQL en {config.MYSQL_PORT} ({estado_apache})."
    return "⏳ XAMPP lanzado pero MySQL aún no responde en el puerto {0}. Revisa XAMPP Control.".format(
        config.MYSQL_PORT
    )


def mysql_stop() -> str:
    exe = _xampp_exe("xampp_stop.exe")
    if exe is None:
        return f"❌ No encuentro XAMPP en {config.XAMPP_DIR}."
    subprocess.Popen([str(exe)], cwd=str(config.XAMPP_DIR),
                     creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(20):
        time.sleep(0.5)
        if not _port_open(config.MYSQL_PORT):
            return "🛑 MySQL detenido."
    return "⏳ Envié la orden de parada, pero el puerto sigue abierto. Usa XAMPP Control."


def mysql_status() -> str:
    mysql = "🟢 corriendo" if _port_open(config.MYSQL_PORT) else "🔴 apagado"
    apache = "🟢 corriendo" if _port_open(config.APACHE_PORT) else "🔴 apagado"
    return (f"MySQL (:{config.MYSQL_PORT}) -> {mysql}\n"
            f"Apache (:{config.APACHE_PORT}) -> {apache}")


# ---------------------------------------------------------------------------
# Puertos y procesos
# ---------------------------------------------------------------------------
def list_ports() -> str:
    rows: dict[tuple[str, int], tuple[int, str]] = {}
    for conn in psutil.net_connections(kind="inet"):
        if conn.status != "LISTEN" or not conn.laddr:
            continue
        ip = conn.laddr.ip
        if ip in ("0.0.0.0", "::"):
            ip = "*"
        pid = conn.pid or 0
        name = "-"
        if pid:
            try:
                name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                name = "?"
        rows[(ip, conn.laddr.port)] = (pid, name)

    if not rows:
        return "No veo puertos en escucha (¿quizá falta permiso de administrador?)."
    lines = ["Puertos en escucha:"]
    for (ip, port), (pid, name) in sorted(rows.items(), key=lambda kv: kv[0][1]):
        lines.append(f"  :{port:<6} {ip:<16} {name} (pid {pid or '-'})")
    return "\n".join(lines)


def port_info(slots: dict) -> str:
    try:
        port = int(slots.get("port", "0"))
    except ValueError:
        return "Dime un número de puerto, por ejemplo: que proceso usa el puerto 3306"

    hits = []
    for conn in psutil.net_connections(kind="inet"):
        if not conn.laddr or conn.laddr.port != port:
            continue
        pid = conn.pid or 0
        name = "?"
        if pid:
            try:
                p = psutil.Process(pid)
                name = p.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        hits.append(f"  {conn.status:<12} {name} (pid {pid or '-'})")
    if not hits:
        return f"Nadie está usando el puerto {port}."
    return f"Puerto {port}:\n" + "\n".join(sorted(set(hits)))


def list_processes() -> str:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            procs.append((info["memory_info"].rss, info))
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError, KeyError):
            continue
    procs.sort(reverse=True, key=lambda t: t[0])
    lines = ["Procesos por memoria (top 10):"]
    for rss, info in procs[:10]:
        lines.append(f"  {info['name']:<28} pid {info['pid']:<7} {rss / 1024 / 1024:6.1f} MB")
    return "\n".join(lines)


def sysinfo() -> str:
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    disk = psutil.disk_usage("C:/")
    return (f"CPU: {cpu}%  |  RAM: {vm.percent}% ({vm.used / 1024**3:.1f} de "
            f"{vm.total / 1024**3:.1f} GB)  |  Disco C:: {disk.percent}%")


# ---------------------------------------------------------------------------
# Fechas y hora
# ---------------------------------------------------------------------------
def now_time() -> str:
    return time.strftime("Son las %H:%M del %d/%m/%Y.")


def now_date() -> str:
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    t = time.localtime()
    return f"Hoy es {dias[t.tm_wday]} {t.tm_mday}/{t.tm_mon}/{t.tm_year}."
