import matplotlib
matplotlib.use('TkAgg')  # Use Tkinter backend for GUI window on Ubuntu
import matplotlib.pyplot as plt

# Data for the plot
x = [1, 2, 3, 4, 5]
y = [2, 4, 1, 5, 3]

# Create the plot
plt.plot(x, y)

# Add labels and title
plt.xlabel("X-axis Label")
plt.ylabel("Y-axis Label")
plt.title("Simple Matplotlib Graph")

# Display the plot
plt.show()