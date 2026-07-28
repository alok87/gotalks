#!/usr/bin/env python3
"""Run a command under a pseudo-terminal of a fixed size.

presenterm queries the terminal for its dimensions and graphics capabilities
even when only validating, so it cannot run under a plain pipe. This gives it a
pty of a known size, answers those probes, nudges it with `q` so it never sits
waiting on a keypress, and forwards its output plus exit status.

usage: ptyrun.py [--cols N] [--rows N] [--timeout S] -- cmd [args...]
"""
import argparse
import fcntl
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import time

KITTY_QUERY = re.compile(rb"\x1b_G([^\x1b\x07]*)(?:\x1b\\|\x07)")


def answer_queries(fd: int, buf: bytes) -> None:
    """Reply to terminal capability probes so the child never blocks on us.

    presenterm asks whether the terminal speaks the kitty graphics protocol and
    waits for an answer. A real terminal replies; a bare pty never would. We
    answer 'unsupported' so it falls back to ascii blocks, plus the handful of
    ANSI status queries it may also send.
    """
    for m in KITTY_QUERY.finditer(buf):
        ident = b"i=0"
        for field in m.group(1).split(b","):
            if field.startswith(b"i="):
                ident = field
        os.write(fd, b"\x1b_G" + ident + b";ENOTSUPPORTED\x1b\\")
    if b"\x1b[c" in buf or b"\x1b[0c" in buf:
        os.write(fd, b"\x1b[?62;c")
    if b"\x1b[5n" in buf:
        os.write(fd, b"\x1b[0n")
    if b"\x1b[6n" in buf:
        os.write(fd, b"\x1b[1;1R")
    if b"\x1b[>q" in buf:
        os.write(fd, b"\x1bP>|ptyrun\x1b\\")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cols", type=int, default=120)
    ap.add_argument("--rows", type=int, default=40)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        ap.error("no command given")

    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "xterm-256color"
        os.environ["COLUMNS"] = str(args.cols)
        os.environ["LINES"] = str(args.rows)
        os.execvp(cmd[0], cmd)

    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", args.rows, args.cols, 0, 0))

    out = bytearray()
    tail = b""
    status = None
    deadline = time.monotonic() + args.timeout
    last_nudge = 0.0

    while time.monotonic() < deadline:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                chunk = b""          # child closed the pty: it is done
            if not chunk:
                break
            out += chunk
            answer_queries(fd, tail + chunk)
            tail = chunk[-16:]       # keep a tail so split escapes rejoin

        done, st = os.waitpid(pid, os.WNOHANG)
        if done:
            status = st
            break

        # presenterm sits on a keypress once it has nothing left to do
        now = time.monotonic()
        if now - last_nudge > 1.0:
            last_nudge = now
            try:
                os.write(fd, b"q")
            except OSError:
                break

    if status is None:
        for _ in range(20):          # give it a moment to exit on its own
            done, st = os.waitpid(pid, os.WNOHANG)
            if done:
                status = st
                break
            time.sleep(0.1)
        else:
            os.kill(pid, signal.SIGKILL)
            _, status = os.waitpid(pid, 0)
            sys.stderr.write(f"ptyrun: timed out after {args.timeout}s\n")

    os.close(fd)
    sys.stdout.write(out.decode("utf-8", "replace"))
    return os.waitstatus_to_exitcode(status)


if __name__ == "__main__":
    sys.exit(main())
