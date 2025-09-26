import time
from stable_baselines3 import DQN
from train_env import StationTrainEnv # Import our custom environment

# --- 1. Create the custom Gym environment ---
# This is where your custom StationTrainEnv class from the Canvas is instantiated.
print("Initializing the advanced Railway Station Environment...")
env = StationTrainEnv(schedule_file="monday_schedule.csv")
print("Environment created successfully.")

# --- 2. Create the DQN learning agent ---
# We are using the "MlpPolicy" which is a standard neural network.
# verbose=1 will print out the training progress.
print("Creating the DQN Agent...")
# You can experiment with hyperparameters here for better performance
model = DQN(
    "MlpPolicy",
    env,
    verbose=1,
    learning_rate=0.0005,
    buffer_size=50000,
    learning_starts=1000,
    batch_size=32,
    gamma=0.99,
    exploration_fraction=0.1,
    exploration_final_eps=0.01,
    tensorboard_log="./dqn_station_tensorboard/"
)
print("Agent created successfully.")

# --- 3. Train the agent ---
# This is the main training loop. We'll train for a significant number of steps.
# This will take several minutes depending on your computer's speed.
print("\n--- Starting AI Training ---")
start_time = time.time()

# The more timesteps, the smarter the AI will get. 50,000 is a good start.
model.learn(total_timesteps=50000, progress_bar=True)

end_time = time.time()
print(f"--- Training Finished in {end_time - start_time:.2f} seconds ---")


# --- 4. Save the trained model ---
# The trained "brain" is saved to a file. This file is your final deliverable.
print("\nSaving the trained model...")
model.save("station_controller_model")

print("\n✅ AI model has been trained and saved as 'station_controller_model.zip'!")
print("The AI Training step is now complete.")
