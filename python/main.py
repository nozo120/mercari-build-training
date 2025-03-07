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
db = pathlib.Path(__file__).parent.resolve() / "db" / "mercari.sqlite3"

# Define the path to the db folder and create it if it doesn't exist
db_folder = pathlib.Path(__file__).parent.resolve() / "db"
db_folder.mkdir(parents=True, exist_ok=True)


logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

def get_db():
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


# STEP 5-1: set up the database connection
def setup_database():
    if not db.exists():
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        try:
            with open("db/items.sql", "r") as f:
                schema = f.read()
            cursor.executescript(schema)
            conn.commit()
        except Exception as e:
            logger.error(f"Error setting up database: {str(e)}")
            raise RuntimeError(status_code=500, detail="Error setting up the database")
        finally:
            conn.close()
    else:
        logger.info("Database already exists, skipping setup.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield


app = FastAPI(lifespan=lifespan)



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
def get_items(db: sqlite3.Connection = Depends(get_db)):

    try:
        cursor = db.cursor()
        cursor.execute("""
            SELECT items.id, items.name, categories.name AS category_name, items.image_name
            FROM items
            JOIN categories ON items.category_id = categories.id
        """)
        items = cursor.fetchall()
        return {"items": [{"id": item[0], "name": item[1], "category": item[2], "image_name": item[3]} for item in items]}
    
    except Exception as e:
        logger.error(f"Error fetching items from database: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching item data")
    

# add_item is a handler to add a new item for POST /items .
@app.post("/items", response_model=AddItemResponse)
async def add_item(
    name: str = Form(...),
    category_id: int = Form(...),
    image: UploadFile = File(...), 
    db: sqlite3.Connection = Depends(get_db),
):
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    try:
    # hash and save the image
        image_name = await hash_and_save_image(image)

    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        raise HTTPException(status_code=500, detail="Error saving image")

    cursor = db.cursor()
    cursor.execute("INSERT INTO items (name, category_id, image_name) VALUES (?, ?, ?)", 
                   (name, category_id, image_name))
    db.commit()
    return AddItemResponse(message=f"Item '{name}' added successfully")


# get_image is a handler to return an image for GET /images/{filename} .
@app.get("/image/{image_name}")
async def get_image(image_name:str):
    # Create image path
    image_path = images / image_name

    if not image_path.exists():
        logger.warning(f"Image not found: {image_path}")
        image_path = images / "no_image.jpg"
    return FileResponse(image_path)


class Item(BaseModel):
    id: int
    name: str
    category: str
    image_name: str 

# hash the image file
async def hash_and_save_image(image: UploadFile):
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

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT items.id, items.name, categories.name AS category_name, items.image_name
        FROM items
        JOIN categories ON items.category_id = categories.id
        WHERE items.id = ?
    """, (item_id,))
    item = cursor.fetchone()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item[0], "name": item[1], "category": item[2], "image_name": item[3]}
    
@app.get("/search")
def search_items(keyword: str, db: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = db.cursor()

        # use the LIKE operator in an SQL statement to search for products that contain a keyword
        cursor.execute("""
            SELECT items.name, categories.name AS category_name, items.image_name
            FROM items
            JOIN categories ON items.category_id = categories.id
            WHERE items.name LIKE ?
        """, (f"%{keyword}%",))

        items = cursor.fetchall()

        # If products are found, they are returned as a list.
        if items:
            result = [{"name": item[0], "category": item[1], "image_name": item[2]} for item in items]
            return {"items": result}
        else:
            return {"items": []}  # 見つからなかった場合、空のリストを返す

    except Exception as e:
        # If an error occurs, return a 500 error
        logger.error(f"Error searching items: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching items: {str(e)}")
           
 
