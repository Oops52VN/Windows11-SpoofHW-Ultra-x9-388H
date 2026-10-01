#!/usr/bin/env python3
"""
SpoofHW: Hardware Specification Emulation & Registry Override Utility
Main Entry Point
"""
import sys
from spoofhw.cli import run_cli

def main():
    sys.exit(run_cli())

if __name__ == "__main__":
    main()
