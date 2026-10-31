#!/usr/bin/env python3
"""
Wireless Prober Entrypoint Wrapper.
Maintains backward compatibility while routing to modern modular CLI.
"""
from prober.cli import main

if __name__ == "__main__":
    main()
