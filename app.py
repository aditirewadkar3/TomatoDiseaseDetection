from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image
from pydantic import BaseModel
import io
import os
import uuid
import mysql.connector
from mysql.connector import errorcode
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="CropGuard Backend")

# Enable CORS if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the trained model
# Note: Using the trained model from the runs directory for best accuracy on tomato diseases
MODEL_PATH = r"C:\BTech TY\SEM2\CropDetection\runs\classify\runs\classify\tomato_disease_model3\weights\best.pt"
try:
    model = YOLO(MODEL_PATH)
    print(f"Model loaded successfully from {MODEL_PATH}")
except Exception as e:
    print(f"Error loading model: {e}")
    # Fallback to the base model if the specific one fails to load
    model = YOLO("yolov8m-cls.pt")

# Configure Gemini AI
# API Key is now retrieved from .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
    print("WARNING: GEMINI_API_KEY is not set or is the default placeholder. AI recommendations may fail.")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Database configuration
db_config = {
    'user': 'root',
    'password': 'student',
    'host': 'localhost',
    'database': 'cropguard'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

# Pydantic models
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateProfileRequest(BaseModel):
    user_id: int
    name: str

class ChangePasswordRequest(BaseModel):
    user_id: int
    old_password: str
    new_password: str

async def get_gemini_recommendation(disease_name):
    prompt = f"""
    The tomato plant has been diagnosed with: {disease_name}.
    1. Explain briefly why this disease happens.
    2. Provide a list of 3-4 specific precautions or actions to be taken to treat or prevent it.
    
    Format the response as:
    Reason: [Your explanation]
    Actions:
    - [Action 1]
    - [Action 2]
    - [Action 3]
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "Reason: Information unavailable.\nActions:\n- Consult a local expert.\n- Check plant health regularly."

@app.post("/predict")
async def predict(file: UploadFile = File(...), user_id: int = Form(...)):
    try:
        # Read and open image for YOLO
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Save image to uploads folder
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Run YOLO inference
        results = model(image)
        result = results[0]
        top1_index = result.probs.top1
        confidence = float(result.probs.top1conf)
        class_name = result.names[top1_index].replace("_", " ").title()
        
        # Get AI recommendation from Gemini
        ai_advice = await get_gemini_recommendation(class_name)
        
        # Parse Gemini response (simple split for demo)
        parts = ai_advice.split("Actions:")
        reason = parts[0].replace("Reason:", "").strip()
        actions_text = parts[1].strip() if len(parts) > 1 else "- Consult expert"
        actions = [a.strip("- ").strip() for a in actions_text.split("\n") if a.strip()]
        
        # Save to Database
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                query = "INSERT INTO predictions (user_id, image_name, image_path, result, confidence) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (user_id, file.filename, file_path, class_name, confidence))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as db_err:
                print(f"Database error: {db_err}")

        # Format the response
        response_data = {
            "name": class_name,
            "confidence": f"{confidence * 100:.1f}%",
            "reason": reason,
            "actions": actions,
            "image_url": f"/{file_path}"
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/history/{user_id}")
async def get_history(user_id: int):
    conn = get_db_connection()
    if not conn:
        return JSONResponse(status_code=500, content={"error": "Database connection failed"})
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT result, confidence, image_path, created_at FROM predictions WHERE user_id = %s ORDER BY created_at DESC"
        cursor.execute(query, (user_id,))
        history = cursor.fetchall()
        
        # Format dates for JSON
        for item in history:
            item['created_at'] = item['created_at'].strftime("%b %d, %Y")
            item['confidence'] = f"{item['confidence'] * 100:.1f}%"
            
        return JSONResponse(content={"history": history})
    except mysql.connector.Error as err:
        return JSONResponse(status_code=500, content={"error": str(err)})
    finally:
        cursor.close()
        conn.close()

@app.post("/signup")
async def signup(request: SignupRequest):
    conn = get_db_connection()
    if not conn:
        return JSONResponse(status_code=500, content={"error": "Database connection failed"})
    
    try:
        cursor = conn.cursor()
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (request.email,))
        if cursor.fetchone():
            return JSONResponse(status_code=400, content={"error": "Email already registered"})
        
        # Insert new user
        query = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (request.name, request.email, request.password))
        conn.commit()
        
        return JSONResponse(content={"message": "Signup successful"})
    except mysql.connector.Error as err:
        return JSONResponse(status_code=500, content={"error": str(err)})
    finally:
        cursor.close()
        conn.close()

@app.post("/login")
async def login(request: LoginRequest):
    conn = get_db_connection()
    if not conn:
        return JSONResponse(status_code=500, content={"error": "Database connection failed"})
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, name, email FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (request.email, request.password))
        user = cursor.fetchone()
        
        if user:
            return JSONResponse(content={"message": "Login successful", "user": user})
        else:
            return JSONResponse(status_code=401, content={"error": "Invalid email or password"})
    except mysql.connector.Error as err:
        return JSONResponse(status_code=500, content={"error": str(err)})
    finally:
        cursor.close()
        conn.close()

# Mount static directories
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve HTML files
@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/dashboard.html")
async def read_dashboard():
    return FileResponse("dashboard.html")

@app.get("/login.html")
async def read_login():
    return FileResponse("login.html")

@app.get("/signup.html")
async def read_signup():
    return FileResponse("signup.html")

@app.get("/{filename}")
async def read_static_file(filename: str):
    # Fallback for any other static files in the root directory
    import os
    if os.path.exists(filename):
        return FileResponse(filename)
    return JSONResponse(status_code=404, content={"error": "File not found"})

@app.post("/update_profile")
async def update_profile(request: UpdateProfileRequest):
    conn = get_db_connection()
    if not conn:
        return JSONResponse(status_code=500, content={"error": "Database connection failed"})
    
    try:
        cursor = conn.cursor()
        query = "UPDATE users SET name = %s WHERE id = %s"
        cursor.execute(query, (request.name, request.user_id))
        conn.commit()
        
        return JSONResponse(content={"message": "Profile updated successfully"})
    except mysql.connector.Error as err:
        return JSONResponse(status_code=500, content={"error": str(err)})
    finally:
        cursor.close()
        conn.close()

@app.post("/change_password")
async def change_password(request: ChangePasswordRequest):
    conn = get_db_connection()
    if not conn:
        return JSONResponse(status_code=500, content={"error": "Database connection failed"})
    
    try:
        cursor = conn.cursor()
        # Verify old password
        cursor.execute("SELECT id FROM users WHERE id = %s AND password = %s", (request.user_id, request.old_password))
        if not cursor.fetchone():
            return JSONResponse(status_code=401, content={"error": "Incorrect old password"})
        
        # Update password
        query = "UPDATE users SET password = %s WHERE id = %s"
        cursor.execute(query, (request.new_password, request.user_id))
        conn.commit()
        
        return JSONResponse(content={"message": "Password changed successfully"})
    except mysql.connector.Error as err:
        return JSONResponse(status_code=500, content={"error": str(err)})
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
