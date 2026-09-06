"""Record guest bytes and answer terminal queries; never synthesize guest output."""
import re

QUERY = re.compile(rb'\x1b\[(?:\??6n|5n|[>0]?c|18t)|\x1bP\+q([0-9a-fA-F;]+)\x1b\\')


class Terminal:
    def __init__(self):
        self.pending = b''

    def replies(self, data):
        self.pending += data
        replies = []
        end = 0
        for match in QUERY.finditer(self.pending):
            query = match[0]
            end = match.end()
            if match[1] is not None:
                # XTGETTCAP: explicitly report unsupported, allowing fallback.
                replies.append(b'\x1bP0+r' + match[1] + b'\x1b\\')
            else:
                replies.append({b'\x1b[6n': b'\x1b[24;80R', b'\x1b[?6n': b'\x1b[?24;80R',
                                b'\x1b[5n': b'\x1b[0n', b'\x1b[c': b'\x1b[?1;2c',
                                b'\x1b[0c': b'\x1b[?1;2c', b'\x1b[>c': b'\x1b[>0;0;0c',
                                b'\x1b[18t': b'\x1b[8;24;80t'}[query])
        self.pending = self.pending[end:][-256:]
        return b''.join(replies)
