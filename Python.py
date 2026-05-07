# Author: John Punch
# Email: john@gamepadla.com
# License: For non-commercial use only. See full license at https://github.com/cakama3a/Prometheus82/blob/main/LICENSE
VERSION = "5.2.4.6"                 # Updated version with microsecond support

import time
import platform
import serial
import requests
import webbrowser
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
HARDWARE_TEST_ITERATIONS = 10       # Number of iterations for hardware test
STICK_SETUP_DEFLECTION_WAIT = 0.250
STICK_SETUP_FALLBACK_PULSE_DURATION = 80
STICK_SETUP_FALLBACK_DEFLECTION_WAIT = 0.500
STICK_SETUP_FALLBACK_MAX_ITERATIONS = 200

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
def check_cooling_period(test_type=None):
    try:
        if test_type is None:
            warnings = []
            for label, path in (("BUTTON", LAST_TEST_TIME_FILE_BUTTON), ("STICK", LAST_TEST_TIME_FILE_STICK)):
                if os.path.exists(path):
                    with open(path) as f:
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
                            warnings.append(f"{label}: {remaining} seconds")
            if warnings:
                print(f"\n{Fore.YELLOW}WARNING: Cooling required — " + "; ".join(warnings) + f".{Fore.RESET}")
            return True
        else:
            path = LAST_TEST_TIME_FILE_STICK if test_type == TEST_TYPE_STICK else LAST_TEST_TIME_FILE_BUTTON
            if not os.path.exists(path):
                return True
            with open(path) as f:
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
                    label = "STICK" if test_type == TEST_TYPE_STICK else "BUTTON"
                    print(f"\n{Fore.YELLOW}WARNING: Cooling required ({label}): {remaining} seconds remaining.{Fore.RESET}")
                return True
    except (ValueError, IOError):
        return True

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

# Function to record the test completion time
def save_test_completion_time(iterations, test_type):
    try:
        cooling_minutes = (iterations / 400.0) * 10.0
        cooling_seconds = int(cooling_minutes * 60)
        path = LAST_TEST_TIME_FILE_STICK if test_type == TEST_TYPE_STICK else LAST_TEST_TIME_FILE_BUTTON
        with open(path, 'w') as f:
            f.write(f"{time.time()},{cooling_seconds}")
        print(f"\n{Fore.GREEN}Test completion time recorded.{Fore.RESET}")
        label = "STICK" if test_type == TEST_TYPE_STICK else "BUTTON"
        print(f"{Fore.YELLOW}Cooling timer ({label}) set to {cooling_seconds} seconds.{Fore.RESET}")
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

def gui_init(title="Prometheus 82"):
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
    if pygame.display.get_surface() is None:
        icon = load_window_icon()
        if icon:
            pygame.display.set_icon(icon)
        pygame.display.set_mode((900, 650))
    pygame.display.set_caption(title)
    pygame.font.init()
    return pygame.display.get_surface()

def gui_draw_text(screen, text, pos, font, color=(230, 230, 230), max_width=None):
    words = str(text).split(" ")
    lines = []
    current = ""
    for word in words:
        test = word if not current else current + " " + word
        if max_width and font.size(test)[0] > max_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    x, y = pos
    for line in lines:
        screen.blit(font.render(line, True, color), (x, y))
        y += font.get_height() + 4
    return y

def gui_button(screen, rect, text, font, mouse_pos, color=(45, 95, 150), hover=(65, 125, 195), disabled=False):
    draw_color = (55, 55, 60) if disabled else (hover if rect.collidepoint(mouse_pos) else color)
    pygame.draw.rect(screen, draw_color, rect, border_radius=12)
    pygame.draw.rect(screen, (105, 125, 150), rect, 2, border_radius=12)
    label = font.render(text, True, (180, 180, 180) if disabled else (255, 255, 255))
    screen.blit(label, label.get_rect(center=rect.center))

def gui_wait_for_quit():
    screen = gui_init()
    font = pygame.font.Font(None, 30)
    small = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()
    while True:
        mouse = pygame.mouse.get_pos()
        close_rect = pygame.Rect(340, 520, 220, 56)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key in (K_ESCAPE, K_RETURN, K_SPACE):
                return
            if event.type == MOUSEBUTTONDOWN and close_rect.collidepoint(event.pos):
                return
        screen.fill((14, 17, 24))
        gui_draw_text(screen, "Prometheus 82", (40, 40), pygame.font.Font(None, 46), (130, 190, 255))
        gui_draw_text(screen, "Press Enter, Space, Esc or click Close to exit.", (40, 110), small, (220, 220, 220))
        gui_button(screen, close_rect, "Close", font, mouse)
        pygame.display.flip()
        clock.tick(60)

def gui_message(title, lines, buttons=("OK",), accent=(130, 190, 255)):
    screen = gui_init()
    title_font = pygame.font.Font(None, 44)
    font = pygame.font.Font(None, 28)
    small = pygame.font.Font(None, 23)
    clock = pygame.time.Clock()
    if isinstance(lines, str):
        lines = [lines]
    while True:
        mouse = pygame.mouse.get_pos()
        button_rects = []
        total_width = len(buttons) * 180 + (len(buttons) - 1) * 16
        start_x = (screen.get_width() - total_width) // 2
        for i, label in enumerate(buttons):
            button_rects.append((pygame.Rect(start_x + i * 196, 550, 180, 54), label))
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key in (K_RETURN, K_SPACE):
                    return buttons[0]
                if event.key == K_ESCAPE:
                    return buttons[-1]
            if event.type == MOUSEBUTTONDOWN:
                for rect, label in button_rects:
                    if rect.collidepoint(event.pos):
                        return label
        screen.fill((14, 17, 24))
        gui_draw_text(screen, title, (40, 40), title_font, accent, 820)
        y = 120
        for line in lines:
            y = gui_draw_text(screen, line, (50, y), small if len(line) > 90 else font, (225, 225, 225), 800) + 10
        for rect, label in button_rects:
            gui_button(screen, rect, label, font, mouse, color=(50, 110, 75) if label in ("OK", "Continue", "Yes") else (120, 65, 65))
        pygame.display.flip()
        clock.tick(60)

def gui_select(title, options, subtitle=None, allow_cancel=True):
    screen = gui_init()
    title_font = pygame.font.Font(None, 42)
    font = pygame.font.Font(None, 27)
    small = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()
    scroll = 0
    while True:
        mouse = pygame.mouse.get_pos()
        rects = []
        for i, option in enumerate(options):
            rects.append((pygame.Rect(70, 145 + i * 74 - scroll, 760, 58), i))
        cancel_rect = pygame.Rect(670, 570, 160, 48)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if allow_cancel and event.key == K_ESCAPE:
                    return None
                if K_1 <= event.key <= K_9:
                    idx = event.key - K_1
                    if idx < len(options):
                        return idx
                if event.key == K_UP:
                    scroll = max(0, scroll - 40)
                if event.key == K_DOWN:
                    scroll = min(max(0, len(options) * 74 - 380), scroll + 40)
            if event.type == MOUSEWHEEL:
                scroll = min(max(0, len(options) * 74 - 380), max(0, scroll - event.y * 40))
            if event.type == MOUSEBUTTONDOWN:
                if allow_cancel and cancel_rect.collidepoint(event.pos):
                    return None
                for rect, idx in rects:
                    if rect.collidepoint(event.pos):
                        return idx
        screen.fill((14, 17, 24))
        gui_draw_text(screen, title, (40, 34), title_font, (130, 190, 255), 820)
        if subtitle:
            gui_draw_text(screen, subtitle, (44, 90), small, (200, 205, 215), 810)
        for rect, idx in rects:
            if -70 < rect.y < 545:
                gui_button(screen, rect, options[idx], font, mouse)
        if allow_cancel:
            gui_button(screen, cancel_rect, "Cancel", font, mouse, color=(105, 65, 65), hover=(135, 80, 80))
        pygame.display.flip()
        clock.tick(60)

def gui_text_input(title, prompt, default_text=""):
    screen = gui_init()
    title_font = pygame.font.Font(None, 42)
    font = pygame.font.Font(None, 30)
    small = pygame.font.Font(None, 23)
    clock = pygame.time.Clock()
    text = default_text
    while True:
        mouse = pygame.mouse.get_pos()
        ok_rect = pygame.Rect(500, 520, 150, 54)
        cancel_rect = pygame.Rect(670, 520, 150, 54)
        input_rect = pygame.Rect(70, 245, 760, 56)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_RETURN and text.strip():
                    return text.strip()
                if event.key == K_ESCAPE:
                    return None
                if event.key == K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode and len(text) < 80:
                    text += event.unicode
            if event.type == MOUSEBUTTONDOWN:
                if ok_rect.collidepoint(event.pos) and text.strip():
                    return text.strip()
                if cancel_rect.collidepoint(event.pos):
                    return None
        screen.fill((14, 17, 24))
        gui_draw_text(screen, title, (40, 40), title_font, (130, 190, 255), 820)
        gui_draw_text(screen, prompt, (70, 150), small, (220, 220, 220), 760)
        pygame.draw.rect(screen, (28, 34, 45), input_rect, border_radius=10)
        pygame.draw.rect(screen, (110, 140, 180), input_rect, 2, border_radius=10)
        screen.blit(font.render(text, True, (255, 255, 255)), (input_rect.x + 14, input_rect.y + 14))
        gui_button(screen, ok_rect, "OK", font, mouse, disabled=not text.strip(), color=(50, 110, 75))
        gui_button(screen, cancel_rect, "Cancel", font, mouse, color=(105, 65, 65), hover=(135, 80, 80))
        pygame.display.flip()
        clock.tick(60)

def gui_show_status(title, message):
    screen = gui_init()
    screen.fill((14, 17, 24))
    gui_draw_text(screen, title, (40, 44), pygame.font.Font(None, 42), (130, 190, 255), 820)
    gui_draw_text(screen, message, (70, 160), pygame.font.Font(None, 28), (220, 220, 220), 760)
    pygame.display.flip()
    pygame.event.pump()

def upload_results_to_gamepadla(stats, tester, joystick, detected_mode, test_type, gamepad_name, connection):
    test_key = generate_short_id()
    data = {
        'test_key': test_key, 'version': VERSION, 'url': 'https://gamepadla.com',
        'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        'driver': joystick.get_name() if joystick else "N/A", 'connection': connection,
        'mode': detected_mode if detected_mode else "Unknown",
        'name': gamepad_name, 'os_name': platform.system(), 'os_version': platform.uname().version,
        'min_latency': round(stats['min'], 2), 'max_latency': round(stats['max'], 2),
        'avg_latency': round(stats['avg'], 2), 'jitter': stats['jitter'],
        'mathod': 'PNCS' if test_type == TEST_TYPE_STICK else 'PNCB',
        'delay_list': ', '.join(str(round(x, 2)) for x in tester.latency_results),
        'stick_threshold': STICK_THRESHOLD if test_type == TEST_TYPE_STICK else None,
        'contact_delay': stats['contact_delay'], 'pulse_duration': stats['pulse_duration']
    }
    response = requests.post('https://gamepadla.com/scripts/poster.php', data=data)
    if response.status_code == 200:
        webbrowser.open(f'https://gamepadla.com/result/{test_key}/')
        return True, f"Uploaded successfully. Result: https://gamepadla.com/result/{test_key}/"
    return False, f"Server error. Status code: {response.status_code}"

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
    def __init__(self, gamepad, serial_port, test_type, contact_delay=CONTACT_DELAY, iterations=TEST_ITERATIONS):
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
        self.latency_sum = 0.0
        self._skip_first_measurement = True
        self._started = False
        self._last_render_time = 0.0
        self._stick_runtime_fallback_used = False
        self.set_pulse_duration(PULSE_DURATION)  # Use milliseconds for Arduino compatibility
        self.iterations = iterations

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

    def render_test_window(self, average_latency=None):
        if not hasattr(self, "_screen") or self._screen is None:
            return
        self._screen.fill((14, 17, 24))
        header = "Prometheus 82 - Testing"
        surf = pygame.font.Font(None, 42).render(header, True, (130, 190, 255))
        self._screen.blit(surf, (40, 34))
        hint = self._font.render("Keep this window on top during testing", True, (245, 210, 90))
        self._screen.blit(hint, (44, 84))
        
        if self.test_type == TEST_TYPE_HARDWARE:
            surf2 = self._font.render("Status: Calculating hardware timing...", True, (255, 255, 255))
            self._screen.blit(surf2, (70, 160))
        elif self.test_type == TEST_TYPE_STICK and getattr(self, "_started", False) and len(self.latency_results) == 0:
            surf2 = self._font.render("Status: Calibrating stick setup...", True, (255, 255, 255))
            self._screen.blit(surf2, (70, 160))
        else:
            progress_text = f"Progress: {len(self.latency_results)}/{self.iterations}"
            progress = len(self.latency_results) / max(1, self.iterations)
            pygame.draw.rect(self._screen, (30, 36, 48), pygame.Rect(70, 220, 760, 34), border_radius=12)
            pygame.draw.rect(self._screen, (70, 150, 235), pygame.Rect(70, 220, int(760 * progress), 34), border_radius=12)
            pygame.draw.rect(self._screen, (105, 125, 150), pygame.Rect(70, 220, 760, 34), 2, border_radius=12)
            surf2 = self._font.render(progress_text, True, (220, 220, 220))
            self._screen.blit(surf2, (70, 176))
            
        if average_latency is not None:
            surf3 = pygame.font.Font(None, 36).render(f"Average latency: {average_latency:.2f} ms", True, (150, 200, 255))
            self._screen.blit(surf3, (70, 290))
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
            if self.measuring and current_time_us - self.start_time_us > self.max_latency_us:
                self.invalid_measurements += 1
                print(f"Invalid measurement: no input detected within {self.max_latency_us/1000:.2f} ms")
                self.measuring = False
                if self.test_type == TEST_TYPE_STICK and not self._stick_runtime_fallback_used and self.pulse_duration_us < STICK_SETUP_FALLBACK_PULSE_DURATION * 1000:
                    self._stick_runtime_fallback_used = True
                    print_info(f"Switching to stronger solenoid pulse ({STICK_SETUP_FALLBACK_PULSE_DURATION} ms) for remaining measurements.")
                    self.set_pulse_duration(STICK_SETUP_FALLBACK_PULSE_DURATION)
                    self.limit_iterations_for_fallback_pulse()
            pygame.event.pump()
            try:
                now = time.perf_counter()
                if now - self._last_render_time >= 1.0 / 30.0:
                    average_latency = self.latency_sum / len(self.latency_results) if self.latency_results else None
                    self.render_test_window(average_latency)
                    self._last_render_time = now
            except Exception:
                pass
            try:
                time.sleep(0)
            except Exception:
                pass

        self.close_test_window()

def detect_input_mode(name, guid, axes_at_rest):
    name_lower = name.lower()
    guid_lower = guid.lower()
    guid_chunks = {guid_lower[i:i+4] for i in range(0, len(guid_lower), 4) if len(guid_lower[i:i+4]) == 4}

    if any(s in name_lower for s in ("dualsense", "ps5", "edge", "dualshock", "ds4", "ps4", "playstation")):
        return "Sony"

    switch_name_markers = (
        "joy-con",
        "joycon",
        "nintendo switch",
        "switch pro",
        "nintendo",
    )
    if any(s in name_lower for s in switch_name_markers):
        return "Switch"
    if "pro controller" in name_lower and ("nintendo" in name_lower or "057e" in guid_chunks):
        return "Switch"
    if "057e" in guid_chunks:
        return "Switch"
    if any(abs(a + 1) < 0.1 for a in axes_at_rest):
        return "XInput"
    return "DInput"

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
    joystick_name = joystick.get_name()
    joystick_guid = joystick.get_guid()
    
    # Detect mode based on name and axes
    initial_mode = detect_input_mode(joystick_name, joystick_guid, axes_at_rest)
    
    return initial_mode

# Short ID Generation
def generate_short_id(length=12):
    """Generates a random short ID"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def gui_results_screen(stats, tester, joystick, detected_mode, test_type):
    lines = [
        f"Min latency: {stats['min']:.2f} ms",
        f"Max latency: {stats['max']:.2f} ms",
        f"Average latency: {stats['avg']:.2f} ms",
        f"Jitter: {stats['jitter']:.2f} ms",
        f"Iterations: {tester.iterations}",
        f"Total / valid / invalid: {stats['total_samples']} / {stats['valid_samples']} / {stats['invalid_samples']}",
        f"Filtered count: {stats['filtered_samples']}",
        f"Pulse duration: {stats['pulse_duration']:.1f} ms",
        f"Contact delay: {stats['contact_delay']:.3f} ms",
    ]
    if stats['contact_delay'] > 1.2:
        lines.append(f"Warning: tester inherent latency exceeds recommended 1.2 ms.")
    if tester.iterations < 200:
        action = gui_message("Test completed", lines, ("Export CSV", "Exit"), (90, 220, 130))
        if action == "Export CSV":
            export_to_csv(stats, joystick.get_name() if joystick else "N/A", tester.latency_results)
            gui_message("CSV export", "Data saved to CSV file.")
        return
    action = gui_message("Test completed", lines, ("Upload", "Export CSV", "Both", "Exit"), (90, 220, 130))
    if action in ("Upload", "Both"):
        gamepad_name = gui_text_input("Gamepad name", "Enter the gamepad name for Gamepadla.com:", joystick.get_name() if joystick else "")
        if gamepad_name:
            connection_idx = gui_select("Connection type", ("Cable", "Dongle", "Bluetooth"), "Select current controller connection.")
            connection = ("Cable", "Dongle", "Bluetooth")[connection_idx] if connection_idx is not None else "Unset"
            while True:
                gui_show_status("Uploading", "Sending results to Gamepadla.com...")
                try:
                    ok, message = upload_results_to_gamepadla(stats, tester, joystick, detected_mode, test_type, gamepad_name, connection)
                except requests.exceptions.RequestException:
                    ok, message = False, "No internet connection or server is unreachable."
                if ok:
                    gui_message("Upload complete", message)
                    break
                retry = gui_message("Upload failed", message, ("Retry", "Skip"))
                if retry != "Retry":
                    break
    if action in ("Export CSV", "Both"):
        export_to_csv(stats, joystick.get_name() if joystick else "N/A", tester.latency_results)
        gui_message("CSV export", "Data saved to CSV file.")

def main():
    global TEST_ITERATIONS, CONTACT_DELAY
    pygame.init()
    pygame.joystick.init()
    start_async_logger()
    try:
        gui_init("Prometheus 82")
        gui_message("Prometheus 82", [
            f"Version {VERSION}",
            "Professional gamepad latency tester with microsecond precision.",
            "This build uses pygame UI for setup, testing and result actions."
        ], ("Start",))
        joystick = None
        detected_mode = None
        joystick_count = pygame.joystick.get_count()
        if joystick_count:
            joysticks = []
            for i in range(joystick_count):
                joy = pygame.joystick.Joystick(i)
                joy.init()
                joysticks.append(joy)
            if joystick_count == 1:
                joystick = joysticks[0]
            else:
                idx = gui_select("Select gamepad", [joy.get_name() for joy in joysticks], "Choose the controller to test.")
                if idx is not None:
                    joystick = joysticks[idx]
            if joystick:
                gui_show_status("Detecting gamepad", f"Selected: {joystick.get_name()}")
                detected_mode = detect_gamepad_mode(joystick)
        else:
            gui_message("No gamepad found", "Gamepad stick and button tests will be unavailable.", ("Continue",), (245, 190, 80))

        test_options = ["Gamepad - Test analog stick", "Gamepad - Test button", "Keyboard - Test key", "Hardware - Test solenoid and sensor"]
        test_types = [TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD, TEST_TYPE_HARDWARE]
        test_idx = gui_select("Select test type", test_options, "Use number keys, mouse, or arrow keys.")
        if test_idx is None:
            return
        test_type = test_types[test_idx]
        if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON) and not joystick:
            gui_message("No gamepad", f"Can't run {test_type} test without a gamepad.", ("Exit",), (235, 90, 90))
            return
        remaining = get_cooling_remaining_seconds(test_type)
        if remaining > 0:
            choice = gui_message("Cooling warning", f"Device has not cooled yet. Remaining cooling time: {remaining} seconds. Continue anyway?", ("Yes", "No"), (245, 190, 80))
            if choice == "No":
                return
        if test_type in (TEST_TYPE_STICK, TEST_TYPE_BUTTON, TEST_TYPE_KEYBOARD):
            iter_idx = gui_select("Number of iterations", ("400 - Gamepadla validation", "200", "100", "Custom 10-400"), "Select measurement count.")
            if iter_idx is None:
                return
            if iter_idx == 0:
                TEST_ITERATIONS = 400
            elif iter_idx == 1:
                TEST_ITERATIONS = 200
            elif iter_idx == 2:
                TEST_ITERATIONS = 100
            else:
                custom = gui_text_input("Custom iterations", "Enter a number between 10 and 400:", "400")
                try:
                    TEST_ITERATIONS = int(custom)
                    if TEST_ITERATIONS < 10 or TEST_ITERATIONS > 400:
                        raise ValueError
                except Exception:
                    gui_message("Invalid value", "Please enter a number between 10 and 400.", ("Exit",), (235, 90, 90))
                    return

        ports = [p for p in list_ports.comports() if "bluetooth" not in p.description.lower()]
        if not ports:
            gui_message("No COM ports", "No suitable COM ports found. Perhaps Prometheus 82 is not connected.", ("Exit",), (235, 90, 90))
            return
        if len(ports) == 1:
            port = ports[0]
        else:
            idx = gui_select("Select COM port", [f"{p.device} - {p.description}" for p in ports], "Choose Prometheus 82 serial port.")
            if idx is None:
                return
            port = ports[idx]

        gui_show_status("Connecting", f"Opening {port.device}...")
        with serial.Serial(port.device, 115200, timeout=1) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            start_time = time.time()
            ready = False
            fw_version = None
            while time.time() - start_time < 5:
                pygame.event.pump()
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
                gui_message("Connection error", "Prometheus did not send ready signal ('R'). Check connection or firmware.", ("Exit",), (235, 90, 90))
                return
            if not fw_version:
                gui_message("Firmware error", "Arduino firmware version was not reported. Please update Arduino firmware.", ("Exit",), (235, 90, 90))
                return
            def _ver_tuple(s):
                try:
                    return tuple(int(x) for x in s.split("."))
                except Exception:
                    return (0,)
            if _ver_tuple(fw_version) < _ver_tuple(REQUIRED_ARDUINO_VERSION):
                gui_message("Firmware outdated", f"Arduino firmware v{fw_version} is outdated. Please update to at least v{REQUIRED_ARDUINO_VERSION}.", ("Exit",), (235, 90, 90))
                return
            gui_show_status("Calibrating", f"Connected on {port.device}. Testing Arduino latency...")
            avg_latency = test_arduino_latency(ser)
            if avg_latency is not None:
                CONTACT_DELAY = avg_latency
            else:
                gui_message("Calibration warning", f"Arduino latency calibration failed. Default contact delay {CONTACT_DELAY} ms will be used.", ("Continue",), (245, 190, 80))

            tester = LatencyTester(joystick, ser, test_type, CONTACT_DELAY, TEST_ITERATIONS)
            try:
                if test_type == TEST_TYPE_HARDWARE:
                    test_passed, timing_warning = tester.test_hardware()
                    if test_passed and not timing_warning:
                        gui_message("Hardware test passed", "Hardware is fully functional. Ready for stick or button testing.", ("OK",), (90, 220, 130))
                    elif test_passed:
                        gui_message("Hardware warning", "Hardware is functional, but timing warnings were detected. Results may be affected.", ("OK",), (245, 190, 80))
                    else:
                        gui_message("Hardware test failed", "Hardware issues detected. Please check connections and try again.", ("OK",), (235, 90, 90))
                else:
                    if test_type == TEST_TYPE_STICK:
                        gui_message("Stick test", "Stick latency testing requires a reverse sensor. Press Start in the next window when ready.", ("Continue",))
                    elif test_type == TEST_TYPE_BUTTON:
                        gui_message("Button test", "Press Start in the next window, then press the gamepad button you want to measure.", ("Continue",))
                    elif test_type == TEST_TYPE_KEYBOARD:
                        gui_message("Keyboard test", "Press the key to test in the next window, then press Start.", ("Continue",))
                    tester.test_loop()
                    stats = tester.get_statistics()
                    if stats:
                        save_test_completion_time(tester.iterations, test_type)
                        gui_results_screen(stats, tester, joystick, detected_mode, test_type)
                    else:
                        gui_message("No results", "Test finished without valid latency measurements.", ("OK",), (245, 190, 80))
            except KeyboardInterrupt:
                gui_message("Interrupted", "Test interrupted by user.", ("OK",), (245, 190, 80))
    except serial.SerialException as e:
        gui_message("Serial error", f"Opening port failed: {e}", ("Exit",), (235, 90, 90))
    except Exception as e:
        gui_message("Error", f"Unexpected error: {e}", ("Exit",), (235, 90, 90))
    finally:
        stop_async_logger()
        gui_wait_for_quit()
        pygame.quit()

if __name__ == "__main__":
    main()
