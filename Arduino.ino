const int CONTACT_PIN = 3;
const int SOLENOID_PIN = 2;
unsigned long PULSE_DURATION_US = 40000;

volatile bool windowActive = false, contactDetected = false, solenoidActive = false, secondContactDetected = false;
volatile unsigned long solenoidStartTime_us = 0, firstContactTime_us = 0;
const unsigned long BLIND_WINDOW_US = 1500;

void handleContact() {
    if (!windowActive) return;
    unsigned long now = micros();
    if (!contactDetected) {
        Serial.write('S');
        contactDetected = true;
        firstContactTime_us = now;
        return;
    }
    if (!secondContactDetected && (now - firstContactTime_us >= BLIND_WINDOW_US)) {
        Serial.write('F');
        secondContactDetected = true;
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(CONTACT_PIN, INPUT_PULLUP);
    pinMode(SOLENOID_PIN, OUTPUT);
    
    attachInterrupt(digitalPinToInterrupt(CONTACT_PIN), handleContact, FALLING);
    
    for (int i = 0; i < 3; i++) {
        digitalWrite(SOLENOID_PIN, HIGH);
        delay(PULSE_DURATION_US / 1000);
        digitalWrite(SOLENOID_PIN, LOW);
        delay(200);
    }
    
    Serial.write('R');
}

void loop() {
    if (Serial.available() > 0) {
        char cmd = Serial.read();
        
        // Fast handling of 'D' command for delay test
        if (cmd == 'D') {
            Serial.write('R');
            return; // Exit to avoid further checks
        }
        
        // Other commands are processed as before
        if (cmd == 'T') {
            contactDetected = false;
            secondContactDetected = false;
            digitalWrite(SOLENOID_PIN, HIGH);
            solenoidStartTime_us = micros();
            solenoidActive = true;
            windowActive = true;
        }
        else if (cmd == 'P') {
            unsigned long startTime = millis();
            while (Serial.available() < 2 && (millis() - startTime) < 50) {
                ;
            }
            if (Serial.available() >= 2) {
                unsigned long duration_ms = (Serial.read() << 8) | Serial.read();
                PULSE_DURATION_US = duration_ms * 1000;
                Serial.write('A');
            }
            while (Serial.available() > 0) {
                Serial.read();
            }
        }
    }

    if (solenoidActive && (micros() - solenoidStartTime_us >= PULSE_DURATION_US)) {
        digitalWrite(SOLENOID_PIN, LOW);
        solenoidActive = false;
    }
}
