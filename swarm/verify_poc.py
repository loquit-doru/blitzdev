"""
Standalone Proof of Coordination verifier.

Usage:
  python swarm/verify_poc.py poc_logs/poc_<job_id>.jsonl
  python swarm/verify_poc.py poc_logs/poc_<job_id>.jsonl --secret my-secret

Exit code: 0 if valid, 1 if tampered/invalid.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.poc_logger import verify_poc_log

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify a FlashForge PoC log")
    parser.add_argument("log_path", help="Path to the .jsonl PoC log file")
    parser.add_argument(
        "--secret",
        default=os.getenv("SWARM_SECRET", "swarm-secret-change-in-prod"),
        help="Shared HMAC secret (or set SWARM_SECRET env var)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.log_path):
        print(f"❌ File not found: {args.log_path}")
        sys.exit(1)

    ok = verify_poc_log(args.log_path, args.secret)
    sys.exit(0 if ok else 1)
