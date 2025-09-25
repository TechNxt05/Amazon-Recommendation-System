# backend/list_routes.py
import importlib, sys, os
# ensure backend is importable
sys.path.insert(0, os.getcwd())
appmod = importlib.import_module("app")   # assumes you run from backend/
app = getattr(appmod, "app")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: (str(r.rule), str(r.endpoint))):
    methods = ",".join(sorted(rule.methods - {"HEAD","OPTIONS"}))
    print(f"{rule.rule:40s}  -> endpoint: {rule.endpoint:30s}  methods: {methods}")
