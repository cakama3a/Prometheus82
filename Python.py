# -*- coding: utf-8 -*-
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
import csv  # Додано для роботи з CSV

# Global settings
VERSION = "5.2.2.0"             # Updated version with microsecond support
TEST_ITERATIONS = 200           # Number of test iterations
PULSE_DURATION = 40             # Solenoid pulse duration (ms)
LATENCY_TEST_ITERATIONS = 1000  # Number of measurements for Arduino latency test
STICK_MOVEMENT_COMPENSATION = 3.5 # Compensation for stick movement time in ms at 99% deflection

# Variables that should not be changed without need
COOLING_PERIOD_MINUTES = 10      # Cooling period in minutes
COOLING_PERIOD_SECONDS = COOLING_PERIOD_MINUTES * 60  # Cooling period in seconds
LOWER_QUANTILE = 0.05           # Lower quantile for filtering
UPPER_QUANTILE = 0.95           # Upper quantile for filtering
STICK_THRESHOLD = 0.99          # Stick activation threshold
RATIO = 5                       # Delay to pulse duration ratio
TEST_INTERVAL = PULSE_DURATION * RATIO  # Delay time before next pulse
MAX_LATENCY = TEST_INTERVAL - PULSE_DURATION  # Maximum possible gamepad latency
CONTACT_DELAY = 0.2             # Contact sensor delay (ms) for correction (will be updated after calibration)
INCREASE_DURATION = 10          # Pulse duration increase increment (ms)
LATENCY_EQUALITY_THRESHOLD = 0.001  # Threshold for comparing latencies (ms)
CONSECUTIVE_EVENT_LIMIT = 5     # Number of consecutive events for action

# Constants for test types
TEST_TYPE_STICK = "stick"
TEST_TYPE_BUTTON = "button"

# File to store the last completed test time
LAST_TEST_TIME_FILE = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp', 'last_test_time.txt') if platform.system() == 'Windows' else os.path.join('/tmp', 'last_test_time.txt')

# Function to check time since last test
def check_cooling_period():
    if not os.path.exists(LAST_TEST_TIME_FILE):
        return True  # If file doesn't exist, no tests were run yet
    
    try:
        with open(LAST_TEST_TIME_FILE, 'r') as f:
            last_test_time_str = f.read().strip()
            last_test_time = float(last_test_time_str)
            
            # Calculate how many seconds passed since last test
            current_time = time.time()
            elapsed_seconds = current_time - last_test_time
            
            if elapsed_seconds < COOLING_PERIOD_SECONDS:
                remaining_seconds = COOLING_PERIOD_SECONDS - elapsed_seconds
                print(f"\n{Fore.YELLOW}WARNING: Device needs {int(remaining_seconds)} more seconds to cool down!{Fore.RESET}")
                while True:
                    choice = input(f"Continue anyway? (Y/N): ").upper()
                    if choice == 'Y':
                        return True
                    elif choice == 'N':
                        return False
                    else:
                        print("Invalid choice. Please enter Y or N.")
            
            return True
    except (ValueError, IOError):
        # If there's an error reading the file, allow the test to run
        return True

# Function to record the test completion time
def save_test_completion_time():
    try:
        with open(LAST_TEST_TIME_FILE, 'w') as f:
            f.write(str(time.time()))
        print(f"\n{Fore.GREEN}Test completion time recorded.{Fore.RESET}")
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
        start_time = time.perf_counter()
        ser.write(b'D')
        ser.flush()
        response = ser.read()
        if response == b'R':
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000  # Convert to ms
            latencies.append(latency)
        else:
            print(f"\n{Fore.RED}Error testing Arduino latency: No response at measurement {i+1}{Fore.RESET}")
            return None
    
    if latencies:
        avg_latency = statistics.mean(latencies)
        print(f"Arduino latency test results:")
        print(f"Total measurements: {len(latencies)}")
        print(f"Minimum latency:    {min(latencies):.3f} ms")
        print(f"Maximum latency:    {max(latencies):.3f} ms")
        print(f"Average latency:    {avg_latency:.3f} ms")
        print(f"Jitter deviation:   {statistics.stdev(latencies):.3f} ms")
        return avg_latency
    print(f"\n{Fore.RED}Error testing Arduino latency: No valid measurements{Fore.RESET}")
    return None

# Функція для експорту статистики в CSV
def export_to_csv(stats):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"latency_test_{timestamp}.csv"
    stats_copy = stats.copy()
    stats_copy['filtered_results'] = ', '.join(str(round(x, 2)) for x in stats['filtered_results'])
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = stats_copy.keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(stats_copy)
    print(f"Дані збережено у файл {filename}")

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
        
        # For sequence tracking
        self.consecutive_same_latencies = 0
        self.last_latency = None
        self.consecutive_invalid = 0
        
        # Parameters initialization (in microseconds)
        self.pulse_duration_us = PULSE_DURATION * 1000  # Convert ms to µs
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        
        self.latency_results = []
            
        # Set pulse duration
        self.set_pulse_duration(PULSE_DURATION)  # Use milliseconds for Arduino compatibility

    def set_pulse_duration(self, duration_ms):
        """Sets the solenoid pulse duration"""
        # Limit the value
        duration_ms = max(10, min(500, duration_ms))
        
        # Update internal variables (in microseconds)
        self.pulse_duration_us = duration_ms * 1000
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        
        # Send command and value (high byte, low byte)
        if self.serial:
            max_attempts = 3
            for attempt in range(max_attempts):
                # Clearing buffers before sending
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                
                # Sending command and data
                self.serial.write(b'P')
                self.serial.write(bytes([(duration_ms >> 8) & 0xFF, duration_ms & 0xFF]))
                self.serial.flush()  # Make sure the data is sent
                
                # Waiting for confirmation
                start = time.time()
                while time.time() - start < 1.0:  # 1 second timeout
                    if self.serial.in_waiting:
                        response = self.serial.read()
                        if response == b'A':
                            print(f"Pulse duration successfully set to {duration_ms} ms ({self.pulse_duration_us} µs)")
                            return True
                    time.sleep(0.001)  # Short delay to reduce load
            print(f"Error: Failed to set pulse duration after {max_attempts} attempts. Continuing with default value.")
            return False
        print("Error: No serial connection available.")
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
        else:
            self.consecutive_same_latencies = 1
        self.last_latency = latency

        if self.consecutive_same_latencies >= CONSECUTIVE_EVENT_LIMIT:
            print(f"Detected {CONSECUTIVE_EVENT_LIMIT} consecutive_latencies. Increasing pulse duration.")
            self.update_pulse_parameters()
            self.consecutive_same_latencies = 0

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
        if not self.joystick:
            return False
            
        for event in pygame.event.get():
            if event.type == JOYAXISMOTION and event.joy == self.joystick.get_id():
                threshold = STICK_THRESHOLD
                
                if event.axis in [0, 1] and abs(self.joystick.get_axis(event.axis)) > threshold:
                    self.stick_axes = [0, 1]
                    return True
                if event.axis in [2, 3] and abs(self.joystick.get_axis(event.axis)) > threshold:
                    self.stick_axes = [2, 3]
                    return True
        return False

    def detect_active_button(self):
        if not self.joystick:
            return False
            
        for event in pygame.event.get():
            if event.type == JOYBUTTONDOWN and event.joy == self.joystick.get_id():
                if event.button < 4:
                    self.button_to_test = event.button
                    return True
        return False

    def is_button_pressed(self):
        if self.button_to_test is None or not self.joystick:
            return False
        return self.joystick.get_button(self.button_to_test)

    def log_progress(self, latency):
        progress = len(self.latency_results)
        percentage = (progress / TEST_ITERATIONS) * 100
        print(f"[{percentage:3.0f}%] {latency:.2f} ms")

    def is_stick_at_extreme(self):
        if not self.stick_axes or not self.joystick:
            return False
        threshold = STICK_THRESHOLD
        return any(abs(self.joystick.get_axis(axis)) >= threshold for axis in self.stick_axes)

    def trigger_solenoid(self):
        """Sends command to Prometheus to activate the solenoid"""
        if self.serial:
            self.serial.write(b'T')
        self.measuring = False  # Not starting measurement yet, waiting for 'S'
        self.last_trigger_time_us = time.perf_counter() * 1000000  # Time in microseconds

    def check_input(self):
        if self.test_type == TEST_TYPE_STICK:
            if not self.stick_axes and self.measuring:
                if self.detect_active_stick():
                    return False
                
            if self.measuring and self.is_stick_at_extreme():
                # Measure time in microseconds
                current_time_us = time.perf_counter() * 1000000
                latency_us = current_time_us - self.start_time_us + (self.contact_delay * 1000)
                latency_ms = (latency_us / 1000.0) - STICK_MOVEMENT_COMPENSATION  # Apply stick movement compensation
                
                max_latency_ms = self.max_latency_us / 1000.0
                
                if latency_ms <= max_latency_ms:
                    self.latency_results.append(latency_ms)
                    self.log_progress(latency_ms)
                    self._check_consecutive_latencies(latency_ms)
                else:
                    self._handle_invalid_measurement(latency_ms)
                self.measuring = False
                return True
            
        else:  # TEST_TYPE_BUTTON
            if self.button_to_test is None and self.measuring:
                if self.detect_active_button():
                    return False
                
            if self.measuring and self.is_button_pressed():
                # Measure time in microseconds
                current_time_us = time.perf_counter() * 1000000
                latency_us = current_time_us - self.start_time_us + (self.contact_delay * 1000)
                latency_ms = latency_us / 1000.0  # Convert to ms for display and comparison
                
                max_latency_ms = self.max_latency_us / 1000.0
                
                if latency_ms <= max_latency_ms:
                    self.latency_results.append(latency_ms)
                    self.log_progress(latency_ms)
                    self._check_consecutive_latencies(latency_ms)
                else:
                    self._handle_invalid_measurement(latency_ms)
                self.measuring = False
                return True
        
        return False

    def get_statistics(self):
        if not self.latency_results:
            return None
        
        filtered_results = sorted(self.latency_results)[
            int(len(self.latency_results) * LOWER_QUANTILE):
            int(len(self.latency_results) * UPPER_QUANTILE) + 1
        ]
        
        jitter = np.std(filtered_results)
        
        return {
            'total_samples': len(self.latency_results) + self.invalid_measurements,
            'valid_samples': len(self.latency_results),
            'invalid_samples': self.invalid_measurements,
            'filtered_samples': len(filtered_results),
            'min': min(filtered_results),
            'max': max(filtered_results),
            'avg': statistics.mean(filtered_results),
            'jitter': round(jitter, 2),  # 2 decimal places
            'filtered_results': filtered_results,
            'pulse_duration': self.pulse_duration_us / 1000,  # Convert to ms for display
            'contact_delay': self.contact_delay
        }
    
    def check_for_stall_and_adjust(self):
        """Checks for test stalling and adjusts pulse duration if necessary"""
        current_time = time.time()
        current_count = len(self.latency_results)
        
        # Initialize variables at first call
        if not hasattr(self, '_last_stall_check_time'):
            self._last_stall_check_time = current_time
            self._last_measurement_count = current_count
            self._stall_counter = 0
            self._pushes_since_last_stall = 0
            return False
        
        # Update push counter
        self._pushes_since_last_stall += 1
        
        # If no new measurements in 2 seconds
        if current_count == self._last_measurement_count and current_time - self._last_stall_check_time > 2:
            # Increase stall counter
            self._stall_counter += 1
            
            # If this is the first stall or more than 50 pushes since the last stall
            if self._stall_counter == 1 or self._pushes_since_last_stall >= 50:
                if self._stall_counter == 1:
                    print(f"No new measurements for 2 seconds. Making control push without changing parameters...")
                else:
                    print(f"Multiple stalls detected. Increasing pulse duration...")
                    self.update_pulse_parameters()
                
                # Reset push counter after stall
                self._pushes_since_last_stall = 0
                
                # Update time of last check
                self._last_stall_check_time = current_time
                
                # Return True so the main loop knows to make an additional push
                return True
            else:
                print(f"Stall detected, but waiting for more stalls before increasing parameters...")
                # Update time of last check
                self._last_stall_check_time = current_time
                return True
        
        # Update measurement counter if there were new measurements
        if current_count > self._last_measurement_count:
            self._last_measurement_count = current_count
            self._last_stall_check_time = current_time
            # Reset stall counter on successful measurement
            self._stall_counter = 0
        
        return False

    def test_loop(self):
        print(f"\nStarting {TEST_ITERATIONS} measurements with microsecond precision...\n")
                
        # First solenoid activation
        self.trigger_solenoid()
        
        while True:
            current_time_us = time.perf_counter() * 1000000  # Time in microseconds
            
            # Check if the test is finished
            if len(self.latency_results) >= TEST_ITERATIONS:
                break
            
            # Check for stalling and adjust parameters if necessary
            if self.check_for_stall_and_adjust():
                # If there was an adjustment, make a new push immediately
                self.trigger_solenoid()
                
            # Regular interval check for push
            elif not self.measuring and (current_time_us - self.last_trigger_time_us >= self.test_interval_us):
                self.trigger_solenoid()
            
            # Check for data from Arduino
            if self.serial and self.serial.in_waiting:
                data = self.serial.read()
                if data == b'S':
                    self.start_time_us = time.perf_counter() * 1000000
                    self.measuring = True
            
            # Check gamepad state
            self.check_input()
            pygame.event.pump()

# Short ID Generation
def generate_short_id(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

if __name__ == "__main__":
    pygame.init()
    pygame.joystick.init()
    
    # Check if program is started too soon after previous test
    if not check_cooling_period():
        print("\nClosing program...")
        pygame.quit()
        sys.exit()
    
    joystick = None
    if pygame.joystick.get_count() > 0:
        if pygame.joystick.get_count() > 1:
            print("\nAvailable gamepads:")
            for i in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(i)
                joy.init()
                print(f"{i + 1}: {joy.get_name()}")
            
            try:
                choice = int(input(f"Select gamepad (1-" + str(pygame.joystick.get_count()) + "): ")) - 1
                joystick = pygame.joystick.Joystick(choice)
                print(f"\nSelected gamepad: {joystick.get_name()}")
            except (ValueError, IndexError):
                print("Invalid selection! No gamepad will be used.")
                joystick = None
        else:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            print(f"\nAutoselected gamepad: {joystick.get_name()}")
    else:
        print("\nNo gamepad found! Some features will be unavailable.")

    print("\nSelect test type:")
    print("1: Test analog stick (99% threshold)")
    print("2: Test button")
    
    try:
        test_choice = int(input(f"Enter your choice (1-2): "))
        if test_choice == 1:
            if not joystick:
                print("Error: No gamepad found! Can't run stick test.")
                pygame.quit()
                sys.exit()
            test_type = TEST_TYPE_STICK
        elif test_choice == 2:
            if not joystick:
                print("Error: No gamepad found! Can't run button test.")
                pygame.quit()
                sys.exit()
            test_type = TEST_TYPE_BUTTON
        else:
            print("Invalid selection!")
            pygame.quit()
            sys.exit()
    except ValueError:
        print("Invalid input!")
        pygame.quit()
        sys.exit()

    ser = None
    try:
        ports = list_ports.comports()
        if not ports:
            print("No COM ports found! Cannot continue with hardware test.")
            pygame.quit()
            sys.exit()

        if len(ports) > 1:
            print("\nAvailable COM ports:")
            for i, port in enumerate(ports):
                print(f"{i + 1}: {port.device} - {port.description}")
            
            try:
                choice = int(input(f"Select COM port (1-" + str(len(ports)) + "): ")) - 1
                port = ports[choice]
            except (ValueError, IndexError):
                print("Invalid selection!")
                pygame.quit()
                sys.exit()
        else:
            port = ports[0]

        try:
            ser = serial.Serial(port.device, 115200, timeout=1)
            print(f" ")
            print(f"Connecting to {port.device} ({port.description})")
            
            # Clear buffer
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Wait for ready signal from Arduino
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 second timeout
                if ser.in_waiting:
                    data = ser.read()
                    if data == b'R':
                        print(f"Prometheus 82 ready on {port.device}")
                        break
                time.sleep(0.01)
            else:
                print("Error: Prometheus did not send ready signal ('R'). Check connection or Prometheus code.")
                ser.close()
                pygame.quit()
                sys.exit()

            # Test Arduino latency and update CONTACT_DELAY
            avg_latency = test_arduino_latency(ser)
            if avg_latency is None:
                print(f"\n{Fore.RED}Error calibrating Arduino latency: Test failed. Using default CONTACT_DELAY ({CONTACT_DELAY} ms).{Fore.RESET}")
            else:
                CONTACT_DELAY = avg_latency
                print(f"\nSet CONTACT_DELAY to {CONTACT_DELAY:.3f} ms")
        except serial.SerialException as e:
            print(f"Error opening port: {e}")
            pygame.quit()
            sys.exit()
    except Exception as e:
        print(f"Error while setting up COM port: {e}")
        pygame.quit()
        sys.exit()

    tester = LatencyTester(joystick, ser, test_type, CONTACT_DELAY)
    
    if test_type == TEST_TYPE_BUTTON:
        print("\nPress the button on your gamepad that you want to test (A, B, X, Y)...")
        waiting_for_button = True
        while waiting_for_button:
            if tester.detect_active_button():
                waiting_for_button = False
            pygame.event.pump()
            time.sleep(0.01)
        print(f"Selected button #{tester.button_to_test}!")

    if test_type == TEST_TYPE_STICK:
        if not joystick or not ser:
            print(f"{Fore.RED}Error: Gamepad or serial connection not initialized. Cannot proceed with stick test.{Fore.RESET}")
            if ser:
                ser.close()
            pygame.quit()
            sys.exit()
        
        # Try initial solenoid strike with slightly increased pulse, retry with stronger pulse if needed
        print("\nInitiating automatic solenoid strike to detect analog stick axes...")
        tester.set_pulse_duration(PULSE_DURATION + 5)  # Increase by 5ms for better reliability
        tester.trigger_solenoid()
        waiting_for_stick = True
        start_time = time.time()
        retry_attempted = False
        
        while waiting_for_stick and (time.time() - start_time) < 3:  # Reduced timeout to 3 seconds
            if tester.detect_active_stick():
                waiting_for_stick = False
            pygame.event.pump()
            time.sleep(0.01)
        
        # Single retry with increased pulse duration if no detection
        if waiting_for_stick and not retry_attempted:
            print(f"{Fore.YELLOW}No stick movement detected. Retrying with stronger pulse...{Fore.RESET}")
            tester.update_pulse_parameters()  # Increase pulse duration
            tester.trigger_solenoid()
            start_time = time.time()
            retry_attempted = True
            while waiting_for_stick and (time.time() - start_time) < 3:
                if tester.detect_active_stick():
                    waiting_for_stick = False
                pygame.event.pump()
                time.sleep(0.01)
        
        if not waiting_for_stick:
            print(f"Selected analog stick axes: {tester.stick_axes}!")
        else:
            print(f"{Fore.RED}Error: No stick movement detected after retry. Check gamepad or solenoid setup.{Fore.RESET}")
            if ser:
                ser.close()
            pygame.quit()
            sys.exit()
    
    test_completed_normally = False
    
    try:
        tester.test_loop()
        
        stats = tester.get_statistics()
        if stats:
            test_completed_normally = True  # Test completed normally
            print(f"\n{Fore.GREEN}Test completed!{Fore.RESET}")
            print(f"\n{Fore.GREEN}==={Fore.RESET}")
            
            # Record completion time right after the test completes
            save_test_completion_time()
            
            print(f"\nTotal measurements: {stats['total_samples']}")
            print(f"Valid measurements: {stats['valid_samples']}")
            print(f"Invalid measurements (>{stats['pulse_duration']*(RATIO-1):.1f}ms): {stats['invalid_samples']}")
            print(f"Measurements after filtering: {stats['filtered_samples']}")
            print(f"Minimum latency: {stats['min']:.2f} ms")
            print(f"Maximum latency: {stats['max']:.2f} ms")
            print(f"Average latency: {stats['avg']:.2f} ms")
            print(f"Jitter: {stats['jitter']:.2f} ms")
            if stats['contact_delay'] > 1.2:
                print(f"{Fore.RED}Warning: Tester's inherent latency ({stats['contact_delay']:.3f} ms) exceeds recommended 1.2 ms, which may affect results.{Fore.RESET}")
            print(f"{Fore.GREEN}==={Fore.RESET}")

            # Вибір дії у стилі вибору типу тесту
            print("\nSelect action:")
            print("1: Open on Gamepadla.com")
            print("2: Export to CSV")
            print("3: Exit")
            try:
                choice = int(input("Enter your choice (1-3): "))
                if choice == 1:
                    while True:
                        test_key = generate_short_id()
                        gamepad_name = input(f"Enter gamepad name: ")
                        connection = {
                            "1": "Cable",
                            "2": "Bluetooth",
                            "3": "Dongle"
                        }.get(input(f"Current connection (1. Cable, 2. Bluetooth, 3. Dongle): "), "Unset")
                        data = {
                            'test_key': str(test_key),
                            'version': VERSION,
                            'url': 'https://gamepadla.com',
                            'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                            'driver': joystick.get_name() if joystick else "N/A",
                            'connection': connection,
                            'name': gamepad_name,
                            'os_name': platform.system(),
                            'os_version': platform.uname().version,
                            'min_latency': round(stats['min'], 2),
                            'max_latency': round(stats['max'], 2),
                            'avg_latency': round(stats['avg'], 2),
                            'jitter': stats['jitter'],
                            'mathod': 'PNCS' if test_type == TEST_TYPE_STICK else 'PNCB',
                            'delay_list': ', '.join(str(round(x, 2)) for x in stats['filtered_results']),
                            'stick_threshold': STICK_THRESHOLD if test_type == TEST_TYPE_STICK else None,
                            'contact_delay': stats['contact_delay'],
                            'pulse_duration': stats['pulse_duration']
                        }
                        try:
                            response = requests.post('https://gamepadla.com/scripts/poster.php', data=data)
                            if response.status_code == 200:
                                print("Test results successfully sent to the server.")
                                webbrowser.open(f'https://gamepadla.com/result/{test_key}/')
                                break
                            else:
                                print(f"\nServer error. Status code: {response.status_code}")
                        except requests.exceptions.RequestException as e:
                            print("\nNo internet connection or server is unreachable")
                        retry = input(f"\nDo you want to try sending the data again? (Y/N): ").upper()
                        if retry != 'Y':
                            break
                elif choice == 2:
                    export_to_csv(stats)
                elif choice != 3:
                    print("Invalid selection!")
            except ValueError:
                print("Invalid input!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        if ser:
            ser.close()
        pygame.quit()
        
        input("Press Enter to exit...")