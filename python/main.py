import os
import logging
import pathlib
from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pydantic import BaseModel
from contextlib import asynccontextmanager
import json
import hashlib

# Define the path to the images & sqlite3 database
images = pathlib.Path(__file__).parent.resolve() / "images"
items_file = pathlib.Path(__file__).parent.resolve() / "db" / "items.json"
db = pathlib.Path(__file__).parent.resolve() / "db" / "mercari.sqlite3"


# Define the path to the db folder and create it if it doesn't exist
db_folder = pathlib.Path(__file__).parent.resolve() / "db"
db_folder.mkdir(parents=True, exist_ok=True)

def get_db():
    if not db.exists():
        yield

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


# STEP 5-1: set up the database connection
def setup_database():
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger("uvicorn")
logger.level = logging.INFO

origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


class HelloResponse(BaseModel):
    message: str



@app.get("/", response_model=HelloResponse)
def hello():
    return HelloResponse(**{"message": "Hello, world!"})


class AddItemResponse(BaseModel):
    message: str
@app.get("/items")
def get_items():
    if not items_file.exists():  # ファイルがない場合の処理を追加
        logger.warning(f"{items_file} not found. Creating an empty items list.")
        return {"items": []}

    try:
        with open(items_file, "r") as file:
            data = json.load(file)
        if not data.get("items"):
            return {"items": [], "message": "No items available."}
        return {"items": data.get("items", [])}
    except Exception as e:
        logger.error(f"Error reading items.json: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading item data")
    

# add_item is a handler to add a new item for POST /items .
@app.post("/items", response_model=AddItemResponse)
async def add_item(
    name: str = Form(...),
    category: str = Form(...),
  　db: sqlite3.Connection = Depends(get_db),
):
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    
    # hash and save the image
    image_name = await hash_and_save_image(image)
    item = Item(name=name, category=category, image_name=image_name)
    insert_item(item)
    return AddItemResponse(message=f"Item received: {name}")


# get_image is a handler to return an image for GET /images/{filename} .
@app.get("/image/{image_name}")
async def get_image(image_name:str):
    # Create image path
    image = images / image_name

    if not image_name.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "no_image.jpg"

    return FileResponse(image)


class Item(BaseModel):
    name: str
    category: str
    image: str 

# hash the image file
async def hash_and_save_image(image: UploadFile):
    if not image.filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")


    # create an instance of a hash function
    sha256 = hashlib.sha256()

    # get the binary data of the uploaded image
    contents = await image.read()

    # perform a hash calculation
    sha256.update(contents)

    # rename the file to a hash value
    image_name = f"{sha256.hexdigest()}.jpg"

    # save
    image_path = images / image_name
    with open(image_path, "wb") as f:
        f.write(contents)

    return image_name

def insert_item(item: Item):

    try:

        if not items_file.exists():
            with open(items_file, "w") as file:
                json.dump({"items": []}, file, indent=4) 
        
        # load the items.json file
        with open(items_file, "r") as file:
            data = json.load(file)

        # add a new item to the "items" array
        data["items"].append({"name": item.name, "category": item.category,"image_name": item.image_name})
    
        # save the updated data to items.json
        with open(items_file, "w") as file:
            json.dump(data, file, indent=4)
        return {"message": "Item added successfully", "status": 200}
    except Exception as e:
        logger.error(f"Error inserting item: {str(e)}")
        raise HTTPException(status_code=500, detail="Error saving item data")
        

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    items = get_items()["items"] 

    # Check if the item_id is valid
    if item_id < 1 or item_id > len(items):
        raise HTTPException(status_code=404, detail="Item not found")

    # Get the item at the specified index (item_id - 1 because list indexing starts at 0)
    item = items[item_id - 1]
    return item
    

           
    
