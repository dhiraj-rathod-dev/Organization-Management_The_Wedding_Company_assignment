
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime
from app.auth import get_current_admin
from app.utils import hash_password, verify_password, create_jwt_token, decode_jwt_token
from app.db import orgs_collection, admins_collection, master_db
from app.schemas import OrgCreate, OrgGet, OrgUpdate, OrgDelete, AdminLogin
from pymongo import errors

app = FastAPI(title="Organization Management Service")

security = HTTPBearer()

def org_collection_name(name: str) -> str:
    safe = name.strip().lower().replace(" ", "_")
    return f"org_{safe}"

# -----------------------------
# Create Organization
# -----------------------------
@app.post("/org/create")
def create_organization(payload: OrgCreate):
    org_name = payload.organization_name.strip()

    # Check duplicate name
    if orgs_collection.find_one({"organization_name": {"$regex": f"^{org_name}$", "$options": "i"}}):
        raise HTTPException(status_code=400, detail="Organization name already exists")

    # Create admin
    hashed_pw = hash_password(payload.password)
    admin_doc = {
        "email": payload.email.lower(),
        "password": hashed_pw,
        "organization_name": org_name,
        "created_at": datetime.utcnow()
    }
    admin_res = admins_collection.insert_one(admin_doc)
    admin_id = admin_res.inserted_id

    # Create tenant collection
    collection_name = org_collection_name(org_name)
    tenant_collection = master_db[collection_name]

    try:
        tenant_collection.insert_one({"_init": True})
        tenant_collection.delete_one({"_init": True})
    except:
        pass

    # Store in master org table
    orgs_collection.insert_one({
        "organization_name": org_name,
        "collection_name": collection_name,
        "admin_id": admin_id,
        "created_at": datetime.utcnow()
    })

    return {"status": "success", "organization": {"organization_name": org_name, "collection_name": collection_name}}


# -----------------------------
# Get Organization
# -----------------------------
@app.get("/org/get")
def get_organization(organization_name: str):
    org = orgs_collection.find_one(
        {"organization_name": {"$regex": f"^{organization_name}$", "$options": "i"}}
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "status": "success",
        "organization": {
            "organization_name": org["organization_name"],
            "collection_name": org["collection_name"],
            "admin_id": str(org["admin_id"]),
            "created_at": org["created_at"]
        }
    }


# -----------------------------
# Update Organization
# -----------------------------
@app.put("/org/update")
def update_organization(payload: OrgUpdate, current=Depends(get_current_admin)):

    admin_org = current["organization_name"].lower()
    old_org_name = payload.old_organization_name.strip().lower()
    new_org_name = payload.new_organization_name.strip()

    if admin_org != old_org_name:
        raise HTTPException(status_code=403, detail="You can only update your own organization")

    # Check new name availability
    if orgs_collection.find_one({"organization_name": {"$regex": f"^{new_org_name}$", "$options": "i"}}):
        raise HTTPException(status_code=400, detail="New organization name already exists")

    old_org = orgs_collection.find_one({"organization_name": {"$regex": f"^{old_org_name}$", "$options": "i"}})
    if not old_org:
        raise HTTPException(status_code=404, detail="Old organization not found")

    old_coll_name = old_org["collection_name"]
    new_coll_name = org_collection_name(new_org_name)

    # Copy collection data
    old_coll = master_db[old_coll_name]
    new_coll = master_db[new_coll_name]

    docs = list(old_coll.find({}))
    for d in docs:
        d.pop("_id", None)
    if docs:
        new_coll.insert_many(docs)

    # Update metadata
    orgs_collection.update_one(
        {"_id": old_org["_id"]},
        {"$set": {
            "organization_name": new_org_name,
            "collection_name": new_coll_name,
            "updated_at": datetime.utcnow()
        }}
    )

    # Update all admin records
    admins_collection.update_many(
        {"organization_name": old_org["organization_name"]},
        {"$set": {"organization_name": new_org_name}}
    )

    master_db.drop_collection(old_coll_name)

    return {
        "status": "success",
        "organization": {
            "organization_name": new_org_name,
            "collection_name": new_coll_name
        }
    }


# -----------------------------
# Delete Organization
# -----------------------------
@app.delete("/org/delete")
def delete_organization(payload: OrgDelete, current=Depends(get_current_admin)):

    admin_org = current["organization_name"].lower()
    req_org = payload.organization_name.strip().lower()

    if admin_org != req_org:
        raise HTTPException(status_code=403, detail="You can only delete your own organization")

    org = orgs_collection.find_one(
        {"organization_name": {"$regex": f"^{req_org}$", "$options": "i"}}
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    master_db.drop_collection(org["collection_name"])
    admins_collection.delete_many({"organization_name": org["organization_name"]})
    orgs_collection.delete_one({"_id": org["_id"]})

    return {"status": "success", "message": f"Organization {payload.organization_name} deleted"}


# -----------------------------
# Admin Login
# -----------------------------
@app.post("/admin/login")
def admin_login(payload: AdminLogin):

    admin = admins_collection.find_one({"email": payload.email.lower()})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, admin["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_payload = {
        "admin_id": str(admin["_id"]),
        "email": admin["email"],
        "organization_name": admin["organization_name"]
    }

    token = create_jwt_token(token_payload)

    return {"status": "success", "token": token}
