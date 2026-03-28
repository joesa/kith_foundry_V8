with open("/home/joe/repos/kith_foundry_V8/backend/main.py", "r") as f:
    orig = f.read()

new_code = orig.replace(
    'preview_url = project.preview_url if project else ""',
    'preview_url = worker.preview_url if worker and worker.preview_url else (project.preview_url if project else "")'
)

with open("/home/joe/repos/kith_foundry_V8/backend/main.py", "w") as f:
    f.write(new_code)
