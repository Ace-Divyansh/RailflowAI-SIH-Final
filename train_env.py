# train_env.py

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import simpy # <-- FIX: Imported simpy

# Make sure station_simulation.py is in the same directory
from station_simulation import StationSimulation

class StationTrainEnv(gym.Env):
    """
    The Gymnasium wrapper for our advanced StationSimulation.
    This is the interface the AI interacts with.
    """
    def __init__(self, schedule_file="monday_schedule.csv"):
        super(StationTrainEnv, self).__init__()
        self.schedule_file = schedule_file
        self.simpy_env = None # Will be instantiated in reset()
        self.station = None   # Will be instantiated in reset()

        # --- Define the AI's Senses (Observation Space) ---
        self.observation_space = spaces.Box(low=0, high=1, shape=(2,), dtype=np.float32)

        # --- Define the AI's Actions (Action Space) ---
        self.action_space = spaces.Discrete(5)
        self.action_to_route = {
            0: "UP_MAIN", 1: "UP_PLATFORM", 2: "DOWN_MAIN",
            3: "DOWN_PLATFORM", 4: "DOWN_SIDING"
        }

    def _get_observation(self):
        """Gets the information for the next train in the schedule."""
        if self.schedule.empty:
            return np.array([0, 0], dtype=np.float32)

        next_train = self.schedule.iloc[0]
        priority = 1 if next_train['priority'] == 'high' else 0
        direction = 1 if next_train['direction'] == 'south' else 0
        return np.array([priority, direction], dtype=np.float32)

    def reset(self, seed=None, options=None):
        """Resets the simulation for a new training episode."""
        super().reset(seed=seed)
        self.schedule = pd.read_csv(self.schedule_file)

        # --- FIX: Properly create the SimPy environment and the station ---
        self.simpy_env = simpy.Environment()
        self.station = StationSimulation(self.simpy_env)

        observation = self._get_observation()
        info = {}
        return observation, info

    def step(self, action):
        """
        The main loop for the AI. It takes an action, runs the simulation,
        and calculates the reward.
        """
        if isinstance(action, np.ndarray):
            action = action.item()

        if self.schedule.empty:
            return self._get_observation(), 0, True, False, {}

        route_decision = self.action_to_route.get(action)
        train_info = self.schedule.iloc[0]
        self.schedule = self.schedule.iloc[1:]

        # --- FIX: Correctly process and run the simulation for one train's journey ---
        self.simpy_env.process(self.station.train_process(
            train_info['train_id'],
            train_info['direction'],
            train_info['priority'],
            route_decision
        ))
        self.simpy_env.run() # This executes the simulation until the process is done

        # --- Calculate Reward ---
        reward = 0
        is_valid_route = (train_info['direction'] == 'north' and route_decision in ["UP_MAIN", "UP_PLATFORM"]) or \
                         (train_info['direction'] == 'south' and route_decision in ["DOWN_MAIN", "DOWN_PLATFORM", "DOWN_SIDING"])
        
        if is_valid_route:
            reward += 1
            if train_info['priority'] == 'high' and 'MAIN' in route_decision:
                reward += 2
        else:
            reward -= 5

        done = self.schedule.empty
        observation = self._get_observation()
        info = {}
        truncated = False

        return observation, reward, done, truncated, info