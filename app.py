from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image
import io

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
MODEL_PATH = r"runs\classify\runs\classify\tomato_disease_model3\weights\best.pt"
try:
    model = YOLO(MODEL_PATH)
    print(f"Model loaded successfully from {MODEL_PATH}")
except Exception as e:
    print(f"Error loading model: {e}")
    # Fallback to the base model if the specific one fails to load
    model = YOLO("yolov8m-cls.pt")

# Hardcoded recommendations for tomato diseases (can be expanded)
RECOMMENDATIONS = {
    "Healthy": [
        "No action needed.",
        "Maintain current watering schedule.",
        "Keep monitoring weekly."
    ],
    "Tomato_Early_blight": [
        "Remove infected lower leaves.",
        "Apply copper fungicide.",
        "Avoid overhead watering."
    ],
    "Tomato_Late_blight": [
        "Destroy infected plants.",
        "Apply protective fungicide.",
        "Ensure good drainage."
    ],
    "Tomato___healthy": [
        "No action needed.",
        "Maintain current watering schedule.",
        "Keep monitoring weekly."
    ]
}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        # Read the image file
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Run inference
        results = model(image)
        
        # Extract prediction
        result = results[0]
        top1_index = result.probs.top1
        confidence = float(result.probs.top1conf)
        class_name = result.names[top1_index]
        
        # Get recommendations (fallback to generic if not found)
        actions = RECOMMENDATIONS.get(
            class_name, 
            [
                "Consult a local agricultural expert.",
                "Isolate the affected plant if possible.",
                "Ensure proper air circulation."
            ]
        )
        
        # Format the response
        response_data = {
            "name": class_name.replace("_", " ").title(),
            "confidence": f"{confidence * 100:.1f}%",
            "actions": actions,
            "raw_class": class_name
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# Mount static directories
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
