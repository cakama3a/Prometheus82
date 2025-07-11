![image](https://github.com/user-attachments/assets/c381a466-5ec2-460f-a508-51514bf5bfd5)
> [!WARNING]
> The page is still under development and the data is not yet complete.

## Description
Prometheus 82 is an open-source, Arduino-based electromechanical device designed for testing gamepad input latency. It utilizes a solenoid to simulate button presses and stick movements, paired with Python software that mimics a game engine to precisely measure the delay between physical actions and system response. This testing method is an advanced alternative to high-speed camera testing, eliminating monitor input lag and the need for frame counting. Ideal for gamepad enthusiasts, developers, and researchers. [Reddit article](https://www.reddit.com/r/Controller/comments/1i5uglp/gamepad_punch_tester_a_new_method_for_testing/) 

![photo-collage png (1)](https://github.com/user-attachments/assets/62b7c93d-78df-475c-8eaa-3c639ab4379a)
*Prometheus 82 in full assembly*

## How to Get Prometheus 82
You have two options to obtain a Prometheus 82 device:  
1. Build It Yourself: Follow the [instructions](#test-bench) in this repository to 3D-print the test bench, source components, and assemble the device. All necessary files and guides are provided below.
2. Order a Pre-Built Device: Purchase a ready-to-use Prometheus 82 from our shop at [Ko-fi Shop](https://ko-fi.com/gamepadla/shop?g=3) for $196 (Quantity is limited).

## How to Use Prometheus 82
1. Connect the P82 device to the computer (Upper port).
2. Connect the power supply to the device (Lower port).
3. Connect the gamepad to the computer (via cable, receiver, or Bluetooth).
4. Place the gamepad in the test stand and secure it (not too tightly).
5. Adjust the solenoid for testing the gamepad's buttons or sticks [as shown](https://www.youtube.com/watch?v=NBS_tU-7VqA).
6. Launch the testing program: https://github.com/cakama3a/Prometheus82/releases/
7. Select the testing option for the gamepad's sticks or buttons in the program menu.
8. Start the test and wait for it to complete.
9. Submit the test to Gamepadla.com for detailed analysis or exit the program.

![image](https://github.com/user-attachments/assets/0900068d-f3f0-4ae1-958f-e919bea8ca53)
Test results on a temporary personalized Gamepadla.com page

## Test bench
The test bench itself must be printed on a 3D printer from PLA or PETG plastic. You can download the STL files of the project on [thingiverse](https://www.thingiverse.com/cakama3a/designs).   
All parts can be printed in 3 passes in about 10 hours and 250 grams of plastic.  
![photo-collage png](https://github.com/user-attachments/assets/7bed604b-53cf-4254-9142-979886f6fa6e)

## Assembly Diagram
The diagrams show the schematic of the current Prometheus 82 tester assembly of revision 1.0.4 (not to be confused with the program revision). The blueprint also adds a solenoid and a sensor button, and the diagram exactly reflects the device on the photo. The solenoid and the sensor button are connected via a separate power cable, which can be made according to the video instructions below.  
![photo-collage png (2)](https://github.com/user-attachments/assets/727d81b4-aca1-4deb-8ebc-2ac8486cb9eb)
- There is also an alternative build scheme (newer and more optimized) [for Patreons](https://www.patreon.com/posts/prometheus-82-v5-133249717?utm_medium=clipboard_copy&utm_source=copyLink&utm_campaign=postshare_creator&utm_content=join_link) or [Ko-Fi supporters](https://ko-fi.com/i/II2I81HINLS)

## Assembly Instructions (For DIY)
1. Video: [Main board assembly](https://youtu.be/GRk6pmUU0J8)
2. Video: [Solenoid assembly](https://ko-fi.com/post/Prometheus-82-Assembling-solenoid-block-instructi-P5P41GFCHP) (Only available to ko-fi supporters for now)
3. Video: [Cable assembly](https://youtu.be/LMggf17Mmno)
4. Video: [Stand assembly](https://youtu.be/FciFS4pwg_E)

## Components for Assembly
![DSC03593 copy-min](https://github.com/user-attachments/assets/c7fd17e1-17a8-420c-a5c7-bb23654ae301)


> [!NOTE]
> If the link doesn't open the product and instead displays a 404 page, [write here](https://github.com/cakama3a/Prometheus82/issues/1)
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
| 9 | Decoy Trigger | $1.51 | To convert 5V from the power supply to the required voltage | [AliExpress](https://s.click.aliexpress.com/e/_oDIgTYG) |
| 10 | 20W Charger | $6.61 | It is important to use a powerful power supply, at least 20W | [AliExpress](https://s.click.aliexpress.com/e/_okS7gqX) |

### Construction and Connection Materials
| № | Component Name | Price | Why | Link |
|---|----------------|-------|------|------|
| 11 | Wire 30AWG | $1.04 | Must be elastic to connect the sensor button | [Aliexpress](https://s.click.aliexpress.com/e/_oBqNaqw) |
| 12 | UL2468 2 Pins Electrical Wire 24AWG | $1.33 | Connects the solenoid ports to the main board | [AliExpress](https://s.click.aliexpress.com/e/_oDjYJVX) |
| 13 | Wire Connector Set XH2.54 mm | $3.10 | A set of ports and connectors for creating connections | [AliExpress](https://s.click.aliexpress.com/e/_oElq2W9) |
| 14 | Solder Cable 24AWG 8cm | $2.32 | Wires for soldering the main control board | [AliExpress](https://s.click.aliexpress.com/e/_olvnxRB) |
| 15 | PETG/PLA Filament 1.75mm | $16.99 | Filament for printing test bench components | [AliExpress](https://s.click.aliexpress.com/e/_oFkcL3T) |
| 16 | Double Sided Adhesive Tape 10mm | $2.64 | Adhesive tape for mounting eva material to the stand | [AliExpress](https://www.aliexpress.com/item/1005007294703509.html) |
| 17 | Gecko tape 1mm | $1.36 | To glue the power trigger to the board | [AliExpress](https://s.click.aliexpress.com/e/_oFLtiPk) |
| 18 | Cosplay Eva Foam 2mm | $2.06 | Eva material for the stand, necessary for the gamepad to be securely fixed | [AliExpress](https://s.click.aliexpress.com/e/_opseJQv) |
| 19 | Heat Shrink Tube 5mm | $0.42 | It is required when creating a cable connecting the main board with the solenoid unit | [AliExpress](https://s.click.aliexpress.com/e/_oEHmeLX) |
| 20 | PET Expandable Cable Sleeve 4mm | $0.32 | Wrapping the cable to make it look good | [AliExpress](https://s.click.aliexpress.com/e/_opZIqHF) |
| 21 | Brass Heat Insert Nut M3 | $3.59 | Required for secure fixation of the button at the end of the solenoid | [AliExpress](https://s.click.aliexpress.com/e/_oCiDrMZ) |
| 22 | Screws M3 50Pcs, 10mm | $2.08 | To connect components printed on a 3D printer | [AliExpress](https://s.click.aliexpress.com/e/_olQ572m) |

## Required Tools

For successful assembly, you will need the following tools:

| № | Tool Name | Why | Link |
|---|-----------|------|-------|
| 23| Side Cutters 4.5 inch | For cutting wires during main board assembly | [AliExpress](https://s.click.aliexpress.com/e/_oF9KQnh) |
| 24 | Soldering Iron | For soldering the main board and solenoid block | [AliExpress](https://s.click.aliexpress.com/e/_oF9euD9) |
| 25 | Crimping Tool 2.54 | To create a cable between the main board and the solenoid | [AliExpress](https://s.click.aliexpress.com/e/_oD0rvjH) |
| 26 | Flux | To make the solder behave well =) | [AliExpress](https://s.click.aliexpress.com/e/_opcxu03) |
| 27 | Solder | To install components and wires on the board | [AliExpress](https://s.click.aliexpress.com/e/_oF4jIPD) |
| 28 | 3D Printer | To create a test bench, board case, and solenoid unit | [BambuLab A1 Mini](https://bambulab.com/en/a1-mini) |

## Notes and tips
- Video comparison of [6V solenoid with 12V](https://www.reddit.com/r/GPDL/comments/1laafjl/nerd_stuff_comparison_of_prometheus_82_on_6v_and/) filmed at 1000 FPS and tips on power supply
- For a 6V solenoid, you should set the power supply to 9V, for a 12V solenoid, you should set the power supply to 15V, this guarantees stable results when testing
- Video about the [solenoid's own delays](https://www.reddit.com/r/GPDL/comments/1kv7ys9/i_finally_bought_a_camera_that_can_record_1000/) and how it is reflected in the measurements at 1000 FPS
- Prometheus 82 has its own delays that are not compensated for after the test is completed. For buttons, it's an additional ~0.2-0.7ms, for joysticks it's ~3-4ms.
- Both ports of the control board use Type-C interfaces, so do not confuse them, remember that the lower port is used for power, and the upper port is used to connect to a PC.
- The movement of the solenoid should be easy, it should not cling to the inner hole. Make sure that its leg is smooth and free of snags, as this can cause friction, which increases heat, wear and tear on the component and introduces an error in the measurement.
- Distance matters. When positioning the gamepad during tests, you need to install the stick and button as far away from the sensor as possible so that the solenoid has time to accelerate sufficiently. If you install the solenoid too close, it will give incorrect measurement results.
- Over time, the solenoid can degrade, especially if it is frequently overheated. Therefore, it is worth getting a separate control gamepad (with stable firmware) to periodically check if the delay has changed.
- When conducting tests, you should do it at least 2 times. It is better to recalibrate the position of the gamepad on the stand before the second test to avoid positioning errors.
- Some Chinese Arduino devices may not work well with the button press detection function (voltage drop on D3), if something does not work, it may be worth replacing the Arduino board.
- Currently, the permissible error of the Prometheus 82 tester is ±0.69 ms (when testing sticks).

## License
This project is licensed under the Prometheus 82 License. 

- **For enthusiasts and bloggers**: You may use the Prometheus 82 Tester for non-commercial purposes (e.g., videos, posts, reviews) free of charge, provided you include a prominent notice crediting "Prometheus 82 by John Punch" and a link to https://gamepadla.com in your content.
- **For commercial use**: Corporations or organizations wishing to use the tester for commercial purposes, such as testing gamepads and publishing results, must contact the author at john@gamepadla.com to negotiate a commercial license. Commercial use without a prior agreement is prohibited.

See the [LICENSE](LICENSE) file for details.

## Contact
john@gamepadla.com

## Donation
Gamepadla is not a commercial project, and its development is based solely on the author's enthusiasm. If you want to support me, please do so at https://ko-fi.com/gamepadla
