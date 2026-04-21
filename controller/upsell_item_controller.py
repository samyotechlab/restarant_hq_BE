from datetime import datetime, timezone
import math
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status
from models.upsell_item_model import PaginatedUpsellItemResponse, PopulateMenuItemOffer, UpsellItemCreate, UpsellItemResponse, UpsellItemUpdate


def _validate_object_id(oid: str, label: str = "ID") -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(oid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{oid}' is not a valid {label}.",
        )

async def _to_response(item: dict, db) -> UpsellItemResponse:
  populate_item = None
  if item.get('item'):
    try:
      menu_item = await db["menu_items"].find_one({"_id": ObjectId(item["item"])})
      if menu_item:
        populate_item = PopulateMenuItemOffer(
          menu_item_id=str(menu_item['_id']),
          item_no=menu_item.get('item_no'),
          item_name=menu_item.get('item_name'),
          category=menu_item.get('category'),
          base_price=menu_item.get('base_price'),
          online_price=menu_item.get('online_price'),
          available=menu_item.get('available'),
          dietary=menu_item.get('dietary'),
        )
    except Exception:
      populate_item = None
  
  return UpsellItemResponse(
    id=str(item["_id"]),
    item=populate_item,
    original_price=item["original_price"],
    offer_price=item["offer_price"],
    offer_percentage=item["offer_percentage"],
    available=item['available'],
    created_at=item['created_at'],
    updated_at=item['updated_at']
  )


class UpsellItemController:
  @staticmethod
  async def create_upsell_item(data: UpsellItemCreate, db) -> UpsellItemResponse:
    _validate_object_id(data.item, "Menu Item ID")
    now = datetime.now(timezone.utc)
    item_doc = {
      "item": ObjectId(data.item),
      "upsell_item_id": f"UPSELL-{uuid4().hex[:8].upper()}",
      "original_price": data.original_price,
      "offer_price": data.offer_price,
      "offer_percentage": data.offer_percentage,
      "available": data.available,
      "created_at": now,
      "updated_at": now,
    }
    print(item_doc)
    result = await db['upsell_items'].insert_one(item_doc)
    item_doc['_id'] = result.inserted_id

    return await _to_response(item_doc, db)
  
  @staticmethod
  async def get_all_upsell_item_paginated(db, page:int = 1, limit:int=10) -> PaginatedUpsellItemResponse:
    skip = (page - 1) * limit
    total = await db['upsell_items'].count_documents({})
    item_offer = await db['upsell_items'].find().skip(skip).limit(limit).to_list(length=None)
    return PaginatedUpsellItemResponse(
      total_results=total,
      limit=limit,
      page=page,
      total_pages=math.ceil(total/limit),
      data=[await _to_response(i, db) for i in item_offer]
    )
  
  @staticmethod
  async def get_item_by_id(offer_id: str, db) -> UpsellItemResponse:
      _validate_object_id(offer_id)
      doc = await db["upsell_items"].find_one({"_id": ObjectId(offer_id)})
      if not doc:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
      return await _to_response(doc, db)
  
  @staticmethod
  async def get_all(db):
    item_offers = await db['upsell_items'].find().sort('created_at', -1).to_list(length=None)
    return [await _to_response(u, db) for u in item_offers]
  
  @staticmethod
  async def update_upsell_item(offer_id: str, data: UpsellItemUpdate, db) -> UpsellItemResponse:
    _validate_object_id(offer_id, "Item Offer ID")

    existing_offer = await db['upsell_items'].find_one({"_id": ObjectId(offer_id)})
    if data.item:
      _validate_object_id(data.item, "Menu Item ID")

    if not existing_offer:
      raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Item offer not found.",
    )
    update_doc = {}
    now = datetime.now(timezone.utc)

    if data.item is not None:
      _validate_object_id(data.item, "Menu Item ID")
      update_doc["item"] = ObjectId(data.item)
    if data.original_price is not None:
        update_doc["original_price"] = data.original_price
    if data.offer_price is not None:
        update_doc["offer_price"] = data.offer_price
    if data.offer_percentage is not None:
        update_doc["offer_percentage"] = data.offer_percentage
    if data.available is not None:
        update_doc["available"] = data.available

    base_price = update_doc.get("original_price", existing_offer.get("original_price"))
    offer_price = update_doc.get("offer_price", existing_offer.get("offer_price"))
    if base_price is not None and offer_price is not None:
      if offer_price >= base_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer price must be less than base price.",
        )
    if update_doc:
      update_doc["updated_at"] = now
      await db["upsell_items"].update_one(
          {"_id": ObjectId(offer_id)},
          {"$set": update_doc},
      )
    updated_offer = await db["upsell_items"].find_one(
        {"_id": ObjectId(offer_id)}
    )
    return await _to_response(updated_offer, db)
     
  @staticmethod
  async def remove_upsell_item(offer_id: str, db) -> dict:
    _validate_object_id(offer_id, "Item Offer ID")
    result = await db['upsell_items'].delete_one({"_id": ObjectId(offer_id)})
    if result.deleted_count == 0:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
    return {"deleted item offer": offer_id}
