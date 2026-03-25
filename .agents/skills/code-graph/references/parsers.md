# Language-Specific Parsing Strategies

## Python

### Tools available (via pip)
```bash
pip install ast --break-system-packages  # built-in, no install needed
pip install pyflowchart --break-system-packages
```

### AST-based parsing (recommended)
```python
import ast, os

def extract_calls(filepath):
    with open(filepath) as f:
        tree = ast.parse(f.read())
    
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(f"{node.func.attr}")
    return calls

def extract_functions(filepath):
    with open(filepath) as f:
        tree = ast.parse(f.read())
    return [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

def extract_imports(filepath):
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    return [i for i in imports if i]
```

### Entry point detection
- `if __name__ == "__main__":` block
- `main()` function at module level
- Flask/FastAPI: `app = Flask(__name__)` or `app = FastAPI()`; routes are entry points
- Django: `urls.py` patterns

---

## JavaScript / TypeScript

### Bash-based quick parse
```bash
# Find all function definitions
grep -rn "function \|const .* = (" --include="*.js" --include="*.ts" .

# Find all imports
grep -rn "^import \|require(" --include="*.js" --include="*.ts" .

# Find all function calls (rough)
grep -rn "[a-zA-Z_]\+(" --include="*.js" --include="*.ts" .
```

### Entry point detection
- `index.js`, `main.js`, `app.js`, `server.js`
- `package.json` → `"main"` field
- Express: `app.get/post/put/delete(` routes
- React: `ReactDOM.render(` or `createRoot(` in `index.js`
- Next.js: `pages/` directory — each file is an entry point

### TypeScript specifics
- Check `tsconfig.json` → `"include"` and `"outDir"` for project structure
- Interfaces/types create nodes but not edges unless used as function params

---

## Java

### Bash-based parsing
```bash
# Find all class definitions
grep -rn "^public class\|^class " --include="*.java" .

# Find method definitions
grep -rn "public\|private\|protected" --include="*.java" . | grep "void\|String\|int\|boolean"

# Find method calls (rough)
grep -rn "\.[a-zA-Z]\+()" --include="*.java" .
```

### Entry point detection
- `public static void main(String[] args)`
- Spring Boot: `@SpringBootApplication`, `@RestController`, `@RequestMapping`
- Android: `Activity.onCreate()`

---

## Go

```bash
# Find all functions
grep -rn "^func " --include="*.go" .

# Find imports
grep -rn "\"" --include="*.go" . | grep import

# Find function calls
grep -rn "[A-Z][a-zA-Z]\+(" --include="*.go" .
```

Entry point: `func main()` in `main.go`

---

## Ruby

```bash
# Find method definitions
grep -rn "def " --include="*.rb" .

# Find requires
grep -rn "require\|require_relative" --include="*.rb" .
```

Entry point detection:
- Rails: `config/routes.rb`, controllers in `app/controllers/`
- Sinatra: `get '/'`, `post '/'` etc.

---

## Rust

```bash
grep -rn "^fn \|^pub fn " --include="*.rs" .
grep -rn "^use \|^mod " --include="*.rs" .
```

Entry point: `fn main()` in `src/main.rs`; lib crate exposes `pub` functions.

---

## C / C++

```bash
# Function definitions
grep -rn "^[a-zA-Z_*].*(" --include="*.c" --include="*.cpp" --include="*.h" .

# Includes
grep -rn "^#include" --include="*.c" --include="*.cpp" --include="*.h" .
```

Entry point: `int main(` — usually in one `.c` / `.cpp` file.

---

## PHP

```bash
grep -rn "^function \|public function \|private function " --include="*.php" .
grep -rn "^require\|^include\|^use " --include="*.php" .
```

Entry point: `index.php`, Laravel routes in `routes/web.php`, `routes/api.php`.

---

## General Fallback (any language)

When language-specific parsing isn't available or is ambiguous:

1. **File-level graph**: Each file = 1 node. Draw edges from file A → file B if A imports/requires/includes B.
2. **Size heuristic**: Files with more outgoing edges are likely "orchestrators"; files with more incoming edges are utilities/libraries.
3. **Naming heuristic**: Files named `main`, `index`, `app`, `server`, `router`, `bootstrap` are likely entry points.

Use this as a fallback or for a quick high-level overview before doing deep per-function parsing.
