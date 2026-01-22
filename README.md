![image](https://github.com/user-attachments/assets/c381a466-5ec2-460f-a508-51514bf5bfd5)

> [!IMPORTANT]
> **UPDATE 2026:** Starting in 2026, a separate sensor (along with a second solenoid) with a reverse button layout has been added for testing sticks. If you have an older version with a single button at the end of the solenoid, here is the [latest stable release for it](https://github.com/cakama3a/Prometheus82/releases/tag/5.2.3.6).  
[Backup branch on GitHub](https://github.com/cakama3a/Prometheus82/tree/One_Solenoid)  
P.S. Video instructions on how to use the new reversible solenoid for sticks are not ready yet.

## Description
Prometheus 82 is an open-source, Arduino-based electromechanical device designed for precise testing of gamepad input latency. Utilizing a solenoid to physically simulate button presses and analog stick movements, paired with Python software that mimics a game engine, it accurately measures the delay between a physical action and the system's response. Unlike traditional end-to-end latency testing methods using high-speed cameras, which include delays from monitors, GPU frame rendering, and vary depending on specific games, Prometheus 82 directly captures the entire signal chain from physical input to system registration, eliminating these delays. This method ensures consistent testing conditions across different testers, requiring no synchronization of equipment such as monitors, GPUs, or game engines for comparable results. This makes Prometheus 82 an ideal tool for gamepad enthusiasts, developers, and researchers seeking accurate and comparable input latency data. [Reddit article](https://www.reddit.com/r/Controller/comments/1i5uglp/gamepad_punch_tester_a_new_method_for_testing/) 

![photo-collage png (1)](https://github.com/user-attachments/assets/62b7c93d-78df-475c-8eaa-3c639ab4379a)
*Prometheus 82 in full assembly (The photo shows an outdated method of testing a stick)*

## Testing Process
This section outlines the testing process for the Prometheus82 device, designed to measure input latency between the controller and a PC.

### Testing Procedure
1. **Test Initiation**  
   The `Prometheus82.exe` program on the PC sends a signal to the "P82" device to activate the solenoid.
2. **Solenoid Movement**  
   The solenoid moves and, at a specific moment, strikes a button or stick on the gamepad.
3. **Interaction Detection**  
   The "Kalih Mute Button" sensor at the end of the solenoid registers the moment of contact.
4. **Signal Transmission**  
   The "P82" device instantly sends a signal to the `Prometheus82.exe` program, confirming interaction with the gamepad's button or stick.
5. **Latency Timer Start**  
   The `Prometheus82.exe` program starts a timer to measure input latency.
6. **Gamepad Signal**  
   Starting from the moment of contact (step 3), the gamepad sends a signal to the PC, received by `Prometheus82.exe`.
7. **Timer Stop**  
   Upon receiving the gamepad signal, the timer from step 5 stops. The elapsed time represents the input latency.
8. **Test Repetition**  
   The program repeats this process 500 times to calculate minimum, average, and maximum latency, as well as jitter.

### Joystick Latency Algorithm
Prometheus 82 uses a standardized **Center-to-Edge** measurement method for analog sticks to ensure consistent comparisons between different controllers.

1. **T0 (Start):** The solenoid is activated to strike the stick.
2. **Physical Travel:** The solenoid arm pushes the stick from the center (0%) towards the edge (100%).
3. **Pressing the sensor:** The sensor button at the end of the stick's movement is pressed when it is deflected to the end.
4. **T1 (Stop):** The timer stops the precise moment the gamepad reports a logical value of **≥99%** deviation.
5. **Calculation:** `Total Time - 3.5ms = Input Latency`.


### Permissible Errors and Accuracy
This section describes potential measurement deviations caused by the physical properties of controllers and the testing methodology.

#### Device Consistency
The variation between different Prometheus 82 units is minimal (approximately **0.012 ms**), which ensures consistent results across different testers. This was verified in a comprehensive [test with 5 devices](https://www.reddit.com/r/GPDL/comments/1mdwp2c/testing_the_accuracy_of_5_prometheus_82_devices/) combined in various configurations.

#### Measurement Tolerances

* **Analog Sticks:** Permissible error **±1 ms**.
    * **Reason:** Depending on the external dead zone of the gamepad, the signal may be sent before the sensor button is pressed.
    * > **Note:** In the gamepad settings, it is recommended to minimize the external dead zone as much as possible (if possible).

* **Buttons:** Permissible error **±1 ms**.
    * **Reason:** Mechanical button play (pre-travel) and design differences in switches from various manufacturers.

#### Recommendations
To minimize errors, it is recommended to:
1.  Use a fast Arduino board (with self-delay ≤ 0.5 ms).
2.  Connect the P82 device directly to your PC motherboard's USB port (avoid front panel hubs).

### Summary
The testing process ensures accurate measurement of the Prometheus82 device's input latency. Running the test 200/400 times provides comprehensive data to evaluate the device's stability and performance under real-world conditions.

## How to Get Prometheus 82
You have two options to obtain a Prometheus 82 device:  
1. Build It Yourself: Follow the [instructions](#test-bench) in this repository to 3D-print the test bench, source components, and assemble the device. All necessary files and guides are provided below.
2. Order a Pre-Built Device: Purchase a ready-to-use Prometheus 82 from our shop at [Ko-fi Shop](https://ko-fi.com/gamepadla/shop?g=3).
* The files do not include the STL file for case for the P82 board (This feature is only for buyers).

## How to update the firmware of a P82 device
[Detailed video instruction](https://youtu.be/hoBuqWb5SLw)

⚠️ Before using the device, you must flash the Arduino with the provided firmware:
1. Open the [Arduino.ino](https://github.com/cakama3a/Prometheus82/blob/main/Arduino.ino) file in the **Arduino IDE**.
2. Connect your Arduino board to the computer via USB.
3. In the Arduino IDE, go to **Tools → Board** and select the correct Arduino model.
4. Go to **Tools → Port** and select the correct COM port.
5. Click the **Upload** button to flash the code to the Arduino.

## How to Use Prometheus 82
[![2025-07-13_09-59](https://github.com/user-attachments/assets/1f5d08aa-0afb-40de-a22f-f82d48ff92d4)](https://www.youtube.com/watch?v=NBS_tU-7VqA)  
  
1. Connect the P82 device to the computer (Upper port).
2. Connect the power supply to the device (Lower port).
3. Connect the gamepad to the computer (via cable, receiver, or Bluetooth).
4. Place the gamepad in the test stand and secure it (not too tightly).
5. Adjust the solenoid for testing the gamepad's buttons or sticks as shown in the video (important!).
7. Launch the testing program: https://github.com/cakama3a/Prometheus82/releases/
8. Select the testing option for the gamepad's sticks or buttons in the program menu.
9. Start the test and wait for it to complete.
10. Submit the test to Gamepadla.com for detailed analysis or exit the program (optional).

![image](https://github.com/user-attachments/assets/0900068d-f3f0-4ae1-958f-e919bea8ca53)
Test results on a temporary personalized Gamepadla.com page

## Test bench
The test bench itself must be printed on a 3D printer from PLA or PETG plastic.  
You can download the STL files of the project on [thingiverse](https://www.thingiverse.com/cakama3a/designs).   
All parts can be printed in 3 passes in about 10 hours and 250 grams of plastic.  
![photo-collage png](https://github.com/user-attachments/assets/7bed604b-53cf-4254-9142-979886f6fa6e)

## Assembly Diagram
The diagrams show the schematic of the current Prometheus 82 tester assembly of revision 1.0.4 (not to be confused with the program revision). The blueprint also adds a solenoid and a sensor button, and the diagram exactly reflects the device on the photo. The solenoid and the sensor button are connected via a separate power cable, which can be made according to the video instructions below.  
![photo-collage png (2)](https://github.com/user-attachments/assets/727d81b4-aca1-4deb-8ebc-2ac8486cb9eb)
- There is also an alternative build scheme (newer and more optimized) [for Ko-Fi supporters](https://ko-fi.com/i/IE1E31N5NMT)

## Assembly Instructions (For DIY)
1. Video: [Main board assembly](https://youtu.be/GRk6pmUU0J8)
2. Video: [Solenoid assembly](https://ko-fi.com/post/Prometheus-82-Assembling-solenoid-block-instructi-P5P41GFCHP) (Only available to ko-fi supporters for now)
3. Video: [Solenoid assembly v2](https://youtu.be/f90D_e_PUD4) (For DIY Set Byers)
4. Video: [Cable assembly](https://youtu.be/LMggf17Mmno) (A bit outdated, because now you can buy the cable ready-made)
5. Video: [Stand assembly](https://youtu.be/FciFS4pwg_E)

## Components for Assembly
![P82Tools copy-min (1)](https://github.com/user-attachments/assets/a9b18a0e-e46e-4942-aad0-72950e2bf78a)


> [!NOTE]
> If the link doesn't open the product and instead displays a 404 page, [write here](https://github.com/cakama3a/Prometheus82/issues/1)
### Main Electronic Components
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|-------|
| 1 | Solenoid TAU-0530T 12V | $1.58 | The main component for moving sticks and buttons | [AliExpress](https://www.aliexpress.com/item/32731717962.html), [Amazon](https://sovrn.co/tf717uc) |
| 2 | Arduino Nano 3.0 ATMEGA328P TypeC | $2.79 | Sensor and solenoid control board | [AliExpress](https://www.aliexpress.com/item/1005007066680464.html), [Amazon](https://sovrn.co/13xpdmr) |
| 3 | Transistor IRLB8721 (1/5pcs) | $1.81 | To activate the solenoid move | [AliExpress](https://www.aliexpress.com/item/1005003607855008.html), [Amazon](https://sovrn.co/q3lxwld) |
| 4 | Kailh Mute Button 6x6x7.3mm | $2.00 | To record the moment you press a button or stick on the gamepad | [AliExpress](https://www.aliexpress.com/item/1005007474707757.html), [Amazon](https://sovrn.co/aa2nj3s) |
| 5 | Diode P6KE18A (1/20pcs) | $0.82 | To protect the board control circuitry | [AliExpress](https://www.aliexpress.com/item/4000267321292.html), [Amazon](https://sovrn.co/1ekve0l) |
| 6 | Capacitor 25V 680uF 10x12 (1/5pcs) | $4.38 | To protect the board control circuitry | [AliExpress](https://www.aliexpress.com/item/1005008585838492.html), [Amazon](https://sovrn.co/1jo501t) |
| 7 | PCB Circuit Board 4x6 | $0.56 | To install all components of the control board | [AliExpress](https://www.aliexpress.com/item/1005007084130033.html), [Amazon](https://sovrn.co/alrorsw) |
| 8 | Resistor Set (3/300psc) | $1.34 | To protect the board control circuitry | [AliExpress](https://www.aliexpress.com/item/1005002992010027.html), [Amazon](https://sovrn.co/hutmsuj) |

### Power and Charging
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|------|
| 9 | Decoy Trigger | $0.76 | To convert 5V from the power supply to the required voltage | [AliExpress](https://www.aliexpress.com/item/1005006822642152.html), [Amazon](https://sovrn.co/27k7gdk) |
| 10 | 20W Charger | $6.61 | It is important to use a powerful power supply, at least 20W | [EU socket](https://www.aliexpress.com/item/1005004992896883.html), [US socket](https://sovrn.co/1lk0zoc) |

### Construction and Connection Materials
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|------|
| 11 | Wire 30AWG (20cm/1m) | $1.04 | Must be elastic to connect the sensor button | [Aliexpress](https://www.aliexpress.com/item/1005001590476043.html) |
| 12 | XH-2.54mm Plug Opposite direction, 300mm, 4P (1/5psc) | $1.13 | Connects the solenoid ports to the main board | [AliExpress](https://www.aliexpress.com/item/1005008864031395.html) |
| 13 | Wire Connector 4Pin XH2.54 mm (2/80pcs) | $3.10 | A set of ports and connectors for creating connections | [AliExpress](https://www.aliexpress.com/item/1005003422202370.html) |
| 14 | Solder Cable 24AWG 8cm (5/120pcs) | $2.32 | Wires for soldering the main control board | [AliExpress](https://www.aliexpress.com/item/1005008194967488.html) |
| 15 | PETG/PLA Filament 1.75mm (350/1000g) | $16.99 | Filament for printing test bench components | [AliExpress](https://www.aliexpress.com/w/wholesale-PLA-filament.html) |
| 16 | Double Sided Adhesive Tape 10mm (1/5m) | $2.64 | Adhesive tape for mounting eva material to the stand | [AliExpress](https://www.aliexpress.com/item/1005007294703509.html) |
| 17 | Gecko tape 1mm (3/100cm) | $1.36 | To glue the power trigger to the board | [AliExpress](https://www.aliexpress.com/item/1005005231672146.html) |
| 18 | Cosplay Eva Foam 2mm (35x50cm) (~5% matherial) | $2.84 | Eva material for the stand, necessary for the gamepad to be securely fixed | [AliExpress](https://www.aliexpress.com/item/1005005603490236.html) |
| 19 | Heat Shrink Tube 5mm (5/100cm) | $0.55 | It is required when creating a cable connecting the main board with the solenoid unit | [AliExpress](https://www.aliexpress.com/item/1005008540789806.html) |
| 20 | PET Expandable Cable Sleeve 4mm (30/100cm) | $0.32 | Wrapping the cable to make it look good | [AliExpress](https://www.aliexpress.com/item/32998589638.html) |
| 21 | Brass Heat Insert Nut M3/5.3mm (1/80pcs) | $3.59 | Required for secure fixation of the button at the end of the solenoid | [AliExpress](https://www.aliexpress.com/item/4001307378488.html) |
| 22 | Screws M3 50Pcs, 8mm (7/50pcs) | $2.08 | To connect components printed on a 3D printer | [AliExpress](https://www.aliexpress.com/item/1005007593838226.html) |
| 22a | Screws M3 50Pcs, 4mm (2/50pcs) | $1.08 | For Solenoid fix | [AliExpress](https://www.aliexpress.com/item/1005007593838226.html) |

## Required Tools

For successful assembly, you will need the following tools:

| № | Tool Name | Why | Link |
|---|-----------|------|-------|
| 23| Side Cutters 4.5 inch | For cutting wires during main board assembly | [AliExpress](https://www.aliexpress.com/item/1005005055962041.html) |
| 24 | Soldering Iron | For soldering the main board and solenoid block | [AliExpress](https://www.aliexpress.com/w/wholesale-Soldering-Iron.html) |
| 25 | --- | --- | --- |
| 26 | Flux | To make the solder behave well =) | [AliExpress](https://www.aliexpress.com/item/32894800641.html) |
| 27 | Solder | To install components and wires on the board | [AliExpress](https://www.aliexpress.com/w/wholesale-Solder.html) |
| 28 | 3D Printer | To create a test bench, board case, and solenoid unit | [BambuLab A1 Mini](https://bambulab.com/en/a1-mini) |

## Notes and tips
- Video comparison of [6V solenoid with 12V](https://www.reddit.com/r/GPDL/comments/1laafjl/nerd_stuff_comparison_of_prometheus_82_on_6v_and/) filmed at 1000 FPS and tips on power supply (outdated stick testing method)
- For a 12V solenoid, you should set the power trigger to 15V, this guarantees stable results when testing.
- Video about the [solenoid's own delays](https://www.reddit.com/r/GPDL/comments/1kv7ys9/i_finally_bought_a_camera_that_can_record_1000/) and how it is reflected in the measurements at 1000 FPS (outdated stick testing method)
- Both ports of the control board use Type-C interfaces, so do not confuse them, remember that the lower port is used for power, and the upper port is used to connect to a PC.
- The movement of the solenoid should be easy, it should not cling to the inner hole. Make sure that its leg is smooth and free of snags, as this can cause friction, which increases heat, wear and tear on the component and introduces an error in the measurement.
- Distance matters. When positioning the gamepad during tests, you need to install the stick and button as far away from the sensor as possible so that the solenoid has time to accelerate sufficiently. If you install the solenoid too close, it will give incorrect measurement results.
- Over time, the solenoid can degrade, especially if it is frequently overheated. Therefore, it is worth getting a separate control gamepad (with stable firmware) to periodically check if the delay has changed.
- When conducting tests, you should do it at least 2 times. It is better to recalibrate the position of the gamepad on the stand before the second test to avoid positioning errors.
- Some Chinese Arduino devices may not work well, if something does not work, it may be worth replacing the Arduino board.
- Some Arduino boards are slower than others. For the Prometheus 82 tester, only boards with self-delay ≤0.6 ms should be used. You can check it with [this script](https://github.com/cakama3a/Prometheus82/tree/main/ArduinoSpeedTestScript)
- You should not modify the device in your own way, as this can skew the test results and cause an error in the latency. Currently, the code is optimally adapted for the components listed above.
- P82 device should be plugged directly into your PC's motherboard, as the ports on the front of the case can sometimes cause problems.

## License

This project operates under a dual-license model. Please choose the one that fits your use case.

-   **Personal & Non-Commercial Use:** You are free to build and use Prometheus 82 for personal projects, academic research, and non-monetized content. For the full terms, please see the **[Personal Use License](LICENSE)**.

-   **Commercial Use:** A commercial license is **required** for any organization using the device for business purposes (e.g., product R&D, quality assurance, marketing). To review the terms and pricing, please see the full **[Commercial License Agreement](COMMERCIAL_LICENSE.md)**.


## 🛡️ Official Licensee Registry

To maintain transparency and build trust within the community, we publish a registry of all official commercial licensees. Companies listed here have purchased a **Prometheus 82 Commercial Kit** or an annual license, granting them the right to use the device for product development, quality assurance, and marketing.

Each license is verified and has a specific validity period.

| Licensee / Identifier                          | Plan         | Status      | Valid Until      |
| ---------------------------------------------- | ------------ | ----------- | ---------------- |
| **GuliKit** | `Enterprise` | ✅ Active   | `July 31, 2026`  |
| `8a4b1c9e-7d2f-4b0a-8c1f-9e6a5b3d7c0f`         | `Professional` | ✅ Active   | `October 15, 2026` |
| **GameSir**         | `Professional` | ✅ Active   | `December 15, 2026` |

---
### How to Get Your License

Interested in using Prometheus 82 for your business? The best way to get started is with our **Commercial Kit**, which includes:
* A pre-built, calibrated, and ready-to-use Prometheus 82 device.
* Your first year's **Professional License**.
* Priority technical support.

By purchasing a license, you not only ensure legal compliance but also support the continued development of this open-source project.

**To purchase your kit or learn more, contact us at `john@gamepadla.com`.**

*We respect our clients' privacy. Licensees can choose to be listed by their company name or a unique anonymous identifier (UUID).*

## Contact
john@gamepadla.com

## Donation
- Gamepadla is not a commercial project, and its development is based solely on the author's enthusiasm. If you want to support me, please do so at https://ko-fi.com/gamepadla
- Or you can donate in cryptocurrency at [https://plisio.net/donate/1pkNYhBv](https://plisio.net/donate/1pkNYhBv)
