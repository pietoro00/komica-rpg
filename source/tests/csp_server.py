import http.server, json, functools, os
cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','staticwebapp.config.json')))['globalHeaders']
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        for k, v in cfg.items(): self.send_header(k, v)
        super().end_headers()
    def log_message(self, *a): pass
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..'))
http.server.ThreadingHTTPServer(('127.0.0.1', 8766), H).serve_forever()
