import sqlite3
import matplotlib
matplotlib.use('TkAgg')  # Use Tkinter backend for GUI window on Ubuntu
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import deque
import time
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class PostureMetrics:
    def __init__(self, db_path="posture_data.db", window_size=30):
        self.db_path = db_path
        self.window_size = window_size
        self.recent_readings = deque(maxlen=window_size)
        self.fig = None
        self.ax = None
        self.last_alert_time = 0  # Track last alert timestamp
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posture_readings (
                timestamp DATETIME,
                status TEXT,
                is_good INTEGER
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_reading(self, status):
        is_good = 1 if status == "looks good" else 0
        timestamp = datetime.now()
        
        # Salvar no banco
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO posture_readings VALUES (?, ?, ?)",
            (timestamp, status, is_good)
        )
        conn.commit()
        conn.close()
        
        self.recent_readings.append(is_good)
        
        # Verificar se precisa alertar
        if len(self.recent_readings) >= self.window_size//2:
            good_readings = sum(self.recent_readings)
            if good_readings < self.window_size // 2:
                self.trigger_alert()
    
    def trigger_alert(self):
        current_time = time.time()

        # Check if at least 1 minute (60 seconds) has passed since last alert
        if current_time - self.last_alert_time >= 2:
            logger.info("ALERT: Bad posture detected!")
            try:
                print('\a\a\a', end='', flush=True)
            except Exception as e:
                logger.warning(f"Could not play alert sound: {e}")

            # Update last alert time
            self.last_alert_time = current_time
        else:
            # Calculate remaining time until next alert is allowed
            remaining_time = 60 - (current_time - self.last_alert_time)
            logger.debug(f"Alert cooldown active. Next alert in {remaining_time:.1f} seconds")



class PostureWindow:

    def __init__(self, db_path="posture_data.db"):
        self.db_path = db_path
        self.fig = None
        self.ax = None

    def plot_daily_summary(self, hours_back=1):
        start_date = datetime.now() - timedelta(hours=hours_back)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT timestamp, is_good FROM posture_readings WHERE timestamp > ?",
            (start_date,)
        )
        data = cursor.fetchall()
        conn.close()

        if not data:
            print("Nenhum dado encontrado")
            return

        timestamps = [datetime.fromisoformat(row[0]) for row in data]
        values = [row[1] for row in data]

        # Create figure if it doesn't exist, otherwise clear it
        if self.fig is None or not plt.fignum_exists(self.fig.number):
            plt.ion()  # Turn on interactive mode first
            self.fig, self.ax = plt.subplots(figsize=(12, 4))

            # Set up close event handler
            def on_close(event):
                print("\nWindow closed by user. Stopping posture monitoring...")
                plt.close('all')
                import sys
                sys.exit(0)

            self.fig.canvas.mpl_connect('close_event', on_close)

            # Make the window appear and be interactive
            self.fig.show()
            # Give the GUI time to initialize
            plt.pause(0.1)
        else:
            self.ax.clear()
        
        # Plot the data
        self.ax.plot(timestamps, values, 'b-', linewidth=1, marker='o', markersize=3)
        self.ax.set_ylim(-0.1, 1.1)
        self.ax.set_ylabel('Postura (1=Boa, 0=Ruim)')
        self.ax.set_xlabel('Tempo')
        self.ax.set_title(f'Monitoramento de Postura - Últimas {hours_back} horas(s)')
        self.ax.grid(True, alpha=0.3)

        # Format x-axis
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=2))
        plt.setp(self.ax.get_xticklabels(), rotation=45)

        self.fig.tight_layout()

        # Draw and update the figure with proper event handling
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        # Allow time for user interactions
        plt.pause(0.1)

    def close_plot(self):
        plt.close('all')


# main that is called to plot daily summary with updates
if __name__ == "__main__":
    postureMetrics = PostureWindow()
    postureMetrics.plot_daily_summary(hours_back=1)
    running = True
    try:
        while running:
            # Sleep in smaller chunks to allow GUI events to be processed
            for _ in range(100):  # 10 seconds total, but in 0.1s chunks
                time.sleep(0.1)
                plt.pause(0.001)  # Allow GUI events to be processed

                # Check again if window still exists during sleep
                if postureMetrics.fig is None or not plt.fignum_exists(postureMetrics.fig.number):
                    print("\nWindow was closed. Stopping posture monitoring...")
                    running = False
                    break
            if running:
                # Only update if we didn't break out of the inner loop
                postureMetrics.plot_daily_summary(hours_back=1)
    except KeyboardInterrupt:
        print("\nStopping posture monitoring...")
        postureMetrics.close_plot()
