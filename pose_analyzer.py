import cv2
from roboflow import Roboflow
import time
import os
from dotenv import load_dotenv
import tempfile
import traceback
import logging
from threading import Thread, Lock
from typing import TypedDict, Callable
from pose_statistics import PostureMetrics
import subprocess

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class PredictionResult(TypedDict):
    class_name: str
    confidence: float
    timestamp: int

    def __repr__(self):
        return f"PredictionResult(class_name={self.class_name}, confidence={self.confidence}, timestamp={self.timestamp})"
    




class PoseAnalyzer:
    def __init__(self, api_key=None):
        # Initialize Roboflow model
        rf = Roboflow(api_key=api_key)
        project = rf.workspace().project("posture_correction_v4")
        self.model = project.version(1).model
        
        # Create a temporary directory for frame processing
        self.temp_dir = tempfile.mkdtemp()
        
        
        self.latest_frame = None
        self.current_status = "Initializing..."
        self.running = True
        self.frame_ready = False
        self.last_prediction_time = 0
        self.prediction_interval = 0.5

    def prediction_worker(self,cap:cv2.VideoCapture, callback:Callable[[PredictionResult], None]=None):
        while self.running:
            ret, frame = cap.read()
            if not ret:
                break
            current_time = time.time()
            if current_time - self.last_prediction_time >= self.prediction_interval:
                latest_frame = frame.copy()
                self.last_prediction_time = current_time
                try:
                    status = self.analyze_posture(latest_frame)
                    self.current_status = status
                    if callback:
                        callback(status)
                except Exception as e:
                    logger.error(f"Error in prediction worker: {e}")
            
            time.sleep(0.5)  # Small sleep to prevent CPU spinning

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
        
        return PredictionResult(class_name=predicted_class, confidence=confidence, timestamp=int(time.time()))
    
    def cleanup(self):
        # Cleanup temp directory
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

def start_worker(analyzer:PoseAnalyzer, cv2_cap:cv2.VideoCapture, callback:Callable[[PredictionResult], None]):
    prediction_thread = Thread(target=analyzer.prediction_worker, daemon=True, args=(cv2_cap, callback,))
    prediction_thread.start()
    return prediction_thread            

def stop_worker(analyzer:PoseAnalyzer, prediction_thread:Thread):
    analyzer.running = False
    prediction_thread.join(timeout=1.0)
 
def print_video(cv2_cap:cv2.VideoCapture, result:PredictionResult):
    ret, frame = cv2_cap.read()
    if not ret:
        logger.error("Failed to read frame in callback")
        return
    message = f"{result['class_name']} ({result['confidence']:.2%})" if result else "No result"
    # Display frame with status
    cv2.putText(frame, message, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    # Add instructions for key commands
    cv2.putText(frame, "Press 'g' for graph, 'q' to quit", (10, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    cv2.imshow('Posture Analyzer', frame)

last_pose_result = None
last_pose_result_number = 0

def worker_callback(postureMetrics:PostureMetrics):
    def collect_result(result:PredictionResult):
        global last_pose_result
        last_pose_result = result
        global last_pose_result_number
        last_pose_result_number += 1
        logger.info(f"Callback {last_pose_result_number}: {result}")
        if result:
            postureMetrics.add_reading(result['class_name'])
    return collect_result

def real_time_monitor(analyzer:PoseAnalyzer, camera_index=0, fps=60):
    import matplotlib
    matplotlib.use('Qt5Agg') 

    # Real-time posture monitoring
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    postureMetrics = PostureMetrics()
    prediction_thread = start_worker(analyzer, cap, worker_callback(postureMetrics))

    logger.info("Posture monitoring started!")
    logger.info("Press 'g' to show daily graph, 'q' to quit")
    graph_subprocess = None

    while True:
        time.sleep(1/fps)
        print_video(cap, last_pose_result)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF

        # Exit on 'q' key
        if key == ord('q'):
            break
        # Show graph on 'g' key
        elif key == ord('g'):
            if not graph_subprocess or graph_subprocess.poll() is not None:
                graph_subprocess = subprocess.Popen(['python', '-m', 'pose_statistics'])
                logger.info("Graph started!")
            else:
                logger.info("Close graph!")
                graph_subprocess.terminate()

                
        

    stop_worker(analyzer, prediction_thread)
    cap.release()
    cv2.destroyAllWindows()
    if graph_subprocess:
        graph_subprocess.terminate()
    analyzer.cleanup()
    

def main():
    try:
        analyzer = PoseAnalyzer(api_key=os.getenv('ROBOFLOW_API_KEY'))
        real_time_monitor(analyzer)
    except ValueError as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        print(f"Error: {e}")
        print("Please make sure you have set up the ROBOFLOW_API_KEY in your .env file")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}\n{traceback.format_exc()}")
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()