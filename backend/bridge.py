from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os

app = FastAPI()

class EditRequest(BaseModel):
    file_path: str
    search_block: str
    replace_block: str

class ReadRequest(BaseModel):
    file_path: str

class RunRequest(BaseModel):
    command: str

@app.post("/api/v1/edit")
async def edit_file(req: EditRequest):
    # Security: Ensure file_path does not escape /workspace
    full_path = os.path.abspath(os.path.join("/workspace", req.file_path))
    if not full_path.startswith("/workspace"):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    if not os.path.exists(full_path):
        # Create file and parent directories if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(req.replace_block)
        return {"status": "success", "message": f"Created {req.file_path}"}
    
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if req.search_block not in content:
        raise HTTPException(status_code=400, detail="Search block not found in file")
    
    new_content = content.replace(req.search_block, req.replace_block, 1)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    return {"status": "success"}

@app.post("/api/v1/read")
async def read_file(req: ReadRequest):
    full_path = os.path.abspath(os.path.join("/workspace", req.file_path))
    if not full_path.startswith("/workspace"):
        raise HTTPException(status_code=403, detail="Path traversal detected")
        
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return {"status": "success", "content": content}

class WriteRequest(BaseModel):
    file_path: str
    content: str

@app.post("/api/v1/write")
async def write_file(req: WriteRequest):
    """Write complete file content (full-file replacement)."""
    full_path = os.path.abspath(os.path.join("/workspace", req.file_path))
    if not full_path.startswith("/workspace"):
        raise HTTPException(status_code=403, detail="Path traversal detected")
    
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(req.content)
        
    return {"status": "success", "message": f"Wrote {req.file_path}"}

class FileEntry(BaseModel):
    file_path: str
    content: str

class WriteBatchRequest(BaseModel):
    files: list[FileEntry]

@app.post("/api/v1/write_batch")
async def write_batch(req: WriteBatchRequest):
    """Write multiple files atomically. Sorts by dependency order to avoid HMR import errors."""
    
    def sort_key(f: FileEntry) -> int:
        """Types first, then utils, then components, then App, then CSS, then main."""
        path = f.file_path.lower()
        if "type" in path: return 0
        if "util" in path: return 1
        if "component" in path or "page" in path: return 2
        if "app.css" in path: return 3
        if "app.tsx" in path or "app.jsx" in path: return 4
        if "main.tsx" in path or "main.jsx" in path: return 5
        return 3
    
    sorted_files = sorted(req.files, key=sort_key)
    written = []
    
    for file_entry in sorted_files:
        full_path = os.path.abspath(os.path.join("/workspace", file_entry.file_path))
        if not full_path.startswith("/workspace"):
            continue
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(file_entry.content)
        written.append(file_entry.file_path)
    
    return {"status": "success", "written": written, "count": len(written)}

@app.get("/api/v1/tree")
async def get_file_tree():
    """Returns the recursive file tree of the workspace src/ directory."""
    import pathlib
    
    def build_tree(root_path: str, base_path: str = ""):
        entries = []
        try:
            for item in sorted(pathlib.Path(root_path).iterdir()):
                rel_path = os.path.join(base_path, item.name) if base_path else item.name
                if item.name.startswith('.') or item.name == 'node_modules':
                    continue
                if item.is_dir():
                    children = build_tree(str(item), rel_path)
                    entries.append({
                        "name": item.name,
                        "path": rel_path,
                        "type": "dir",
                        "children": children
                    })
                else:
                    entries.append({
                        "name": item.name,
                        "path": rel_path,
                        "type": "file"
                    })
        except PermissionError:
            pass
        return entries
    
    tree = build_tree("/workspace/src", "src")
    # Also include root config files
    root_files = []
    for f in ["package.json", "tsconfig.json", "vite.config.ts", "index.html"]:
        p = os.path.join("/workspace", f)
        if os.path.exists(p):
            root_files.append({"name": f, "path": f, "type": "file"})
    
    return {"tree": root_files + tree}

@app.post("/api/v1/run")
async def run_command(req: RunRequest):
    try:
        result = subprocess.run(
            req.command,
            shell=True,
            cwd="/workspace",
            capture_output=True,
            text=True
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/run_background")
async def run_background_command(req: RunRequest):
    try:
        # Start the process in the background
        process = subprocess.Popen(
            req.command,
            shell=True,
            cwd="/workspace",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {
            "status": "success",
            "pid": process.pid,
            "message": f"Started background process: {req.command}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
