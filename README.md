<p align="center">
  <img src="Logos/P82_white.svg" alt="Prometheus 82 Logo" width="100%" />
</p>

An up-to-date user guide: https://www.youtube.com/watch?v=Jr5kND7qLt8

## Partners
These brands use Prometheus 82 to research and develop their gamepads:

<p align="center">
  <a href="https://www.gulikit.com"><img src="Logos/Gulikit_v2.png" alt="GuliKit" height="40" /></a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://www.gamesir.hk"><img src="Logos/gamesir_v2.png" alt="GameSir" height="40" /></a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://retrofighters.com"><img src="Logos/retro_fighters_v2.webp" alt="Retro Fighters" height="40" /></a>
</p>

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

> [!TIP]
> **Proper Positioning:** For the most accurate results, the distance between the solenoid and the stick should be **~1 mm** before the test starts. This prevents "[unrealistic overloads](https://www.reddit.com/r/GPDL/comments/1tayl2v/standardization_of_stick_testing_on_gamepadlacom/)" caused by the solenoid's extreme speed (3x faster than a human finger), which a player could never replicate.
> 
> ![P82 Positioning Guide](Box_Papers/P82%20Positioning%20Guide.png)

1. **T0 (Start):** The solenoid is activated to strike the stick.
2. **Physical Travel:** The solenoid arm pushes the stick from the center (0%) towards the edge (100%).
3. **Sensor Trigger:** The sensor button (new Reverse Solenoid mod) is pressed exactly when the stick reaches its maximum physical deflection.
4. **T1 (Stop):** The timer stops the precise moment the gamepad reports a logical value of **≥99%** deviation.
5. **Calculation:** Since the hardware design (Reverse Solenoid) captures the end-of-travel event directly, providing a real-time hardware trigger, **no manual offset subtraction is required**.


### Accuracy and Permissible Errors
This section details the measurement precision and potential deviations caused by physical properties, system variability, and device assembly.

#### 1. Device-to-Device Consistency
The discrepancy between different, correctly assembled Prometheus 82 units is minimal, typically around **0.2 ms**. 
* Under ideal, highly optimized conditions, this variation can be as low as **0.012 ms**, as demonstrated in our [comparative study of 5 devices](https://www.reddit.com/r/GPDL/comments/1mdwp2c/testing_the_accuracy_of_5_prometheus_82_devices/).

#### 2. System and Controller Tolerances
While the P82 hardware is extremely consistent, total measurement error can increase due to the PC environment and gamepad design:
* **Analog Sticks:** Permissible error **±1 ms**.
    * *Reason:* Depending on the controller's dead zone settings, the logical signal may trigger before the physical sensor button is fully pressed.
* **Buttons:** Permissible error **±1 ms**.
    * *Reason:* Mechanical play (pre-travel), switch design variations, and slight positioning shifts on the stand.

#### 3. Impact of Gamepad Settings & Format
Software settings on the gamepad can significantly alter latency results.
* **Raw Format:** It is highly recommended to test gamepads in **Raw format** (or the mode that provides the lowest and most stable results if Raw is not available).
* **Dead Zones:** Always minimize the external dead zone in the controller's software to ensure the hardware trigger matches the logical signal as closely as possible.

#### 4. Hardware Recommendations to Minimize Error
* **Arduino Choice:** Use a high-quality Arduino board with a self-delay of **≤0.5 ms**. You can verify this using [this script](https://github.com/cakama3a/Prometheus82/tree/main/ArduinoSpeedTestScript).
* **Connection:** Plug the P82 device directly into a USB port on the PC motherboard. Avoid front-panel hubs or external splitters, as they can introduce jitter.

#### Real-world Consistency (Live Statistics)
The reliability of Prometheus 82 is documented through continuous comparative testing between independent devices and users. You can access the live [Latency Consistency Report here](https://gamepadla.com/latency/).

Based on our verified dataset of dozens of comparable groups:
* **Average Tester-to-Tester Delta:** **0.92 ms** (confirming our **±1 ms** permissible error guideline).
* **High Consistency:** **50.0%** of all test pairs match within a tight **0.50 ms** range.
* **Top-tier Accuracy:** Optimized setups and high-quality hardware can achieve average deltas as low as **0.16 ms**.
* **Controller Variance:** Discrepancies above 1.00 ms (occurring in ~33% of pairs) are typically linked to specific controller models or firmware versions that exhibit higher internal jitter or varied processing logic.



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
3. In the [Arduino IDE](https://www.arduino.cc/en/software/), go to **Tools → Board** and select the correct Arduino model.
4. Go to **Tools → Port** and select the correct COM port.
5. Click the **Upload** button to flash the code to the Arduino.

## How to Use Prometheus 82
[![2025-07-13_09-59](https://github.com/user-attachments/assets/1f5d08aa-0afb-40de-a22f-f82d48ff92d4)](https://www.youtube.com/watch?v=NBS_tU-7VqA)  
*(For stick testing, see the [Stick Testing Video Guide (Reverse Solenoid)](https://www.youtube.com/watch?v=MLsXo8Si730))* 
1. Connect the P82 device to the computer (Upper port).
2. Connect the power supply to the device (Lower port).
3. Connect the gamepad to the computer (via cable, receiver, or Bluetooth).
4. Place the gamepad in the test stand and secure it (not too tightly).
5. Adjust the solenoid for testing the gamepad's buttons or sticks as shown in the video (important! For sticks, keep a **~1 mm** distance; see the [Positioning Guide](Box_Papers/P82%20Positioning%20Guide.png)).
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
4. Video: [Cable assembly](https://youtu.be/LMggf17Mmno) (Optional, if not using a ready-made cable)
5. Video: [Stand assembly](https://youtu.be/FciFS4pwg_E)

## Components for Assembly
![P82Tools copy-min (1)](https://github.com/user-attachments/assets/a9b18a0e-e46e-4942-aad0-72950e2bf78a)  
### Individual 3D printed parts for Reverse Solenoid (Test Stick)
<img width="1455" height="661" alt="image" src="https://github.com/user-attachments/assets/c2fb2819-99bd-4c37-be96-e3658059c3a6" />  
You can find it on thingiverse under the name P82_2006_Reverse_Solenoid_mod.3mf - https://www.thingiverse.com/thing:7017737/files

### Main Electronic Components
> [!NOTE]
> If the link doesn't open the product and instead displays a 404 page, [write here](https://github.com/cakama3a/Prometheus82/issues/1)

| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|-------|
| 1 | Solenoid TAU-0530T 12V | $1.58 | The main component for moving sticks and buttons | [AliExpress](https://s.click.aliexpress.com/e/_c4VSpABv), [Amazon](https://amzn.to/4qezZfr) |
| 2 | Arduino Nano 3.0 ATMEGA328P TypeC | $2.79 | Sensor and solenoid control board | [AliExpress](https://s.click.aliexpress.com/e/_c3tRYaQR), [Amazon](https://amzn.to/4rzM2oJ) |
| 3 | Transistor IRLB8721 (1/5pcs) | $1.81 | To activate the solenoid move | [AliExpress](https://s.click.aliexpress.com/e/_c3t1HGuj), [Amazon](https://amzn.to/3O5WZzS) |
| 4 | Kailh Mute Button 6x6x7.3mm | $2.00 | To record the moment you press a button or stick on the gamepad | [AliExpress](https://s.click.aliexpress.com/e/_c2xn8EG7), [Amazon](https://amzn.to/4qVE7lD) |
| 5 | Diode P6KE18A (1/20pcs) | $0.82 | To protect the board control circuitry | [AliExpress](https://s.click.aliexpress.com/e/_c3Ap7uH9), [Amazon](https://amzn.to/45PeBWU) |
| 6 | Capacitor 25V 680uF 10x12 (1/5pcs) | $4.38 | To protect the board control circuitry | [AliExpress](https://www.aliexpress.com/item/1005008585838492.html), [Amazon](https://amzn.to/4qtNxnG) |
| 7 | PCB Circuit Board 4x6 | $0.56 | To install all components of the control board | [AliExpress](https://s.click.aliexpress.com/e/_c3Zl6wub), [Amazon](https://amzn.to/4qecMtN) |
| 8 | Resistor Set (3/300psc) | $1.34 | To protect the board control circuitry | [AliExpress](https://s.click.aliexpress.com/e/_c40uZEyj), [Amazon](https://amzn.to/4rzLYW1) |

### Power and Charging
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|------|
| 9 | Decoy Trigger | $0.76 | To convert 5V from the power supply to the required voltage | [AliExpress](https://www.aliexpress.com/item/1005006822642152.html), [Amazon](https://amzn.to/3O4xpLB) |
| 10 | 20W Charger | $6.61 | It is important to use a powerful power supply, at least 20W | [EU socket](https://s.click.aliexpress.com/e/_c3DVBgP1), [US socket]([https://sovrn.co/1lk0zoc](https://amzn.to/46ro2vJ)) |

### Construction and Connection Materials
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|------|
| 11 | Wire 30AWG (20cm/1m) | $1.04 | Must be elastic to connect the sensor button | [Aliexpress](https://s.click.aliexpress.com/e/_c2yFyGpN) |
| 12 | XH-2.54mm Plug Opposite direction, 300mm, 4P (1/5psc) | $1.13 | Connects the solenoid ports to the main board | [AliExpress](https://s.click.aliexpress.com/e/_c42fU4wf) |
| 13 | Wire Connector 4Pin XH2.54 mm (2/80pcs) | $3.10 | A set of ports and connectors for creating connections | [AliExpress](https://www.aliexpress.com/item/1005003422202370.html) |
| 14 | Solder Cable 24AWG 8cm (5/120pcs) | $2.32 | Wires for soldering the main control board | [AliExpress](https://www.aliexpress.com/item/1005008194967488.html) |
| 15 | PETG/PLA Filament 1.75mm (350/1000g) | $16.99 | Filament for printing test bench components | [AliExpress](https://www.aliexpress.com/w/wholesale-PLA-filament.html) |
| 16 | Double Sided Adhesive Tape 10mm (1/5m) | $2.64 | Adhesive tape for mounting eva material to the stand | [AliExpress](https://www.aliexpress.com/item/1005007294703509.html) |
| 17 | Gecko tape 1mm (3/100cm) | $1.36 | To glue the power trigger to the board | [AliExpress](https://www.aliexpress.com/item/1005005231672146.html) |
| 18 | Cosplay Eva Foam 2mm (35x50cm) (~5% matherial) | $2.84 | Eva material for the stand, necessary for the gamepad to be securely fixed | [AliExpress](https://www.aliexpress.com/item/1005005603490236.html) |
| 19 | Heat Shrink Tube 5mm (5/100cm) | $0.55 | It is required when creating a cable connecting the main board with the solenoid unit | [AliExpress](https://www.aliexpress.com/item/1005008540789806.html) |
| 20 | PET Expandable Cable Sleeve 4mm (30/100cm) | $0.32 | Wrapping the cable to make it look good | [AliExpress](https://www.aliexpress.com/item/32998589638.html) |
| 21 | Brass Heat Insert Nut M3/5.3mm (Height: 3mm, 1/80pcs) | $3.59 | Required for secure fixation of the button at the end of the solenoid. Height must be 3mm. | [AliExpress](https://www.aliexpress.com/item/4001307378488.html) |
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

### Reversible sensor components
For testing sticks according to the new standard
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|-------|
| 29 | Solenoid TAU-0530T 12V | $1.58 | The main component for moving sticks and buttons | [AliExpress](https://s.click.aliexpress.com/e/_c4VSpABv), [Amazon](https://amzn.to/4qezZfr) |
| 30 | Kailh Mute Button 6x6x7.3mm | $2.00 | To record the moment you press a button or stick on the gamepad | [AliExpress](https://s.click.aliexpress.com/e/_c2xn8EG7), [Amazon](https://amzn.to/4qVE7lD) |
| 31 | Wire 30AWG (20cm/1m) | $1.04 | Must be elastic to connect the sensor button | [Aliexpress](https://s.click.aliexpress.com/e/_c2yFyGpN) |
| 32 | Screws M3 50Pcs, 4mm (3/50pcs) | $1.08 | For Solenoid fix | [AliExpress](https://www.aliexpress.com/item/1005007593838226.html) |
| 33 | Brass Heat Insert Nut M3/5.3mm (Height: 3mm, 1/80pcs) | $3.59 | Required for secure fixation of the button at the end of the solenoid. Height must be 3mm. | [AliExpress](https://s.click.aliexpress.com/e/_c39Fuau3) |
| 34 | Wire Connector 4Pin XH2.54 mm (2/80pcs) | $3.10 | A set of ports and connectors for creating connections | [AliExpress](https://www.aliexpress.com/item/1005003422202370.html) |

## Notes and tips
- **Maintenance:** The movement of the solenoid should be easy and smooth. Ensure the leg is free of snags to avoid friction, which can introduce measurement errors and increase wear.
- **Power Supply:** For a 12V solenoid, set the power trigger to **15V** to guarantee stable results. See this [comparison of 6V vs 12V](https://www.reddit.com/r/GPDL/comments/1laafjl/nerd_stuff_comparison_of_prometheus_82_on_6v_and/) and the video on [solenoid-only delays](https://www.reddit.com/r/GPDL/comments/1kv7ys9/i_finally_bought_a_camera_that_can_record_1000/).
- **Connectivity:** The control board has two Type-C ports: the **lower** port is for power, and the **upper** port is for the PC connection.
- **Testing Protocol:** Always run tests at least **2 times**. Recalibrate the gamepad position on the stand between runs to avoid positioning errors.
- **Degradation:** Solenoids can degrade over time, especially if overheated. Use a "control" gamepad (with known stable firmware) to periodically check if the tester's results remain consistent.
- **No Modifications:** Do not modify the hardware or code. The system is optimally calibrated for the components listed in this guide; unauthorized changes will skew results.

## License

This project operates under a dual-license model. Please choose the one that fits your use case.

-   **Personal & Non-Commercial Use:** You are free to build and use Prometheus 82 for personal projects, academic research, and non-monetized content. For the full terms, please see the **[Personal Use License](LICENSE)**.

-   **Commercial Use:** A commercial license is **required** for any organization using the device for business purposes (e.g., product R&D, quality assurance, marketing). To review the terms and request a quote, please see the full **[Commercial License Agreement](COMMERCIAL_LICENSE.md)**.


## 🛡️ Official Licensee Registry

To maintain transparency and build trust within the community, we publish a registry of all official commercial licensees. Companies listed here have purchased a **Prometheus 82 Commercial Kit** or an annual license, granting them the right to use the device for product development, quality assurance, and marketing.

Each license is verified and has a specific validity period.

| Licensee / Identifier                          | Plan         | Status      | Valid Until      |
| ---------------------------------------------- | ------------ | ----------- | ---------------- |
| `8a4b1c9e-7d2f-4b0a-8c1f-9e6a5b3d7c0f`         | `Commercial` | ✅ Active   | `October 15, 2026` |
| **GameSir**                                    | `Commercial` | ✅ Active   | `December 15, 2026` |
| **Retro Fighters**                             | `Commercial` | ✅ Active   | `July 31, 2027`  |
| **GuliKit**                                    | `Commercial` | ✅ Active   | `August 31, 2027` |
| `f3b4d2e1-a0c9-4b8a-9d7e-6f5a4b3c2d1e`         | `Commercial` | ✅ Active   | `May 11, 2031`   |

---
### How to Get Your License

Interested in using Prometheus 82 for your business? Pricing is formed individually to be practical and fit your company's scale and activities. To request a quote and get your **Commercial Kit** (which includes a pre-built, calibrated, and ready-to-use device, your commercial license, and technical support), please contact us at `john@gamepadla.com`. 

In your email, please specify:
* A brief overview of what your company/project does.
* Your main goals and intended use cases for the device.

By purchasing a license, you not only ensure legal compliance but also support the continued development of this open-source project.

*We respect our clients' privacy. Licensees can choose to be listed by their company name or a unique anonymous identifier (UUID).*

## Credits
- **Yaroslav Solovei (Ярослав Соловей)** - PCB design and assistance with the hardware architecture of the physical version of Prometheus 82.

## Contact
john@gamepadla.com

## Donation
- Gamepadla is not a commercial project, and its development is based solely on the author's enthusiasm. If you want to support me, please do so at https://ko-fi.com/gamepadla
- Or you can donate in cryptocurrency at [https://plisio.net/donate/1pkNYhBv](https://plisio.net/donate/1pkNYhBv)
