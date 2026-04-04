import sys

path = r'C:\GammaEnginePython\gamma_engine_telemetry_logger.py'
content = open(path, encoding='utf-8').read()

# Fix: move freshness call to BEFORE persist_snapshot
# Find the block we need to replace
OLD = (
    '    result = run_health_check(python_executable)\n'
    '    snapshot = build_snapshot(result)\n'
    '    persist_snapshot(snapshot, max_snapshots)\n'
    '\n'
    '    freshness = check_table_freshness()\n'
    '    snapshot["table_freshness"] = freshness\n'
    '\n'
    '    hb_status = "OK" if result["returncode"] == 0 else "ERROR"\n'
    '    if freshness.get("any_stale") and hb_status == "OK":\n'
    '        hb_status = "WARN"'
)

NEW = (
    '    result = run_health_check(python_executable)\n'
    '    snapshot = build_snapshot(result)\n'
    '\n'
    '    freshness = check_table_freshness()\n'
    '    snapshot["table_freshness"] = freshness\n'
    '    if freshness.get("any_stale"):\n'
    '        snapshot["event_level"] = "WARN"\n'
    '\n'
    '    persist_snapshot(snapshot, max_snapshots)\n'
    '\n'
    '    hb_status = "OK" if result["returncode"] == 0 else "ERROR"\n'
    '    if freshness.get("any_stale") and hb_status == "OK":\n'
    '        hb_status = "WARN"'
)

if OLD not in content:
    print("FAIL: anchor block not found. Showing context around persist_snapshot:")
    idx = content.find('persist_snapshot(snapshot, max_snapshots)')
    print(repr(content[max(0, idx-200):idx+200]))
    sys.exit(1)

content = content.replace(OLD, NEW, 1)
open(path, 'w', encoding='utf-8').write(content)
print("SUCCESS - freshness check now runs before persist_snapshot")
print("New file length:", len(content))
