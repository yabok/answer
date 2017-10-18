from operator import itemgetter
import re

class Router:
    def __init__(self):
        self.map = {}

    def compile(self):
        self.compiled = {re.compile(k): v for (k, v) in self.map.items()}

    def add(self, path, handler):
        self.map[path] = handler

    def match(self, path, handlers=None, groups=None):
        if not handlers:
            handlers = self.map
        if not groups:
            groups = {}

        if callable(handlers):
            return (handlers, groups)

        if path == '':
            if '/' in handlers:
                return (handlers['/'], groups)
            else:
                raise RuntimeError("Missing handler")

        matches = []
        for pattern, value in handlers.items():
            match = re.match(pattern, path)
            if not match:
                continue

            match_length = match.end()
            remaining_path = path[match_length:]
            matched_groups = groups.copy().update(match.groupdict())
            matches.append((match_length
                           ,{"path": remaining_path
                            ,"handlers": value
                            ,"groups": matched_groups}))

        (length, longest_match) = max(matches, key=itemgetter(0))
        groups.update(longest_match["groups"])
        longest_match["groups"] = groups
        return self.match_list(**longest_match)
