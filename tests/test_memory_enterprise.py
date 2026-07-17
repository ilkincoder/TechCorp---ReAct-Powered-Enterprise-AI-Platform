"""Quick enterprise memory test — verify enterprise entity types, dedup, and search."""
import asyncio
from techcorp_platform.tools.memory_tool import MemoryTool
from techcorp_platform.conversations import clear_memories
from qdrant_client import QdrantClient
from techcorp_platform.config import QDRANT_URL, MEMORY_COLLECTION


async def test():
    # Clean slate
    await clear_memories()
    client = QdrantClient(url=QDRANT_URL, timeout=30)
    try:
        client.delete_collection(MEMORY_COLLECTION)
    except Exception:
        pass

    tool = MemoryTool()

    # Print new config
    print("Entity types:", tool._input_schema()["properties"]["entity_type"]["enum"])
    print("Default:", tool._input_schema()["properties"]["entity_type"]["default"])
    print()

    # Test 1: Store enterprise facts
    tests = [
        ("The Phoenix project deadline is September 15th", "project_detail"),
        ("Q3 marketing budget allocated at 50k", "budget"),
        ("We are migrating the auth service to PostgreSQL 16", "technical_context"),
        ("The vendor Acme Corp agreed to 10 percent discount", "vendor_customer"),
        ("Sprint 4 review decision: delay the release by one week", "meeting_decision"),
    ]

    print("--- Storing enterprise context ---")
    ids = []
    for content, etype in tests:
        r = await tool.execute(action="store", content=content, entity_type=etype)
        status = "UPDATED" if r.data.get("updated") else "NEW"
        eid = r.metadata.get("entry_id")
        ids.append(eid)
        print(f"  [{status}] id={eid} type={etype} -> {content[:60]}")

    # Test 2: Dedup — rephrase the Phoenix deadline
    print()
    print("--- Dedup: rephrase Phoenix deadline ---")
    r = await tool.execute(
        action="store",
        content="Remember that the Phoenix project deadline is Sept 15",
        entity_type="project_detail",
    )
    dedup_id = r.metadata.get("entry_id")
    updated = r.data.get("updated")
    print(f"  id={dedup_id} updated={updated}")
    if updated and dedup_id == ids[0]:
        print("  PASS: rephrase updated existing entry (no duplicate)")
    else:
        print(f"  FAIL: expected updated={True} with id={ids[0]}, got updated={updated} id={dedup_id}")

    # Test 3: Search
    print()
    print("--- Search: Phoenix project deadline ---")
    r = await tool.execute(action="search", query="What is the Phoenix project deadline?")
    results = r.data.get("results", [])
    phoenix = [m for m in results if "phoenix" in m["content"].lower()]
    print(f"  Phoenix matches: {len(phoenix)}")
    if len(phoenix) == 1:
        print("  PASS: exactly 1 Phoenix entry (no duplicates)")
    else:
        print(f"  FAIL: {len(phoenix)} Phoenix entries (expected 1)")

    # Test 4: Total count
    print()
    recent = await tool.execute(action="recent", limit=50)
    total = recent.data.get("total_entries", 0)
    print(f"  Total entries: {total}")
    if total == 5:
        print("  PASS: 5 entries (4 new + 1 dedup = 5 unique)")
    else:
        print(f"  FAIL: expected 5, got {total}")

    print()
    print("All tests complete.")


asyncio.run(test())
