import supervision as sv
import cv2
from roboflow import Roboflow
import time
import os
from dotenv import load_dotenv
import tempfile
import traceback
import logging
from threading import Thread, Lock

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class PoseAnalyzer:
    def __init__(self, api_key=None):
        # Initialize Roboflow model
        rf = Roboflow(api_key=api_key)
        project = rf.workspace().project("posture_correction_v4")
        self.model = project.version(1).model
        
        # Create a temporary directory for frame processing
        self.temp_dir = tempfile.mkdtemp()
        
        # Threading setup
        self.frame_lock = Lock()
        self.status_lock = Lock()
        self.latest_frame = None
        self.current_status = "Initializing..."
        self.running = True
        self.frame_ready = False

    def prediction_worker(self):
        while self.running:
            current_frame = None
            
            # Get latest frame if available
            with self.frame_lock:
                if self.frame_ready:
                    current_frame = self.latest_frame.copy()
                    self.frame_ready = False  # Mark as consumed
            
            if current_frame is not None:
                try:
                    status = self.analyze_posture(current_frame)
                    # Update current status thread-safely
                    with self.status_lock:
                        self.current_status = status
                except Exception as e:
                    logger.error(f"Error in prediction worker: {e}")
            
            time.sleep(0.01)  # Small sleep to prevent CPU spinning

    def analyze_posture(self, frame):
        # Save frame temporarily
        temp_path = os.path.join(self.temp_dir, 'temp_frame.jpg')
        cv2.imwrite(temp_path, frame)
        
        # Predict using the Roboflow model with file path
        predictions = self.model.predict(temp_path).json()
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Process predictions
        posture_status = self.interpret_predictions(predictions)
        return posture_status

    def interpret_predictions(self, predictions):
        # For classification model, the response format is different
        if not predictions or 'predictions' not in predictions:
            return "No posture detected"
            
        # Get the top prediction
        top_prediction = predictions['predictions'][0]['predictions'][0]
        logger.info(f'Top prediction: {top_prediction}')
        predicted_class = top_prediction['class']
        confidence = top_prediction['confidence']
        
        # Prioritize posture recommendations
        if predicted_class == "looks good":
            return f"Good Posture ({confidence:.2%})"
        elif predicted_class == "sit up straight":
            return f"Adjust Posture: Sit Up Straight ({confidence:.2%})"
        elif predicted_class == "straighten head":
            return f"Adjust Posture: Straighten Head ({confidence:.2%})"
        else:
            return f"Posture Needs Improvement ({confidence:.2%})"

    def real_time_monitor(self, camera_index=0, fps=30):
        # Start prediction worker thread
        prediction_thread = Thread(target=self.prediction_worker, daemon=True)
        prediction_thread.start()
        
        # Real-time posture monitoring
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        last_prediction_time = 0
        prediction_interval = 1.0  # Predict every second
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            current_time = time.time()
            
            # Update latest frame for prediction every second
            if current_time - last_prediction_time >= prediction_interval:
                with self.frame_lock:
                    self.latest_frame = frame.copy()
                    self.frame_ready = True
                last_prediction_time = current_time
            
            # Get current status thread-safely
            with self.status_lock:
                status = self.current_status
            
            # Display frame with status
            cv2.putText(frame, status, (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Posture Analyzer', frame)
            
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        self.running = False
        prediction_thread.join(timeout=1.0)
        cap.release()
        cv2.destroyAllWindows()
        
        # Cleanup temp directory
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

def main():
    try:
        analyzer = PoseAnalyzer(api_key=os.getenv('ROBOFLOW_API_KEY'))
        analyzer.real_time_monitor()
    except ValueError as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        print(f"Error: {e}")
        print("Please make sure you have set up the ROBOFLOW_API_KEY in your .env file")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}\n{traceback.format_exc()}")
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()