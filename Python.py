# Author: John Punch
# Email: john@gamepadla.com
# License: For non-commercial use only. See full license at https://github.com/cakama3a/Prometheus82/blob/main/LICENSE
VERSION = "5.2.5.1"                 # Updated version with microsecond support
MAX_CONSECUTIVE_TIMEOUTS = 15       # Global limit for missed hits

import time
import platform
import gc
import serial
import requests
import webbrowser
import os
from serial.tools import list_ports
from colorama import Fore, Style, init
import msvcrt
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
import math

# Async logging helpers placed before main so they exist at startup
ASYNC_LOG_QUEUE = None
ASYNC_LOG_STOP = None
ASYNC_LOG_THREAD = None
LAST_RENDER_CALL = None

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
HARDWARE_TEST_ITERATIONS = 10       # Number of iterations for hardware test
STICK_SETUP_DEFLECTION_WAIT = 0.250
STICK_SETUP_FALLBACK_PULSE_DURATION = 80
STICK_SETUP_FALLBACK_DEFLECTION_WAIT = 0.500
STICK_SETUP_FALLBACK_MAX_ITERATIONS = 200
STICK_MAX_CONSECUTIVE_TIMEOUTS = 8

# Variables that should not be changed without need
COOLING_PERIOD_MINUTES = 10         # Cooling period in minutes
COOLING_PERIOD_SECONDS = COOLING_PERIOD_MINUTES * 60  # Cooling period in seconds
LOWER_QUANTILE = 0.02               # Lower quantile for filtering
UPPER_QUANTILE = 0.98               # Upper quantile for filtering
STICK_THRESHOLD = 0.99              # Stick activation threshold
RATIO = 5                           # Delay to pulse duration ratio
CONTACT_DELAY = 0.2                 # Contact sensor delay (ms) for correction (will be updated after calibration)
REQUIRED_ARDUINO_VERSION = "1.1.1"
LATENCY_EQUALITY_THRESHOLD = 0.001  # Threshold for comparing latencies (ms)

# Constants for test types
TEST_TYPE_STICK = "stick"
TEST_TYPE_BUTTON = "button"
TEST_TYPE_HARDWARE = "hardware"     # New test type for hardware check
TEST_TYPE_KEYBOARD = "keyboard"

_TEMP_DIR = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp') if platform.system() == 'Windows' else '/tmp'
LAST_TEST_TIME_FILE_BUTTON = os.path.join(_TEMP_DIR, 'last_test_time_button.txt')
LAST_TEST_TIME_FILE_STICK = os.path.join(_TEMP_DIR, 'last_test_time_stick.txt')

# Function to check time since last test
def check_cooling_period(leading_newline=True):
    """Displays a premium cooling status dashboard in the console."""
    CYAN = Fore.CYAN + Style.BRIGHT
    prefix = "\n" if leading_newline else ""
    print(f"{prefix}{CYAN}┌" + "─" * 45 + "┐")
    print(f"{CYAN}│ {Fore.WHITE}COOLING SYSTEM STATUS" + " " * 23 + f"{CYAN}│")
    print(f"{CYAN}├" + "─" * 45 + f"┤{Style.RESET_ALL}")
    
    test_types = [
        (TEST_TYPE_STICK, "Stick Solenoid"),
        (TEST_TYPE_BUTTON, "Button Solenoid")
    ]
    
    for t_type, label in test_types:
        remaining = get_cooling_remaining_seconds(t_type)
        if remaining > 0:
            status_text = f"WAIT ({remaining}s)"
            status_color = Fore.YELLOW
            icon = "⏳"
        else:
            status_text = "READY"
            status_color = Fore.GREEN
            icon = "✅"
        
        # Manually construct the line with precise spacing
        line = f"{CYAN}│{Style.RESET_ALL}  {icon} {label}:"
        line += " " * (25 - len(label))
        line += f"{status_color}{status_text}{Style.RESET_ALL}"
        line += " " * (14 - len(status_text))
        line += f"{CYAN}│"
        print(line)
    
    print(f"{CYAN}└" + "─" * 45 + f"┘{Style.RESET_ALL}")

def get_cooling_remaining_seconds(test_type):
    path = LAST_TEST_TIME_FILE_STICK if test_type == TEST_TYPE_STICK else LAST_TEST_TIME_FILE_BUTTON
    if not os.path.exists(path):
        return 0
    try:
        with open(path) as f:
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

def save_test_completion_time(iterations, test_type):
    if iterations <= 0 or test_type == TEST_TYPE_KEYBOARD:
        return
    try:
        # Calculate new cooling time based on iterations (10 min per 400 iterations)
        new_cooling = int((iterations / 400.0) * 10.0 * 60)
        
        # Get remaining time from previous test
        remaining = get_cooling_remaining_seconds(test_type)
        
        # Total cooling time is remaining + new
        total_cooling = remaining + new_cooling
        
        path = LAST_TEST_TIME_FILE_STICK if test_type == TEST_TYPE_STICK else LAST_TEST_TIME_FILE_BUTTON
        with open(path, 'w') as f:
            f.write(f"{time.time()},{total_cooling}")
            
        print(f"\n{Fore.GREEN}Test completion time recorded.{Fore.RESET}")
        label = "STICK" if test_type == TEST_TYPE_STICK else "BUTTON"
        if remaining > 0:
            print(f"{Fore.YELLOW}Added {new_cooling}s to remaining {remaining}s. Total cooling timer ({label}): {total_cooling}s.{Fore.RESET}")
        else:
            print(f"{Fore.YELLOW}Cooling timer ({label}) set to {total_cooling} seconds.{Fore.RESET}")
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

def get_input_with_countdown(prompt, menu=None, show_cooling=True):
    """Reads user input while updating the cooling status in real-time and keeping the Pygame window responsive."""
    if platform.system() != 'Windows':
        if menu: print(menu)
        return input(prompt)
    inp, last, up = "", 0, (7 if show_cooling else 0) + (menu.count('\n') + 1 if menu else 0)
    try:
        while True:
            # Keep Pygame window responsive if it's open
            if pygame.display.get_init() and pygame.display.get_surface() is not None:
                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.display.quit()
                global LAST_RENDER_CALL
                if LAST_RENDER_CALL:
                    try:
                        LAST_RENDER_CALL()
                    except:
                        pass
            
            now = time.time()
            if show_cooling and now - last >= 1:
                if last: sys.stdout.write(f"\033[?25l\r\033[A" * up)
                check_cooling_period(True)
                if menu: print(menu)
                sys.stdout.write(f"\r{prompt}{inp}\033[K\033[?25h")
                sys.stdout.flush(); last = now
            elif not show_cooling and last == 0:
                if menu: print(menu)
                sys.stdout.write(f"\r{prompt}{inp}")
                sys.stdout.flush(); last = now

            if msvcrt.kbhit():
                c = msvcrt.getch()
                if c in b'\r\n':
                    if show_cooling and last > 0:
                        # Move up to the start of the whole block (cooling + menu)
                        sys.stdout.write(f"\r\033[A" * up + "\033[J")
                        # Restore only the menu text, leaving the cooling dashboard removed
                        if menu: print(menu)
                        sys.stdout.write(f"{prompt}{inp.strip()}\n")
                    else:
                        print()
                    return inp.strip()
                if c == b'\x08':
                    inp = inp[:-1]
                    if show_cooling:
                        sys.stdout.write(f"\r\033[K{prompt}{inp}")
                    else:
                        sys.stdout.write("\b \b")
                elif c == b'\x03': raise KeyboardInterrupt
                elif c in b'\xe0\x00': msvcrt.getch()
                else:
                    try:
                        char = c.decode('utf-8', errors='ignore')
                        if char.isprintable(): inp += char; sys.stdout.write(char)
                    except: pass
                sys.stdout.flush()
            time.sleep(0.01)
    except KeyboardInterrupt: print(); raise

class LatencyTester:
    def __init__(self, gamepad, serial_port, test_type, contact_delay=CONTACT_DELAY, iterations=TEST_ITERATIONS, protocol=None):
        self.joystick = gamepad
        self.serial = serial_port
        self.test_type = test_type
        self.contact_delay = contact_delay  # Use calibrated contact delay
        self.measuring = False
        self.start_time_us = 0  # Start time in microseconds
        self.last_trigger_time_us = 0  # Last trigger time in microseconds
        self.stick_axes = None
        self.primary_axis = None  # Calibrated primary axis from first solenoid strike
        self.axis_direction = None  # Direction of primary axis (1 for positive, -1 for negative)
        self.button_to_test = None
        self.key_to_test = None
        self.invalid_measurements = 0
        self.pulse_duration_us = PULSE_DURATION * 1000  # Convert ms to µs
        self.test_interval_us = self.pulse_duration_us * RATIO
        self.max_latency_us = self.test_interval_us - self.pulse_duration_us
        self.latency_results = []
        self.latency_sum = 0.0
        self._skip_first_measurement = True
        self._started = False
        self._last_render_time = 0.0
        self._stick_runtime_fallback_used = False
        self._consecutive_timeouts = 0
        self.test_aborted = False
        self._protocol = protocol
        self.set_pulse_duration(PULSE_DURATION)  # Use milliseconds for Arduino compatibility
        self.iterations = iterations
        self._bg_surface = None  # Pre-rendered background

    def limit_iterations_for_fallback_pulse(self):
        if self.test_type == TEST_TYPE_STICK and self.iterations > STICK_SETUP_FALLBACK_MAX_ITERATIONS:
            self.iterations = STICK_SETUP_FALLBACK_MAX_ITERATIONS
            print_info(f"Stronger solenoid pulse mode is limited to {self.iterations} measurements to reduce heating.")

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
        
        # UI Colors
        BG_COLOR = (10, 12, 18)
        ACCENT_COLOR = (0, 200, 255)
        
        start_rect = pygame.Rect(0, 0, 240, 70)
        start_rect.center = (self._screen.get_width() // 2, self._screen.get_height() // 2 + 50)
        
        title_font = pygame.font.Font(None, 72)
        info_font = pygame.font.Font(None, 36)
        
        clock = pygame.time.Clock()
        while not self._started:
            time_val = time.time()
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
            
            # Background gradient
            for y in range(0, 600, 2):
                c = (10 + y//60, 12 + y//50, 18 + y//30)
                pygame.draw.rect(self._screen, c, (0, y, 800, 2))
                
            # Animated title glow
            glow_alpha = int(abs(math.sin(time_val * 2)) * 100) + 155
            title_surf = title_font.render("PROMETHEUS 82", True, (0, glow_alpha, 255))
            title_rect = title_surf.get_rect(center=(400, 150))
            self._screen.blit(title_surf, title_rect)
            
            # Subtitle
            sub_text = "READY TO START"
            sub_surf = info_font.render(sub_text, True, (200, 200, 200))
            self._screen.blit(sub_surf, sub_surf.get_rect(center=(400, 210)))

            if self.test_type == TEST_TYPE_KEYBOARD:
                msg = "Press any key to test, then press Start"
                if self.key_to_test is not None:
                    try:
                        key_name = pygame.key.name(self.key_to_test)
                    except Exception:
                        key_name = str(self.key_to_test)
                    msg = f"Selected key: {key_name.upper()}"
                msg_surf = info_font.render(msg, True, (0, 255, 150))
                self._screen.blit(msg_surf, msg_surf.get_rect(center=(400, 280)))

            # Button hover effect
            mouse_pos = pygame.mouse.get_pos()
            btn_color = (0, 180, 100) if start_rect.collidepoint(mouse_pos) else (0, 140, 70)
            
            # Draw button with glow
            for i in range(5):
                alpha_rect = start_rect.inflate(i*2, i*2)
                pygame.draw.rect(self._screen, (0, 50, 20), alpha_rect, border_radius=15)
                
            pygame.draw.rect(self._screen, btn_color, start_rect, border_radius=12)
            label = info_font.render("START TEST", True, (255, 255, 255))
            label_pos = label.get_rect(center=start_rect.center)
            self._screen.blit(label, label_pos)
            
            pygame.display.flip()
            clock.tick(60)

    def close_test_window(self):
        return

    def _pre_render_bg(self):
        """Pre-renders the static background and header to save CPU"""
        if self._bg_surface is not None:
            return
        self._bg_surface = pygame.Surface((800, 600))
        # Background gradient
        for y in range(0, 600, 4):
            c = (10 + y//100, 12 + y//80, 18 + y//60)
            pygame.draw.rect(self._bg_surface, c, (0, y, 800, 4))
        # Header (Height 60)
        pygame.draw.rect(self._bg_surface, (30, 35, 50), (0, 0, 800, 60))
        pygame.draw.line(self._bg_surface, (60, 70, 90), (0, 60), (800, 60), 1)
        title_font = pygame.font.Font(None, 32)
        ACCENT_BLUE = (0, 180, 255)
        header_surf = title_font.render("PROMETHEUS 82 | PERFORMANCE MONITOR", True, ACCENT_BLUE)
        # Vertically center header text
        self._bg_surface.blit(header_surf, (25, 30 - header_surf.get_height() // 2))

    def render_test_window(self, average_latency=None):
        if not hasattr(self, "_screen") or self._screen is None:
            return
            
        # UI Colors
        ACCENT_BLUE = (0, 180, 255)
        ACCENT_CYAN = (0, 255, 220)
        TEXT_WHITE = (255, 255, 255)
        TEXT_GRAY = (180, 190, 210)
        
        # Draw pre-rendered background
        self._pre_render_bg()
        self._screen.blit(self._bg_surface, (0, 0))
        
        title_font = pygame.font.Font(None, 32)
        
        # Test Status Card
        card_rect = pygame.Rect(25, 80, 750, 100)
        pygame.draw.rect(self._screen, (20, 25, 35), card_rect, border_radius=15)
        pygame.draw.rect(self._screen, (50, 60, 80), card_rect, width=1, border_radius=15)
        
        if self.test_type == TEST_TYPE_HARDWARE:
            status_text = "HARDWARE TEST: RUNNING..."
            status_color = (255, 180, 0)
        elif self.test_type == TEST_TYPE_STICK and getattr(self, "_started", False) and len(self.latency_results) == 0:
            status_text = "STICK CALIBRATION IN PROGRESS..."
            status_color = ACCENT_CYAN
        else:
            status_text = f"{self.test_type.upper()} TEST: {len(self.latency_results)} / {self.iterations}"
            status_color = TEXT_WHITE
            
        status_surf = title_font.render(status_text, True, status_color)
        self._screen.blit(status_surf, (50, 105))
        
        # Progress Bar with Glow and Animation
        bar_x, bar_y = 50, 145
        bar_w, bar_h = 700, 12
        pygame.draw.rect(self._screen, (40, 45, 55), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        
        if self.iterations > 0:
            progress_pct = len(self.latency_results) / self.iterations
            progress_w = int(progress_pct * bar_w)
            if progress_w > 0:
                # Gradient for progress bar
                pygame.draw.rect(self._screen, ACCENT_BLUE, (bar_x, bar_y, progress_w, bar_h), border_radius=6)

        # Latency Dashboard
        if average_latency is not None:
            dash_rect = pygame.Rect(25, 200, 750, 360)
            pygame.draw.rect(self._screen, (15, 20, 28), dash_rect, border_radius=20)
            pygame.draw.rect(self._screen, (40, 50, 70), dash_rect, width=1, border_radius=20)
            
            # Glow for latency text
            label_font = pygame.font.Font(None, 36)
            lat_label = label_font.render("AVERAGE RESPONSE TIME", True, TEXT_GRAY)
            self._screen.blit(lat_label, (dash_rect.centerx - lat_label.get_width()//2, 250))
            
            val_font = pygame.font.Font(None, 120)
            val_text = f"{average_latency:.2f}"
            unit_text = "ms"
            
            val_surf = val_font.render(val_text, True, ACCENT_CYAN)
            unit_font = pygame.font.Font(None, 48)
            unit_surf = unit_font.render(unit_text, True, ACCENT_BLUE)
            
            total_w = val_surf.get_width() + unit_surf.get_width() + 8
            start_x = dash_rect.centerx - total_w // 2
            
            # Align ms precisely to the baseline of the large digits
            val_y = 320
            unit_y = val_y + (val_surf.get_height() - unit_surf.get_height()) - 5 # Manual adjustment for font padding
            
            self._screen.blit(val_surf, (start_x, val_y))
            self._screen.blit(unit_surf, (start_x + val_surf.get_width() + 8, unit_y))
            
            # Stats breakdown with fixed positions to prevent jumping
            if self.latency_results:
                min_lat = min(self.latency_results)
                max_lat = max(self.latency_results)
                
                # Calculate jitter (standard deviation)
                jitter = statistics.stdev(self.latency_results) if len(self.latency_results) > 1 else 0.0
                
                # Render each stat at a fixed offset
                min_surf = label_font.render(f"MIN: {min_lat:.2f}ms", True, TEXT_GRAY)
                max_surf = label_font.render(f"MAX: {max_lat:.2f}ms", True, TEXT_GRAY)
                jitter_surf = label_font.render(f"JITTER: {jitter:.2f}ms", True, TEXT_GRAY)
                
                # Positions based on thirds of the card
                self._screen.blit(min_surf, (100, 480))
                self._screen.blit(max_surf, (330, 480))
                self._screen.blit(jitter_surf, (550, 480))
            
        # Check if test is finished
        is_finished = len(self.latency_results) >= self.iterations and self.iterations > 0
        
        # Status Badge (vertically centered in header)
        if is_finished:
            # FINISHED Badge
            badge_rect = pygame.Rect(680, 16, 95, 28)
            pygame.draw.rect(self._screen, (0, 30, 10), badge_rect, border_radius=6)
            pygame.draw.rect(self._screen, (0, 150, 70), badge_rect, width=1, border_radius=6)
            badge_font = pygame.font.Font(None, 24)
            badge_surf = badge_font.render("FINISHED", True, (0, 255, 120))
            self._screen.blit(badge_surf, (badge_rect.centerx - badge_surf.get_width()//2, 23))
        else:
            # LIVE Badge
            pulse = int(abs(math.sin(time.time() * 2)) * 50) + 100
            badge_rect = pygame.Rect(710, 16, 65, 28)
            pygame.draw.rect(self._screen, (30, 0, 0), badge_rect, border_radius=6)
            pygame.draw.rect(self._screen, (pulse, 20, 40), badge_rect, width=1, border_radius=6)
            
            # Red dot inside badge
            pygame.draw.circle(self._screen, (255, 40, 60), (722, 30), 4)
            
            badge_font = pygame.font.Font(None, 24)
            badge_surf = badge_font.render("LIVE", True, (255, 60, 80))
            self._screen.blit(badge_surf, (732, 23))

        # Instruction at the bottom
        hint_font = pygame.font.Font(None, 24)
        if is_finished:
            hint_text = "TEST COMPLETE - CONTINUE IN CONSOLE TO SAVE RESULTS"
            hint_color = (0, 255, 180)
        else:
            hint_text = "KEEP WINDOW ACTIVE AND ON TOP TO CAPTURE INPUTS"
            hint_color = (150, 150, 50)
            
        hint_surf = hint_font.render(hint_text, True, hint_color)
        self._screen.blit(hint_surf, (400 - hint_surf.get_width() // 2, 575))
        
        pygame.display.flip()

    def check_stick_setup(self, iterations=5):
        if self.test_type != TEST_TYPE_STICK:
            return None
        if not self.serial:
            return None

        ok = self._check_stick_setup_once(iterations, STICK_SETUP_DEFLECTION_WAIT, report_errors=False)
        if ok:
            return True

        print_info(f"Retrying setup check with stronger solenoid pulse ({STICK_SETUP_FALLBACK_PULSE_DURATION} ms).")
        self.set_pulse_duration(STICK_SETUP_FALLBACK_PULSE_DURATION)
        self.limit_iterations_for_fallback_pulse()
        return self._check_stick_setup_once(iterations, STICK_SETUP_FALLBACK_DEFLECTION_WAIT, report_errors=True)

    def _check_stick_setup_once(self, iterations=5, deflection_wait=STICK_SETUP_DEFLECTION_WAIT, report_errors=True):
        if self.test_type != TEST_TYPE_STICK:
            return None
        if not self.serial:
            return None
        print(f"\nVerifying setup: {iterations} hits")
        
        invalid_hold_count = 0
        invalid_deflection_count = 0
        invalid_contact_count = 0
        try:
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
        except Exception:
            pass
            
        for i in range(iterations):
            pygame.event.pump()
            baseline_axes = []
            if self.joystick:
                baseline_axes = [self.joystick.get_axis(a) for a in range(self.joystick.get_numaxes())]

            max_deflection = 0.0
            
            def update_deflection():
                nonlocal max_deflection
                if not self.stick_axes:
                    self.detect_active_stick()
                else:
                    pygame.event.pump()
                    
                if self.joystick:
                    axes = self.stick_axes if self.stick_axes else range(self.joystick.get_numaxes())
                    for axis in axes:
                        current_val = self.joystick.get_axis(axis)
                        if self.stick_axes:
                            val = abs(current_val)
                            if val > max_deflection:
                                max_deflection = val
                        elif axis < len(baseline_axes) and abs(current_val - baseline_axes[axis]) > 0.05:
                            val = abs(current_val)
                            if val > max_deflection:
                                max_deflection = val

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
                update_deflection()
                try:
                    time.sleep(0.001)
                except Exception:
                    pass
            
            hold_ok = None

            if not contact_time_us:
                invalid_contact_count += 1
            else:
                # 20 ms hold-check
                try:
                    time.sleep(0.020)
                    update_deflection()

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
                            
                            update_deflection()
                            time.sleep(0.001)
                except Exception:
                    pass

                # Wait a bit longer to capture max deflection (delay for stick peak)
                t_deflect = time.perf_counter()
                while time.perf_counter() - t_deflect < deflection_wait:
                    update_deflection()
                    time.sleep(0.001)
                
            deflection_pct = min(int(max_deflection * 100), 100)
            
            if deflection_pct < 99:
                deflection_str = f"{Fore.RED}{deflection_pct}%{Fore.RESET}"
                invalid_deflection_count += 1
            else:
                deflection_str = f"{deflection_pct}%"

            if not contact_time_us or hold_ok is False:
                if hold_ok is False:
                    invalid_hold_count += 1
                print(f"Hit {i+1}/{iterations}: {Fore.RED}FAIL{Fore.RESET} | Deflection {deflection_str}")
            else:
                print(f"Hit {i+1}/{iterations}: OK | Deflection {deflection_str}")
                
            time.sleep(0.1)
            try:
                self.render_test_window(None)
            except Exception:
                pass

        if any([invalid_contact_count > 0, invalid_deflection_count > 0, invalid_hold_count > 0]):
            sensor_errors = invalid_contact_count + invalid_hold_count
            if report_errors and sensor_errors > 0:
                print_error(f"Setup check failed: Sensor button did not register the hit properly ({sensor_errors} invalid hits).\nPlease move the gamepad closer to the sensor. Instruction: https://youtu.be/MLsXo8Si730")
            if report_errors and invalid_deflection_count > 0:
                print_error(f"Setup check failed: Stick is not fully deflecting ({invalid_deflection_count} hits < 99%).\nPlease reinstall the gamepad on the stand or adjust the sensor position with a screwdriver.")
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
        """Checks if stick is at extreme position, auto-locking to the primary axis on first hit."""
        if not self.stick_axes or not self.joystick:
            return False
        
        # If we already know which axis is being hit, check only that one
        if self.primary_axis is not None:
            return abs(self.joystick.get_axis(self.primary_axis)) >= STICK_THRESHOLD
            
        # On the first hit, detect which axis of the pair reached the threshold first
        for axis in self.stick_axes:
            if abs(self.joystick.get_axis(axis)) >= STICK_THRESHOLD:
                self.primary_axis = axis
                print(f"Primary axis detected and locked: Axis {axis}")
                return True
        return False

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
        """Calculates current latency including contact delay"""
        current_time_us = time.perf_counter() * 1000000
        # Calculate raw latency in milliseconds
        latency_ms = (current_time_us - self.start_time_us) / 1000.0
        # Add contact delay
        latency_ms += self.contact_delay
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
                self.latency_sum += latency_ms
                self._consecutive_timeouts = 0
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
            'jitter': round(statistics.pstdev(filtered_results) if len(filtered_results) > 0 else 0.0, 2),
            'filtered_results': filtered_results,
            'pulse_duration': self.pulse_duration_us / 1000,
            'contact_delay': self.contact_delay
        }

    def test_loop(self):
        """Main test loop for stick or button tests with high-precision optimizations"""
        global LAST_RENDER_CALL
        LAST_RENDER_CALL = None
        print("\nPreparing test window...")
        self.open_test_window()
        print("Test window ready. Switch to the graphical window and press START TEST to begin.")
        self.wait_for_start()
        
        if self.test_type == TEST_TYPE_STICK:
            ok = self.check_stick_setup(iterations=5)
            if not ok:
                if pygame.display.get_init() and pygame.display.get_surface() is not None:
                    pygame.display.quit()
                return
                
        print(f"\nStarting {self.iterations} measurements with microsecond precision...\n")
        
        # --- High Precision Mode: Start ---
        # 1. Set High Process Priority (Windows)
        if platform.system() == 'Windows':
            try:
                # HIGH_PRIORITY_CLASS = 0x00000080
                ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
            except Exception:
                pass
        
        # 2. Disable Garbage Collector
        gc.collect()
        gc.disable()
        
        try:
            self.trigger_solenoid()
            while len(self.latency_results) < self.iterations:
                current_time_us = time.perf_counter() * 1000000
                
                # Trigger handling
                if not self.measuring:
                    time_since_trigger = current_time_us - self.last_trigger_time_us
                    if time_since_trigger >= self.test_interval_us:
                        self.trigger_solenoid()
                        current_time_us = time.perf_counter() * 1000000 # Update after trigger
                
                # Serial handling (waiting for 'S')
                if self.serial and self.serial.in_waiting:
                    found = False
                    while self.serial.in_waiting:
                        if self.serial.read() == b'S':
                            found = True
                            break
                    if found:
                        self.start_time_us = time.perf_counter() * 1000000
                        self.measuring = True
                
                # Input handling (waiting for gamepad)
                self.check_input()
                
                # Timeout handling
                if self.measuring and current_time_us - self.start_time_us > self.max_latency_us:
                    self.invalid_measurements += 1
                    self._consecutive_timeouts += 1
                    print(f"Invalid measurement: no input detected within {self.max_latency_us/1000:.2f} ms")
                    self.measuring = False
                    
                    limit = STICK_MAX_CONSECUTIVE_TIMEOUTS if self.test_type == TEST_TYPE_STICK else MAX_CONSECUTIVE_TIMEOUTS
                    if self._consecutive_timeouts >= limit:
                        print_error(f"Test stopped: too many consecutive missed inputs ({self._consecutive_timeouts}).\nMake sure the test window is focused and receiving input before restarting.")
                        self.test_aborted = True
                        break
                    
                    if self.test_type == TEST_TYPE_STICK and not self._stick_runtime_fallback_used and self.pulse_duration_us < STICK_SETUP_FALLBACK_PULSE_DURATION * 1000:
                        self._stick_runtime_fallback_used = True
                        print_info(f"Switching to stronger solenoid pulse ({STICK_SETUP_FALLBACK_PULSE_DURATION} ms) for remaining measurements.")
                        self.set_pulse_duration(STICK_SETUP_FALLBACK_PULSE_DURATION)
                        self.limit_iterations_for_fallback_pulse()
                
                # Optimized Pygame pumping
                pygame.event.pump()
                
                # System and UI responsiveness (only when not in critical measurement phase)
                is_active_phase = self.measuring or (current_time_us - self.last_trigger_time_us < self.max_latency_us)
                
                if not is_active_phase:
                    # Resting phase: we can yield to the system and render UI
                    time.sleep(0.001)
                    
                    try:
                        now = time.perf_counter()
                        if now - self._last_render_time >= 1.0 / 30.0:
                            average_latency = self.latency_sum / len(self.latency_results) if self.latency_results else None
                            self.render_test_window(average_latency)
                            self._last_render_time = now
                    except Exception:
                        pass
                        
        finally:
            # --- High Precision Mode: End ---
            # 1. Enable Garbage Collector
            gc.enable()
            
            # 2. Restore Normal Process Priority (Windows)
            if platform.system() == 'Windows':
                try:
                    # NORMAL_PRIORITY_CLASS = 0x00000020
                    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000020)
                except Exception:
                    pass
                    
        # Final render with results
        average_latency = self.latency_sum / len(self.latency_results) if self.latency_results else None
        self.render_test_window(average_latency)
        
        # Set background render call for the console input loops
        LAST_RENDER_CALL = lambda: self.render_test_window(average_latency)

        # Start cooling period immediately after measurements finish (even if aborted)
        total_hits = len(self.latency_results) + self.invalid_measurements
        if total_hits > 0:
            # Use requested iterations if successful, or actual hits if aborted
            save_test_completion_time(self.iterations if not self.test_aborted else total_hits, self.test_type)
        
        if not self.test_aborted:
            pass

        self.close_test_window()

def detect_input_mode(name, guid, axes, num_hats, num_buttons):
    """Detects protocol based on name, guid, resting axes state, and structural features."""
    n, g = name.lower(), guid.lower()
    guid_chunks = {g[i:i+4] for i in range(0, len(g), 4) if len(g[i:i+4]) == 4}

    # 1. Official Sony markers and licensed brands
    sony_markers = ("dualsense", "ps5", "edge", "dualshock", "ds4", "ps4", "playstation", "astro")
    if any(s in n for s in sony_markers):
        return "Sony"

    # 2. Sony family vendor IDs (extracted from GUID chunks)
    # 054c: Sony, 9886: Astro, 146b: Nacon, 1532: Razer, 294b: Scuf, 0c12: Zeroplus, 0f0d: Hori
    sony_vids = {"4c05", "8698", "6b14", "3215", "4b29", "120c", "0d0f"}
    if any(vid in guid_chunks for vid in sony_vids):
        return "Sony"

    # 3. Structural heuristic: Sony-layout controllers (D-pad is buttons, so 0 hats)
    # Standard XInput (Xbox) ALWAYS has 1 hat (Hat 0) in the standard Windows driver.
    # If it has 0 hats but is a full gamepad (14+ buttons), it's highly likely a Sony-style layout.
    if num_hats == 0 and num_buttons >= 14 and "xbox" not in n:
        return "Sony"

    if any(s in n for s in ("joy-con", "joycon", "nintendo switch", "switch pro", "nintendo")) or "057e" in g:
        return "Switch"
    
    # 4. XInput protocol check (Triggers rest at -1.0)
    if any(abs(a + 1) < 0.1 for a in axes):
        return "XInput"
        
    return "DInput"

# Axis pair groupings per protocol (used for partner-axis pairing)
INPUT_MODE_AXIS_PAIRS = {
    "DInput": [(0, 1), (3, 5)],
    "Default": [(0, 1), (2, 3)]
}

def detect_gamepad_mode(joystick):
    """Detect gamepad mode (XInput, DInput, Sony, Switch) based on name and axes at rest"""
    time.sleep(0.1)  # Wait for initialization
    for _ in range(10):  # Warmup
        pygame.event.pump()
        [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
        time.sleep(0.01)
    
    axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
    return detect_input_mode(joystick.get_name(), joystick.get_guid(), axes, joystick.get_numhats(), joystick.get_numbuttons())

# Short ID Generation
def generate_short_id(length=12):
    """Generates a random short ID"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def restart_current_program():
    try:
        stop_async_logger()
    except Exception:
        pass
    try:
        if pygame.display.get_init():
            pygame.display.quit()
        pygame.quit()
    except Exception:
        pass
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)

if __name__ == "__main__":
    wait_on_exit = True
    pygame.init()
    init(autoreset=True) # Initialize colorama
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
        # Show premium initial instructions in the Pygame window
        screen = pygame.display.get_surface()
        font_large = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 32)
        
        # Background gradient
        for y in range(0, 600, 4):
            c = (15 + y//100, 20 + y//80, 30 + y//60)
            pygame.draw.rect(screen, c, (0, y, 800, 4))
            
        msg1 = "PROMETHEUS 82 IS READY"
        msg2 = "Please go to the console to configure the test."
        msg3 = "Do not close this window."
        
        surf1 = font_large.render(msg1, True, (0, 200, 255))
        surf2 = font_small.render(msg2, True, (200, 200, 200))
        surf3 = font_small.render(msg3, True, (150, 150, 50))
        
        screen.blit(surf1, (400 - surf1.get_width()//2, 240))
        screen.blit(surf2, (400 - surf2.get_width()//2, 300))
        screen.blit(surf3, (400 - surf3.get_width()//2, 550))
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
            menu_gamepads = "Available gamepads:\n" + "\n".join([f"{i + 1}: {pygame.joystick.Joystick(i).get_name()}" for i in range(joystick_count)])
            while True:
                try:
                    choice_input = get_input_with_countdown(f"Select gamepad (1-{joystick_count}): ", menu_gamepads).strip()
                    if not choice_input: continue
                    joystick = pygame.joystick.Joystick(int(choice_input) - 1)
                    print(f"\nSelected gamepad: {joystick.get_name()}")
                    break
                except (ValueError, IndexError):
                    print_error(f"Invalid selection! Please enter 1-{joystick_count}.")
        else:
            joystick = pygame.joystick.Joystick(0)
            print(f"\nAutoselected gamepad: {joystick.get_name()}")
        joystick.init()
        
        # Detect gamepad mode (XInput, DInput, Sony, Switch)
        detected_mode = detect_gamepad_mode(joystick)
        print(f"Detected protocol:  {Fore.GREEN}{detected_mode}{Fore.RESET}")
    else:
        print_error("No gamepad found! Some features will be unavailable.")

    # Select test type
    menu_test_type = "Select test type:\n1: Gamepad\t- Test analog stick\n2: Gamepad\t- Test button\n3: Keyboard\t- Test key\n4: Hardware\t- Test solenoid and sensor"
    while True:
        try:
            choice_input = get_input_with_countdown("Enter your choice (1-4): ", menu_test_type).strip()
            if not choice_input:
                continue
            test_choice = int(choice_input)
            test_type = {1: TEST_TYPE_STICK, 2: TEST_TYPE_BUTTON, 3: TEST_TYPE_KEYBOARD, 4: TEST_TYPE_HARDWARE}.get(test_choice)
            if not test_type:
                print_error("Invalid choice! Please select 1-4.")
                continue
                
            if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON) and not joystick:
                print_error(f"No gamepad found! Can't run {test_type} test.")
                continue # Allow selecting another type or connecting gamepad? Actually joystick was detected earlier.
            
            remaining = get_cooling_remaining_seconds(test_type)
            if remaining > 0 and (test_type != TEST_TYPE_STICK or remaining >= 40):
                print(f"\n{Fore.YELLOW}WARNING: Device has not cooled yet. Running this test now may cause degradation. Remaining cooling time: {remaining} seconds.{Fore.RESET}")
                inner_choice = ""
                while inner_choice not in ('Y', 'N'):
                    inner_choice = get_input_with_countdown("Continue anyway? (Y/N): ", show_cooling=False).upper().strip()
                if inner_choice == 'N':
                    print("Please wait for cooling or select another test.")
                    continue
            
            # If we reach here, selection is valid
            break
        except ValueError:
            print_error("Invalid input! Please enter a number.")

    # Select iterations (affects cooling timeout)
    if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD):
        menu_iters = "Select number of iterations:\n1: 400 (For Gamepadla.com validation)\n2: 200\n3: 100\nOr enter a custom number between 10 and 400."
        while True:
            try:
                iter_input = get_input_with_countdown("Enter your choice (1/2/3 or custom 10-400): ", menu_iters).strip()
                if iter_input == '1':
                    TEST_ITERATIONS = 400
                    break
                elif iter_input == '2':
                    TEST_ITERATIONS = 200
                    break
                elif iter_input == '3':
                    TEST_ITERATIONS = 100
                    break
                else:
                    custom_iters = int(iter_input)
                    if 10 <= custom_iters <= 400:
                        TEST_ITERATIONS = custom_iters
                        break
                    else:
                        print_error("Invalid number! Please enter a value between 10 and 400.")
            except ValueError:
                print_error("Invalid input! Please enter 1, 2, 3, or a number.")

    # Setup serial connection
    # --- MODIFICATION START ---
    all_ports = list_ports.comports()
    # Filter out ports that have "Bluetooth" in their description (case-insensitive)
    ports = [p for p in all_ports if "bluetooth" not in p.description.lower()]

    if not ports:
        print_error("No suitable COM ports found. Perhaps you have not connected Prometheus 82 to your computer.")
        get_input_with_countdown("Press Enter to close...", show_cooling=False)
        pygame.quit()
        sys.exit()
    
    port = None
    if len(ports) == 1:
        port = ports[0]
    else:
        menu_ports = "Available COM ports:\n" + "\n".join([f"{i + 1}: {p.device} - {p.description}" for i, p in enumerate(ports)])
        while True:
            try:
                selection_input = get_input_with_countdown(f"Select COM port (1-{len(ports)}): ", menu_ports).strip()
                if not selection_input: continue
                selection = int(selection_input) - 1
                if 0 <= selection < len(ports):
                    port = ports[selection]
                    break
                else:
                    print_error(f"Please select a number between 1 and {len(ports)}.")
            except ValueError:
                print_error("Invalid input! Please enter a number.")
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
                print_error("Arduino firmware version not reported. Please update Arduino.\nhttps://github.com/cakama3a/Prometheus82/blob/main/README.md#how-to-update-the-firmware-of-a-p82-device")
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
                get_input_with_countdown("Press Enter to close...", show_cooling=False)
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

            tester = LatencyTester(joystick, ser, test_type, CONTACT_DELAY, TEST_ITERATIONS, detected_mode)
            if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD):
                print_info("To start the test, switch to the program window and press Start.")
            
            try:
                if test_type == TEST_TYPE_HARDWARE:
                    test_passed, timing_warning = tester.test_hardware()
                    
                    # Hardware test completed
                    
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
                        print(f"\n{Fore.YELLOW}Stick test setup:{Fore.RESET}")
                        print("Use a reverse sensor for stick latency testing.")
                        print("Set the solenoid tip about 1-2 mm from the stick in the neutral position.")
                        print("Avoid a large gap: extra acceleration before contact can cause stick bounce and high jitter.")
                        print("The sensor button should trigger near the end of stick travel.")
                        print(f"Guide: {Fore.LIGHTRED_EX}https://youtu.be/MLsXo8Si730{Fore.RESET}")
                    elif test_type == TEST_TYPE_KEYBOARD:
                        print("\nKeyboard key will be selected when the test window opens. Press your key at the prompt.")
                    
                    tester.test_loop()
                    
                    # Test completed
                    if getattr(tester, "test_aborted", False):
                        get_input_with_countdown("Press Enter to exit...", show_cooling=False)
                        pygame.quit()
                        sys.exit()
                    
                    stats = tester.get_statistics()
                    if stats:
                        print(f"\n{Fore.GREEN}Test completed!{Fore.RESET}")
                        print(f"\n{Style.BRIGHT}{Fore.CYAN}" + "="*15 + f"LATENCY" + "="*15 + f"{Fore.RESET}{Style.RESET_ALL}")
                        print(f"{'Min latency:':<26}{stats['min']:>8.2f} ms")
                        print(f"{'Max latency:':<26}{stats['max']:>8.2f} ms")
                        print(f"{Style.BRIGHT}{Fore.CYAN}" + f"{'Average latency:':<26}{stats['avg']:>8.2f} ms{Fore.RESET}" + f"{Style.RESET_ALL}")
                        print(f"{'Jitter:':<26}{stats['jitter']:>8.2f} ms")
                        print(f"{Style.BRIGHT}{Fore.CYAN}" + "="*37 + f"{Fore.RESET}{Style.RESET_ALL}")
                        print(f"{Fore.LIGHTBLACK_EX}* Statistics are calculated using {int(LOWER_QUANTILE*100)}%-{int(UPPER_QUANTILE*100)}% quantile filtering.{Fore.RESET}")
                        print(f"\n{Style.BRIGHT}Measurement Details{Style.RESET_ALL}")
                        print(f"{'Iterations:':<26}{tester.iterations:>8}")
                        print(f"{'Total measurements:':<26}{stats['total_samples']:>8}")
                        print(f"{'Valid measurements:':<26}{stats['valid_samples']:>8}")
                        print(f"{'Invalid measurements:':<26}{stats['invalid_samples']:>8} (>{stats['pulse_duration']*(RATIO-1):.1f} ms)")
                        print(f"{'Filtered count:':<26}{stats['filtered_samples']:>8}")
                        print(f"{'Pulse duration:':<26}{stats['pulse_duration']:>8.1f} ms")
                        print(f"{'Contact delay:':<26}{stats['contact_delay']:>8.3f} ms")
        
                        if stats['contact_delay'] > 1.2:
                            print(f"\n{Fore.RED}Warning: Tester's inherent latency ({stats['contact_delay']:.3f} ms) exceeds recommended 1.2 ms, which may affect results.{Fore.RESET}")

                        uploaded_to_gamepadla = False
                        exported_to_csv = False
                        # Action selection with retry on invalid input
                        while True:
                            if uploaded_to_gamepadla:
                                open_label = f"{Fore.LIGHTBLACK_EX}Open on Gamepadla.com (already used){Fore.RESET}"
                            elif stats['valid_samples'] < 200:
                                open_label = f"{Fore.LIGHTBLACK_EX}Open on Gamepadla.com (min 200 req.){Fore.RESET}"
                            else:
                                open_label = "Open on Gamepadla.com"
                            export_label = f"{Fore.LIGHTBLACK_EX}Export to CSV (already used){Fore.RESET}" if exported_to_csv else "Export to CSV"
                            print(f"\nSelect action:\n1: {open_label}\n2: {export_label}\n3: Restart test\n4: Exit")
                            try:
                                choice_val = get_input_with_countdown("Enter your choice (1-4): ", show_cooling=False)
                                if not choice_val: continue
                                choice = int(choice_val)
                                if choice not in [1, 2, 3, 4]:
                                    print("Invalid selection! Please enter 1, 2, 3, or 4.")
                                    continue
                            except ValueError:
                                print_error("Invalid input! Please enter 1, 2, 3, or 4.")
                                continue

                            if choice == 1:
                                if stats['valid_samples'] < 200:
                                    print_error(f"Test results cannot be uploaded to Gamepadla.com because they contain fewer than 200 measurements (current: {stats['valid_samples']}).")
                                    print("Please run a test with at least 200 iterations to share your results.")
                                    continue
                                if uploaded_to_gamepadla:
                                    print(f"{Fore.YELLOW}Warning: This result has already been opened on Gamepadla.com. Restart the test to send a new result.{Fore.RESET}")
                                    continue
                                while True:
                                    test_key = generate_short_id()
                                    gamepad_name = get_input_with_countdown("Enter gamepad name: ", show_cooling=False)
                                    connection = {"1": "Cable", "2": "Dongle", "3": "Bluetooth"}.get(
                                        get_input_with_countdown("Current connection (1. Cable, 2. Dongle, 3. Bluetooth): ", show_cooling=False), "Unset")
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
                                            uploaded_to_gamepadla = True
                                            break
                                        print(f"\nServer error. Status code: {response.status_code}")
                                    except requests.exceptions.RequestException:
                                        print("\nNo internet connection or server is unreachable")
                                    if get_input_with_countdown("\nDo you want to try sending the data again? (Y/N): ", show_cooling=False).upper() != 'Y':
                                        break
                            elif choice == 2:
                                if exported_to_csv:
                                    print(f"{Fore.YELLOW}Warning: This result has already been exported to CSV. Restart the test to export a new result.{Fore.RESET}")
                                    continue
                                export_to_csv(stats, joystick.get_name() if joystick else "N/A", tester.latency_results)
                                exported_to_csv = True
                                continue
                            elif choice == 3:
                                print("\nRestarting with a fresh test session...")
                                restart_current_program()
                            elif choice == 4:
                                wait_on_exit = False
                                break
                            
                            continue
            except KeyboardInterrupt:
                print("\nTest interrupted by user.")
    except serial.SerialException as e:
        print_error(f"Opening port failed: {e}")
    except Exception as e:
        print_error(f"While setting up COM port: {e}")
    finally:
        stop_async_logger()
        pygame.quit()
        if wait_on_exit:
            get_input_with_countdown("Press Enter to exit...", show_cooling=False)
