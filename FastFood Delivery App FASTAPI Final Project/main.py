from fastapi import FastAPI, Query, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# ------------------ DATA ------------------

menu = [
    {"id": 1, "name": "Pizza", "price": 200, "category": "Pizza", "is_available": True},
    {"id": 2, "name": "Burger", "price": 120, "category": "Burger", "is_available": True},
    {"id": 3, "name": "Coke", "price": 50, "category": "Drink", "is_available": True},
    {"id": 4, "name": "Fries", "price": 90, "category": "Snack", "is_available": False},
    {"id": 5, "name": "Ice Cream", "price": 80, "category": "Dessert", "is_available": True},
    {"id": 6, "name": "Pasta", "price": 180, "category": "Main", "is_available": True},
]

orders = []
order_counter = 1

cart = []

# ------------------ HELPERS ------------------

def find_menu_item(item_id):
    for item in menu:
        if item["id"] == item_id:
            return item
    return None

def calculate_bill(price, quantity, order_type):
    total = price * quantity
    if order_type == "delivery":
        total += 30
    return total

def filter_menu_logic(category, max_price, is_available):
    result = menu
    if category is not None:
        result = [i for i in result if i["category"].lower() == category.lower()]
    if max_price is not None:
        result = [i for i in result if i["price"] <= max_price]
    if is_available is not None:
        result = [i for i in result if i["is_available"] == is_available]
    return result

# ------------------ MODELS ------------------

class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=20)
    delivery_address: str = Field(..., min_length=10)
    order_type: str = "delivery"

class NewMenuItem(BaseModel):
    name: str = Field(..., min_length=2)
    price: int = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    is_available: bool = True

class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str

# ------------------ DAY 1 ------------------

@app.get("/")
def home():
    return {"message": "Welcome to Food Delivery App"}

@app.get("/menu")
def get_menu():
    return {"items": menu, "total": len(menu)}

@app.get("/menu/summary")
def summary():
    return {
        "total": len(menu),
        "available": len([i for i in menu if i["is_available"]]),
        "categories": list(set([i["category"] for i in menu]))
    }

@app.get("/menu/{item_id}")
def get_item(item_id: int):
    item = find_menu_item(item_id)
    if not item:
        return {"error": "Item not found"}
    return item

@app.get("/orders")
def get_orders():
    return {"orders": orders, "total": len(orders)}

# ------------------ DAY 2 & 3 ------------------

@app.post("/orders")
def create_order(req: OrderRequest):
    global order_counter

    item = find_menu_item(req.item_id)
    if not item:
        raise HTTPException(404, "Item not found")

    if not item["is_available"]:
        raise HTTPException(400, "Item not available")

    total = calculate_bill(item["price"], req.quantity, req.order_type)

    order = {
        "order_id": order_counter,
        "customer": req.customer_name,
        "total": total
    }

    orders.append(order)
    order_counter += 1

    return order

@app.get("/menu/filter")
def filter_menu(
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    is_available: Optional[bool] = None
):
    data = filter_menu_logic(category, max_price, is_available)
    return {"items": data, "count": len(data)}

# ------------------ CRUD ------------------

@app.post("/menu")
def add_item(item: NewMenuItem, response: Response):
    for i in menu:
        if i["name"].lower() == item.name.lower():
            raise HTTPException(400, "Duplicate item")

    new_item = {"id": len(menu) + 1, **item.dict()}
    menu.append(new_item)
    response.status_code = 201
    return new_item

@app.put("/menu/{item_id}")
def update_item(item_id: int, price: Optional[int] = None, is_available: Optional[bool] = None):
    item = find_menu_item(item_id)
    if not item:
        raise HTTPException(404, "Not found")

    if price is not None:
        item["price"] = price
    if is_available is not None:
        item["is_available"] = is_available

    return item

@app.delete("/menu/{item_id}")
def delete_item(item_id: int):
    item = find_menu_item(item_id)
    if not item:
        raise HTTPException(404, "Not found")

    menu.remove(item)
    return {"message": "Deleted"}

# ------------------ WORKFLOW ------------------

@app.post("/cart/add")
def add_to_cart(item_id: int, quantity: int = 1):
    item = find_menu_item(item_id)
    if not item or not item["is_available"]:
        raise HTTPException(400, "Invalid item")

    for c in cart:
        if c["item_id"] == item_id:
            c["quantity"] += quantity
            return {"message": "Updated cart"}

    cart.append({"item_id": item_id, "quantity": quantity})
    return {"message": "Added"}

@app.get("/cart")
def get_cart():
    total = 0
    for c in cart:
        item = find_menu_item(c["item_id"])
        total += item["price"] * c["quantity"]
    return {"cart": cart, "total": total}

@app.post("/cart/checkout")
def checkout(req: CheckoutRequest, response: Response):
    global order_counter

    if not cart:
        raise HTTPException(400, "Cart empty")

    created = []

    for c in cart:
        item = find_menu_item(c["item_id"])
        total = item["price"] * c["quantity"]

        order = {
            "order_id": order_counter,
            "customer": req.customer_name,
            "total": total
        }
        orders.append(order)
        created.append(order)
        order_counter += 1

    cart.clear()
    response.status_code = 201
    return {"orders": created}

# ------------------ DAY 6 ------------------

@app.get("/menu/search")
def search(keyword: str):
    result = [i for i in menu if keyword.lower() in i["name"].lower()]
    return {"results": result}

@app.get("/menu/sort")
def sort(sort_by: str = "price", order: str = "asc"):
    reverse = order == "desc"
    return sorted(menu, key=lambda x: x[sort_by], reverse=reverse)

@app.get("/menu/page")
def paginate(page: int = 1, limit: int = 3):
    start = (page - 1) * limit
    return menu[start:start + limit]

@app.get("/menu/browse")
def browse(keyword: Optional[str] = None):
    data = menu
    if keyword:
        data = [i for i in data if keyword.lower() in i["name"].lower()]
    return data