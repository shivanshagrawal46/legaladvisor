from fastapi.testclient import TestClient
from server import app
from api.auth import create_access_token

tok = create_access_token({"sub": "rakeshsir@mtreh.com"})
h = {"Authorization": f"Bearer {tok}"}
c = TestClient(app)

r = c.get("/api/dashboard/stats", headers=h)
print("dashboard:", r.status_code, "keys:", list(r.json().keys())[:6])

r = c.get("/api/portfolio/properties?is_david=true&limit=5", headers=h)
j = r.json()
print("portfolio:", r.status_code, "total:", j["total"], "row0:",
      {k: j["rows"][0][k] for k in ("address", "is_david", "insurance_in_force", "litigation_count")} if j["rows"] else None)

pid = j["rows"][0]["property_id"] if j["rows"] else None
if pid:
    r = c.get(f"/api/properties/{pid}", headers=h)
    d = r.json()
    print("detail:", r.status_code, "timeline:", len(d["timeline"]), "findings:", d["finding_counts"])

r = c.get("/api/findings?severity=critical", headers=h)
j = r.json()
print("findings:", r.status_code, "total:", j["total"], "facets:", j["facets"]["by_severity"])

r = c.get("/api/findings?limit=3", headers=h)
print("findings sample titles:", [i["title"][:40] for i in r.json()["items"][:3]])
