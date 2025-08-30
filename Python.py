# Author: John Punch
# Email: john@gamepadla.com
# License: For non-commercial use only. See full license at https://github.com/cakama3a/Prometheus82/blob/main/LICENSE

import time
import platform
import serial
import requests
import webbrowser
import numpy as np
import os
from serial.tools import list_ports
from datetime import datetime
from colorama import Fore
import pygame
from pygame.locals import *
import statistics
import random
import string
import sys
import csv

# Try to import the keyboard library and provide instructions if it's missing
try:
    import keyboard
except ImportError:
    print(f"{Fore.RED}Error: The 'keyboard' library is required for keyboard testing.{Fore.RESET}")
    print("Please install it using: pip install keyboard")
    print(f"{Fore.YELLOW}Note: On Linux, this library may require superuser (sudo) privileges to work.{Fore.RESET}")
    sys.exit()


# Global settings
VERSION = "5.3.2.0"                 # Updated version with keyboard connection type
TEST_ITERATIONS = 400               # Number of test iterations
PULSE_DURATION = 40                 # Solenoid pulse duration (ms)
LATENCY_TEST_ITERATIONS = 1000      # Number of measurements for Arduino latency test
STICK_MOVEMENT_COMPENSATION = 3.5   # Compensation for stick movement time in ms at 99% deflection
HARDWARE_TEST_ITERATIONS = 10       # Number of iterations for hardware test

# Variables that should not be changed without need
COOLING_PERIOD_MINUTES = 10         # Cooling period in minutes
COOLING_PERIOD_SECONDS = COOLING_PERIOD_MINUTES * 60  # Cooling period in seconds
LOWER_QUANTILE = 0.02               # Lower quantile for filtering
UPPER_QUANTILE = 0.98               # Upper quantile for filtering
STICK_THRESHOLD = 0.99              # Stick activation threshold
RATIO = 5                           # Delay to pulse duration ratio
TEST_INTERVAL = PULSE_DURATION * RATIO  # Delay time before next pulse
MAX_LATENCY = TEST_INTERVAL - PULSE_DURATION  # Maximum possible gamepad latency
CONTACT_DELAY = 0.2                 # Contact sensor delay (ms) for correction (will be updated after calibration)
INCREASE_DURATION = 10              # Pulse duration increase increment (ms)
LATENCY_EQUALITY_THRESHOLD = 0.001  # Threshold for comparing latencies (ms)
CONSECUTIVE_EVENT_LIMIT = 5         # Number of consecutive events for action

# Constants for test types
TEST_TYPE_STICK = "stick"
TEST_TYPE_BUTTON = "button"
TEST_TYPE_KEYBOARD = "keyboard"     # New test type for keyboard
TEST_TYPE_HARDWARE = "hardware"     # New test type for hardware check

# File to store the last completed test time
LAST_TEST_TIME_FILE = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp', 'last_test_time.txt') if platform.system() == 'Windows' else os.path.join('/tmp', 'last_test_time.txt')

# Function to check time since last test
def check_cooling_period():
    if not os.path.exists(LAST_TEST_TIME_FILE):
        return True  # If file doesn't exist, no tests were run yet
    
    try:
        with open(LAST_TEST_TIME_FILE) as f:
            elapsed = time.time() - float(f.read().strip())
            if elapsed < COOLING_PERIOD_SECONDS:
                print(f"\n{Fore.YELLOW}WARNING: Device needs {int(COOLING_PERIOD_SECONDS - elapsed)} more seconds to cool down!{Fore.RESET}")
                while True:
                    choice = input("Continue anyway? (Y/N): ").upper()
                    if choice in ('Y', 'N'):
                        return choice == 'Y'
                    print("Invalid choice. Please enter Y or N.")
            return True
    except (ValueError, IOError):
        return True  # If there's an error reading the file, allow the test to run

# Function to record the test completion time
def save_test_completion_time():
    try:
        with open(LAST_TEST_TIME_FILE, 'w') as f:
            f.write(str(time.time()))
        print(f"{Fore.GREEN}Test completion time recorded.{Fore.RESET}")
        print(f"{Fore.YELLOW}Wait {COOLING_PERIOD_MINUTES} minutes before next test to prevent solenoid overheating.{Fore.RESET}")
    except IOError as e:
        print(f"\n{Fore.RED}Error recording test completion time: {e}{Fore.RESET}")

# Function to test Arduino communication latency
def test_arduino_latency(ser):
    print(f"\nTesting Arduino communication latency... {LATENCY_TEST_ITERATIONS} measurements")
    latencies = []
    ser.timeout = 1
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    for i in range(LATENCY_TEST_ITERATIONS):
        start = time.perf_counter()
        ser.write(b'D')
        ser.flush()
        if ser.read() == b'R':
            latencies.append((time.perf_counter() - start) * 1000)  # Convert to ms
        else:
            print(f"\n{Fore.RED}Error testing Arduino latency: No response at measurement {i+1}{Fore.RESET}")
            return None
    
    if latencies:
        avg_latency = statistics.mean(latencies)
        print(f"Arduino latency test results:\nTotal measurements: {len(latencies)}\n"
              f"Minimum latency:    {min(latencies):.3f} ms\nMaximum latency:    {max(latencies):.3f} ms\n"
              f"Average latency:    {avg_latency:.3f} ms\nJitter deviation:   {statistics.stdev(latencies):.3f} ms")
        return avg_latency
    print(f"\n{Fore.RED}Error testing Arduino latency: No valid measurements{Fore.RESET}")
    return None

# Function to export statistics to CSV
def export_to_csv(stats, device_name, raw_results):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"latency_test_{timestamp}.csv"
    stats_copy = stats.copy()
    stats_copy['filtered_results'] = ', '.join(str(round(x, 2)) for x in stats['filtered_results'])
    stats_copy['device_name'] = device_name
    stats_copy['raw_results'] = ', '.join(str(round(x, 2)) for x in raw_results)
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=stats_copy.keys())
        writer.writeheader()
        writer.writerow(stats_copy)
    print(f"Data saved to file {filename}")

# ASCII Logo
print(f" ")
print(f" ")
print("██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗██╗  ██╗███████╗██╗   ██╗███████╗   " + Fore.LIGHTRED_EX + " █████╗ ██████╗ " + Fore.RESET + "")
print("██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝██║  ██║██╔════╝██║   ██║██╔════╝   " + Fore.LIGHTRED_EX + "██╔══██╗╚════██╗" + Fore.RESET + "")
print("██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║   ███████║█████╗  ██║   ██║███████╗   " + Fore.LIGHTRED_EX + "╚█████╔╝ █████╔╝" + Fore.RESET + "")
print("██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██╔══╝  ██║   ██║╚════██║   " + Fore.LIGHTRED_EX + "██╔══██╗██╔═══╝ " + Fore.RESET + "")
print("██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║   ██║  ██║███████╗╚██████╔╝███████║   " + Fore.LIGHTRED_EX + "╚█████╔╝███████╗" + Fore.RESET + "")
print("╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝   " + Fore.LIGHTRED_EX + " ╚════╝ ╚══════╝" + Fore.RESET + "")                                                                                                 
print(f"v.{VERSION} by John Punch (" + Fore.LIGHTRED_EX + "https://gamepadla.com" + Fore.RESET + ")")
print(f"Support the project: " + Fore.LIGHTRED_EX + "https://ko-fi.com/gamepadla" + Fore.RESET)
print(f"How to use Prometheus 82: " + Fore.LIGHTRED_EX + "https://youtu.be/NBS_tU-7VqA" + Fore.RESET)
print(f"GitHub page: " + Fore.LIGHTRED_EX + "https://github.com/cakama3a/Prometheus82" + Fore.RESET)

class LatencyTester:
    def __init__(self, serial_port, test_type, gamepad=None, contact_delay=CONTACT_DELAY):
        self.joystick = gamepad
        self.serial = serial_port
        self.test_type = test_type
        self.contact_delay = contact_delay
        self.measuring = False
        self.start_time_us = 0
        self.last_trigger_time_us = 0
        self.stick_axes = None
        self.button_to_test = None
        self.key_to_test = None
        self.invalid_measurements = 0
        self.consecutive_same_latencies = 0
        self.last_latency = None
        self.consecutive_invalid = 0
        self.pulse_duration_us = PULSE_DURATION * 1000
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        self.latency_results = []
        self.set_pulse_duration(PULSE_DURATION)

    def set_pulse_duration(self, duration_ms):
        duration_ms = max(10, min(500, duration_ms))
        self.pulse_duration_us = duration_ms * 1000
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        
        if not self.serial:
            print("Error: No serial connection available.")
            return False
        
        for _ in range(3):
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.serial.write(b'P')
            self.serial.write(bytes([(duration_ms >> 8) & 0xFF, duration_ms & 0xFF]))
            self.serial.flush()
            start = time.time()
            while time.time() - start < 1.0:
                if self.serial.in_waiting and self.serial.read() == b'A':
                    print(f"Pulse duration successfully set to {duration_ms} ms ({self.pulse_duration_us} µs)")
                    return True
                time.sleep(0.001)
        print(f"Error: Failed to set pulse duration after 3 attempts. Continuing with default value.")
        return False

    def update_pulse_parameters(self):
        duration_ms = int(self.pulse_duration_us / 1000) + INCREASE_DURATION
        self.set_pulse_duration(duration_ms)
        print(f"Updated parameters: PULSE_DURATION={duration_ms} ms, TEST_INTERVAL={int(self.test_interval_us/1000)} ms, MAX_LATENCY={int(self.max_latency_us/1000)} ms")

    def _check_consecutive_latencies(self, latency):
        if self.last_latency is not None and abs(latency - self.last_latency) < LATENCY_EQUALITY_THRESHOLD:
            self.consecutive_same_latencies += 1
            if self.consecutive_same_latencies >= CONSECUTIVE_EVENT_LIMIT:
                print(f"Detected {CONSECUTIVE_EVENT_LIMIT} consecutive_latencies. Increasing pulse duration.")
                self.update_pulse_parameters()
                self.consecutive_same_latencies = 0
        else:
            self.consecutive_same_latencies = 1
        self.last_latency = latency

    def _handle_invalid_measurement(self, latency):
        self.invalid_measurements += 1
        self.consecutive_invalid += 1
        print(f"Invalid measurement: {latency:.2f} ms (> {self.max_latency_us/1000:.2f} ms)")
        if self.consecutive_invalid >= CONSECUTIVE_EVENT_LIMIT:
            print(f"Detected {CONSECUTIVE_EVENT_LIMIT} consecutive invalid measurements. Increasing pulse duration.")
            self.update_pulse_parameters()
            self.consecutive_invalid = 0
        self.consecutive_same_latencies = 0

    def detect_active_stick(self):
        if not self.joystick: return False
        for event in pygame.event.get():
            if event.type == JOYAXISMOTION and event.joy == self.joystick.get_id():
                if event.axis in [0, 1] and abs(self.joystick.get_axis(event.axis)) > STICK_THRESHOLD:
                    self.stick_axes = [0, 1]
                    return True
                if event.axis in [2, 3] and abs(self.joystick.get_axis(event.axis)) > STICK_THRESHOLD:
                    self.stick_axes = [2, 3]
                    return True
        return False

    def detect_active_button(self):
        if not self.joystick: return False
        for event in pygame.event.get():
            if event.type == JOYBUTTONDOWN and event.joy == self.joystick.get_id() and event.button < 4:
                self.button_to_test = event.button
                return True
        return False
        
    def detect_active_key(self):
        """Detects the first key press to be used for testing."""
        print("\nPress any key on your keyboard that you want to test...")
        print(f"{Fore.YELLOW}Note: This might require running the script with administrator (or sudo on Linux) privileges to work correctly.{Fore.RESET}")
        self.key_to_test = keyboard.read_key(suppress=True)
        print(f"Selected key: {self.key_to_test}")
        time.sleep(0.5) # Small delay to avoid double reading
        return True
        
    def is_key_pressed(self):
        """Checks if the selected key is currently pressed."""
        return self.key_to_test is not None and keyboard.is_pressed(self.key_to_test)

    def is_button_pressed(self):
        return self.button_to_test is not None and self.joystick and self.joystick.get_button(self.button_to_test)

    def log_progress(self, latency):
        progress = len(self.latency_results)
        print(f"[{progress / TEST_ITERATIONS * 100:3.0f}%] {latency:.2f} ms")

    def is_stick_at_extreme(self):
        return self.stick_axes and self.joystick and any(abs(self.joystick.get_axis(axis)) >= STICK_THRESHOLD for axis in self.stick_axes)

    def trigger_solenoid(self):
        if self.serial:
            self.serial.write(b'T')
        self.measuring = False
        self.last_trigger_time_us = time.perf_counter() * 1000000

    def test_hardware(self):
        print(f"\nStarting hardware test with {HARDWARE_TEST_ITERATIONS} iterations...\n")
        successful_tests = 0
        
        for i in range(HARDWARE_TEST_ITERATIONS):
            print(f"Test {i+1}/{HARDWARE_TEST_ITERATIONS}")
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.trigger_solenoid()
            start = time.time()
            while time.time() - start < 1.0:
                if self.serial.in_waiting and self.serial.read() == b'S':
                    print(f"{Fore.GREEN}Test {i+1}: Solenoid activated, sensor detected contact successfully.{Fore.RESET}")
                    successful_tests += 1
                    break
            else:
                print(f"{Fore.RED}Test {i+1}: Failed - No sensor response detected.{Fore.RESET}")
            time.sleep(self.pulse_duration_us / 1000000 + 0.2)
        
        print(f"\n{Fore.CYAN}Hardware Test Results:{Fore.RESET}\nTotal tests: {HARDWARE_TEST_ITERATIONS}\n"
              f"Successful: {successful_tests}\nFailed: {HARDWARE_TEST_ITERATIONS - successful_tests}")
        print(f"{Fore.GREEN if successful_tests == HARDWARE_TEST_ITERATIONS else Fore.RED}"
              f"Hardware test {'passed: Solenoid and sensor are functioning correctly.' if successful_tests == HARDWARE_TEST_ITERATIONS else 'failed: Check solenoid and sensor connections or hardware integrity.'}{Fore.RESET}")
        return successful_tests == HARDWARE_TEST_ITERATIONS

    def check_input(self):
        if self.test_type not in (TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD) or not self.measuring:
            return False
        
        latency_ms = None
        
        if self.test_type == TEST_TYPE_STICK:
            pygame.event.pump()
            if not self.stick_axes and self.detect_active_stick(): return False
            if self.is_stick_at_extreme():
                latency_ms = ((time.perf_counter() * 1000000 - self.start_time_us + self.contact_delay * 1000) / 1000.0) - STICK_MOVEMENT_COMPENSATION
        elif self.test_type == TEST_TYPE_BUTTON:
            pygame.event.pump()
            if self.button_to_test is None and self.detect_active_button(): return False
            if self.is_button_pressed():
                latency_ms = (time.perf_counter() * 1000000 - self.start_time_us + self.contact_delay * 1000) / 1000.0
        elif self.test_type == TEST_TYPE_KEYBOARD:
            if self.is_key_pressed():
                latency_ms = (time.perf_counter() * 1000000 - self.start_time_us + self.contact_delay * 1000) / 1000.0
        
        if latency_ms is not None:
            if latency_ms <= self.max_latency_us / 1000.0:
                self.latency_results.append(latency_ms)
                self.log_progress(latency_ms)
                self._check_consecutive_latencies(latency_ms)
            else:
                self._handle_invalid_measurement(latency_ms)
            self.measuring = False
            return True
        return False

    def get_statistics(self):
        if not self.latency_results: return None
        filtered_results = sorted(self.latency_results)[int(len(self.latency_results) * LOWER_QUANTILE):int(len(self.latency_results) * UPPER_QUANTILE) + 1]
        return {
            'total_samples': len(self.latency_results) + self.invalid_measurements,
            'valid_samples': len(self.latency_results),
            'invalid_samples': self.invalid_measurements,
            'filtered_samples': len(filtered_results),
            'min': min(filtered_results),
            'max': max(filtered_results),
            'avg': statistics.mean(filtered_results),
            'jitter': round(np.std(filtered_results), 2),
            'filtered_results': filtered_results,
            'pulse_duration': self.pulse_duration_us / 1000,
            'contact_delay': self.contact_delay
        }

    def check_for_stall_and_adjust(self):
        current_time = time.time()
        current_count = len(self.latency_results)
        if not hasattr(self, '_last_stall_check_time'):
            self._last_stall_check_time = current_time
            self._last_measurement_count = current_count
            self._stall_counter = 0
            self._pushes_since_last_stall = 0
            return False
        
        self._pushes_since_last_stall += 1
        if current_count == self._last_measurement_count and current_time - self._last_stall_check_time > 2:
            self._stall_counter += 1
            if self._stall_counter == 1 or self._pushes_since_last_stall >= 50:
                print(f"No new measurements for 2 seconds. {'Making control push without changing parameters...' if self._stall_counter == 1 else 'Multiple stalls detected. Increasing pulse duration...'}")
                if self._stall_counter > 1:
                    self.update_pulse_parameters()
                self._pushes_since_last_stall = 0
                self._last_stall_check_time = current_time
                return True
            print("Stall detected, but waiting for more stalls before increasing parameters...")
            self._last_stall_check_time = current_time
            return True
        
        if current_count > self._last_measurement_count:
            self._last_measurement_count = current_count
            self._last_stall_check_time = current_time
            self._stall_counter = 0
        return False

    def test_loop(self):
        print(f"\nStarting {TEST_ITERATIONS} measurements with microsecond precision...\n")
        self.trigger_solenoid()
        while len(self.latency_results) < TEST_ITERATIONS:
            current_time_us = time.perf_counter() * 1000000
            if self.check_for_stall_and_adjust() or (not self.measuring and current_time_us - self.last_trigger_time_us >= self.test_interval_us):
                self.trigger_solenoid()
            if self.serial and self.serial.in_waiting and self.serial.read() == b'S':
                self.start_time_us = time.perf_counter() * 1000000
                self.measuring = True
            self.check_input()

# Short ID Generation
def generate_short_id(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

if __name__ == "__main__":
    # The rest of the script remains the same until the final data submission part
    
    if not check_cooling_period():
        print("\nClosing program...")
        sys.exit()
    
    # --- Main Menu ---
    print("\nSelect what you want to test:\n1: Gamepad\n2: Keyboard\n3: Hardware (solenoid and sensor)")
    try:
        main_choice = int(input("Enter your choice (1-3): "))
        if main_choice not in [1, 2, 3]: raise ValueError
    except ValueError:
        print("Invalid input!")
        sys.exit()

    joystick = None
    test_type = None
    pygame_initialized = False
    device_name_for_csv = "N/A"

    if main_choice == 1: # Gamepad
        pygame.init()
        pygame.joystick.init()
        pygame_initialized = True
        
        joystick_count = pygame.joystick.get_count()
        if joystick_count:
            if joystick_count > 1:
                print("\nAvailable gamepads:")
                for i in range(joystick_count):
                    joy = pygame.joystick.Joystick(i)
                    joy.init()
                    print(f"{i + 1}: {joy.get_name()}")
                try:
                    joystick_index = int(input(f"Select gamepad (1-{joystick_count}): ")) - 1
                    joystick = pygame.joystick.Joystick(joystick_index)
                except (ValueError, IndexError):
                    print("Invalid selection! No gamepad will be used.")
                    joystick = None
            else:
                joystick = pygame.joystick.Joystick(0)
            
            if joystick:
                joystick.init()
                print(f"\nAutoselected gamepad: {joystick.get_name()}")
                device_name_for_csv = joystick.get_name()
        else:
            print("\nNo gamepad found!")
        
        if not joystick:
            print("Can't continue without a gamepad.")
            if pygame_initialized: pygame.quit()
            sys.exit()

        print("\nSelect test type:\n1: Test analog stick (99% threshold)\n2: Test button")
        try:
            test_choice = int(input("Enter your choice (1-2): "))
            test_type = {1: TEST_TYPE_STICK, 2: TEST_TYPE_BUTTON}.get(test_choice)
            if not test_type: raise ValueError
        except ValueError:
            print("Invalid input!")
            if pygame_initialized: pygame.quit()
            sys.exit()

    elif main_choice == 2: # Keyboard
        test_type = TEST_TYPE_KEYBOARD
        device_name_for_csv = "Keyboard"
    elif main_choice == 3: # Hardware
        test_type = TEST_TYPE_HARDWARE

    # Setup serial connection
    ports = list_ports.comports()
    if not ports:
        print("No COM ports found! Cannot continue.")
        if pygame_initialized: pygame.quit()
        sys.exit()
    
    port_info = ports[0]
    if len(ports) > 1:
        print("\nAvailable COM ports:")
        for i, p in enumerate(ports):
            print(f"{i + 1}: {p.device} - {p.description}")
        try:
            port_index = int(input(f"Select COM port (1-{len(ports)}): ")) - 1
            port_info = ports[port_index]
        except (ValueError, IndexError):
            print("Invalid selection!")
            if pygame_initialized: pygame.quit()
            sys.exit()

    try:
        with serial.Serial(port_info.device, 115200, timeout=1) as ser:
            print(f"\nConnecting to {port_info.device} ({port_info.description})")
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            start_time = time.time()
            while time.time() - start_time < 5:
                if ser.in_waiting and ser.read() == b'R':
                    print(f"Prometheus 82 ready on {port_info.device}")
                    break
            else:
                print("Error: Prometheus did not send ready signal ('R'). Check connection or Prometheus code.")
                if pygame_initialized: pygame.quit()
                sys.exit()

            avg_latency = test_arduino_latency(ser)
            if avg_latency is None:
                print(f"\n{Fore.RED}Error calibrating Arduino latency: Test failed. Using default CONTACT_DELAY ({CONTACT_DELAY} ms).{Fore.RESET}")
            else:
                CONTACT_DELAY = avg_latency
                print(f"\nSet CONTACT_DELAY to {CONTACT_DELAY:.3f} ms")

            tester = LatencyTester(ser, test_type, joystick, CONTACT_DELAY)
            
            try:
                if test_type == TEST_TYPE_HARDWARE:
                    tester.test_hardware()
                else:
                    if test_type == TEST_TYPE_BUTTON:
                        print("\nPress the button on your gamepad that you want to test (A, B, X, Y)...")
                        while not tester.detect_active_button(): time.sleep(0.01)
                        print(f"Selected button #{tester.button_to_test}!")
                    elif test_type == TEST_TYPE_STICK:
                        print("\nMove the analog stick that you want to test to its extreme position...")
                        while not tester.detect_active_stick(): time.sleep(0.01)
                        print(f"Selected analog stick axes: {tester.stick_axes}!")
                    elif test_type == TEST_TYPE_KEYBOARD:
                        tester.detect_active_key()

                    tester.test_loop()
                    stats = tester.get_statistics()
                    if stats:
                        save_test_completion_time()
                        print(f"\n{Fore.GREEN}Test completed!{Fore.RESET}\n===============\n"
                              f"Total measurements: {stats['total_samples']}\nValid measurements: {stats['valid_samples']}\n"
                              f"Invalid measurements (>{stats['pulse_duration']*(RATIO-1):.1f}ms): {stats['invalid_samples']}\n"
                              f"Measurements after filtering: {stats['filtered_samples']}\n"
                              f"Minimum latency: {stats['min']:.2f} ms\nMaximum latency: {stats['max']:.2f} ms\n"
                              f"Average latency: {stats['avg']:.2f} ms\nJitter: {stats['jitter']:.2f} ms")
                        if stats['contact_delay'] > 1.2:
                            print(f"\n{Fore.RED}Warning: Tester's inherent latency ({stats['contact_delay']:.3f} ms) exceeds recommended 1.2 ms, which may affect results.{Fore.RESET}")
                        print(f"===============")

                        while True:
                            print("\nSelect action:\n1: Open on Gamepadla.com\n2: Export to CSV\n3: Exit")
                            try:
                                choice = int(input("Enter your choice (1-3): "))
                                if choice not in [1, 2, 3]:
                                    print("Invalid selection! Please enter 1, 2, or 3.")
                                    continue
                                if choice == 1:
                                    while True:
                                        test_key = generate_short_id()
                                        device_prompt = "Enter gamepad name: " if main_choice == 1 else "Enter keyboard name: "
                                        user_device_name = input(device_prompt)
                                        
                                        # --- MODIFIED BLOCK ---
                                        connection_type = "Unset"
                                        # Ask for connection type for both Gamepad and Keyboard tests
                                        if main_choice in [1, 2]:
                                            connection_input = input("Current connection (1. Cable, 2. Bluetooth, 3. Dongle/Receiver): ")
                                            connection_type = {"1": "Cable", "2": "Bluetooth", "3": "Dongle"}.get(connection_input, "Unset")
                                        # --- END OF MODIFIED BLOCK ---

                                        data = {
                                            'test_key': test_key, 'version': VERSION, 'url': 'https://gamepadla.com',
                                            'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                            'driver': joystick.get_name() if joystick else "Keyboard", 'connection': connection_type,
                                            'name': user_device_name, 'os_name': platform.system(), 'os_version': platform.uname().version,
                                            'min_latency': round(stats['min'], 2), 'max_latency': round(stats['max'], 2),
                                            'avg_latency': round(stats['avg'], 2), 'jitter': stats['jitter'],
                                            'mathod': 'PNCS' if test_type == TEST_TYPE_STICK else ('PNCB' if test_type == TEST_TYPE_BUTTON else 'PNCK'),
                                            'delay_list': ', '.join(str(round(x, 2)) for x in tester.latency_results),
                                            'stick_threshold': STICK_THRESHOLD if test_type == TEST_TYPE_STICK else None,
                                            'contact_delay': stats['contact_delay'], 'pulse_duration': stats['pulse_duration']
                                        }
                                        try:
                                            response = requests.post('https://gamepadla.com/scripts/poster.php', data=data)
                                            if response.status_code == 200:
                                                print("Test results successfully sent to the server.")
                                                webbrowser.open(f'https://gamepadla.com/result/{test_key}/')
                                                break
                                            print(f"\nServer error. Status code: {response.status_code}")
                                        except requests.exceptions.RequestException:
                                            print("\nNo internet connection or server is unreachable")
                                        if input("\nDo you want to try sending the data again? (Y/N): ").upper() != 'Y':
                                            break
                                elif choice == 2:
                                    export_to_csv(stats, device_name_for_csv, tester.latency_results)
                                elif choice == 3:
                                    break
                                break
                            except ValueError:
                                print("Invalid input! Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                print("\nTest interrupted by user.")
    except serial.SerialException as e:
        print(f"Error opening port: {e}")
    except Exception as e:
        print(f"Error while setting up COM port: {e}")
    finally:
        if pygame_initialized:
            pygame.quit()
        input("Press Enter to exit...")