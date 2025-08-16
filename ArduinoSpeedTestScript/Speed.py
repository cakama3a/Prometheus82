import serial
import time
from serial.tools import list_ports
import statistics

NUM_TESTS = 1000  # Number of tests

def main():
    ports = list_ports.comports()
    if not ports:
        print("No COM ports found!")
        return
        
    if len(ports) > 1:
        print("\nAvailable COM ports:")
        for i, port in enumerate(ports):
            print(f"{i + 1}: {port.device} - {port.description}")
        try:
            choice = int(input("Select COM port (1-" + str(len(ports)) + "): ")) - 1
            port = ports[choice]
        except:
            print("Invalid selection!")
            return
    else:
        port = ports[0]
        
    try:
        ser = serial.Serial(port.device, 115200, timeout=1)
        print(f"Connected to {port.device}")
        time.sleep(2)  # Wait for Arduino initialization
        
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        latencies = []
        
        print(f"\nStarting test... {NUM_TESTS} measurements\n")
        
        for i in range(NUM_TESTS):
            start_time = time.perf_counter()
            ser.write(b'T')  # Send test byte
            
            response = ser.read()  # Wait for response
            if response == b'R':
                end_time = time.perf_counter()
                latency = (end_time - start_time) * 1000  # Convert to ms
                latencies.append(latency)
                print(f"Test {i + 1}/{NUM_TESTS}: {latency:.3f} ms")
        
        if latencies:
            print("\nResults:")
            print(f"Total measurements: {len(latencies)}")
            print(f"Minimum latency: {min(latencies):.3f} ms")
            print(f"Maximum latency: {max(latencies):.3f} ms")
            print(f"Average latency: {statistics.mean(latencies):.3f} ms")
            print(f"Jitter (standard deviation): {statistics.stdev(latencies):.3f} ms")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ser.close()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()