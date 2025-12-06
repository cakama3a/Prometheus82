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
from colorama import Fore, Style
import pygame
from pygame.locals import *
import statistics
import random
import string
import sys
import csv

# Global settings
VERSION = "5.2.3.9"                 # Updated version with microsecond support
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
TEST_TYPE_HARDWARE = "hardware"     # New test type for hardware check

# File to store the last completed test time
LAST_TEST_TIME_FILE = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp', 'last_test_time.txt') if platform.system() == 'Windows' else os.path.join('/tmp', 'last_test_time.txt')

# Function to check time since last test
def check_cooling_period():
    if not os.path.exists(LAST_TEST_TIME_FILE):
        return True
    try:
        with open(LAST_TEST_TIME_FILE) as f:
            content = f.read().strip()
            parts = content.split(',')
            if len(parts) == 2:
                last_time = float(parts[0])
                cooling_seconds = float(parts[1])
            else:
                last_time = float(content)
                cooling_seconds = COOLING_PERIOD_SECONDS
            remaining = max(0, int(cooling_seconds - (time.time() - last_time)))
            if remaining > 0:
                print(f"\n{Fore.YELLOW}WARNING: Cooling required: {remaining} seconds remaining.{Fore.RESET}")
            return True
    except (ValueError, IOError):
        return True

def get_cooling_remaining_seconds():
    if not os.path.exists(LAST_TEST_TIME_FILE):
        return 0
    try:
        with open(LAST_TEST_TIME_FILE) as f:
            content = f.read().strip()
            parts = content.split(',')
            if len(parts) == 2:
                last_time = float(parts[0])
                cooling_seconds = float(parts[1])
            else:
                last_time = float(content)
                cooling_seconds = COOLING_PERIOD_SECONDS
            return max(0, int(cooling_seconds - (time.time() - last_time)))
    except (ValueError, IOError):
        return 0

# Function to record the test completion time
def save_test_completion_time(iterations):
    try:
        cooling_minutes = (iterations / 400.0) * 10.0
        cooling_seconds = int(cooling_minutes * 60)
        with open(LAST_TEST_TIME_FILE, 'w') as f:
            f.write(f"{time.time()},{cooling_seconds}")
        print(f"{Fore.GREEN}Test completion time recorded.{Fore.RESET}")
        print(f"{Fore.YELLOW}Cooling timer set to {cooling_seconds} seconds.{Fore.RESET}")
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
def export_to_csv(stats, gamepad_name, raw_results):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"latency_test_{timestamp}.csv"
    stats_copy = stats.copy()
    stats_copy['filtered_results'] = ', '.join(str(round(x, 2)) for x in stats['filtered_results'])
    stats_copy['gamepad_name'] = gamepad_name  # Add gamepad name to stats
    stats_copy['raw_results'] = ', '.join(str(round(x, 2)) for x in raw_results)  # Add raw results to stats
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=stats_copy.keys())
        writer.writeheader()
        writer.writerow(stats_copy)
    print(f"Data saved to file {filename}")

# ASCII Logo
print(f" ")
print("██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗██╗  ██╗███████╗██╗   ██╗███████╗   " + Fore.LIGHTRED_EX + " █████╗ ██████╗ " + Fore.RESET + "")
print("██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝██║  ██║██╔════╝██║   ██║██╔════╝   " + Fore.LIGHTRED_EX + "██╔══██╗╚════██╗" + Fore.RESET + "")
print("██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║   ███████║█████╗  ██║   ██║███████╗   " + Fore.LIGHTRED_EX + "╚█████╔╝ █████╔╝" + Fore.RESET + "")
print("██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██╔══╝  ██║   ██║╚════██║   " + Fore.LIGHTRED_EX + "██╔══██╗██╔═══╝ " + Fore.RESET + "")
print("██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║   ██║  ██║███████╗╚██████╔╝███████║   " + Fore.LIGHTRED_EX + "╚█████╔╝███████╗" + Fore.RESET + "")
print("╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝   " + Fore.LIGHTRED_EX + " ╚════╝ ╚══════╝" + Fore.RESET + "")                                                                                                 
print(f"v.{VERSION} by John Punch (" + Fore.LIGHTRED_EX + "https://gamepadla.com" + Fore.RESET + ")")
print(f"{Fore.YELLOW}Commercial use requires a license: https://github.com/cakama3a/Prometheus82/blob/main/LICENSE.md{Fore.RESET}")
print(f" ")
print(f"{Fore.CYAN}Professional gamepad latency tester with microsecond precision.{Fore.RESET}")
print(f"{Fore.CYAN}Measures button and stick response time using Prometheus 82 hardware tester.{Fore.RESET}")
print(f" ")
print(f"Support the project: " + Fore.LIGHTRED_EX + "https://ko-fi.com/gamepadla" + Fore.RESET + "")
print(f"How to use Prometheus 82: " + Fore.LIGHTRED_EX + "https://youtu.be/NBS_tU-7VqA" + Fore.RESET + "")
print(f"GitHub page: " + Fore.LIGHTRED_EX + "https://github.com/cakama3a/Prometheus82" + Fore.RESET + "")
print(f"{Style.DIM}To open links, press CTRL+Click{Style.RESET_ALL}")

class LatencyTester:
    def __init__(self, gamepad, serial_port, test_type, contact_delay=CONTACT_DELAY):
        self.joystick = gamepad
        self.serial = serial_port
        self.test_type = test_type
        self.contact_delay = contact_delay  # Use calibrated contact delay
        self.measuring = False
        self.start_time_us = 0  # Start time in microseconds
        self.last_trigger_time_us = 0  # Last trigger time in microseconds
        self.stick_axes = None
        self.button_to_test = None
        self.invalid_measurements = 0
        self.consecutive_same_latencies = 0
        self.last_latency = None
        self.consecutive_invalid = 0
        self.pulse_duration_us = PULSE_DURATION * 1000  # Convert ms to µs
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        self.latency_results = []
        self._skip_first_measurement = True
        self.set_pulse_duration(PULSE_DURATION)  # Use milliseconds for Arduino compatibility

    def set_pulse_duration(self, duration_ms):
        """Sets the solenoid pulse duration"""
        duration_ms = max(10, min(500, duration_ms))  # Limit the value
        self.pulse_duration_us = duration_ms * 1000
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        
        if not self.serial:
            print("Error: No serial connection available.")
            return False
        
        for _ in range(3):  # Send command and value (high byte, low byte)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.serial.write(b'P')
            self.serial.write(bytes([(duration_ms >> 8) & 0xFF, duration_ms & 0xFF]))
            self.serial.flush()
            start = time.time()
            while time.time() - start < 1.0:  # 1 second timeout
                if self.serial.in_waiting and self.serial.read() == b'A':
                    print(f"Pulse duration successfully set to {duration_ms} ms ({self.pulse_duration_us} µs)")
                    return True
                time.sleep(0.001)
        print(f"Error: Failed to set pulse duration after 3 attempts. Continuing with default value.")
        return False

    def update_pulse_parameters(self):
        """Updates PULSE_DURATION, TEST_INTERVAL and MAX_LATENCY"""
        duration_ms = int(self.pulse_duration_us / 1000) + INCREASE_DURATION
        self.set_pulse_duration(duration_ms)
        print(f"Updated parameters: PULSE_DURATION={duration_ms} ms, TEST_INTERVAL={int(self.test_interval_us/1000)} ms, MAX_LATENCY={int(self.max_latency_us/1000)} ms")

    def _check_consecutive_latencies(self, latency):
        """Checks for consecutive identical latencies and updates pulse parameters if needed."""
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
        """Processes invalid measurements and updates parameters if needed."""
        self.invalid_measurements += 1
        self.consecutive_invalid += 1
        print(f"Invalid measurement: {latency:.2f} ms (> {self.max_latency_us/1000:.2f} ms)")
        if self.consecutive_invalid >= CONSECUTIVE_EVENT_LIMIT:
            print(f"Detected {CONSECUTIVE_EVENT_LIMIT} consecutive invalid measurements. Increasing pulse duration.")
            self.update_pulse_parameters()
            self.consecutive_invalid = 0
        self.consecutive_same_latencies = 0  # Reset identical latencies counter

    def detect_active_stick(self):
        """Detects active stick movement beyond threshold and dynamically determines the axis pair."""
        if not self.joystick:
            return False
        for event in pygame.event.get():
            if event.type == JOYAXISMOTION and event.joy == self.joystick.get_id():
                if abs(self.joystick.get_axis(event.axis)) > STICK_THRESHOLD:
                    activated_axis = event.axis
                    partner_axis = -1

                    if activated_axis % 2 == 0:
                        partner_axis = activated_axis + 1
                    else:
                        partner_axis = activated_axis - 1

                    if 0 <= partner_axis < self.joystick.get_numaxes():
                        self.stick_axes = sorted([activated_axis, partner_axis])
                        return True
        return False

    def detect_active_button(self):
        """Detects button press events"""
        if not self.joystick:
            return False
        for event in pygame.event.get():
            if event.type == JOYBUTTONDOWN and event.joy == self.joystick.get_id() and event.button < 4:
                self.button_to_test = event.button
                return True
        return False

    def is_button_pressed(self):
        """Checks if the selected button is pressed"""
        return self.button_to_test is not None and self.joystick and self.joystick.get_button(self.button_to_test)

    def log_progress(self, latency):
        """Logs test progress with percentage"""
        progress = len(self.latency_results)
        print(f"[{progress / TEST_ITERATIONS * 100:3.0f}%] {latency:.2f} ms")

    def is_stick_at_extreme(self):
        """Checks if stick is at extreme position"""
        return self.stick_axes and self.joystick and any(abs(self.joystick.get_axis(axis)) >= STICK_THRESHOLD for axis in self.stick_axes)

    def trigger_solenoid(self):
        """Sends command to Prometheus to activate the solenoid"""
        if self.serial:
            self.serial.write(b'T')
        self.measuring = False  # Not starting measurement yet, waiting for 'S'
        self.last_trigger_time_us = time.perf_counter() * 1000000  # Time in microseconds

    def test_hardware(self):
        """Tests the solenoid and sensor functionality"""
        print(f"\nStarting hardware test with {HARDWARE_TEST_ITERATIONS} iterations...\n")
        successful_tests = 0
        sensor_press_times = []
        
        for i in range(HARDWARE_TEST_ITERATIONS):
            print(f"Test {i+1}/{HARDWARE_TEST_ITERATIONS}")
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.trigger_solenoid()
            start = time.time()
            while time.time() - start < 1.0:  # 1 second timeout
                if self.serial.in_waiting and self.serial.read() == b'S':
                    print(f"{Fore.GREEN}Test {i+1}: Solenoid activated, sensor detected contact successfully.{Fore.RESET}")
                    sensor_press_times.append(time.perf_counter())
                    successful_tests += 1
                    break
            else:
                print(f"{Fore.RED}Test {i+1}: Failed - No sensor response detected.{Fore.RESET}")
            time.sleep(self.pulse_duration_us / 1000000 + 0.2)  # Wait for solenoid pulse and small delay
        
        print(f"\n{Fore.CYAN}Hardware Test Results:{Fore.RESET}\nTotal tests: {HARDWARE_TEST_ITERATIONS}\n"
              f"Successful: {successful_tests}\nFailed: {HARDWARE_TEST_ITERATIONS - successful_tests}")
        
        # --- NEW DRY REFACTORED BLOCK START ---
        if len(sensor_press_times) > 2:  # Need at least 3 presses to get 2 intervals
            press_intervals = [(sensor_press_times[i] - sensor_press_times[i-1]) * 1000 
                               for i in range(1, len(sensor_press_times))]

            print(f"\n{Fore.CYAN}Sensor Interval Results:{Fore.RESET}")
            print(f"Total intervals measured: {len(press_intervals)}")

            # Set defaults
            filtered_intervals = press_intervals
            filter_note = f"  {Fore.YELLOW}Note: Not enough intervals to filter, showing simple average.{Fore.RESET}"

            if len(press_intervals) > 2: # Need at least 3 intervals to filter min/max
                press_intervals.sort()
                filtered_intervals = press_intervals[1:-1] # Re-assign with filtered list
                filter_note = f"Filtered intervals (removed min/max): {len(filtered_intervals)}" # Re-assign note
            
            # Common logic
            avg_interval = statistics.mean(filtered_intervals)
            print(filter_note)
            print(f"Average time between sensor presses: {avg_interval:.2f} ms")
            print(f"{Fore.YELLOW}(Note: Normal values are around 250 ±2ms){Fore.RESET}\n")
        else:
            print(f"\n{Fore.YELLOW}Not enough sensor presses detected ({len(sensor_press_times)}) to calculate intervals.{Fore.RESET}")
        # --- NEW DRY REFACTORED BLOCK END ---

        print(f"{Fore.GREEN if successful_tests == HARDWARE_TEST_ITERATIONS else Fore.RED}"
              f"Hardware test {'passed: Solenoid and sensor are functioning correctly.' if successful_tests == HARDWARE_TEST_ITERATIONS else 'failed: Check solenoid and sensor connections or hardware integrity.'}{Fore.RESET}")
        return successful_tests == HARDWARE_TEST_ITERATIONS

    def check_input(self):
        """Processes gamepad input for stick or button tests"""
        if self.test_type not in (TEST_TYPE_STICK, TEST_TYPE_BUTTON) or not self.measuring:
            return False
        
        if self.test_type == TEST_TYPE_STICK:
            if not self.stick_axes and self.detect_active_stick():
                return False
            if self.is_stick_at_extreme():
                latency_ms = ((time.perf_counter() * 1000000 - self.start_time_us + self.contact_delay * 1000) / 1000.0) - STICK_MOVEMENT_COMPENSATION
        else:  # TEST_TYPE_BUTTON
            if self.button_to_test is None and self.detect_active_button():
                return False
            if self.is_button_pressed():
                latency_ms = (time.perf_counter() * 1000000 - self.start_time_us + self.contact_delay * 1000) / 1000.0
        
        if 'latency_ms' in locals():
            if self._skip_first_measurement:
                self._skip_first_measurement = False
                self.measuring = False
                return True
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
        """Calculates test statistics"""
        if not self.latency_results:
            return None
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
        """Checks for test stalling and adjusts pulse duration if necessary"""
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
        """Main test loop for stick or button tests"""
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
            pygame.event.pump()

def detect_gamepad_mode(joystick):
    """Detect gamepad mode (XInput, DInput, Sony, Switch) based on name and axes at rest"""
    MODES = {
        "Sony": {"right_axes": (2, 3), "code": "dualsense"},
        "XInput": {"right_axes": (2, 3), "code": "xinput"},
        "Switch": {"right_axes": (2, 3), "code": "switch"},
        "DInput": {"right_axes": (3, 5), "code": "dinput"},
    }
    
    # Additional delay after init (some controllers need this)
    time.sleep(0.1)
    
    # Warmup joystick (longer for better detection)
    warmup_until = time.perf_counter() + 0.50  # 0.50 seconds warmup
    while time.perf_counter() < warmup_until:
        pygame.event.pump()
        for i in range(joystick.get_numaxes()):
            joystick.get_axis(i)
        time.sleep(0.01)
    
    # Get axes at rest after warmup
    axes_at_rest = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
    name_lower = joystick.get_name().lower()
    
    # Detect mode based on name and axes
    initial_mode = "DInput"
    if any(s in name_lower for s in ("dualsense", "ps5", "edge")):
        initial_mode = "Sony"
    elif any(s in name_lower for s in ("switch", "joy-con", "pro controller")):
        initial_mode = "Switch"
    elif any(s in name_lower for s in ("dualshock", "ds4", "ps4", "playstation")):
        initial_mode = "Sony"
    elif any(abs(a + 1) < 0.1 for a in axes_at_rest):
        initial_mode = "XInput"
    
    return initial_mode

# Short ID Generation
def generate_short_id(length=12):
    """Generates a random short ID"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

if __name__ == "__main__":
    pygame.init()
    pygame.joystick.init()
    
    # Cooling period check will be performed after selecting test iterations
    
    # Select gamepad
    joystick = None
    detected_mode = None
    joystick_count = pygame.joystick.get_count()
    if joystick_count:
        if joystick_count > 1:
            print("\nAvailable gamepads:")
            for i in range(joystick_count):
                joy = pygame.joystick.Joystick(i)
                joy.init()
                print(f"{i + 1}: {joy.get_name()}")
            try:
                joystick = pygame.joystick.Joystick(int(input(f"Select gamepad (1-{joystick_count}): ")) - 1)
                print(f"\nSelected gamepad: {joystick.get_name()}")
            except (ValueError, IndexError):
                print("Invalid selection! No gamepad will be used.")
        else:
            joystick = pygame.joystick.Joystick(0)
            print(f"\nAutoselected gamepad: {joystick.get_name()}")
        joystick.init()
        
        # Detect gamepad mode (XInput, DInput, Sony, Switch)
        detected_mode = detect_gamepad_mode(joystick)
        print(f"Detected protocol:  {Fore.GREEN}{detected_mode}{Fore.RESET}")
    else:
        print("\nNo gamepad found! Some features will be unavailable.")

    # Cooling status before selecting test type
    check_cooling_period()

    # Select test type
    print("\nSelect test type:\n1: Test analog stick (99% threshold)\n2: Test button\n3: Test hardware (solenoid and sensor)")
    try:
        test_choice = int(input("Enter your choice (1-3): "))
        test_type = {1: TEST_TYPE_STICK, 2: TEST_TYPE_BUTTON, 3: TEST_TYPE_HARDWARE}.get(test_choice)
        if not test_type:
            raise ValueError
        if test_type != TEST_TYPE_HARDWARE and not joystick:
            print(f"Error: No gamepad found! Can't run {test_type} test.")
            input("Press Enter to close...")
            pygame.quit()
            sys.exit()
        remaining = get_cooling_remaining_seconds()
        if remaining > 0:
            print(f"\n{Fore.YELLOW}WARNING: Device has not cooled yet. Running this test now may cause degradation. Remaining cooling time: {remaining} seconds.{Fore.RESET}")
            while True:
                choice = input("Continue anyway? (Y/N): ").upper()
                if choice in ('Y', 'N'):
                    break
                print("Invalid choice. Please enter Y or N.")
            if choice == 'N':
                print("Test cancelled.")
                input("Press Enter to close...")
                pygame.quit()
                sys.exit()
    except ValueError:
        print("Invalid input!")
        input("Press Enter to close...")
        pygame.quit()
        sys.exit()

    # Select iterations (affects cooling timeout)
    if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON):
        print("\nSelect number of iterations:\n1: 400 (For Gamepadla.com validation)\n2: 200\n3: 100\nOr enter a custom number between 10 and 400.")
        try:
            iter_input = input("Enter your choice (1/2/3 or custom 10-400): ").strip()
            if iter_input == '1':
                TEST_ITERATIONS = 400
            elif iter_input == '2':
                TEST_ITERATIONS = 200
            elif iter_input == '3':
                TEST_ITERATIONS = 100
            else:
                custom_iters = int(iter_input)
                if custom_iters < 10 or custom_iters > 400:
                    raise ValueError
                TEST_ITERATIONS = custom_iters
        except ValueError:
            print("Invalid iterations input! Please enter 1, 2, 3, or a number between 10 and 400.")
            input("Press Enter to close...")
            pygame.quit()
            sys.exit()

        pass

    # Setup serial connection
    # --- MODIFICATION START ---
    all_ports = list_ports.comports()
    # Filter out ports that have "Bluetooth" in their description (case-insensitive)
    ports = [p for p in all_ports if "bluetooth" not in p.description.lower()]

    if not ports:
        print("No suitable COM ports found. All available ports were Bluetooth or no ports are connected.")
        input("Press Enter to close...")
        pygame.quit()
        sys.exit()
    
    port = None
    if len(ports) == 1:
        port = ports[0]
        print(f"\nAutoselected COM port: {port.device} - {port.description}")
    else:
        print("\nAvailable COM ports:")
        for i, p in enumerate(ports):
            print(f"{i + 1}: {p.device} - {p.description}")
        try:
            selection = int(input(f"Select COM port (1-{len(ports)}): ")) - 1
            if 0 <= selection < len(ports):
                port = ports[selection]
            else:
                # Trigger the except block for out-of-range numbers
                raise IndexError("Selection out of range")
        except (ValueError, IndexError):
            print("Invalid selection!")
            input("Press Enter to close...")
            pygame.quit()
            sys.exit()
    # --- MODIFICATION END ---

    try:
        with serial.Serial(port.device, 115200, timeout=1) as ser:
            print(f"Connecting to {port.device} ({port.description})")
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Wait for ready signal from Arduino
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 second timeout
                if ser.in_waiting and ser.read() == b'R':
                    print(f"Prometheus 82 ready on {port.device}")
                    break
            else:
                print("Error: Prometheus did not send ready signal ('R'). Check connection or Prometheus code.")
                input("Press Enter to close...")
                pygame.quit()
                sys.exit()

            # Test Arduino latency and update CONTACT_DELAY
            avg_latency = test_arduino_latency(ser)
            if avg_latency is None:
                print(f"\n{Fore.RED}Error calibrating Arduino latency: Test failed. Using default CONTACT_DELAY ({CONTACT_DELAY} ms).{Fore.RESET}")
            else:
                CONTACT_DELAY = avg_latency
                print(f"\nSet CONTACT_DELAY to {CONTACT_DELAY:.3f} ms")

            tester = LatencyTester(joystick, ser, test_type, CONTACT_DELAY)
            
            try:
                if test_type == TEST_TYPE_HARDWARE:
                    test_passed = tester.test_hardware()
                    print(f"{Fore.GREEN if test_passed else Fore.RED}"
                          f"Hardware is {'fully functional. Ready for stick or button testing.' if test_passed else 'issues detected. Please check connections and try again.'}{Fore.RESET}")
                else:
                    if test_type == TEST_TYPE_BUTTON:
                        print("\nPress the button on your gamepad that you want to test (A, B, X, Y)...")
                        while not tester.detect_active_button():
                            pygame.event.pump()
                            time.sleep(0.01)
                        print(f"Selected button #{tester.button_to_test}!")
                    elif test_type == TEST_TYPE_STICK:
                        print("\nMove the analog stick that you want to test to its extreme position...")
                        while not tester.detect_active_stick():
                            pygame.event.pump()
                            time.sleep(0.01)
                        print(f"Selected analog stick axes: {tester.stick_axes}!")
                    
                    tester.test_loop()
                    stats = tester.get_statistics()
                    if stats:
                        save_test_completion_time(TEST_ITERATIONS)
                        print(f"\n{Fore.GREEN}Test completed!{Fore.RESET}")
                        print(f"\n{Style.BRIGHT}{Fore.CYAN}" + "="*15 + f"LATENCY" + "="*15 + f"{Fore.RESET}{Style.RESET_ALL}")
                        print(f"{'Min latency:':<26}{stats['min']:>8.2f} ms")
                        print(f"{'Max latency:':<26}{stats['max']:>8.2f} ms")
                        print(f"{Style.BRIGHT}{Fore.CYAN}" + f"{'Average latency:':<26}{stats['avg']:>8.2f} ms{Fore.RESET}" + f"{Style.RESET_ALL}")
                        print(f"{'Jitter:':<26}{stats['jitter']:>8.2f} ms")
                        print(f"{Style.BRIGHT}{Fore.CYAN}" + "="*37 + f"{Fore.RESET}{Style.RESET_ALL}")
                        print(f"\n{Style.BRIGHT}Measurement Results{Style.RESET_ALL}")
                        print(f"{'Iterations:':<26}{TEST_ITERATIONS:>8}")
                        print(f"{'Total measurements:':<26}{stats['total_samples']:>8}")
                        print(f"{'Valid measurements:':<26}{stats['valid_samples']:>8}")
                        print(f"{'Invalid measurements:':<26}{stats['invalid_samples']:>8} (>{stats['pulse_duration']*(RATIO-1):.1f} ms)")
                        print(f"{'Filtered count:':<26}{stats['filtered_samples']:>8}")
                        print(f"{'Pulse duration:':<26}{stats['pulse_duration']:>8.1f} ms")
                        print(f"{'Contact delay:':<26}{stats['contact_delay']:>8.3f} ms")
        
                        if stats['contact_delay'] > 1.2:
                            print(f"\n{Fore.RED}Warning: Tester's inherent latency ({stats['contact_delay']:.3f} ms) exceeds recommended 1.2 ms, which may affect results.{Fore.RESET}")

                        # Action selection with retry on invalid input
                        while True:
                            print("\nSelect action:\n1: Open on Gamepadla.com\n2: Export to CSV\n3: Upload to Gamepadla.com AND Export to CSV\n4: Exit")
                            try:
                                choice = int(input("Enter your choice (1-4): "))
                                if choice not in [1, 2, 3, 4]:
                                    print("Invalid selection! Please enter 1, 2, 3, or 4.")
                                    continue
                                if choice == 1 or choice == 3:
                                    if TEST_ITERATIONS < 200:
                                        print(f"\n{Fore.YELLOW}Uploading is disabled: tests with fewer than 200 iterations cannot be sent to gamepadla.com.{Fore.RESET}")
                                        continue
                                    while True:
                                        test_key = generate_short_id()
                                        gamepad_name = input("Enter gamepad name: ")
                                        connection = {"1": "Cable", "2": "Bluetooth", "3": "Dongle"}.get(
                                            input("Current connection (1. Cable, 2. Bluetooth, 3. Dongle): "), "Unset")
                                        data = {
                                            'test_key': test_key, 'version': VERSION, 'url': 'https://gamepadla.com',
                                            'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                            'driver': joystick.get_name() if joystick else "N/A", 'connection': connection,
                                            'mode': detected_mode if detected_mode else "Unknown",
                                            'name': gamepad_name, 'os_name': platform.system(), 'os_version': platform.uname().version,
                                            'min_latency': round(stats['min'], 2), 'max_latency': round(stats['max'], 2),
                                            'avg_latency': round(stats['avg'], 2), 'jitter': stats['jitter'],
                                            'mathod': 'PNCS' if test_type == TEST_TYPE_STICK else 'PNCB', # mathod name is not a mistake!
                                            'delay_list': ', '.join(str(round(x, 2)) for x in tester.latency_results),
                                            'stick_threshold': STICK_THRESHOLD if test_type == TEST_TYPE_STICK else None,
                                            'contact_delay': stats['contact_delay'], 'pulse_duration': stats['pulse_duration']
                                        }
                                        try:
                                            response = requests.post('https://gamepadla.com/scripts/poster.php', data=data)
                                            if response.status_code == 200:
                                                print("Test results successfully sent to the server.")
                                                webbrowser.open(f'https://gamepadla.com/result/{test_key}/')
                                                # If choice 3, also export to CSV
                                                if choice == 3:
                                                    export_to_csv(stats, joystick.get_name() if joystick else "N/A", tester.latency_results)
                                                break
                                            print(f"\nServer error. Status code: {response.status_code}")
                                        except requests.exceptions.RequestException:
                                            print("\nNo internet connection or server is unreachable")
                                        if input("\nDo you want to try sending the data again? (Y/N): ").upper() != 'Y':
                                            # If choice 3 and user doesn't want to retry, still save CSV
                                            if choice == 3:
                                                export_to_csv(stats, joystick.get_name() if joystick else "N/A", tester.latency_results)
                                            break
                                elif choice == 2:
                                    export_to_csv(stats, joystick.get_name() if joystick else "N/A", tester.latency_results)
                                elif choice == 4:
                                    break
                                break
                            except ValueError:
                                print("Invalid input! Please enter 1, 2, 3, or 4.")
            except KeyboardInterrupt:
                print("\nTest interrupted by user.")
    except serial.SerialException as e:
        print(f"Error opening port: {e}")
    except Exception as e:
        print(f"Error while setting up COM port: {e}")
    finally:
        pygame.quit()
        input("Press Enter to exit...")
