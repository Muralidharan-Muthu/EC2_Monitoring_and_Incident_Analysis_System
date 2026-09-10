"""
Remote EC2 Stress Trigger for Incident Testing.

Connects to the configured EC2 instance via SSH and executes
resource stress scenarios (CPU, RAM, Disk, Multi-Resource)
to test anomaly detection, incident correlation, and LangGraph AI analysis.

Usage:
    python trigger_stress.py
    python trigger_stress.py --scenario multi --duration 180
    python trigger_stress.py --scenario cpu --duration 120
    python trigger_stress.py --scenario stop
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure Windows terminal handles UTF-8 / special characters safely
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path to leverage app configuration and SSH client
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.core.config import get_settings
    from app.ssh.client import EC2SSHClient
except ImportError:
    # Standalone fallback if invoked outside virtualenv
    get_settings = None
    EC2SSHClient = None


def discover_ec2_host(settings) -> str | None:
    """Discover running EC2 instance public DNS if EC2_HOST is not set or needs update."""
    if settings.ec2_host and settings.ec2_host.strip():
        return settings.ec2_host.strip()

    if not (settings.aws_access_key_id and settings.aws_secret_access_key):
        return None

    try:
        import boto3
        ec2 = boto3.client(
            "ec2",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        res = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        for r in res.get("Reservations", []):
            for inst in r.get("Instances", []):
                dns = inst.get("PublicDnsName") or inst.get("PublicIpAddress")
                if dns:
                    return dns
    except Exception as exc:
        print(f"[!] EC2 auto-discovery warning: {exc}")
    return None


async def run_stress_remote(scenario: str, duration: int = 180):
    """Upload stress script and execute remotely over SSH."""
    if get_settings is None or EC2SSHClient is None:
        print("[ERROR] Please run this script using the backend virtual environment:")
        print(r"  .\backend\venv\Scripts\python.exe trigger_stress.py")
        return

    settings = get_settings()
    host = discover_ec2_host(settings)
    if not host:
        print("[ERROR] Could not determine EC2 Host. Please ensure EC2_HOST or AWS credentials are set in backend/.env")
        return

    key_path = settings.resolved_key_path
    if not key_path or not os.path.isfile(key_path):
        print(f"[ERROR] SSH private key not found at: {key_path}")
        return

    print(f"\n[+] Connecting to EC2 instance: {host} (user: {settings.ec2_username})...")
    import asyncssh

    client_keys = [key_path]
    conn_kwargs = {
        "host": host,
        "port": settings.ec2_port,
        "username": settings.ec2_username,
        "client_keys": client_keys,
        "known_hosts": None,
        "connect_timeout": 15,
    }

    try:
        async with asyncssh.connect(**conn_kwargs) as conn:
            print("[OK] SSH Connected successfully!")
            
            # 1. Upload stress_ec2.sh to remote instance
            local_script = ROOT_DIR / "scripts" / "stress_ec2.sh"
            if not local_script.exists():
                local_script = ROOT_DIR / "stress_ec2.sh"

            if local_script.exists():
                remote_dest = "/home/ubuntu/stress_ec2.sh"
                print(f"[+] Syncing {local_script.name} to EC2 ({remote_dest})...")
                async with conn.start_sftp_client() as sftp:
                    await sftp.put(str(local_script), remote_dest)
                await conn.run("chmod +x /home/ubuntu/stress_ec2.sh", check=True)
                print("[OK] Remote stress script ready.")

            # 2. Build remote command
            if scenario == "stop":
                cmd = "bash /home/ubuntu/stress_ec2.sh stop"
            else:
                cmd = f"bash /home/ubuntu/stress_ec2.sh {scenario} {duration}"

            print(f"\n[+] Executing on EC2: {cmd}")
            print(f"[i] Monitor the frontend dashboard to see anomalies and incidents in real time!\n" + "="*70)

            # Stream output live
            process = await conn.create_process(cmd)
            async for line in process.stdout:
                print(line, end="", flush=True)

            await process.wait()
            print("="*70 + f"\n[OK] Remote stress task ({scenario}) completed with exit code: {process.returncode}")

    except Exception as exc:
        print(f"[ERROR] Failed during remote SSH execution: {exc}")


def print_menu():
    print("""
========================================================================
           EC2 INCIDENT TESTING & RESOURCE STRESS GENERATOR
========================================================================
Select a scenario to execute remotely on EC2:

  [1] Scenario A: Stress CPU to 97%            (Flags CPU_CRITICAL > 90%)
  [2] Scenario B: Stress Memory (RAM) to 92%+  (Flags MEMORY_CRITICAL > 90%)
  [3] Scenario C: Stress Disk Storage to >90% (Flags DISK_CRITICAL > 90%)
  [4] Scenario D: Assessment Multi-Resource   (CPU 96% + RAM 91% -> LangGraph AI)
  [5] Scenario E: Extreme Triple Saturation    (CPU + RAM + Disk)
  [6] Stop All:   Kill stress-ng & clean disk files
  [0] Exit
========================================================================
""")


def main():
    parser = argparse.ArgumentParser(description="Trigger resource stress tests on EC2.")
    parser.add_argument(
        "positional_scenario",
        nargs="?",
        default=None,
        help="Stress scenario (e.g. cpu, ram, disk, multi, all, stop)"
    )
    parser.add_argument(
        "positional_duration",
        nargs="?",
        type=int,
        default=None,
        help="Duration in seconds"
    )
    parser.add_argument(
        "--scenario",
        choices=["cpu", "ram", "memory", "disk", "multi", "assessment", "all", "triple", "stop", "clean"],
        default=None,
        help="Stress scenario to run"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=180,
        help="Duration in seconds (default: 180s for consecutive anomaly sampling)"
    )

    args = parser.parse_args()

    # Determine scenario and normalize aliases
    scenario = args.scenario or args.positional_scenario
    if scenario:
        scenario = scenario.lower()
        if scenario in ("memory",):
            scenario = "ram"
        elif scenario in ("assessment",):
            scenario = "multi"
        elif scenario in ("triple",):
            scenario = "all"
        elif scenario in ("clean", "cleanup"):
            scenario = "stop"

    duration = args.positional_duration if args.positional_duration is not None else args.duration

    if scenario:
        asyncio.run(run_stress_remote(scenario, duration))
    else:
        print_menu()
        choice = input("Enter choice [0-6] (Default: 4): ").strip() or "4"
        scenario_map = {
            "1": "cpu",
            "2": "ram",
            "3": "disk",
            "4": "multi",
            "5": "all",
            "6": "stop",
        }
        if choice == "0":
            print("Exiting.")
            return

        scenario = scenario_map.get(choice)
        if not scenario:
            print("[!] Invalid choice.")
            return

        if scenario != "stop":
            dur_input = input(f"Enter duration in seconds (Default: 180): ").strip()
            duration = int(dur_input) if dur_input.isdigit() else 180
        else:
            duration = 0

        asyncio.run(run_stress_remote(scenario, duration))


if __name__ == "__main__":
    main()
