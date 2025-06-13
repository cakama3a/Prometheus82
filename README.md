![image](https://github.com/user-attachments/assets/c381a466-5ec2-460f-a508-51514bf5bfd5)
> [!WARNING]
> The page is still under development and the data is not yet complete.

## Description
Prometheus 82 is an open-source, Arduino-based electromechanical device designed for testing gamepad input latency. It utilizes a solenoid to simulate button presses and stick movements, paired with Python software that mimics a game engine to precisely measure the delay between physical actions and system response. This testing method is an advanced alternative to high-speed camera testing, eliminating monitor input lag and the need for frame counting. Ideal for gamepad enthusiasts, developers, and researchers. [Reddit article](https://www.reddit.com/r/Controller/comments/1i5uglp/gamepad_punch_tester_a_new_method_for_testing/) 

![photo-collage png (1)](https://github.com/user-attachments/assets/62b7c93d-78df-475c-8eaa-3c639ab4379a)
*Prometheus 82 in full assembly*

## How to Get Prometheus 82
You have two options to obtain a Prometheus 82 device:  
1. Build It Yourself: Follow the instructions in this repository to 3D-print the test bench, source components, and assemble the device. All necessary files and guides are provided below.
2. Order a Pre-Built Device: Purchase a ready-to-use Prometheus 82 from our shop at [Ko-fi Shop](https://ko-fi.com/gamepadla/shop?g=3) for $196 (Quantity is limited).

## Test bench
The test bench itself must be printed on a 3D printer from PLA or PETG plastic. You can download the STL files of the project on [thingiverse](https://www.thingiverse.com/cakama3a/designs)
![PadTester v106 (1)](https://github.com/user-attachments/assets/a75fc10b-8110-416a-8f8a-26b7f26e1005)

## Assembly Diagram

### Complete Device Diagram
![image](https://github.com/user-attachments/assets/5768d50b-eec4-45a8-af1f-702fe822724b)


### Visually clear scheme
![Prometheus82](https://github.com/user-attachments/assets/1977329f-0190-45db-8a4a-3186e70f244c)


### The final look of the board (May be outdated, see the scheme above)
![image](https://github.com/user-attachments/assets/0d869e9c-6ba7-44e7-b669-271fb21384e4)


> [!NOTE]
> - The Decoy Trigger voltage should be set to 15 volts instead of 12 volts, as this reduces the number of test errors, although it does lead to higher heat.
> - The lower port of the tester is for the power supply, the upper port is for connecting to a PC.

## Components for Assembly

### Main Electronic Components
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|-------|
| 1 | Solenoid TAU-0530T 12V | $1.58 | The main component for moving sticks and buttons | [AliExpress](https://s.click.aliexpress.com/e/_olUL07J) |
| 2 | Arduino Nano 3.0 ATMEGA328P TypeC | $2.79 | Sensor and solenoid control board | [AliExpress](https://s.click.aliexpress.com/e/_oDnDkCb) |
| 3 | Transistor IRLB8721PBF | $2.08 | To activate the solenoid move | [AliExpress](https://s.click.aliexpress.com/e/_oEGL679) |
| 4 | Kailh Mute Button 6*6*7.3mm | $2.24 | To record the moment you press a button or stick on the gamepad | [AliExpress](https://s.click.aliexpress.com/e/_om11hvf) |
| 5 | Diode P6KE18A | $1.80 | To protect the board control circuitry | [AliExpress](https://s.click.aliexpress.com/e/_oFMCugb) |
| 6 | Capacitor 25V 680uF 10x12 | $4.12 | To protect the board control circuitry | [AliExpress](https://www.aliexpress.com/item/1005003020234581.html) |
| 7 | PCB Circuit Board 4x6 | $0.56 | To install all components of the control board | [AliExpress](https://s.click.aliexpress.com/e/_opZCvzR) |
| 8 | Resistor Set | $1.28 | To protect the board control circuitry | [AliExpress](https://s.click.aliexpress.com/e/_oBNMBNX) |

### Power and Charging
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|------|
| 1 | Decoy Trigger | $1.51 | To convert 5V from the power supply to the required voltage | [AliExpress](https://s.click.aliexpress.com/e/_oDIgTYG) |
| 2 | 20W Charger | $6.61 | It is important to use a powerful power supply, at least 20W | [AliExpress](https://s.click.aliexpress.com/e/_okS7gqX) |

### Construction and Connection Materials
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|------|
| 1 | Wire 30AWG | $1.04 | Must be elastic to connect the sensor button | [Aliexpress](https://s.click.aliexpress.com/e/_oBqNaqw) |
| 2 | UL2468 2 Pins Electrical Wire 24AWG | $1.33 | Connects the solenoid ports to the main board | [AliExpress](https://s.click.aliexpress.com/e/_oDjYJVX) |
| 3 | Wire Connector Set XH2.54 mm | $3.10 | A set of ports and connectors for creating connections | [AliExpress](https://s.click.aliexpress.com/e/_oElq2W9) |
| 4 | Solder Cable 24AWG 8cm | $2.32 | Wires for soldering the main control board | [AliExpress](https://s.click.aliexpress.com/e/_olvnxRB) |
| 5 | PETG/PLA Filament 1.75mm | $16.99 | Filament for printing test bench components | [AliExpress](https://s.click.aliexpress.com/e/_oFkcL3T) |
| 6 | Double Sided Adhesive Tape 10mm | $2.64 | Adhesive tape for mounting eva material to the stand | [AliExpress](https://www.aliexpress.com/item/1005007294703509.html) |
| 7 | Cosplay Eva Foam 2mm | $2.06 | Eva material for the stand, necessary for the gamepad to be securely fixed | [AliExpress](https://s.click.aliexpress.com/e/_opseJQv) |
| 8 | Heat Shrink Tube 5mm | $0.42 | It is required when creating a cable connecting the main board with the solenoid unit | [AliExpress](https://s.click.aliexpress.com/e/_oEHmeLX) |
| 9 | PET Expandable Cable Sleeve 4mm | $0.32 | Wrapping the cable to make it look good | [AliExpress](https://s.click.aliexpress.com/e/_opZIqHF) |
| 10 | Brass Heat Insert Nut M3 | $3.59 | Required for secure fixation of the button at the end of the solenoid | [AliExpress](https://s.click.aliexpress.com/e/_oCiDrMZ) |
| 11 | Screws M3 50Pcs, 10mm | $2.08 | To connect components printed on a 3D printer | [AliExpress](https://s.click.aliexpress.com/e/_olQ572m) |

**Total component cost: ~$59.16**

## Required Tools

For successful assembly, you will need the following tools:

| № | Tool Name | Why | Link |
|---|-----------|------|-------|
| 1 | Side Cutters 4.5 inch | For cutting wires during main board assembly | [AliExpress](https://s.click.aliexpress.com/e/_oF9KQnh) |
| 2 | Soldering Iron | For soldering the main board and solenoid block | [AliExpress](https://s.click.aliexpress.com/e/_oF9euD9) |
| 3 | Crimping Tool 2.54 | To create a cable between the main board and the solenoid | [AliExpress](https://s.click.aliexpress.com/e/_oD0rvjH) |
| 4 | Flux | To make the solder behave well =) | [AliExpress](https://s.click.aliexpress.com/e/_opcxu03) |
| 5 | Solder | To install components and wires on the board | [AliExpress](https://s.click.aliexpress.com/e/_oF4jIPD) |
| 6 | 3D Printer | To create a test bench, board case, and solenoid unit | [BambuLab A1 Mini](https://bambulab.com/en/a1-mini) |

## Assembly Instructions (For DIY)
1. Video: [Main board assembly](https://youtu.be/GRk6pmUU0J8)
2. Video: Solenoid assembly (Comoing Soon)
3. Video: Cable assembly (Comoing Soon)
4. Video: Stand assembly (Comoing Soon)

## How to Perform Testing
1. Connect the device to the computer (Upper port).
2. Connect the power supply to the device (Lower port).
3. Connect the gamepad to the computer (via cable, receiver, or Bluetooth).
4. Place the gamepad in the test stand and secure it (not too tightly).
5. Adjust the solenoid for testing the gamepad's buttons or sticks as shown.

   > [!NOTE]
   > The video will be added soon.

6. Launch the testing program: https://github.com/cakama3a/Prometheus82/releases/
7. Select the testing option for the gamepad's sticks or buttons in the program menu.
8. Start the test and wait for it to complete.
9. Submit the test to Gamepadla.com for detailed analysis or exit the program.

![image](https://github.com/user-attachments/assets/0900068d-f3f0-4ae1-958f-e919bea8ca53)
Test results on a temporary personalized Gamepadla.com page

## Notes and tips
- Video comparison of [6V solenoid with 12V](https://www.reddit.com/r/GPDL/comments/1laafjl/nerd_stuff_comparison_of_prometheus_82_on_6v_and/) filmed at 1000 FPS and tips on power supply
- For a 6V solenoid, you should set the power supply to 9V, for a 12V solenoid, you should set the power supply to 15V, this guarantees stable results when testing
- Video about the [solenoid's own delays](https://www.reddit.com/r/GPDL/comments/1kv7ys9/i_finally_bought_a_camera_that_can_record_1000/) and how it is reflected in the measurements at 1000 FPS
- Prometheus 82 has its own delays that are not compensated for after the test is completed. For buttons, it's an additional ~0.2-0.7ms, for joysticks it's ~3-4ms.

## License
This project is licensed under the Prometheus 82 License. It may be used for non-commercial purposes only. Any derivative works must include a prominent notice crediting "Prometheus 82 by John Punch (https://gamepadla.com)" in the visible part of the program. See the [LICENSE](LICENSE) file for details.

## Contact
john@gamepadla.com

## Donation
https://ko-fi.com/gamepadla
