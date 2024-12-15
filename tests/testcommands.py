#!/usr/bin/env python3
"""
Test command runner for OpenToolController.
Provides standardized commands for running different test configurations.
"""
import subprocess
import sys
import os
import argparse

def run_login_tests(verbose=False):
    """Run login module tests"""
    cmd = ["pytest", "tests/test_login.py"]
    if verbose:
        cmd.append("-v")
    subprocess.run(cmd)

def run_all_tests(verbose=False):
    """Run all tests"""
    cmd = ["pytest", "tests"]
    if verbose:
        cmd.append("-v")
    subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="OpenToolController test runner")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--login", action="store_true", help="Run login tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.login:
        run_login_tests(args.verbose)
    elif args.all:
        run_all_tests(args.verbose)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
