#!/usr/bin/env python3
"""Compatibility entry point; new commands use aat3ds_tool.py."""
import aat3ds_tool as _implementation

globals().update({name:value for name,value in vars(_implementation).items()
                  if not name.startswith('__')})

if __name__ == '__main__':
    _implementation.main()
