from flask import Flask, render_template, jsonify
import pandas as pd
from stable_baselines3 import DQN
from station_simulation import StationSimulation
from train_env import StationTrainEnv

app = Flask(__name__)

# ===================================================================
# ### SIMULATION SPEED CONTROLS ###
# These control ONLY the speed of simulation, not train behavior
# Multiplier for all timing in station_simulation.py
# 1.0 = normal speed, 0.5 = half speed, 2.0 = double speed
# ===================================================================
SIMULATION_SPEED_MULTIPLIER = 2.0
# ===================================================================

# --- WEB PAGE ROUTES ---
@app.route('/')
def landing_page():
    """Serves the main landing page."""
    return render_template('landing.html')

@app.route('/simulation')
def simulation_page():
    """Serves the interactive simulation demo page."""
    return render_template('simulation.html')

# --- API ROUTES ---
@app.route('/get_ai_sim_data')
def get_ai_sim_data():
    """Runs the simulation with the trained AI and returns the event log."""
    print("--- Running Simulation with TRAINED AI CONTROLLER ---")

    # Apply speed multiplier to station simulation timing
    import station_simulation
    original_times = _backup_original_times()
    _apply_speed_multiplier(SIMULATION_SPEED_MULTIPLIER)

    try:
        # Load the trained agent and environment
        model = DQN.load("station_controller_model")
        env = StationTrainEnv(schedule_file="monday_schedule.csv")

        obs, _ = env.reset()
        done = False

        # Run the full simulation episode using the AI's decisions
        while not done:
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = env.step(action)

        # The environment's station object now holds the complete event log
        event_log = env.station.event_log
        schedule = pd.read_csv("monday_schedule.csv").to_dict('records')

        return jsonify({
            'events': event_log, 
            'schedule': schedule,
            'speed_multiplier': SIMULATION_SPEED_MULTIPLIER
        })
    finally:
        # Restore original timing values
        _restore_original_times(original_times)

@app.route('/get_naive_sim_data')
def get_naive_sim_data():
    """Runs the simulation with the basic 'naive' controller."""
    print("--- Running Simulation with NAIVE CONTROLLER ---")

    # Apply speed multiplier to station simulation timing
    import station_simulation
    original_times = _backup_original_times()
    _apply_speed_multiplier(SIMULATION_SPEED_MULTIPLIER)

    try:
        # Create the environment, but we won't use an AI model
        env = StationTrainEnv(schedule_file="monday_schedule.csv")
        env.reset()

        # Rule-based naive logic:
        # Always send high-priority to main lines, low-priority to platforms.
        # This loop replaces the AI's decision-making process.
        while not env.schedule.empty:
            train_info = env.schedule.iloc[0]

            # Naive routing decision
            if train_info['direction'] == 'north':
                route = "UP_MAIN" if train_info['priority'] == 'high' else "UP_PLATFORM"
            else: # south
                route = "DOWN_MAIN" if train_info['priority'] == 'high' else "DOWN_PLATFORM"

            # Find the integer action that corresponds to this route
            action = [k for k, v in env.action_to_route.items() if v == route][0]

            env.step(action) # Execute the naive action

        event_log = env.station.event_log
        schedule = pd.read_csv("monday_schedule.csv").to_dict('records')

        return jsonify({
            'events': event_log, 
            'schedule': schedule,
            'speed_multiplier': SIMULATION_SPEED_MULTIPLIER
        })
    finally:
        # Restore original timing values
        _restore_original_times(original_times)

# --- SPEED CONTROL FUNCTIONS ---
def _backup_original_times():
    """Backup original timing constants."""
    import station_simulation
    return {
        'TIME_MAIN_SEGMENT': station_simulation.TIME_MAIN_SEGMENT,
        'TIME_PLATFORM_SEGMENT': station_simulation.TIME_PLATFORM_SEGMENT,
        'TIME_AT_PLATFORM': station_simulation.TIME_AT_PLATFORM,
        'TIME_ON_CROSSOVER': station_simulation.TIME_ON_CROSSOVER
    }

def _apply_speed_multiplier(multiplier):
    """Apply speed multiplier to timing constants."""
    import station_simulation
    station_simulation.TIME_MAIN_SEGMENT = int(station_simulation.TIME_MAIN_SEGMENT / multiplier)
    station_simulation.TIME_PLATFORM_SEGMENT = int(station_simulation.TIME_PLATFORM_SEGMENT / multiplier)
    station_simulation.TIME_AT_PLATFORM = int(station_simulation.TIME_AT_PLATFORM / multiplier)
    station_simulation.TIME_ON_CROSSOVER = int(station_simulation.TIME_ON_CROSSOVER / multiplier)

def _restore_original_times(original_times):
    """Restore original timing constants."""
    import station_simulation
    station_simulation.TIME_MAIN_SEGMENT = original_times['TIME_MAIN_SEGMENT']
    station_simulation.TIME_PLATFORM_SEGMENT = original_times['TIME_PLATFORM_SEGMENT']
    station_simulation.TIME_AT_PLATFORM = original_times['TIME_AT_PLATFORM']
    station_simulation.TIME_ON_CROSSOVER = original_times['TIME_ON_CROSSOVER']

# --- SPEED CONTROL API ---
@app.route('/set_speed/<float:speed>')
def set_speed(speed):
    """Set simulation speed multiplier."""
    global SIMULATION_SPEED_MULTIPLIER

    if 0.1 <= speed <= 10.0:  # Reasonable bounds
        SIMULATION_SPEED_MULTIPLIER = speed
        return jsonify({
            'status': 'success',
            'speed_multiplier': SIMULATION_SPEED_MULTIPLIER,
            'message': f'Speed set to {speed}x'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Speed must be between 0.1 and 10.0'
        }), 400

@app.route('/get_speed')
def get_speed():
    """Get current speed multiplier."""
    return jsonify({
        'speed_multiplier': SIMULATION_SPEED_MULTIPLIER
    })

if __name__ == '__main__':
    print("🚆 Starting RailFlow AI Server...")
    print(f"⚡ Simulation Speed: {SIMULATION_SPEED_MULTIPLIER}x")
    print("🎛️ Speed Control: /set_speed/<value> and /get_speed")
    app.run(debug=True)