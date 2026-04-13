import io
import math
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from difflib import SequenceMatcher
import pandas as pd
from thefuzz import process, fuzz


PROGRESS_EVERY = 50


# ─── NORMALIZATION TABLES ─────────────────────────────────────────────────────
_FRACTION_MAP = {
    "1/4": "250", "1/2": "500", "3/4": "750",
    "¼":   "250", "½":   "500", "¾":   "750",
}
_UNIT_ALIASES = [
    (r"\bkgs?\b",     "kg"),
    (r"\bgrams?\b",   "gm"),
    (r"\bgrms?\b",    "gm"),
    (r"\bg\b",        "gm"),
    (r"\bpcs\b",      "pc"),
    (r"\bpieces?\b",  "pc"),
    (r"\bltrs?\b",    "litre"),
    (r"\bliters?\b",  "litre"),
]
_SPELLING_MAP = {
    " rasmalai":    " reshmi rasmalai",
    " ras malai":   " reshmi rasmalai",
    " ras gulla":   " rasgulla",
    " kanpoori":    " kanpuri",
    " lado ":       " ladoo ",
    " ladu ":       " ladoo ",
    " laddu ":      " ladoo ",
    "chamcham":     "cham cham",
    "butte pav":    "butter pav",
    "muimbai":      "mumbai",
    " bese":        " base",
    "keasr":        "kesar",
    "ragulla":      "rasgulla",
    "lacch ":       "lachha ",
    "urnt garlic":  "burnt garlic",
    "vada pao":     "vada pav",
    "papdichaat":   "papdi chaat",
}
_QTY_TOKENS = {
    "1","2","3","4","5","6","8","10","12","20","50","100","250","500","750","1000",
    "pc","pcs","gm","gms","kg","ml","litre","x2","x4","x","serves","pack","pkt",
    "packet","small","big","large","medium","box","thali","per","no",
}


def _normalize(name: str) -> str:
    name = unicodedata.normalize("NFKC", name)
    name = name.lower().strip()
    for frac, val in _FRACTION_MAP.items():
        name = name.replace(frac, val)
    name = re.sub(r"[\(\)\[\]]", " ", name)
    name = re.sub(r"[^\w\s]", " ", name)
    for pattern, replacement in _UNIT_ALIASES:
        name = re.sub(pattern, replacement, name)
    padded = " " + name + " "
    for wrong, right in _SPELLING_MAP.items():
        padded = padded.replace(wrong, right)
    name = padded.strip()
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _core_tokens(norm_name: str) -> frozenset:
    return frozenset(t for t in norm_name.split() if t not in _QTY_TOKENS and len(t) > 1)


def _token_set_ratio(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _split_combo(name: str) -> list:
    parts = re.split(r"\s*[+&]\s*", name)
    return [p.strip() for p in parts if p.strip()]


# ─── MANUAL MAP ───────────────────────────────────────────────────────────────
MANUAL_MAP = {
    # Puri variants
    "pani puri pkt":                            "Iftaar Pani Puri Share Pack",
    "puri pkt":                                 "Mumbai Puri 1 Pcs",
    "puri packet":                              "Mumbai Puri 1 Pcs",
    "muimbai puri":                             "Mumbai Puri 1 Pcs",
    "muimbai puri bhaji":                       "Mumbai Puri Bhaji",
    # Chutneys
    "sweet chutney":                            "Hot N Sweet Chili Pickle",
    "sweet chatney":                            "Hot N Sweet Chili Pickle",
    "sweet bundi":                              "Mithi Bundi",
    # Jalebi Rabdi
    "jalebi rabdi":                             "Coin Jalebi With Rabdi (250 gm)",
    # Chaat
    "sev puri":                                 "Mumbai Sev Batata Puri",
    "chaana chaat":                             "Chana Chaat",
    "churmur chura":                            "Kolkata Churmur Chaat",
    "churmur papdi":                            "Kolkata Churmur Chaat",
    "dahi vada":                                "Iftaar Special Dahi Bhalla",
    # Bengali sweets — GOTI=1pc, BASE=2pc
    "ras gulla":                                "Rasgulla (2 pc)",
    "angoori ras gulla":                        "Angoori Rasgulla",
    "rasmalai goti":                            "Reshmi Rasmalai (1 pc)",
    "rasmalai base":                            "Reshmi Rasmalai (2 pc)",
    "ras malai goti":                           "Reshmi Rasmalai (1 pc)",
    "reshmi ras malai":                         "Reshmi Rasmalai (2 pc)",
    "cham cham goti":                           "Milk Cham Cham (1 pc)",
    "chamcham goti":                            "Milk Cham Cham (1 pc)",
    "cham cham base":                           "Milk Cham Cham (2 pc)",
    "malai sandwich goti":                      "Malai Sandwich (1 pc)",
    "malai sandwich base":                      "Malai Sandwich (2 pc)",
    "kheer kadam goti":                         "Kheer Kadam (1 pc)",
    "kheer kadam base":                         "Kheer Kadam (2 pc)",
    "petha paan base":                          "Petha Paan (2 pc)",
    "petha paan bese":                          "Petha Paan (2 pc)",
    "petha paan thali":                         "Petha Paan (2 pc)",
    # Ladoo
    "kanpoori lado":                            "Kanpuri Ladoo (500 gm)",
    "kanpuri lado jalebi":                      "Kanpuri Ladoo (500 gm)",
    "pista paan ladu":                          "Pista Paan Ladoo (250 gm)",
    # Barfi
    "kesar barfi":                              "Bikaneri Keasr Barfi (250 gm)",
    "chocolate barfi":                          "Jaipur Chocolate  Mawa Barfi (250 gm)",
    "kala kand besan lado":                     "Plain Kala Kand (250 gm)",
    "kala kand besan ladoo":                    "Plain Kala Kand (250 gm)",
    # Sandwich
    "paneer veg sandwich":                      "Mumbai Paneer  Sandwich (Plain)",
    "paneer  veg sandwich":                     "Mumbai Paneer  Sandwich (Plain)",
    # Chinese
    "baby corn dragon":                         "Baby Corn Chilli",
    "dragon baby corn":                         "Baby Corn Chilli",
    "veg exotic veg":                           "Exotic Veg Stir Fry",
    "veg lollipop":                             "Chinese Thali",
    # Vada Pav
    "cheese grill vada pav":                    "Mumbai Cheese Vada Pav",
    "cheese grilled vada pav":                  "Mumbai Cheese Vada Pav",
    # Beverages
    "kolkata soda":                             "Kolkata Victoria Soda",
    "soda masala":                              "Kolkata Victoria Soda",
    # Misc
    "mix masala":                               "Masala Nimki",
    "kala masala":                              "Khakra Masala",
    "gheyar":                                   "Big Dry Ghewar",
    "mix farsan":                               "Salli Mixture",
    "lunch thali":                              "Business Thali",
    "phulka":                                   "Tawa Roti X2",
    "urnt garlic hakka noodles":                "Burnt Galic Hakka Noodle",
    "butte pav":                                "Butter Pav (1 Pcs)",
    "fruit masala":                             "Mausambi Masala",
    "corn masala":                              "Honey Chilli Potatoes",
    "laccha paratha":                           "Tawa Lachha Paratha",
    "tawa lacch":                               "Tawa Lachha Paratha",
    "kaju tarbooz thali":                       "Kaju Pista Tarbooz (250 gm)",
    # Combos → representative item
    "jalebi malai sandwich cham cham":          "Malai Sandwich (1 pc)",
    "besan barfi angoori gulab jamun":          "Angoori Gulab Jamun",
    "kheer kadam cham cham bun maska":          "Kheer Kadam (2 pc)",
    "kala jamun ragulla malai sandwich ras malai": "Kala Jamun (2 pc)",
    "kala jamun gulab jamun lancha kheer kadam ras gulla": "Kala Jamun (2 pc)",
    "kala jamun gulab jamun lancha kheer kadam rasgulla": "Kala Jamun (2 pc)",
    "reshmi rasmalai bhalla papdi chaat":       "Reshmi Rasmalai (2 pc)",
    "baked rasgulla pva bhaji":                 "Baked Rasgulla (2 pc)",
    "kanpuri ladoo jalebi":                     "Kanpuri Ladoo (500 gm)",
}

# ─── SKIP keywords — non-menu items ──────────────────────────────────────────
_SKIP_SUBSTRINGS = [
    "catering event", "charity", "transport charge", "glass rental",
    "invoice wi", "hi tea pax", " pax", "special event", "sepcial event",
    "jalebi syrup", "sugar syrup", "dates thali", " sauf",
    "fancy box", "samll box", "snack box", "usal mixture",
    "malai for ghewar", "coin jaleb18", "special hi tea",
]

# ─── PERMANENTLY UNLINK — genuinely not in menu ───────────────────────────────
_UNLINK_SUBSTRINGS = [
    "mix dry fruit box",
    "kaju tasty",
]


# ─── Menu Cache ───────────────────────────────────────────────────────────────
_menu_cache: list = []
_menu_norm_index: dict = {}
_menu_name_index: dict = {}
_menu_sn_index:   dict = {}


async def _load_menu_cache(db):
    global _menu_cache, _menu_norm_index, _menu_name_index, _menu_sn_index
    if _menu_cache:
        return
    _menu_cache = await db["menu_items"].find(
        {}, {"_id": 1, "item_name": 1, "search_name": 1}
    ).to_list(length=None)
    for doc in _menu_cache:
        raw = doc.get("item_name", "") or ""
        sn  = doc.get("search_name", "") or ""
        _menu_norm_index[_normalize(raw)] = doc
        _menu_name_index[raw.lower()] = doc
        if sn:
            _menu_sn_index[sn] = doc
            _menu_norm_index[_normalize(sn)] = doc


def clear_menu_cache():
    global _menu_cache, _menu_norm_index, _menu_name_index, _menu_sn_index
    _menu_cache = []
    _menu_norm_index = {}
    _menu_name_index = {}
    _menu_sn_index   = {}
# ─────────────────────────────────────────────────────────────────────────────


def _safe_float(val):
    try:
        v = float(val)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _safe_str(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "") else None


def _parse_phone(raw_phone: str):
    if not raw_phone:
        return None, None
    cleaned = re.sub(r"[\s\-()]", "", raw_phone).strip()
    if cleaned.startswith("+971"):
        return "+971", cleaned[4:]
    if cleaned.startswith("971") and len(cleaned) >= 11:
        return "+971", cleaned[3:]
    if cleaned.startswith("0") and len(cleaned) >= 9:
        return "+971", cleaned[1:]
    return None, cleaned


def _make_search_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _normalize_item_name(name: str) -> str:
    if not name:
        return name
    name = re.sub(r" {2,}", " ", name)
    name = re.sub(r"\(\s+", "(", name)
    name = re.sub(r"\s+\)", ")", name)
    return name.strip()


# ═════════════════════════════════════════════════════════════════════════════
# 5-PASS MATCHER
# ═════════════════════════════════════════════════════════════════════════════

def _run_5pass(query_norm: str) -> Optional[dict]:
    # Pass 1: Exact
    if query_norm in _menu_norm_index:
        return _menu_norm_index[query_norm]

    qcore        = _core_tokens(query_norm)
    qcore_sorted = " ".join(sorted(qcore))

    # Pass 2: Core-token exact
    for mnorm, doc in _menu_norm_index.items():
        mc = _core_tokens(mnorm)
        if qcore_sorted == " ".join(sorted(mc)) and qcore_sorted:
            return doc

    best_doc, best_score = None, 0.0

    for mnorm, doc in _menu_norm_index.items():
        mc = _core_tokens(mnorm)

        # Pass 3: Full token-set ratio ≥ 0.70
        s3 = _token_set_ratio(query_norm, mnorm)
        if s3 >= 0.70 and s3 > best_score:
            best_doc, best_score = doc, s3

        # Pass 4: Core token-set ratio ≥ 0.65
        if qcore and mc:
            s4 = _token_set_ratio(" ".join(qcore), " ".join(mc))
            if s4 >= 0.65 and s4 > best_score:
                best_doc, best_score = doc, s4

        # Pass 5: SequenceMatcher on sorted core ≥ 0.75
        if qcore and mc:
            s5 = _seq_ratio(qcore_sorted, " ".join(sorted(mc)))
            if s5 >= 0.75 and s5 > best_score:
                best_doc, best_score = doc, s5

    return best_doc if best_score >= 0.45 else None


# ═════════════════════════════════════════════════════════════════════════════
# MAIN FIND FUNCTION — 7 passes total
# ═════════════════════════════════════════════════════════════════════════════

async def _find_menu_item(item_name: str, db) -> Optional[dict]:
    await _load_menu_cache(db)

    normalized = _normalize_item_name(item_name)
    norm_key   = _normalize(normalized)
    lower_key  = normalized.lower()
    sn_key     = _make_search_name(normalized)

    # Pass 0: Skip / Unlink check
    for kw in _SKIP_SUBSTRINGS:
        if kw in norm_key:
            return None
    for kw in _UNLINK_SUBSTRINGS:
        if kw in norm_key:
            return None

    # Pass 1: Manual map
    if norm_key in MANUAL_MAP:
        target = MANUAL_MAP[norm_key]
        t_low  = target.lower()
        if t_low in _menu_name_index:
            return _menu_name_index[t_low]
        t_norm = _normalize(target)
        if t_norm in _menu_norm_index:
            return _menu_norm_index[t_norm]

    # Pass 2: Exact name (case-insensitive)
    if lower_key in _menu_name_index:
        return _menu_name_index[lower_key]

    # Pass 3: Exact search_name
    if sn_key in _menu_sn_index:
        return _menu_sn_index[sn_key]

    # Pass 4: 5-pass smart matcher
    doc = _run_5pass(norm_key)
    if doc:
        return doc

    # Pass 5: Combo split → 5-pass on each part
    parts = _split_combo(item_name)
    if len(parts) > 1:
        combo_norm = _normalize(" ".join(parts))
        if combo_norm in MANUAL_MAP:
            target = MANUAL_MAP[combo_norm]
            t_low  = target.lower()
            if t_low in _menu_name_index:
                return _menu_name_index[t_low]
        for part in parts:
            d = _run_5pass(_normalize(part))
            if d:
                return d

    # Pass 6: thefuzz fallback
    all_sns = list(_menu_sn_index.keys())
    if all_sns:
        result = process.extractOne(sn_key, all_sns, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= 70:
            return _menu_sn_index[result[0]]

    # Pass 7: DB regex last resort
    words = [w for w in sn_key.split() if len(w) > 2]
    if words:
        candidates = await db["menu_items"].find(
            {"search_name": {"$regex": re.escape(words[0]), "$options": "i"}}
        ).to_list(length=30)
        for c in candidates:
            cand = c.get("search_name") or _make_search_name(c.get("item_name", ""))
            ow = set(re.findall(r"[a-z0-9]+", sn_key))
            mw = set(re.findall(r"[a-z0-9]+", cand))
            if ow and mw and len(ow & mw) / len(ow) >= 0.80:
                return c

    return None


# ═════════════════════════════════════════════════════════════════════════════
# BULK UPLOAD JOB PROCESSOR
# ═════════════════════════════════════════════════════════════════════════════

async def _process_bulk_upload_job(job_id: str, file_path: str, db):
    clear_menu_cache()
    await db["order_bulk_jobs"].update_one(
        {"job_id": job_id},
        {"$set": {"status": "processing", "started_at": datetime.now(timezone.utc)}}
    )

    customers_created = 0
    customers_found   = 0
    orders_skipped    = 0
    orders_created    = 0
    skipped_no_phone  = 0
    items_not_found   = []
    errors            = []
    processed         = 0

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        if file_path.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content), header=5)

        df.columns = df.columns.str.strip()
        df["Invoice No."] = pd.to_numeric(df["Invoice No."], errors="coerce")
        df = df[df["Invoice No."].notna()]
        df["Invoice No."] = df["Invoice No."].astype(int).astype(str)

        grouped        = df.groupby("Invoice No.", sort=False)
        total_invoices = len(grouped)

        await db["order_bulk_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {"total_invoices": total_invoices}}
        )

        clear_menu_cache()

        for invoice_no, group in grouped:
            first = group.iloc[0]

            try:
                raw_phone = _safe_str(first.get("Phone"))
                if not raw_phone:
                    skipped_no_phone += 1
                    processed += 1
                    continue

                country_code, phone_number = _parse_phone(raw_phone)
                if not phone_number:
                    skipped_no_phone += 1
                    processed += 1
                    continue

                cust_name = _safe_str(first.get("Name"))
                address   = _safe_str(first.get("Address"))

                existing = await db["customers"].find_one(
                    {"phone_number": {"$regex": re.escape(phone_number), "$options": "i"}}
                )
                if not existing and cust_name:
                    existing = await db["customers"].find_one(
                        {"name": {"$regex": f"^{re.escape(cust_name)}$", "$options": "i"}}
                    )

                if existing:
                    customer_id = str(existing["_id"])
                    customers_found += 1
                else:
                    new_cust = {
                        "name":         cust_name or "Unknown",
                        "country_code": country_code if country_code else "+971",
                        "phone_number": phone_number,
                        "email":        None,
                        "address":      address,
                        "orders":       [],
                        "status":       "new",
                        "created_at":   datetime.now(timezone.utc),
                        "updated_at":   datetime.now(timezone.utc),
                    }
                    ins = await db["customers"].insert_one(new_cust)
                    customer_id = str(ins.inserted_id)
                    customers_created += 1

                order_items  = []
                agg_sub = agg_discount = agg_tax = agg_grand = agg_vat = 0.0

                for _, row in group.iterrows():
                    item_name = _safe_str(row.get("Item Name"))
                    if not item_name:
                        continue

                    menu_item    = await _find_menu_item(item_name, db)
                    menu_item_id = str(menu_item["_id"]) if menu_item else None

                    if not menu_item:
                        items_not_found.append({
                            "invoice_no": invoice_no,
                            "item_name":  item_name,
                        })

                    price       = _safe_float(row.get("Price"))
                    qty         = _safe_float(row.get("Qty."))
                    sub_total   = _safe_float(row.get("Sub Total"))   or 0.0
                    discount    = _safe_float(row.get("Discount"))    or 0.0
                    tax         = _safe_float(row.get("Tax"))         or 0.0
                    final_total = _safe_float(row.get("Final Total")) or 0.0
                    vat_rate    = _safe_float(row.get("VAT Rate"))
                    vat_amount  = _safe_float(row.get("VAT Amount"))  or 0.0
                    non_taxable = _safe_str(row.get("Non Taxable"))

                    order_items.append({
                        "menu_item":   menu_item_id,
                        "item_name":   item_name,
                        "variation":   _safe_str(row.get("Variation")),
                        "category":    _safe_str(row.get("Category")),
                        "group_name":  _safe_str(row.get("Group Name")),
                        "hsn":         _safe_str(row.get("HSN")),
                        "price":       price,
                        "quantity":    qty,
                        "sub_total":   sub_total,
                        "discount":    discount,
                        "tax":         tax,
                        "vat_rate":    vat_rate,
                        "vat_amount":  vat_amount,
                        "non_taxable": non_taxable in ("1", "True", "true"),
                        "final_total": final_total,
                    })

                    agg_sub      += sub_total
                    agg_discount += discount
                    agg_tax      += tax
                    agg_grand    += final_total
                    agg_vat      += vat_amount

                raw_pay = _safe_str(first.get("Payment Type")) or "Pending"
                payment = {"cash": "Cash", "card": "Card", "online": "Online"}.get(
                    raw_pay.lower(), "Pending"
                )

                raw_status = _safe_str(first.get("Status")) or "Pending"
                ord_status = {"success": "Success", "failed": "Failed", "pending": "Pending"}.get(
                    raw_status.lower(), "Pending"
                )

                order_date = order_timestamp = None
                date_val = first.get("Date")
                if date_val is not None and str(date_val).strip() not in ("", "nan", "NaT"):
                    try:
                        order_date = pd.to_datetime(str(date_val)).to_pydatetime()
                    except Exception:
                        pass

                ts_val = first.get("Timestamp")
                if ts_val is not None and str(ts_val).strip() not in ("", "nan", "NaT"):
                    try:
                        order_timestamp = pd.to_datetime(str(ts_val)).to_pydatetime()
                    except Exception:
                        pass

                order_doc = {
                    "order_id":        f"ORD-{uuid.uuid4().hex[:8].upper()}",
                    "invoice_no":      invoice_no,
                    "order_date":      order_date,
                    "order_timestamp": order_timestamp,
                    "order_type":      _safe_str(first.get("Order Type")),
                    "area":            _safe_str(first.get("Area")),
                    "table_no":        _safe_str(first.get("Table No.")),
                    "covers":          _safe_float(first.get("Covers")),
                    "server_name":     _safe_str(first.get("Server Name")),
                    "assign_to":       _safe_str(first.get("Assign To")),
                    "customer":        ObjectId(customer_id),
                    "items":           order_items,
                    "sub_total":       round(agg_sub, 2),
                    "discount":        round(agg_discount, 2),
                    "tax":             round(agg_tax, 2),
                    "grand_total":     round(agg_grand, 2),
                    "vat_amount":      round(agg_vat, 2),
                    "non_taxable":     _safe_float(first.get("Non Taxable")),
                    "gst":             _safe_str(first.get("GST")),
                    "payment_method":  payment,
                    "status":          ord_status,
                    "is_paid":         ord_status == "Success",
                    "notes":           None,
                    "created_at":      datetime.now(timezone.utc),
                    "updated_at":      datetime.now(timezone.utc),
                }

                existing_order = await db["orders"].find_one(
                    {"invoice_no": invoice_no}, {"_id": 1}
                )
                if existing_order:
                    orders_skipped += 1
                else:
                    ins_order = await db["orders"].insert_one(order_doc)
                    await db["customers"].update_one(
                        {"_id": ObjectId(customer_id)},
                        {
                            "$addToSet": {"orders": ins_order.inserted_id},
                            "$set":      {"updated_at": datetime.now(timezone.utc)},
                        }
                    )
                    orders_created += 1

            except Exception as e:
                errors.append({"invoice_no": invoice_no, "error": str(e)})

            processed += 1

            if processed % PROGRESS_EVERY == 0:
                await db["order_bulk_jobs"].update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "processed_invoices": processed,
                        "customers_created":  customers_created,
                        "customers_found":    customers_found,
                        "orders_created":     orders_created,
                        "skipped_no_phone":   skipped_no_phone,
                        "items_not_found":    items_not_found[-100:],
                        "errors":             errors[-50:],
                    }}
                )

        await db["order_bulk_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {
                "status":             "completed",
                "processed_invoices": processed,
                "total_invoices":     total_invoices,
                "customers_created":  customers_created,
                "customers_found":    customers_found,
                "orders_created":     orders_created,
                "skipped_no_phone":   skipped_no_phone,
                "items_not_found":    items_not_found,
                "errors":             errors,
                "completed_at":       datetime.now(timezone.utc),
            }}
        )

    except Exception as e:
        await db["order_bulk_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {
                "status":       "failed",
                "errors":       [{"error": str(e)}],
                "completed_at": datetime.now(timezone.utc),
            }}
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)