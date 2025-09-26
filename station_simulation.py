import simpy
from collections import namedtuple
import pandas as pd

# --- Simulation Constants ---
# These values control the "speed" of the simulation.
TIME_MAIN_SEGMENT = 25     # Time to travel on a main line section
TIME_PLATFORM_SEGMENT = 40  # Time to travel on a platform line section
TIME_AT_PLATFORM = 50      # Time a train stops at a platform
TIME_ON_CROSSOVER = 10      # Time to traverse a crossover switch

# A simple data structure to hold the state of a point/switch
PointState = namedtuple('PointState', ['position']) # position can be 'normal' or 'reverse'

class StationSimulation:
    """
    The advanced "Digital Twin" of the 5-line station, including controllable points.
    This class manages the world state and train movements.
    """
    def __init__(self, env):
        self.env = env
        self.event_log = []

        # --- Define all track segments and platforms as SimPy Resources ---
        self.line1_up_platform = simpy.Resource(env, capacity=1)
        self.line2_up_main_approach = simpy.Resource(env, capacity=1)
        self.line2_up_main_exit = simpy.Resource(env, capacity=1)
        self.line3_down_main_approach = simpy.Resource(env, capacity=1)
        self.line3_down_main_exit = simpy.Resource(env, capacity=1)
        self.line4_down_platform = simpy.Resource(env, capacity=1)
        self.line5_down_siding = simpy.Resource(env, capacity=1)
        self.mainline_crossover = simpy.Resource(env, capacity=1)

        # --- Define the 7 Points (Switches) as Controllable Objects ---
        self.points = {
            'P1': {'resource': simpy.Resource(env, capacity=1), 'state': 'normal'},
            'P2': {'resource': simpy.Resource(env, capacity=1), 'state': 'normal'},
            'P3': {'resource': simpy.Resource(env, capacity=1), 'state': 'normal'},
            'P4': {'resource': simpy.Resource(env, capacity=1), 'state': 'normal'},
            'PX1': {'resource': simpy.Resource(env, capacity=1), 'state': 'normal'},
            'PX2': {'resource': simpy.Resource(env, capacity=1), 'state': 'normal'},
            'P5': {'resource': simpy.Resource(env, capacity=1), 'state': 'normal'},
        }

    def train_process(self, train_id, direction, priority, route_decision):
        """A single train's journey, directed by an AI's route decision."""
        self.log_event(train_id, direction, 'spawned', {'route': route_decision})

        path_map = {
            "UP_MAIN": self.path_up_main,
            "UP_PLATFORM": self.path_up_platform,
            "DOWN_MAIN": self.path_down_main,
            "DOWN_PLATFORM": self.path_down_platform,
            "DOWN_SIDING": self.path_down_siding
        }

        path_function = path_map.get(route_decision)
        if path_function:
            yield self.env.process(path_function(train_id, direction))
        else:
            print(f"Error: Unknown route decision '{route_decision}' for train {train_id}")

        self.log_event(train_id, direction, 'finished', {})

    # --- Path Definitions for UP Direction ---

    def path_up_main(self, train_id, direction):
        """Path for a train to travel straight on the UP MAIN LINE."""
        with self.points['P1']['resource'].request() as p1_req, self.points['P2']['resource'].request() as p2_req:
            yield p1_req & p2_req
            self.points['P1']['state'] = 'normal'
            self.points['P2']['state'] = 'normal'
            self.log_event(train_id, direction, 'points_set', {'points': ['P1', 'P2'], 'state': 'normal'})

            with self.line2_up_main_approach.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L2_Approach'})
                yield self.env.timeout(TIME_MAIN_SEGMENT)
            with self.line2_up_main_exit.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L2_Exit'})
                yield self.env.timeout(TIME_MAIN_SEGMENT)

    def path_up_platform(self, train_id, direction):
        """Path for a train to stop at PLATFORM 2 on LINE 1."""
        with self.points['P1']['resource'].request() as p1_req, self.points['P2']['resource'].request() as p2_req:
            yield p1_req & p2_req
            self.points['P1']['state'] = 'reverse'
            self.points['P2']['state'] = 'reverse'
            self.log_event(train_id, direction, 'points_set', {'points': ['P1', 'P2'], 'state': 'reverse'})

            with self.line2_up_main_approach.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L2_Approach'})
                yield self.env.timeout(TIME_ON_CROSSOVER)
            with self.line1_up_platform.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L1_Platform_2'})
                yield self.env.timeout(TIME_AT_PLATFORM)

    # --- Symmetrical Path Definitions for DOWN Direction ---

    def path_down_main(self, train_id, direction):
        """Path for a train to travel straight on the DOWN MAIN LINE."""
        with self.points['P3']['resource'].request() as p3_req, self.points['P4']['resource'].request() as p4_req:
            yield p3_req & p4_req
            self.points['P3']['state'] = 'normal'
            self.points['P4']['state'] = 'normal'
            self.log_event(train_id, direction, 'points_set', {'points': ['P3', 'P4'], 'state': 'normal'})

            with self.line3_down_main_approach.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L3_Approach'})
                yield self.env.timeout(TIME_MAIN_SEGMENT)
            with self.line3_down_main_exit.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L3_Exit'})
                yield self.env.timeout(TIME_MAIN_SEGMENT)

    def path_down_platform(self, train_id, direction):
        """Path for a train to stop at PLATFORM 1 on LINE 4."""
        with self.points['P3']['resource'].request() as p3_req, self.points['P4']['resource'].request() as p4_req:
            yield p3_req & p4_req
            self.points['P3']['state'] = 'reverse'
            self.points['P4']['state'] = 'reverse'
            self.log_event(train_id, direction, 'points_set', {'points': ['P3', 'P4'], 'state': 'reverse'})

            with self.line3_down_main_approach.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L3_Approach'})
                yield self.env.timeout(TIME_ON_CROSSOVER)
            with self.line4_down_platform.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L4_Platform_1'})
                yield self.env.timeout(TIME_AT_PLATFORM)

    def path_down_siding(self, train_id, direction):
        """Path for a train to be stabled on the SIDING LINE 5."""
        # This path requires P3, P4, and P5.
        with self.points['P3']['resource'].request() as p3_req, self.points['P4']['resource'].request() as p4_req, self.points['P5']['resource'].request() as p5_req:
            yield p3_req & p4_req & p5_req
            self.points['P3']['state'] = 'reverse'
            self.points['P4']['state'] = 'reverse' # Assuming P4 must be reversed to access P5
            self.points['P5']['state'] = 'reverse'
            self.log_event(train_id, direction, 'points_set', {'points': ['P3', 'P4', 'P5'], 'state': 'reverse'})

            with self.line3_down_main_approach.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L3_Approach'})
                yield self.env.timeout(TIME_ON_CROSSOVER)
            with self.line4_down_platform.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L4_Platform_1'})
                yield self.env.timeout(TIME_PLATFORM_SEGMENT)
            with self.line5_down_siding.request() as track_req:
                yield track_req
                self.log_event(train_id, direction, 'enter_track', {'track': 'L5_Siding'})
                yield self.env.timeout(TIME_AT_PLATFORM) # Train waits here

    def log_event(self, train_id, direction, event_type, details):
        log_entry = {
            'time': self.env.now,
            'train_id': str(train_id),
            'direction': direction,
            'event': event_type,
            'details': details
        }
        self.event_log.append(log_entry)
        print(f"LOG | T:{log_entry['time']:.2f} | Train {train_id} | {event_type} | {details}")

# This part is just for testing the simulation directly
if __name__ == "__main__":
    env = simpy.Environment()
    station = StationSimulation(env)
    
    # Test run with both UP and DOWN trains
    def test_runner():
        print("--- Starting Simulation Test Run ---")
        env.process(station.train_process('N1(P)', 'north', 'low', 'UP_PLATFORM'))
        yield env.timeout(5)
        env.process(station.train_process('N2(M)', 'north', 'high', 'UP_MAIN'))
        yield env.timeout(10)
        env.process(station.train_process('S1(P)', 'south', 'low', 'DOWN_PLATFORM'))
        yield env.timeout(15)
        env.process(station.train_process('S2(S)', 'south', 'low', 'DOWN_SIDING'))

    env.process(test_runner())
    env.run(until=150)
    print("\n--- Simulation Test Finished ---")

