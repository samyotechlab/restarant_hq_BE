import math
from bson import ObjectId
from fastapi import HTTPException
from models.catering_quotation_model import CateringQuotationResponse, CreateCateringQuotation, PaginatedCateringQuotationResponse, UpdateCateringQuotation
from datetime import datetime, timezone

class CateringQuotationController:
  @staticmethod
  def _to_response(doc: dict) -> CateringQuotationResponse:
      doc = dict(doc)
      doc["id"] = str(doc.pop("_id"))
      return CateringQuotationResponse(**doc)

  @staticmethod
  def _compute_totals(data: dict) -> dict:
    revenue_qty = float(data.get("revenue_qty", 0) or 0)
    revenue_rate = float(data.get("revenue_rate", 0) or 0)
    total_revenue = round(revenue_qty * revenue_rate, 2)

    food_cost_qty = float(data.get("food_cost_qty", 0) or 0)
    food_cost_rate = float(data.get("food_cost_rate", 0) or 0)
    food_cost = round(food_cost_qty * food_cost_rate, 2)

    staff_cost_qty = float(data.get("staff_cost_qty", 0) or 0)
    staff_cost_rate = float(data.get("staff_cost_rate", 0) or 0)
    staff_cost = round(staff_cost_qty * staff_cost_rate, 2)

    full_day_service_qty = float(data.get("full_day_service_qty", 0) or 0)
    full_day_service_rate = float(data.get("full_day_service_rate", 0) or 0)
    full_day_service = round(full_day_service_qty * full_day_service_rate, 2)

    half_day_service_qty = float(data.get("half_day_service_qty", 0) or 0)
    half_day_service_rate = float(data.get("half_day_service_rate", 0) or 0)
    half_day_service = round(half_day_service_qty * half_day_service_rate, 2)

    outsourced_service_qty = float(data.get("outsourced_service_qty", 0) or 0)
    outsourced_service_rate = float(data.get("outsourced_service_rate", 0) or 0)
    outsourced_service = round(outsourced_service_qty * outsourced_service_rate, 2)

    transport_qty = float(data.get("transport_qty", 0) or 0)
    transport_rate = float(data.get("transport_rate", 0) or 0)
    transport = round(transport_qty * transport_rate, 2)

    decoration_qty = float(data.get("decoration_qty", 0) or 0)
    decoration_rate = float(data.get("decoration_rate", 0) or 0)
    decoration = round(decoration_qty * decoration_rate, 2)

    glasses_etc_qty = float(data.get("glasses_etc_qty", 0) or 0)
    glasses_etc_rate = float(data.get("glasses_etc_rate", 0) or 0)
    glasses_etc = round(glasses_etc_qty * glasses_etc_rate, 2)

    other_rentals_qty = float(data.get("other_rentals_qty", 0) or 0)
    other_rentals_rate = float(data.get("other_rentals_rate", 0) or 0)
    other_rentals = round(other_rentals_qty * other_rentals_rate, 2)

    total_c2 = round( food_cost + staff_cost + full_day_service + half_day_service + outsourced_service, 2)

    total_c3 = round(transport + decoration + glasses_etc + other_rentals, 2)

    total_costs = round(total_c2 + total_c3, 2)
    gross_profit = round(total_revenue - total_costs, 2)
    gross_margin_pct = round(
        ((gross_profit / total_revenue) * 100) if total_revenue else 0,
        2,
    )

    status = "approved" if gross_margin_pct >= 30 else "pending"

    return {
      "revenue_qty": revenue_qty,
      "revenue_rate": revenue_rate,
      "total_revenue": total_revenue,

      "food_cost_qty": food_cost_qty,
      "food_cost_rate": food_cost_rate,
      "food_cost": food_cost,

      "staff_cost_qty": staff_cost_qty,
      "staff_cost_rate": staff_cost_rate,
      "staff_cost": staff_cost,

      "full_day_service_qty": full_day_service_qty,
      "full_day_service_rate": full_day_service_rate,
      "full_day_service": full_day_service,

      "half_day_service_qty": half_day_service_qty,
      "half_day_service_rate": half_day_service_rate,
      "half_day_service": half_day_service,

      "outsourced_service_qty": outsourced_service_qty,
      "outsourced_service_rate": outsourced_service_rate,
      "outsourced_service": outsourced_service,

      "transport_qty": transport_qty,
      "transport_rate": transport_rate,
      "transport": transport,

      "decoration_qty": decoration_qty,
      "decoration_rate": decoration_rate,
      "decoration": decoration,

      "glasses_etc_qty": glasses_etc_qty,
      "glasses_etc_rate": glasses_etc_rate,
      "glasses_etc": glasses_etc,

      "other_rentals_qty": other_rentals_qty,
      "other_rentals_rate": other_rentals_rate,
      "other_rentals": other_rentals,

      "total_c2": total_c2,
      "total_c3": total_c3,
      "total_costs": total_costs,
      "gross_profit": gross_profit,
      "gross_margin_pct": gross_margin_pct,
      "status": status,
  }

  @staticmethod
  def _sync_pax_rates(data: dict) -> dict:
      estimated_pax = float(data.get("estimated_pax", 0) or 0)
      quoted_price_per_pax = float(data.get("quoted_price_per_pax", 0) or 0)
      food_cost_per_pax = float(data.get("food_cost_per_pax", 0) or 0)

      if estimated_pax > 0:
          data["revenue_qty"] = estimated_pax
          data["food_cost_qty"] = estimated_pax

      data["revenue_rate"] = quoted_price_per_pax
      data["food_cost_rate"] = food_cost_per_pax
      return data
  
  @staticmethod
  async def create_quotation(data: CreateCateringQuotation, db):
    quotation_doc = data.model_dump()
    quotation_doc = CateringQuotationController._sync_pax_rates(quotation_doc)
    quotation_doc.update(CateringQuotationController._compute_totals(quotation_doc))

    now = datetime.now(timezone.utc)
    quotation_doc["created_at"] = now
    quotation_doc["updated_at"] = now

    result = await db["catering_quotation"].insert_one(quotation_doc)
    created = await db["catering_quotation"].find_one({"_id": result.inserted_id})
    return CateringQuotationController._to_response(created)
  
  @staticmethod
  async def get_quotation_paginated(page: int, limit: int, db):
    skip = (page - 1) * limit
    total = await db['catering_quotation'].count_documents({})
    docs = await db['catering_quotation'].find().skip(skip).sort('created_at', -1).limit(limit).to_list(length=None)
    data = [CateringQuotationController._to_response(doc) for doc in docs]
    return PaginatedCateringQuotationResponse(
      page=page,
      total_pages=math.ceil(total / limit),
      limit=limit,
      total_results=total,
      data=data
    )
  
  @staticmethod
  async def get_quotation_by_id(quotation_id: str, db):
    quot = await db['catering_quotation'].find_one({"_id": ObjectId(quotation_id)})
    if not quot:
      raise HTTPException(status_code=404, detail="Catering Quotation not found!")
    return CateringQuotationController._to_response(quot)
  
  @staticmethod
  async def update_quotation(quotation_id: str, db, update_data: UpdateCateringQuotation):
    exist = await db['catering_quotation'].find_one({"_id": ObjectId(quotation_id)})
    if not exist:
      raise HTTPException(status_code=404, detail="Catering Quotation not found!")
    
    update_body = update_data.model_dump(exclude_unset=True)
    if not update_body:
      raise HTTPException(status_code=400, detail="Provide fields to update")
    
    if update_body:
      update_body['updated_at'] = datetime.now(timezone.utc)

    merged = {**exist, **update_body}
    merged = CateringQuotationController._sync_pax_rates(merged)
    recalculated = CateringQuotationController._compute_totals(merged)
    update_body.update(recalculated)
    update_body["updated_at"] = datetime.now(timezone.utc)

    await db["catering_quotation"].update_one(
        {"_id": ObjectId(quotation_id)},
        {"$set": update_body}
    )
    updated = await db['catering_quotation'].find_one({"_id": ObjectId(quotation_id)})
    return CateringQuotationController._to_response(updated)
    
  @staticmethod
  async def update_quotation_status(quotation_id: str, db, payload):
    exist = await db["catering_quotation"].find_one({"_id": ObjectId(quotation_id)})
    if not exist:
        raise HTTPException(status_code=404, detail="Catering Quotation not found!")

    update_body = {
      "status": payload["status"],
      "updated_at": datetime.now(timezone.utc)
    }

    await db["catering_quotation"].update_one(
      {"_id": ObjectId(quotation_id)},
      {"$set": update_body}
    )

    updated = await db["catering_quotation"].find_one({"_id": ObjectId(quotation_id)})
    return CateringQuotationController._to_response(updated)
  
  @staticmethod
  async def delete_quotation(quotation_id, db):
    exist = await db['catering_quotation'].find_one({"_id": ObjectId(quotation_id)})
    if not exist:
      raise HTTPException(status_code=404, detail="Catering Quotation not found!")
    
    await db['catering_quotation'].delete_one({"_id": ObjectId(quotation_id)})
    return CateringQuotationController._to_response(exist)