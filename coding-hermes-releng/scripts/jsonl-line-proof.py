#!/usr/bin/env python3
"""Byte-level proof that a JSONL board edit touched only what you intended.

WHY THIS EXISTS
    The two obvious proofs both fail silently on a multi-megabyte board.

    1. `git diff -U0 <board> | grep '^@@'` prints NOTHING, and
       `git diff --numstat` prints `-\t-`, because git classifies the file as
       BINARY. The check returns no lines, reads as "no change", and leaves a
       completed repair unproven.
    2. `cmp -n $(stat -c%s <pre-copy>) <pre-copy> <board>` NAMES the pre-copy.
       On an unattended surface the lifecycle gate refuses any command that
       references a file above its ~1 MiB scan cap, so the check never runs at
       all. This script is small enough to be scanned and reads the big files
       itself, from inside the process.

USAGE
    jsonl-line-proof.py <pre-copy> <post-file>
    jsonl-line-proof.py <pre-copy> <post-file> --expect-line 1388
    jsonl-line-proof.py <pre-copy> <post-file> --expect-append 2

    <pre-copy> is a copy of the board taken BEFORE the write (cp, or
    `git show HEAD:<board> > pre`). Keep it outside the tracked tree.

EXIT CODES
    0 = the proof holds
    3 = the proof FAILED (diff set is not what was asserted)
    2 = usage error / unreadable input

OUTPUT
    key=value lines: both line counts, trailing-newline flags, the differing
    1-based line indices, a classification (replace-one / pure-append / other),
    and prefix/suffix byte identity. Paste them into the row's note; a reader
    can then audit the write without re-running it.
"""

import argparse
import sys


def read_lines(path):
    with open(path, 'rb') as fh:
        data = fh.read()
    trailing = data.endswith(b'\n')
    lines = data.split(b'\n')
    if trailing:
        lines = lines[:-1]
    return lines, trailing


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('pre')
    ap.add_argument('post')
    ap.add_argument('--expect-line', type=int, default=None,
                    help='the single 1-based line index that may differ')
    ap.add_argument('--expect-append', type=int, default=None,
                    help='the number of rows appended at the tail')
    args = ap.parse_args()

    try:
        pre, pre_nl = read_lines(args.pre)
        post, post_nl = read_lines(args.post)
    except OSError as exc:
        print('error=%s' % exc)
        return 2

    print('lines_pre=%d' % len(pre))
    print('lines_post=%d' % len(post))
    print('trailing_newline_pre=%s' % pre_nl)
    print('trailing_newline_post=%s' % post_nl)

    common = min(len(pre), len(post))
    differ = [i + 1 for i in range(common) if pre[i] != post[i]]
    print('differing_line_indices=%s' % (','.join(str(i) for i in differ) or 'none'))

    appended = len(post) - len(pre)
    pure_append = (
        appended > 0
        and not differ
        and post[:len(pre)] == pre
    )
    replace_one = len(pre) == len(post) and len(differ) == 1

    if pure_append:
        print('classification=pure-append')
        print('appended_rows=%d' % appended)
    elif replace_one:
        print('classification=replace-one')
        print('changed_line=%d' % differ[0])
    else:
        print('classification=other')

    if differ:
        first = differ[0] - 1
        last = differ[-1]
        print('prefix_identical=%s' % (pre[:first] == post[:first]))
        print('suffix_identical=%s' % (pre[last:] == post[last:]))
    else:
        print('prefix_identical=%s' % (post[:len(pre)] == pre))
        print('suffix_identical=True')

    ok = True
    if args.expect_line is not None:
        ok = ok and len(pre) == len(post) and differ == [args.expect_line]
        print('expected_line=%d' % args.expect_line)
    if args.expect_append is not None:
        ok = ok and pure_append and appended == args.expect_append
        print('expected_append=%d' % args.expect_append)
    if args.expect_line is None and args.expect_append is None:
        ok = replace_one or pure_append

    print('RESULT=%s' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main())
