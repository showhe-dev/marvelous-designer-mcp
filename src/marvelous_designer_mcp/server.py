from mcp.server.fastmcp import FastMCP

from . import bridge
from .config import MD_HOST, MD_PORT

mcp = FastMCP("marvelous-designer")


def _md_exec(code: str) -> dict:
    """Run code inside MD and flatten the listener response envelope."""
    try:
        resp = bridge.call("execute_python", {"code": code})
    except bridge.BridgeError as e:
        return {"ok": False, "error": "bridge: {}".format(e)}
    if not isinstance(resp, dict):
        return {"ok": True, "result": resp}
    out = {"ok": False, "error": resp["error"]} if resp.get("error") else {"ok": True, "result": resp.get("result")}
    if resp.get("stdout"):
        out["stdout"] = resp["stdout"]
    return out


@mcp.tool()
def ping() -> dict:
    """Verify the MD listener is reachable."""
    try:
        return {"ok": True, "host": MD_HOST, "port": MD_PORT, "result": bridge.call("ping")}
    except bridge.BridgeError as e:
        return {"ok": False, "host": MD_HOST, "port": MD_PORT, "error": str(e)}


@mcp.tool()
def execute_python(code: str) -> dict:
    """Execute arbitrary Python inside Marvelous Designer. Bind return data to result."""
    try:
        return bridge.call("execute_python", {"code": code})
    except bridge.BridgeError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def shutdown_listener() -> dict:
    """Stop the blocking MD listener and release the Marvelous Designer GUI."""
    try:
        return {"ok": True, "result": bridge.call("shutdown")}
    except bridge.BridgeError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def capabilities() -> dict:
    """Detect MD/Python versions and the API surface used by this MCP."""
    return _md_exec(
        "import sys, importlib\n"
        "modules = ['import_api', 'export_api', 'fabric_api', 'pattern_api', 'utility_api']\n"
        "module_info = {}\n"
        "for name in modules:\n"
        "    try:\n"
        "        mod = importlib.import_module(name)\n"
        "        module_info[name] = {'available': True, 'functions': [n for n in dir(mod) if not n.startswith('_')]}\n"
        "    except Exception as e:\n"
        "        module_info[name] = {'available': False, 'error': str(e), 'functions': []}\n"
        "import utility_api\n"
        "version = [utility_api.GetMajorVersion(), utility_api.GetMinorVersion(), utility_api.GetPatchVersion()]\n"
        "checks = {"
        "'ImportFile': ('import_api','ImportFile'), 'ImportFileW': ('import_api','ImportFileW'), "
        "'ExportZPrj': ('export_api','ExportZPrj'), 'ExportZPrjW': ('export_api','ExportZPrjW'), "
        "'CreatePatternWithPoints': ('pattern_api','CreatePatternWithPoints'), "
        "'AssignFabricToPattern': ('fabric_api','AssignFabricToPattern'), "
        "'AddFabric': ('fabric_api','AddFabric'), 'GetPatternCount': ('pattern_api','GetPatternCount'), "
        "'NewProject': ('utility_api','NewProject'), 'Simulate': ('utility_api','Simulate')}\n"
        "features = {k: (module_info.get(m, {}).get('available', False) and f in module_info[m]['functions']) for k,(m,f) in checks.items()}\n"
        "result = {'md_version': version, 'python_version': sys.version, "
        "'modules': {k: {'available': v.get('available',False), 'function_count': len(v.get('functions',[])), 'error': v.get('error')} for k,v in module_info.items()}, "
        "'features': features}\n"
    )


@mcp.tool()
def scene_info() -> dict:
    """Return current project, MD version, pattern count and fabric information."""
    return _md_exec(
        "import utility_api, pattern_api, fabric_api\n"
        "result = {'project_name': utility_api.GetProjectName(), 'project_path': utility_api.GetProjectFilePath(), "
        "'md_version': [utility_api.GetMajorVersion(), utility_api.GetMinorVersion(), utility_api.GetPatchVersion()], "
        "'pattern_count': pattern_api.GetPatternCount(), 'fabric_count': fabric_api.GetFabricCount(True), "
        "'fabric_styles': fabric_api.GetFabricStyleNameList()}\n"
    )


@mcp.tool()
def list_patterns() -> dict:
    """List pattern pieces with index, name, fabric and 2D position."""
    return _md_exec(
        "import pattern_api\n"
        "result = [{'index': i, 'name': pattern_api.GetPatternPieceName(i), "
        "'fabric_index': pattern_api.GetPatternPieceFabricIndex(i), 'position': pattern_api.GetPatternPiecePos(i)} "
        "for i in range(pattern_api.GetPatternCount())]\n"
    )


@mcp.tool()
def get_pattern_info(pattern_index: int) -> dict:
    """Return detailed MD information for one pattern piece."""
    return _md_exec(
        "import pattern_api\n"
        "i = {}\n"
        "result = {{'index': i, 'name': pattern_api.GetPatternPieceName(i), "
        "'position': pattern_api.GetPatternPiecePos(i), 'fabric_index': pattern_api.GetPatternPieceFabricIndex(i), "
        "'information': pattern_api.GetPatternInformation(i), 'input_information': pattern_api.GetPatternInputInformation(i)}}\n"
        .format(int(pattern_index))
    )


@mcp.tool()
def create_pattern(points: list, name: str = "") -> dict:
    """Create a 2D pattern from [[x,y,type], ...]. MD 2025 uses List[Tuple[float,float,int]]."""
    safe = [(float(p[0]), float(p[1]), int(p[2]) if len(p) > 2 else 0) for p in points]
    return _md_exec(
        "import pattern_api\n"
        "pts = {!r}\n"
        "i = pattern_api.CreatePatternWithPoints(pts)\n"
        "name = {!r}\n"
        "if name:\n    pattern_api.SetPatternPieceName(i, name)\n"
        "result = {{'index': i, 'name': pattern_api.GetPatternPieceName(i), 'position': pattern_api.GetPatternPiecePos(i), "
        "'pattern_count': pattern_api.GetPatternCount()}}\n".format(safe, name)
    )


@mcp.tool()
def rename_pattern(pattern_index: int, name: str) -> dict:
    """Rename a pattern piece."""
    return _md_exec(
        "import pattern_api\n"
        "i, name = {}, {!r}\n"
        "pattern_api.SetPatternPieceName(i, name)\n"
        "result = {{'index': i, 'name': pattern_api.GetPatternPieceName(i)}}\n".format(int(pattern_index), name)
    )


@mcp.tool()
def move_pattern(pattern_index: int, x: float, y: float) -> dict:
    """Set a pattern piece's 2D position."""
    return _md_exec(
        "import pattern_api\n"
        "i = {}\n"
        "pattern_api.SetPatternPiecePos(i, {}, {})\n"
        "result = {{'index': i, 'position': pattern_api.GetPatternPiecePos(i)}}\n".format(int(pattern_index), float(x), float(y))
    )


@mcp.tool()
def delete_pattern(pattern_index: int) -> dict:
    """Delete a pattern piece by index."""
    return _md_exec(
        "import pattern_api\n"
        "i = {}\n"
        "before = pattern_api.GetPatternCount()\n"
        "pattern_api.DeletePatternPiece(i)\n"
        "result = {{'deleted_index': i, 'count_before': before, 'count_after': pattern_api.GetPatternCount()}}\n".format(int(pattern_index))
    )


@mcp.tool()
def list_fabrics() -> dict:
    """List fabrics and fabric-style names."""
    return _md_exec(
        "import fabric_api\n"
        "result = {'fabrics': [{'index': i, 'name': fabric_api.GetFabricName(i)} for i in range(fabric_api.GetFabricCount(True))], "
        "'styles': fabric_api.GetFabricStyleNameList()}\n"
    )


@mcp.tool()
def create_fabric(name: str) -> dict:
    """Create a fabric and return its index/name."""
    return _md_exec(
        "import fabric_api\n"
        "name = {!r}\n"
        "i = fabric_api.AddFabric(name)\n"
        "try:\n    fabric_api.SetFabricName(i, name)\n"
        "except Exception:\n    pass\n"
        "result = {'index': i, 'name': fabric_api.GetFabricName(i), 'count': fabric_api.GetFabricCount(True), "
        "'styles': fabric_api.GetFabricStyleNameList()}\n".format(name)
    )


@mcp.tool()
def rename_fabric(fabric_index: int, name: str) -> dict:
    """Rename a fabric."""
    return _md_exec(
        "import fabric_api\n"
        "i, name = {}, {!r}\n"
        "fabric_api.SetFabricName(i, name)\n"
        "result = {'index': i, 'name': fabric_api.GetFabricName(i)}\n".format(int(fabric_index), name)
    )


@mcp.tool()
def assign_fabric(fabric_index: int, pattern_index: int, face: int = 0) -> dict:
    """Assign a fabric to a pattern. Also reports the resulting pattern fabric index.

    MD 2025.0.127 was observed to return False even when the pattern's resulting
    fabric index is the requested fabric, so do not interpret the raw bool alone.
    """
    return _md_exec(
        "import fabric_api, pattern_api\n"
        "fi, pi, fc = {}, {}, {}\n"
        "returned = fabric_api.AssignFabricToPattern(fi, pi, fc)\n"
        "assigned = pattern_api.GetPatternPieceFabricIndex(pi)\n"
        "result = {'returned': returned, 'requested_fabric_index': fi, 'pattern_fabric_index': assigned, "
        "'assigned_matches': assigned == fi}\n".format(int(fabric_index), int(pattern_index), int(face))
    )


@mcp.tool()
def new_project() -> dict:
    """Create a new blank project. This discards the current scene; save first if needed."""
    return _md_exec(
        "import utility_api, pattern_api\n"
        "utility_api.NewProject()\n"
        "result = {'pattern_count': pattern_api.GetPatternCount()}\n"
    )


@mcp.tool()
def import_project(path: str) -> dict:
    """Open a project/garment/mesh using ImportFileW, falling back to ImportFile."""
    return _md_exec(
        "import import_api\n"
        "path = {!r}\n"
        "fn = getattr(import_api, 'ImportFileW', None) or import_api.ImportFile\n"
        "result = {'ok': bool(fn(path)), 'path': path}\n".format(path)
    )


@mcp.tool()
def export_project(path: str) -> dict:
    """Save the current scene as a .zprj using the verified MD 2025 call shape."""
    return _md_exec(
        "import export_api\n"
        "path = {!r}\n"
        "fn = getattr(export_api, 'ExportZPrjW', None)\n"
        "returned = fn(path, False) if fn is not None else export_api.ExportZPrj(path)\n"
        "result = {'ok': True, 'path': path, 'returned': returned}\n".format(path)
    )


@mcp.tool()
def simulate(steps: int = 1) -> dict:
    """Run cloth simulation via utility_api.Simulate(int)."""
    return _md_exec(
        "import utility_api\n"
        "steps = {}\n"
        "result = {'ok': True, 'returned': utility_api.Simulate(steps), 'steps': steps}\n".format(int(steps))
    )


@mcp.tool()
def md_api(module: str, contains: str = "") -> dict:
    """List public names in an MD API module."""
    return _md_exec(
        "import importlib\n"
        "mod = importlib.import_module({!r})\n"
        "sub = {!r}\n"
        "names = [n for n in dir(mod) if not n.startswith('_')]\n"
        "if sub:\n    names = [n for n in names if sub in n.lower()]\n"
        "result = sorted(names)\n".format(module, contains.lower())
    )
