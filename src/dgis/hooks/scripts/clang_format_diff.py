#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ===- clang_format_diff.py - ClangFormat Diff Reformatter ----*- python -*--===#
#
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
# ===------------------------------------------------------------------------===#

r"""
ClangFormat Diff Reformatter
============================

This script reads input from a unified diff and reformats all the changed
lines. This is useful to reformat all the lines touched by a specific patch.
Example usage for git/svn users:

  git diff -U0 HEAD^ | clang_format_diff.py -p1 -i
  svn diff --diff-cmd=diff -x-U0 | clang_format_diff.py -i

"""
from __future__ import print_function

import argparse
import difflib
import os
import re
import subprocess
import sys
from io import StringIO

import colorama


def color_diff(diff):
    for line in diff:
        color = None
        if line.startswith('+'):
            color = colorama.Fore.GREEN
        elif line.startswith('-'):
            color = colorama.Fore.RED
        elif line.startswith('^'):
            color = colorama.Fore.BLUE

        if color is None:
            yield line
        else:
            yield color + line[:-1] + colorama.Fore.RESET + line[-1]


def entry_point():
    parser = argparse.ArgumentParser(description=
                                     'Reformat changed lines in diff. Without -i '
                                     'option just output the diff that would be '
                                     'introduced.')
    parser.add_argument('-i', action='store_true', default=False,
                        help='apply edits to files instead of displaying a diff')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='be more verbose, ineffective without -i')
    parser.add_argument('-style',
                        help='formatting style to apply (LLVM, Google, Chromium, '
                             'Mozilla, WebKit)')
    parser.add_argument('-binary', default='clang-format',
                        help='location of binary to use for clang-format')
    parser.add_argument('-filediff',
                        help='path to file with diff')
    parser.add_argument('-filesrc',
                        help='path to source file')
    parser.add_argument('-workdir', default=".",
                        help='path to work-dir')
    args = parser.parse_args()
    clang_format(args)


def clang_format(args):
    # Extract changed lines for each file.
    lines_by_file = {}
    stdout = None
    with open(os.path.join(args.filesrc), "r") as filesrc:
        code = filesrc.readlines()
    if args.filediff:
        with open(os.path.join(args.filediff), "r") as filediff:
            for line in filediff.readlines():
                match = re.search('^@@.*\+(\d+)(,(\d+))?', line)
                if match:
                    start_line = int(match.group(1))
                    line_count = 1
                    if match.group(3):
                        line_count = int(match.group(3))
                    if line_count == 0:
                        continue
                    end_line = start_line + line_count - 1
                    lines_by_file.setdefault(args.filesrc, []).extend(
                        ['-lines', str(start_line) + ':' + str(end_line)])
    elif args.filesrc:
        lines_by_file.setdefault(args.filesrc, []).extend(['-lines', '1:' + str(len(code))])
    if not lines_by_file:
        # print('not found added lines')
        sys.exit(0)
    for filename, lines in lines_by_file.items():
        if args.verbose:
            print('Formatting', os.path.join(os.path.relpath(os.path.dirname(filename), os.path.abspath(args.workdir)),
                                             os.path.basename(filename)))
        command = [args.binary, os.path.join(os.path.relpath(os.path.dirname(filename), os.path.abspath(args.workdir)),
                                             os.path.basename(filename))]
        if args.i:
            command.append("-i")
        command.extend(lines)
        if args.style:
            command.extend(['-style', args.style])

        if args.verbose:
            print(clang_format_config(args))
            print(command)
        stdout, stderr = caller_clang_binary(command, args.workdir)
        if args.verbose:
            print(stdout)
    if args.i:
        with open(os.path.join(args.filesrc), "r") as filesrc:
            formatted_code = filesrc.readlines()
    else:
        formatted_code = StringIO(stdout.decode()).readlines() if stdout else ''
    diff = difflib.unified_diff(code, formatted_code,
                                args.filesrc, args.filesrc,
                                '--- (BAD CODE)', '+++ (GOOD CODE)', n=1)
    diff = color_diff(diff)
    diff_string = "".join(diff)

    if len(diff_string) > 0:
        print(diff_string.replace('\r', ''))
        sys.exit(1)
    else:
        # print('nothing format')
        sys.exit(0)


def clang_format_config(args):
    command = [args.binary, '--version']
    stdout0, stderr0 = caller_clang_binary(command, args.workdir)
    print(stdout0)

    command = [args.binary, '-dump-config']
    if args.style:
        command.extend(['-style', args.style])
    stdout, stderr = caller_clang_binary(command, args.workdir)
    return stdout


def caller_clang_binary(command, work_dir):
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=sys.stderr,
                         stdin=subprocess.PIPE,
                         cwd=work_dir)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        print(os.path.abspath(os.path.dirname(__file__)))
        sys.exit(p.returncode)
    return stdout, stderr


if __name__ == '__main__':
    entry_point()
