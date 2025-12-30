# Author: John Punch
# Email: john@gamepadla.com
# License: For non-commercial use only. See full license at https://github.com/cakama3a/Prometheus82/blob/main/LICENSE
VERSION = "5.2.4.2"                 # Updated version with microsecond support

import time
import platform
import serial
import requests
import webbrowser
import numpy as np
import os
from serial.tools import list_ports
from colorama import Fore, Style
import pygame
from pygame.locals import *
import statistics
import random
import string
import sys
import csv
import ctypes
import threading
import queue

# Async logging helpers placed before main so they exist at startup
ASYNC_LOG_QUEUE = None
ASYNC_LOG_STOP = None
ASYNC_LOG_THREAD = None

def _printer_loop():
    last_flush = time.perf_counter()
    while ASYNC_LOG_STOP and not ASYNC_LOG_STOP.is_set():
        try:
            line = ASYNC_LOG_QUEUE.get(timeout=0.1)
            try:
                sys.stdout.write(line + "\n")
            except Exception:
                pass
            if time.perf_counter() - last_flush > 0.25:
                try:
                    sys.stdout.flush()
                except Exception:
                    pass
                last_flush = time.perf_counter()
        except Exception:
            pass

def start_async_logger():
    global ASYNC_LOG_QUEUE, ASYNC_LOG_STOP, ASYNC_LOG_THREAD
    try:
        ASYNC_LOG_QUEUE = queue.SimpleQueue()
    except Exception:
        ASYNC_LOG_QUEUE = queue.Queue()
    ASYNC_LOG_STOP = threading.Event()
    ASYNC_LOG_THREAD = threading.Thread(target=_printer_loop, daemon=True)
    ASYNC_LOG_THREAD.start()

def stop_async_logger():
    try:
        if ASYNC_LOG_STOP:
            ASYNC_LOG_STOP.set()
    except Exception:
        pass

def async_log(message):
    try:
        if ASYNC_LOG_QUEUE:
            ASYNC_LOG_QUEUE.put(str(message))
        else:
            print(str(message))
    except Exception:
        try:
            print(str(message))
        except Exception:
            pass
# Enable DPI awareness for Windows to ensure sharp window rendering
if platform.system() == 'Windows':
    try:
        # Try to set DPI awareness (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # Fallback for older Windows versions
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass  # If both fail, continue without DPI awareness

# Global settings
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
CONTACT_DELAY = 0.2                 # Contact sensor delay (ms) for correction (will be updated after calibration)
REQUIRED_ARDUINO_VERSION = "1.1.1"
# INCREASE_DURATION = 10              # Pulse duration increase increment (ms)
LATENCY_EQUALITY_THRESHOLD = 0.001  # Threshold for comparing latencies (ms)
# CONSECUTIVE_EVENT_LIMIT = 5         # Number of consecutive events for action

# Constants for test types
TEST_TYPE_STICK = "stick"
TEST_TYPE_BUTTON = "button"
TEST_TYPE_HARDWARE = "hardware"     # New test type for hardware check
TEST_TYPE_KEYBOARD = "keyboard"

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
        print(f"\n{Fore.GREEN}Test completion time recorded.{Fore.RESET}")
        print(f"{Fore.YELLOW}Cooling timer set to {cooling_seconds} seconds.{Fore.RESET}")
    except IOError as e:
        print_error(f"Recording test completion time: {e}")

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
            print_error(f"Testing Arduino latency: No response at measurement {i+1}")
            return None
    
    if latencies:
        avg_latency = statistics.mean(latencies)
        print(f"Arduino latency test results:\nTotal measurements: {len(latencies)}\n"
              f"Minimum latency:    {min(latencies):.3f} ms\nMaximum latency:    {max(latencies):.3f} ms\n"
              f"Average latency:    {avg_latency:.3f} ms\nJitter deviation:   {statistics.stdev(latencies):.3f} ms")
        return avg_latency
    else:
        print_error("Testing Arduino latency: No valid measurements")
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
def print_error(message):
    print(f"\n{Fore.YELLOW}Error: {message}{Fore.RESET}")
def print_info(message):
    print(f"\n{Fore.GREEN}Info: {message}{Fore.RESET}")

def load_window_icon():
    """Load window icon from various possible locations"""
    icon_paths = [
        "icon.png",  # Current directory
        os.path.join(os.path.dirname(__file__), "icon.png"),  # Script directory
        os.path.join(os.path.dirname(sys.executable), "icon.png"),  # EXE directory
    ]
    
    # Try regular paths first
    for icon_path in icon_paths:
        if icon_path and os.path.exists(icon_path):
            try:
                return pygame.image.load(icon_path)
            except Exception:
                pass
    
    # Try PyInstaller bundle if frozen
    if getattr(sys, 'frozen', False):
        try:
            bundle_dir = sys._MEIPASS
            icon_path = os.path.join(bundle_dir, "icon.png")
            if os.path.exists(icon_path):
                return pygame.image.load(icon_path)
        except Exception:
            pass
    
    return None

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
    def __init__(self, gamepad, serial_port, test_type, contact_delay=CONTACT_DELAY, stick_compensation=STICK_MOVEMENT_COMPENSATION, iterations=TEST_ITERATIONS):
        self.joystick = gamepad
        self.serial = serial_port
        self.test_type = test_type
        self.contact_delay = contact_delay  # Use calibrated contact delay
        self.measuring = False
        self.start_time_us = 0  # Start time in microseconds
        self.last_trigger_time_us = 0  # Last trigger time in microseconds
        self.stick_axes = None
        self.button_to_test = None
        self.key_to_test = None
        self.invalid_measurements = 0
        self.pulse_duration_us = PULSE_DURATION * 1000  # Convert ms to µs
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        self.latency_results = []
        self._skip_first_measurement = True
        self._started = False
        self._last_render_time = 0.0
        self.set_pulse_duration(PULSE_DURATION)  # Use milliseconds for Arduino compatibility
        self.stick_movement_compensation_ms = stick_compensation
        self.iterations = iterations

    def open_test_window(self):
        while True:
            try:
                if not pygame.display.get_init():
                    pygame.display.init()
                if pygame.display.get_surface() is None:
                    # Load and set window icon
                    icon = load_window_icon()
                    if icon:
                        pygame.display.set_icon(icon)
                    pygame.display.set_mode((800, 600))
                    pygame.display.set_caption("Prometheus 82 - Testing")
                    pygame.font.init()
                self._screen = pygame.display.get_surface()
                self._font = pygame.font.Font(None, 28)
                break
            except Exception:
                time.sleep(0.5)

    def wait_for_start(self):
        if not hasattr(self, "_screen") or self._screen is None:
            self.open_test_window()
        if getattr(self, "_started", False):
            return
        self._started = False
        start_rect = pygame.Rect(0, 0, 220, 64)
        start_rect.center = (self._screen.get_width() // 2, self._screen.get_height() // 2)
        info_font = pygame.font.Font(None, 32)
        clock = pygame.time.Clock()
        while not self._started:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN:
                    if self.test_type == TEST_TYPE_KEYBOARD and self.key_to_test is None and event.key not in (K_RETURN, K_SPACE):
                        self.key_to_test = event.key
                    if event.key in (K_RETURN, K_SPACE):
                        self._started = True
                if event.type == MOUSEBUTTONDOWN:
                    if start_rect.collidepoint(event.pos):
                        self._started = True
            self._screen.fill((0, 0, 0))
            banner = info_font.render("Keep this window on top during testing", True, (255, 255, 0))
            self._screen.blit(banner, (20, 20))
            if self.test_type == TEST_TYPE_KEYBOARD:
                msg = "Press the key to test, then press Start"
                if self.key_to_test is not None:
                    try:
                        key_name = pygame.key.name(self.key_to_test)
                    except Exception:
                        key_name = str(self.key_to_test)
                    msg = f"Selected key: {key_name}. Press Start to begin"
                self._screen.blit(info_font.render(msg, True, (200, 200, 200)), (20, 60))
            pygame.draw.rect(self._screen, (50, 150, 50), start_rect, border_radius=12)
            label = info_font.render("Start", True, (255, 255, 255))
            label_pos = label.get_rect(center=start_rect.center)
            self._screen.blit(label, label_pos)
            pygame.display.flip()
            clock.tick(60)

    def close_test_window(self):
        return

    def render_test_window(self, last_latency=None):
        if not hasattr(self, "_screen") or self._screen is None:
            return
        self._screen.fill((0, 0, 0))
        header = "Keep this window on top during testing"
        surf = self._font.render(header, True, (255, 255, 0))
        self._screen.blit(surf, (10, 10))
        
        if self.test_type == TEST_TYPE_HARDWARE:
            surf2 = self._font.render("Calculating...", True, (255, 255, 255))
            self._screen.blit(surf2, (10, 40))
        elif self.test_type == TEST_TYPE_STICK and getattr(self, "_started", False) and len(self.latency_results) == 0:
            surf2 = self._font.render("Calibrating...", True, (255, 255, 255))
            self._screen.blit(surf2, (10, 40))
        else:
            progress_text = f"Progress: {len(self.latency_results)}/{self.iterations}"
            surf2 = self._font.render(progress_text, True, (200, 200, 200))
            self._screen.blit(surf2, (10, 40))
            
        if last_latency is not None:
            surf3 = self._font.render(f"Last latency: {last_latency:.2f} ms", True, (150, 200, 255))
            self._screen.blit(surf3, (10, 70))
        pygame.display.flip()

    def check_stick_setup(self, iterations=5):
        if self.test_type != TEST_TYPE_STICK:
            return None
        if not self.serial:
            return None
        print(f"\nVerifying setup: {iterations} hits")
        
        invalid_hold_count = 0
        try:
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
        except Exception:
            pass
            
        for i in range(iterations):
            if self.serial:
                self.serial.write(b'T')
                try:
                    self.serial.flush()
                except Exception:
                    pass
            
            # Wait for contact
            contact_time_us = None
            t0 = time.perf_counter()
            while time.perf_counter() - t0 < 1.0:
                if self.serial and self.serial.in_waiting and self.serial.read() == b'S':
                    contact_time_us = time.perf_counter() * 1000000
                    break
                pygame.event.pump()
            
            if not contact_time_us:
                print_error("Setup check: no contact signal received")
                time.sleep(0.1)
                continue

            # 20 ms hold-check
            hold_ok = None
            try:
                time.sleep(0.020)
                if self.serial:
                    self.serial.write(b'Q')
                    self.serial.flush()
                    tQ = time.perf_counter()
                    while time.perf_counter() - tQ < 0.200:
                        if self.serial.in_waiting:
                            resp = self.serial.read()
                            if resp in (b'H', b'U'):
                                hold_ok = (resp == b'H')
                                break
                        time.sleep(0.001)
            except Exception:
                pass

            if hold_ok is False:
                invalid_hold_count += 1
                print(f"Hit {i+1}/{iterations}: {Fore.YELLOW}Invalid (released too early){Fore.RESET}")
            else:
                print(f"Hit {i+1}/{iterations}: OK")
                
            time.sleep(0.1)
            try:
                self.render_test_window(None)
            except Exception:
                pass

        if invalid_hold_count > 0:
            print_error(f"Setup check: {invalid_hold_count} invalid hit(s) detected — stick was not fully deflected.\nMove gamepad closer to the sensor and repeat.")
            return False
        
        print(f"{Fore.GREEN}Setup verification passed.{Fore.RESET}")
        return True

    def set_pulse_duration(self, duration_ms):
        """Sets the solenoid pulse duration"""
        duration_ms = max(10, min(500, duration_ms))  # Limit the value
        self.pulse_duration_us = duration_ms * 1000
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        
        if not self.serial:
            print_error("No serial connection available.")
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
        print_error("Failed to set pulse duration after 3 attempts. Continuing with default value.")
        return False

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

    def detect_active_key(self):
        """Detects keyboard key press events"""
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                self.key_to_test = event.key
                return True
        return False

    def is_button_pressed(self):
        """Checks if the selected button is pressed"""
        return self.button_to_test is not None and self.joystick and self.joystick.get_button(self.button_to_test)

    def is_key_pressed(self):
        """Checks if the selected keyboard key is pressed"""
        if self.key_to_test is None:
            return False
        keys = pygame.key.get_pressed()
        return keys[self.key_to_test]

    def log_progress(self, latency):
        """Logs test progress with percentage"""
        progress = len(self.latency_results)
        async_log(f"[{progress / self.iterations * 100:3.0f}%] {latency:.2f} ms")

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
        self.open_test_window()
        self.wait_for_start()
        
        # User requested 10 repetitions of interval measurement.
        # We need 11 presses to get 10 intervals.
        iterations = 11
        # Use standard test interval: pulse_duration * RATIO (converted to seconds)
        interval_s = self.test_interval_us / 1000000.0
        
        print(f"\nStarting hardware test with {iterations} iterations at {interval_s*1000:.0f}ms intervals...\n")
        
        sensor_press_times = []
        successful_detections = 0
        
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        
        # Synchronize start time
        start_loop_time = time.perf_counter()
        
        for i in range(iterations):
            # Calculate when the next shot should happen
            next_shot_time = start_loop_time + (i + 1) * interval_s
            
            # Fire solenoid (blindly, based on time)
            self.trigger_solenoid()
            
            # Wait until the next shot time, while listening for sensor response
            detected_in_cycle = False
            while time.perf_counter() < next_shot_time:
                if self.serial.in_waiting:
                    try:
                        b = self.serial.read()
                        if b == b'S':
                            # Record time immediately
                            now = time.perf_counter()
                            sensor_press_times.append(now)
                            successful_detections += 1
                            detected_in_cycle = True
                            
                            # If we have at least 2 presses, we can calculate and print the interval immediately
                            if len(sensor_press_times) > 1:
                                interval_ms = (sensor_press_times[-1] - sensor_press_times[-2]) * 1000
                                idx = len(sensor_press_times) - 1
                                print(f"Interval {idx}: {interval_ms:.2f} ms")
                                
                    except Exception:
                        pass
                
                # Keep window responsive
                try:
                    self.render_test_window(None)
                except Exception:
                    pass
                
                # Prevent CPU hogging
                time.sleep(0.001)
            
            if not detected_in_cycle:
                # Optional: print failure if needed
                pass
        
        # Wait a little extra after the last shot for any straggling response
        end_wait = time.perf_counter() + 0.1
        while time.perf_counter() < end_wait:
             if self.serial.in_waiting:
                 try:
                     if self.serial.read() == b'S':
                         now = time.perf_counter()
                         sensor_press_times.append(now)
                         successful_detections += 1
                         # Print interval if we have enough points
                         if len(sensor_press_times) > 1:
                            interval_ms = (sensor_press_times[-1] - sensor_press_times[-2]) * 1000
                            idx = len(sensor_press_times) - 1
                            print(f"Interval {idx}: {interval_ms:.2f} ms")
                 except Exception:
                     pass
             time.sleep(0.001)

        print(f"\n{Fore.CYAN}Hardware Test Results:{Fore.RESET}")
        print(f"Total shots: {iterations}")
        print(f"Detected hits: {successful_detections}")
        
        timing_warning = False
        avg_interval = 0
        
        if len(sensor_press_times) > 1:
            intervals = []
            for i in range(1, len(sensor_press_times)):
                interval_ms = (sensor_press_times[i] - sensor_press_times[i-1]) * 1000
                intervals.append(interval_ms)
            
            if intervals:
                avg_interval = statistics.mean(intervals)
                target_interval = interval_s * 1000
                tester_error = avg_interval - target_interval
                
                print(f"\nAverage time between sensor presses: {avg_interval:.2f} ms")
                print(f"Tester error: {tester_error:+.2f} ms")
                print(f"{Fore.YELLOW}(Note: Normal values are around {target_interval:.0f} ±1ms){Fore.RESET}\n")
                
                # Check if timing is outside acceptable range (target ±1ms)
                if avg_interval < (target_interval - 1) or avg_interval > (target_interval + 1):
                    timing_warning = True
        else:
            print(f"\n{Fore.YELLOW}Not enough sensor presses detected to calculate intervals.{Fore.RESET}")

        # Display appropriate final message based on test results and timing
        if successful_detections >= (iterations - 2):
            if timing_warning and avg_interval != 0:
                print(f"{Fore.YELLOW}⚠️  WARNING: Solenoid is operating with incorrect timing!{Fore.RESET}")
                print(f"{Fore.YELLOW}Average timing: {avg_interval:.2f}ms (should be {interval_s*1000:.0f} ±1ms){Fore.RESET}")
                print(f"\n{Fore.YELLOW}This may affect test result accuracy. Recommended actions:{Fore.RESET}")
                print(f"{Fore.YELLOW}• Try reinstalling the gamepad in a different position{Fore.RESET}")
                print(f"{Fore.YELLOW}• Try a different power source or cable{Fore.RESET}")
                print(f"{Fore.YELLOW}• If the issue persists, consider replacing the solenoid{Fore.RESET}")
            else:
                print(f"{Fore.GREEN}Hardware test passed: Solenoid and sensor are functioning correctly.{Fore.RESET}")
        else:
            print(f"{Fore.RED}Hardware test failed: Check solenoid and sensor connections or hardware integrity.{Fore.RESET}")

        self.close_test_window()
        return successful_detections >= (iterations - 2), timing_warning

    def _calculate_latency(self):
        """Calculates current latency including contact delay and compensation"""
        current_time_us = time.perf_counter() * 1000000
        # Calculate raw latency in milliseconds
        latency_ms = (current_time_us - self.start_time_us) / 1000.0
        # Add contact delay
        latency_ms += self.contact_delay
        # Subtract stick compensation if applicable
        if self.test_type == TEST_TYPE_STICK:
            latency_ms -= self.stick_movement_compensation_ms
        return latency_ms

    def check_input(self):
        """Processes input for stick, button, or keyboard tests"""
        if self.test_type not in (TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD) or not self.measuring:
            return False
        
        input_detected = False
        
        if self.test_type == TEST_TYPE_STICK:
            if not self.stick_axes and self.detect_active_stick():
                return False
            if self.is_stick_at_extreme():
                input_detected = True
                
        elif self.test_type == TEST_TYPE_BUTTON:
            if self.button_to_test is None and self.detect_active_button():
                return False
            if self.is_button_pressed():
                input_detected = True
                
        elif self.test_type == TEST_TYPE_KEYBOARD:
            if self.key_to_test is None and self.detect_active_key():
                return False
            if self.is_key_pressed():
                input_detected = True
        
        if input_detected:
            latency_ms = self._calculate_latency()
            
            if self._skip_first_measurement:
                self._skip_first_measurement = False
                self.measuring = False
                return True
                
            if latency_ms <= self.max_latency_us / 1000.0:
                self.latency_results.append(latency_ms)
                self.log_progress(latency_ms)
            else:
                self.invalid_measurements += 1
                print(f"Invalid measurement: {latency_ms:.2f} ms (> {self.max_latency_us/1000:.2f} ms)")
                
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
            'contact_delay': self.contact_delay,
            'stick_movement_compensation': self.stick_movement_compensation_ms
        }

    def test_loop(self):
        """Main test loop for stick or button tests"""
        print("\nPreparing test window...")
        self.open_test_window()
        print("Test window ready. Press Start to begin.")
        self.wait_for_start()
        if self.test_type == TEST_TYPE_STICK:
            ok = self.check_stick_setup(iterations=5)
            if not ok:
                if pygame.display.get_init() and pygame.display.get_surface() is not None:
                    pygame.display.quit()
                return
        print(f"\nStarting {self.iterations} measurements with microsecond precision...\n")
        self.trigger_solenoid()
        while len(self.latency_results) < self.iterations:
            current_time_us = time.perf_counter() * 1000000
            if (not self.measuring and current_time_us - self.last_trigger_time_us >= self.test_interval_us):
                self.trigger_solenoid()
            if self.serial and self.serial.in_waiting:
                found = False
                while self.serial.in_waiting:
                    if self.serial.read() == b'S':
                        found = True
                        break
                if found:
                    self.start_time_us = time.perf_counter() * 1000000
                    self.measuring = True
            self.check_input()
            pygame.event.pump()
            try:
                now = time.perf_counter()
                if now - self._last_render_time >= 1.0 / 30.0:
                    self.render_test_window(self.latency_results[-1] if self.latency_results else None)
                    self._last_render_time = now
            except Exception:
                pass

        self.close_test_window()

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
    start_async_logger()
    try:
        if not pygame.display.get_init():
            pygame.display.init()
        if pygame.display.get_surface() is None:
            # Load and set window icon
            icon = load_window_icon()
            if icon:
                pygame.display.set_icon(icon)
            pygame.display.set_mode((800, 600))
            pygame.display.set_caption("Prometheus 82 - Testing")
            pygame.font.init()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        screen.fill((0, 0, 0))
        msg1 = "Do not close this window."
        msg2 = "Go to the console to manage the test."
        surf1 = font.render(msg1, True, (255, 255, 0))
        surf2 = font.render(msg2, True, (200, 200, 200))
        screen.blit(surf1, (20, 20))
        screen.blit(surf2, (20, 60))
        pygame.display.flip()
    except Exception as e:
        print_error(f"Couldn't create window at startup: {e}")
    
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
        print_error("No gamepad found! Some features will be unavailable.")

    # Cooling status before selecting test type
    check_cooling_period()

    # Select test type
    print("\nSelect test type:\n1: Gamepad - Test analog stick (99% threshold)\n2: Gamepad - Test button\n3: Keyboard - Test key\n4: Test hardware (solenoid and sensor)")
    try:
        test_choice = int(input("Enter your choice (1-4): "))
        test_type = {1: TEST_TYPE_STICK, 2: TEST_TYPE_BUTTON, 3: TEST_TYPE_KEYBOARD, 4: TEST_TYPE_HARDWARE}.get(test_choice)
        if not test_type:
            raise ValueError
        if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON) and not joystick:
            print_error(f"No gamepad found! Can't run {test_type} test.")
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
        print_error("Invalid input!")
        input("Press Enter to close...")
        pygame.quit()
        sys.exit()

    # Select stick movement compensation
    if test_type == TEST_TYPE_STICK:
        print("\nSelect stick movement compensation (2.0 - 6.0 ms):")
        print(f"See {Fore.LIGHTRED_EX}https://gamepadla.com/how-to.html{Fore.RESET} for guide.")
        print("Press Enter for default (3.5 ms).")
        while True:
            try:
                comp_input = input("Enter value (2.0-6.0) or Enter: ").strip()
                if not comp_input:
                    STICK_MOVEMENT_COMPENSATION = 3.5
                    break
                val = float(comp_input)
                if 2.0 <= val <= 6.0:
                    STICK_MOVEMENT_COMPENSATION = val
                    break
                else:
                    print("Value must be between 2.0 and 6.0")
            except ValueError:
                print("Invalid input. Please enter a number.")
        print(f"Stick movement compensation set to: {STICK_MOVEMENT_COMPENSATION} ms")

    # Select iterations (affects cooling timeout)
    if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD):
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
        print_error("No suitable COM ports found. Perhaps you have not connected Prometheus 82 to your computer.")
        input("Press Enter to close...")
        pygame.quit()
        sys.exit()
    
    port = None
    if len(ports) == 1:
        port = ports[0]
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
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            start_time = time.time()
            ready = False
            fw_version = None
            while time.time() - start_time < 5:
                if ser.in_waiting:
                    b = ser.read()
                    if b == b'R':
                        ready = True
                    elif b == b'V':
                        buf = b""
                        t0 = time.time()
                        while time.time() - t0 < 1.0:
                            if ser.in_waiting:
                                c = ser.read()
                                if c in (b'\n', b'\r'):
                                    break
                                buf += c
                            else:
                                time.sleep(0.001)
                        try:
                            fw_version = buf.decode("ascii").strip()
                        except Exception:
                            fw_version = None
                        break
                else:
                    time.sleep(0.001)
            if not ready:
                print_error("Prometheus did not send ready signal ('R'). Check connection or Prometheus code.")
                input("Press Enter to close...")
                pygame.quit()
                sys.exit()
            if not fw_version:
                print_error("Arduino firmware version not reported. Please update Arduino.\nhttps://github.com/cakama3a/Prometheus82?tab=readme-ov-file#how-to-use-prometheus-82")
                input("Press Enter to close...")
                pygame.quit()
                sys.exit()
            def _ver_tuple(s):
                try:
                    return tuple(int(x) for x in s.split("."))
                except Exception:
                    return (0,)
            if _ver_tuple(fw_version) < _ver_tuple(REQUIRED_ARDUINO_VERSION):
                print_error(f"Arduino firmware v{fw_version} is outdated. Please update to at least v{REQUIRED_ARDUINO_VERSION}.\nhttps://github.com/cakama3a/Prometheus82?tab=readme-ov-file#how-to-use-prometheus-82")
                input("Press Enter to close...")
                pygame.quit()
                sys.exit()
            print(f"\nPrometheus 82 connected on {port.device} ({port.description}), Arduino FW v{fw_version}")

            # Test Arduino latency and update CONTACT_DELAY
            avg_latency = test_arduino_latency(ser)
            if avg_latency is None:
                print_error(f"Calibrating Arduino latency failed. Using default CONTACT_DELAY ({CONTACT_DELAY} ms).")
                
            else:
                CONTACT_DELAY = avg_latency
                print(f"\nSet CONTACT_DELAY to {CONTACT_DELAY:.3f} ms")

            tester = LatencyTester(joystick, ser, test_type, CONTACT_DELAY, STICK_MOVEMENT_COMPENSATION, TEST_ITERATIONS)
            if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD):
                print_info("To start the test, switch to the program window and press Start.")
            
            try:
                if test_type == TEST_TYPE_HARDWARE:
                    test_passed, timing_warning = tester.test_hardware()
                    
                    # Close test window after hardware test completes
                    if pygame.display.get_init() and pygame.display.get_surface() is not None:
                        pygame.display.quit()
                    
                    if test_passed:
                        if timing_warning:
                            print(f"\n{Fore.YELLOW}Hardware functional but with timing warnings. See above for details.{Fore.RESET}")
                            print(f"{Fore.YELLOW}Ready for stick or button testing, but results may be affected.{Fore.RESET}")
                        else:
                            print(f"{Fore.GREEN}Hardware is fully functional. Ready for stick or button testing.{Fore.RESET}")
                    else:
                        print(f"{Fore.RED}Hardware issues detected. Please check connections and try again.{Fore.RESET}")
                else:
                    if test_type == TEST_TYPE_BUTTON:
                        print("\nIn the test window, press Start, then press the gamepad button you want to measure.")
                    elif test_type == TEST_TYPE_STICK:
                        pass
                    elif test_type == TEST_TYPE_KEYBOARD:
                        print("\nKeyboard key will be selected when the test window opens. Press your key at the prompt.")
                    
                    tester.test_loop()
                    
                    # Close test window after test completes
                    if pygame.display.get_init() and pygame.display.get_surface() is not None:
                        pygame.display.quit()
                    
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
                        if test_type == TEST_TYPE_STICK:
                            print(f"{'Stick movement comp.:':<26}{stats['stick_movement_compensation']:>8.3f} ms")
        
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
                                            'contact_delay': stats['contact_delay'], 'pulse_duration': stats['pulse_duration'],
                                            'stick_movement_compensation': tester.stick_movement_compensation_ms if test_type == TEST_TYPE_STICK else None
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
                                print_error("Invalid input! Please enter 1, 2, 3, or 4.")
            except KeyboardInterrupt:
                print("\nTest interrupted by user.")
    except serial.SerialException as e:
        print_error(f"Opening port failed: {e}")
    except Exception as e:
        print_error(f"While setting up COM port: {e}")
    finally:
        stop_async_logger()
        pygame.quit()
        input("Press Enter to exit...")
