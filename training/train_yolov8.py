from ultralytics import YOLO

def main():
    # Load a medium pre-trained YOLOv8 classification model for better accuracy
    # 'yolov8m-cls.pt' balances speed and high accuracy.
    model = YOLO('yolov8m-cls.pt')  

    # Train the model
    print("Starting training on the tomato dataset for max accuracy...")
    
    results = model.train(
        data='./dataset_tomato', 
        epochs=10, 
        patience=3,             # EARLY STOPPING: Stop if accuracy doesn't improve for 3 epochs
        imgsz=256,              
        batch=16,               
        device='',              # AUTO-DETECT: It will use GPU if properly installed, otherwise CPU
        optimizer='auto',       
        lr0=0.001,              
        cos_lr=True,            
        pretrained=True,        
        project='runs/classify',
        name='tomato_disease_model'
    )
    
    print("Training complete!")
    print("The BEST model weights were automatically saved in: runs/classify/tomato_disease_model/weights/best.pt")

if __name__ == '__main__':
    main()

