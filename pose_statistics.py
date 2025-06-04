import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import deque



class PostureMetrics:
    def __init__(self, db_path="posture_data.db", window_size=30):
        self.db_path = db_path
        self.window_size = window_size
        self.recent_readings = deque(maxlen=window_size)
        self.fig = None
        self.ax = None
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
        if len(self.recent_readings) == self.window_size:
            bad_readings = sum(1 for x in self.recent_readings if x == 0)
            if bad_readings > self.window_size // 2:
                self.trigger_alert()
    
    def trigger_alert(self):
        print("ALERTA: Postura ruim detectada!")
        # Implementar seu alerta aqui
    
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

        print(f"Encontrados {len(data)} registros para plotar")

        timestamps = [datetime.fromisoformat(row[0]) for row in data]
        values = [row[1] for row in data]

        # Create figure if it doesn't exist, otherwise clear it
        if self.fig is None or not plt.fignum_exists(self.fig.number):
            self.fig, self.ax = plt.subplots(figsize=(12, 4))
            plt.ion()  # Turn on interactive mode
            plt.show(block=False)
            plt.pause(0.1)  # Small pause to update the UI
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

        # Save plot to a temporary file
        temp_filename = 'current_graph.png'
        self.fig.savefig(temp_filename, dpi=150, bbox_inches='tight')
        
        # Draw and update the figure
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        
        print(f"Gráfico salvo em: {temp_filename}")

    def close_plot(self):
        plt.close('all')
